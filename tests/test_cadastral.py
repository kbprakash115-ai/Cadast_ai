"""
Automated Test Suite for CadastralAI.
Tests models, tiled inference, vectorization, topology validation, and GIS layer exports.
"""

import os
import unittest
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, box
import geopandas as gpd

from cadastral_ai.models import CadastralModelEngine, get_model_path
from cadastral_ai.vectorizer import orthogonalize_polygon, compute_polygon_dimensions
from cadastral_ai.topology import clean_geometries, resolve_parcel_overlaps
from cadastral_ai.pipeline import CadastralPipeline
from cadastral_ai.sample_data import generate_sample_drone_data

class TestCadastralAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = "test_run_temp"
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.ori, cls.dsm, cls.gnss = generate_sample_drone_data(cls.test_dir, size_px=512)

    def test_01_models_cpu_inference(self):
        """Verify ONNX models execute cleanly on CPU with bounded memory."""
        engine = CadastralModelEngine(num_threads=2)
        dummy_tile = np.random.rand(3, 256, 256).astype(np.float32)
        
        bld_pred = engine.predict('buildings', dummy_tile)
        self.assertEqual(bld_pred.shape, (1, 256, 256))
        self.assertTrue(0.0 <= bld_pred.min() <= bld_pred.max() <= 1.0)
        
        road_pred = engine.predict('roads', dummy_tile)
        self.assertEqual(road_pred.shape, (1, 256, 256))
        
        lu_pred = engine.predict('landuse', dummy_tile)
        self.assertEqual(lu_pred.shape, (6, 256, 256))

    def test_02_orthogonalization_regularizer(self):
        """Verify building 90-degree corner regularizer."""
        # Create a slightly jittered rectangle
        jittered = Polygon([
            (0.0, 0.0), (10.2, 0.1), (10.1, 8.1), (-0.1, 7.9), (0.0, 0.0)
        ])
        ortho = orthogonalize_polygon(jittered)
        self.assertTrue(ortho.is_valid)
        self.assertFalse(ortho.is_empty)
        length, width = compute_polygon_dimensions(ortho)
        self.assertGreater(length, width)
        self.assertAlmostEqual(length, 10.0, delta=1.0)
        self.assertAlmostEqual(width, 8.0, delta=1.0)

    def test_03_topology_planar_partition(self):
        """Verify that overlapping parcels are topologically clipped with zero overlap."""
        poly1 = box(0, 0, 10, 10)
        poly2 = box(5, 0, 15, 10) # 50% overlap with poly1
        gdf = gpd.GeoDataFrame({
            'id': ['P1', 'P2'],
            'area_sqm': [100.0, 100.0],
            'geometry': [poly1, poly2]
        }, crs="EPSG:3857")
        
        cleaned = resolve_parcel_overlaps(gdf)
        # Verify intersection area is zero
        p1_res = cleaned.iloc[0].geometry
        p2_res = cleaned.iloc[1].geometry
        self.assertAlmostEqual(p1_res.intersection(p2_res).area, 0.0, places=3)

    def test_04_full_pipeline_and_gpkg_export(self):
        """Verify full pipeline run and validate attribute schema in GeoPackage."""
        pipeline = CadastralPipeline(num_threads=2, tile_size=256, overlap=32)
        out_dir = os.path.join(self.test_dir, "pipeline_out")
        
        results = pipeline.run(
            ori_path=self.ori,
            dsm_path=self.dsm,
            gnss_path=self.gnss,
            output_dir=out_dir
        )
        
        gpkg_path = results['gpkg_path']
        self.assertTrue(os.path.exists(gpkg_path))
        
        # Verify layers
        for layer_name in ['buildings', 'roads', 'parcels', 'land_use']:
            layer_gdf = gpd.read_file(gpkg_path, layer=layer_name)
            self.assertFalse(layer_gdf.empty, f"Layer {layer_name} should not be empty")
            # Verify CRS is preserved
            self.assertEqual(str(layer_gdf.crs), "EPSG:3857")
            
        # Verify required attribute columns on parcels
        parcels_gdf = gpd.read_file(gpkg_path, layer='parcels')
        required_cols = ['id', 'class', 'confidence', 'area_sqm', 'perimeter_m', 'length_m', 'width_m', 'geometry']
        for col in required_cols:
            self.assertIn(col, parcels_gdf.columns, f"Column '{col}' missing from parcels layer")
            
        # Verify positive metrics
        self.assertTrue((parcels_gdf['area_sqm'] > 0).all())
        self.assertTrue((parcels_gdf['perimeter_m'] > 0).all())
        self.assertTrue((parcels_gdf['length_m'] > 0).all())
        self.assertTrue((parcels_gdf['width_m'] > 0).all())

if __name__ == "__main__":
    unittest.main()
