"""
Topology Validation and Cadastral Planar Partitioning Engine.
Ensures geometric correctness according to cadastral GIS standards:
  - make_valid repairs
  - Sliver polygon elimination
  - Overlap resolution (strict planar partition: no overlapping parcels)
  - Coordinate Reference System (CRS) preservation
"""

import logging
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.validation import make_valid
from shapely.ops import unary_union
import geopandas as gpd

logger = logging.getLogger("cadastral_ai.topology")

def clean_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Repairs invalid geometries and removes empty/degenerate shapes using make_valid.
    """
    if gdf is None or gdf.empty:
        return gdf

    cleaned_records = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
            
        if not geom.is_valid:
            geom = make_valid(geom)
            
        if geom.geom_type in ['Polygon', 'MultiPolygon', 'LineString', 'MultiLineString']:
            row_copy = row.copy()
            row_copy.geometry = geom
            cleaned_records.append(row_copy)
            
    if not cleaned_records:
        return gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
        
    return gpd.GeoDataFrame(cleaned_records, crs=gdf.crs).reset_index(drop=True)

def remove_sliver_polygons(gdf: gpd.GeoDataFrame, min_area: float = 20.0, min_compactness: float = 0.01) -> gpd.GeoDataFrame:
    """
    Eliminates slivers: tiny or extremely narrow artifact polygons.
    Compactness = 4 * pi * Area / Perimeter^2
    """
    if gdf is None or gdf.empty:
        return gdf

    valid_rows = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
            
        area = geom.area
        perimeter = geom.length
        
        if area < min_area:
            continue
            
        if perimeter > 0:
            compactness = (4.0 * 3.14159265 * area) / (perimeter * perimeter)
            if compactness < min_compactness:
                continue
                
        valid_rows.append(row)

    if not valid_rows:
        return gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
        
    return gpd.GeoDataFrame(valid_rows, crs=gdf.crs).reset_index(drop=True)

def resolve_parcel_overlaps(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Enforces cadastral planar partition: No two parcels may legally overlap.
    Resolves overlaps sequentially by clipping lower-confidence or smaller parcels.
    """
    if gdf is None or len(gdf) <= 1:
        return gdf

    # Sort by area descending
    sorted_gdf = gdf.sort_values(by='area_sqm', ascending=False).reset_index(drop=True)
    
    resolved_geoms = []
    covered_union = None
    
    for idx, row in sorted_gdf.iterrows():
        geom = row.geometry
        if covered_union is None:
            resolved_geoms.append(geom)
            covered_union = geom
        else:
            if geom.intersects(covered_union):
                diff = geom.difference(covered_union)
                if diff.is_empty or diff.area < 10.0:
                    continue
                if diff.geom_type == 'MultiPolygon':
                    diff = max(diff.geoms, key=lambda p: p.area)
                if diff.geom_type == 'Polygon' and diff.area >= 10.0:
                    resolved_geoms.append(diff)
                    covered_union = unary_union([covered_union, diff])
            else:
                resolved_geoms.append(geom)
                covered_union = unary_union([covered_union, geom])
                
    result_gdf = sorted_gdf.iloc[:len(resolved_geoms)].copy()
    result_gdf.geometry = resolved_geoms
    # Recalculate area and perimeter after overlap clipping
    result_gdf['area_sqm'] = result_gdf.geometry.apply(lambda g: round(g.area, 2))
    result_gdf['perimeter_m'] = result_gdf.geometry.apply(lambda g: round(g.length, 2))
    return result_gdf.reset_index(drop=True)

def validate_and_repair_layers(
    buildings_gdf: gpd.GeoDataFrame,
    roads_gdf: gpd.GeoDataFrame,
    parcels_gdf: gpd.GeoDataFrame,
    landuse_gdf: gpd.GeoDataFrame,
    target_crs
) -> dict:
    """
    Runs topological validation across all output layers, repairs defects,
    ensures CRS consistency, and prepares layers for GIS export.
    """
    logger.info("Running topological validation and planar partitioning...")
    
    # 1. Clean Buildings
    if buildings_gdf is not None and not buildings_gdf.empty:
        buildings_gdf = clean_geometries(buildings_gdf)
        buildings_gdf = remove_sliver_polygons(buildings_gdf, min_area=15.0)
        buildings_gdf = buildings_gdf.to_crs(target_crs)

    # 2. Clean Roads
    if roads_gdf is not None and not roads_gdf.empty:
        roads_gdf = clean_geometries(roads_gdf)
        roads_gdf = roads_gdf.to_crs(target_crs)

    # 3. Clean and Planar-Partition Parcels
    if parcels_gdf is not None and not parcels_gdf.empty:
        parcels_gdf = clean_geometries(parcels_gdf)
        parcels_gdf = remove_sliver_polygons(parcels_gdf, min_area=80.0)
        parcels_gdf = resolve_parcel_overlaps(parcels_gdf)
        parcels_gdf = parcels_gdf.to_crs(target_crs)

    # 4. Clean Land Use
    if landuse_gdf is not None and not landuse_gdf.empty:
        landuse_gdf = clean_geometries(landuse_gdf)
        landuse_gdf = remove_sliver_polygons(landuse_gdf, min_area=30.0)
        landuse_gdf = landuse_gdf.to_crs(target_crs)

    return {
        "buildings": buildings_gdf,
        "roads": roads_gdf,
        "parcels": parcels_gdf,
        "land_use": landuse_gdf
    }
