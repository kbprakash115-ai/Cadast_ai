"""
Master Cadastral Pipeline Orchestrator.
Executes end-to-end workflow:
  Drone ORI GeoTIFF -> Tiled AI Inference -> Segmentation -> Vectorization ->
  Topology Validation -> Multi-Layer GeoPackage & GeoJSON Outputs.
"""

import os
import time
import json
import logging
import rasterio
import geopandas as gpd

from .models import CadastralModelEngine
from .inference import TiledInferenceEngine
from .vectorizer import vectorize_buildings, vectorize_roads, vectorize_landuse
from .parcel_delineator import delineate_parcels
from .topology import validate_and_repair_layers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cadastral_ai.pipeline")

class CadastralPipeline:
    """
    Complete end-to-end CPU-friendly Cadastral AI pipeline for low-end PCs.
    """
    def __init__(
        self,
        num_threads: int = 2,
        tile_size: int = 512,
        overlap: int = 64,
        orthogonalize_buildings: bool = True,
        progress_callback = None
    ):
        self.num_threads = num_threads
        self.tile_size = tile_size
        self.overlap = overlap
        self.orthogonalize_buildings = orthogonalize_buildings
        self.progress_callback = progress_callback
        
        # Initialize ONNX CPU engine
        self.model_engine = CadastralModelEngine(num_threads=num_threads)
        self.inference_engine = TiledInferenceEngine(
            model_engine=self.model_engine,
            tile_size=tile_size,
            overlap=overlap,
            progress_callback=progress_callback
        )

    def run(
        self,
        ori_path: str,
        dsm_path: str = None,
        dtm_path: str = None,
        gnss_path: str = None,
        existing_parcels_path: str = None,
        output_dir: str = "output",
        building_threshold: float = 0.50,
        road_threshold: float = 0.45,
        min_building_area: float = 15.0,
        min_parcel_area: float = 80.0,
        snap_tolerance_m: float = 2.0
    ) -> dict:
        """
        Executes the cadastral mapping pipeline.
        
        Args:
            ori_path: Path to Drone Orthorectified Imagery GeoTIFF
            dsm_path: Optional path to DSM GeoTIFF
            dtm_path: Optional path to DTM GeoTIFF
            gnss_path: Optional path to GNSS survey pegs (GeoJSON/CSV)
            existing_parcels_path: Optional path to existing parcels GIS
            output_dir: Directory to save GeoPackage and GeoJSON outputs
            
        Returns:
            dict containing processed GeoDataFrames and summary metadata
        """
        start_time = time.time()
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(ori_path):
            raise FileNotFoundError(f"Input ORI GeoTIFF not found: {ori_path}")
            
        logger.info(f"--- Starting Cadastral AI Pipeline for: {ori_path} ---")
        
        # Load optional GNSS survey pegs
        gnss_gdf = None
        if gnss_path and os.path.exists(gnss_path):
            try:
                if gnss_path.endswith('.csv'):
                    import pandas as pd
                    df = pd.read_csv(gnss_path)
                    # Support common lat/lon column names
                    lon_col = next((c for c in df.columns if c.lower() in ['lon', 'longitude', 'x']), None)
                    lat_col = next((c for c in df.columns if c.lower() in ['lat', 'latitude', 'y']), None)
                    if lon_col and lat_col:
                        gnss_gdf = gpd.GeoDataFrame(
                            df,
                            geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
                            crs="EPSG:4326"
                        )
                else:
                    gnss_gdf = gpd.read_file(gnss_path)
                logger.info(f"Loaded {len(gnss_gdf)} GNSS survey pegs.")
            except Exception as e:
                logger.warning(f"Could not load GNSS pegs: {e}")

        # Stage 1: Tiled AI Inference
        if self.progress_callback:
            self.progress_callback(10, 100, "Starting Tiled AI Inference...")
            
        inf_result = self.inference_engine.run_inference(
            ori_path=ori_path,
            dsm_path=dsm_path,
            dtm_path=dtm_path,
            tasks=['buildings', 'roads', 'landuse']
        )
        
        meta = inf_result['meta']
        transform = meta['transform']
        crs = meta['crs']
        width = meta['width']
        height = meta['height']
        
        # Bounding box of survey area in map CRS
        with rasterio.open(ori_path) as src:
            bounds = src.bounds
            raster_extent = (bounds.left, bounds.bottom, bounds.right, bounds.top)

        # Stage 2: Vectorization
        if self.progress_callback:
            self.progress_callback(50, 100, "Vectorizing Buildings & Regularizing Geometry...")
            
        buildings_gdf = vectorize_buildings(
            prob_map=inf_result['buildings_prob'],
            transform=transform,
            crs=crs,
            threshold=building_threshold,
            min_area_sqm=min_building_area,
            orthogonalize=self.orthogonalize_buildings
        )

        if self.progress_callback:
            self.progress_callback(65, 100, "Skeletonizing Roads & Extracting Network Graph...")
            
        roads_gdf = vectorize_roads(
            prob_map=inf_result['roads_prob'],
            transform=transform,
            crs=crs,
            threshold=road_threshold
        )

        if self.progress_callback:
            self.progress_callback(75, 100, "Classifying Land Use Polygons...")
            
        landuse_gdf = vectorize_landuse(
            landuse_map=inf_result['landuse_map'],
            transform=transform,
            crs=crs
        )

        if self.progress_callback:
            self.progress_callback(85, 100, "Delineating Cadastral Parcel Boundaries...")
            
        parcels_gdf = delineate_parcels(
            raster_bounds=raster_extent,
            crs=crs,
            roads_gdf=roads_gdf,
            buildings_gdf=buildings_gdf,
            gnss_points_gdf=gnss_gdf,
            min_parcel_area_sqm=min_parcel_area,
            snap_tolerance_m=snap_tolerance_m
        )

        # Stage 3: Topology Validation & Planar Partitioning
        if self.progress_callback:
            self.progress_callback(90, 100, "Validating Topology & Planar Integrity...")
            
        cleaned_layers = validate_and_repair_layers(
            buildings_gdf=buildings_gdf,
            roads_gdf=roads_gdf,
            parcels_gdf=parcels_gdf,
            landuse_gdf=landuse_gdf,
            target_crs=crs
        )

        # Stage 4: GIS Output Export (GeoPackage & GeoJSON)
        if self.progress_callback:
            self.progress_callback(95, 100, "Exporting GeoPackage & GeoJSON outputs...")
            
        gpkg_path = os.path.join(output_dir, "cadastral_output.gpkg")
        
        # Write layers to GeoPackage with spatial indices
        for layer_name, gdf in cleaned_layers.items():
            if gdf is not None and not gdf.empty:
                # Mode: 'w' for first layer, 'a' for subsequent
                mode = 'w' if layer_name == "buildings" else 'a'
                gdf.to_file(gpkg_path, layer=layer_name, driver="GPKG", engine="pyogrio")
                
                # Also save standard GeoJSON
                geojson_path = os.path.join(output_dir, f"{layer_name}.geojson")
                # Ensure GeoJSON is exported in WGS84 EPSG:4326 for web compatibility
                gdf_wgs84 = gdf.to_crs("EPSG:4326")
                gdf_wgs84.to_file(geojson_path, driver="GeoJSON")
                logger.info(f"Exported layer [{layer_name}]: {len(gdf)} features -> {geojson_path}")

        # Compute summary metrics
        total_bld_area = float(cleaned_layers['buildings']['area_sqm'].sum()) if not cleaned_layers['buildings'].empty else 0.0
        total_road_len_km = float(cleaned_layers['roads']['length_m'].sum() / 1000.0) if not cleaned_layers['roads'].empty else 0.0
        total_parcel_area_ha = float(cleaned_layers['parcels']['area_sqm'].sum() / 10000.0) if not cleaned_layers['parcels'].empty else 0.0
        
        summary = {
            "processing_time_seconds": round(time.time() - start_time, 2),
            "input_file": os.path.abspath(ori_path),
            "dimensions_px": f"{width}x{height}",
            "crs": str(crs),
            "counts": {
                "buildings": len(cleaned_layers['buildings']),
                "roads": len(cleaned_layers['roads']),
                "parcels": len(cleaned_layers['parcels']),
                "land_use_polygons": len(cleaned_layers['land_use'])
            },
            "metrics": {
                "total_building_footprint_sqm": round(total_bld_area, 2),
                "total_road_network_km": round(total_road_len_km, 3),
                "total_parcel_area_hectares": round(total_parcel_area_ha, 3),
            },
            "outputs": {
                "geopackage": os.path.abspath(gpkg_path),
                "buildings_geojson": os.path.abspath(os.path.join(output_dir, "buildings.geojson")),
                "roads_geojson": os.path.abspath(os.path.join(output_dir, "roads.geojson")),
                "parcels_geojson": os.path.abspath(os.path.join(output_dir, "parcels.geojson")),
                "landuse_geojson": os.path.abspath(os.path.join(output_dir, "land_use.geojson"))
            }
        }
        
        summary_path = os.path.join(output_dir, "cadastral_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        if self.progress_callback:
            self.progress_callback(100, 100, "Cadastral Extraction Completed Successfully!")
            
        logger.info(f"Pipeline complete in {summary['processing_time_seconds']}s. GeoPackage at: {gpkg_path}")
        
        return {
            "layers": cleaned_layers,
            "summary": summary,
            "gpkg_path": gpkg_path
        }
