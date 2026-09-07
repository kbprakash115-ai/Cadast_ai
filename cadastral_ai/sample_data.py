"""
Sample Geospatial Drone Dataset Generator for Cadastral AI.
Generates realistic high-resolution:
  - Drone ORI GeoTIFF (RGB orthomosaic)
  - Co-registered DSM GeoTIFF (Digital Surface Model)
  - Cadastral Ground Truth / GNSS survey pegs (GeoJSON)
Allows instant testing and demonstration without requiring external files.
"""

import os
import math
import numpy as np
import rasterio
from rasterio.transform import from_origin
import geopandas as gpd
from shapely.geometry import Point

def generate_sample_drone_data(output_dir: str = "sample_data", size_px: int = 1024, resolution_m: float = 0.2):
    """
    Generates a realistic synthetic drone cadastral scene:
    Orthomosaic + DSM + GNSS survey pegs.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ori_path = os.path.join(output_dir, "drone_ori.tif")
    dsm_path = os.path.join(output_dir, "drone_dsm.tif")
    gnss_path = os.path.join(output_dir, "gnss_survey_pegs.geojson")
    
    # Coordinate system: UTM Zone 43N (EPSG:32643) or Web Mercator (EPSG:3857)
    # Using EPSG:3857 for seamless global map display
    crs = "EPSG:3857"
    origin_x = 8500000.0
    origin_y = 2100000.0
    transform = from_origin(origin_x, origin_y, resolution_m, resolution_m)
    
    # 1. Base Landscape Canvas: Farmland / Grass
    # Background: Greenish grass / agricultural loam
    r_band = np.full((size_px, size_px), 110, dtype=np.uint8)
    g_band = np.full((size_px, size_px), 145, dtype=np.uint8)
    b_band = np.full((size_px, size_px), 85, dtype=np.uint8)
    
    # Elevation: Base terrain elevation = 100.0 m
    dsm = np.full((size_px, size_px), 100.0, dtype=np.float32)
    # Slight terrain slope
    x_coords, y_coords = np.meshgrid(np.arange(size_px), np.arange(size_px))
    dsm += (x_coords * 0.002 + y_coords * 0.003).astype(np.float32)
    
    # Add agricultural field texture
    noise = (np.random.rand(size_px, size_px) * 20 - 10).astype(np.int16)
    r_band = np.clip(r_band.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    g_band = np.clip(g_band.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    b_band = np.clip(b_band.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # 2. Roads / Street Network (Right-of-Way)
    # Vertical main avenue: col 480 to 544 (width ~ 12m)
    road_mask = np.zeros((size_px, size_px), dtype=bool)
    road_mask[:, 480:544] = True
    
    # Horizontal street: row 480 to 530 (width ~ 10m)
    road_mask[480:530, :] = True
    
    # Secondary pathway: col 200 to 220, row 0 to 480
    road_mask[:480, 200:225] = True
    
    # Road appearance: Grey asphalt
    r_band[road_mask] = 130
    g_band[road_mask] = 130
    b_band[road_mask] = 135
    
    # 3. Tree Clusters / Green Belts
    tree_mask = np.zeros((size_px, size_px), dtype=bool)
    # Tree grove top right
    t_y, t_x = np.ogrid[:size_px, :size_px]
    tree_dist = np.sqrt((t_x - 850)**2 + (t_y - 200)**2)
    tree_mask[tree_dist < 80] = True
    
    r_band[tree_mask] = 35
    g_band[tree_mask] = 115
    b_band[tree_mask] = 40
    dsm[tree_mask] += 5.5 # Trees are elevated by ~5.5m
    
    # 4. Building Footprints (Cadastral Structures)
    # Structured layouts with distinct architectural footprints
    buildings_specs = [
        # (r_min, r_max, c_min, c_max, roof_type)
        (100, 220, 80, 180, "terracotta"),
        (280, 420, 70, 170, "tin"),
        (120, 260, 260, 420, "concrete"),
        (310, 430, 270, 430, "terracotta"),
        (580, 720, 100, 250, "tin"),
        (760, 920, 90, 230, "concrete"),
        (590, 740, 290, 430, "terracotta"),
        (780, 930, 300, 440, "tin"),
        (120, 280, 580, 720, "concrete"),
        (330, 440, 600, 750, "terracotta"),
        (580, 750, 590, 760, "tin"),
        (800, 950, 600, 740, "concrete"),
        (600, 740, 800, 950, "terracotta"),
        (780, 920, 810, 940, "tin")
    ]
    
    gnss_points = []
    peg_id = 1
    
    for r1, r2, c1, c2, roof_type in buildings_specs:
        b_slice = (slice(r1, r2), slice(c1, c2))
        if roof_type == "terracotta":
            r_band[b_slice] = 185
            g_band[b_slice] = 70
            b_band[b_slice] = 55
        elif roof_type == "tin":
            r_band[b_slice] = 200
            g_band[b_slice] = 205
            b_band[b_slice] = 210
        else: # concrete
            r_band[b_slice] = 160
            g_band[b_slice] = 160
            b_band[b_slice] = 165
            
        # Buildings are elevated in DSM by 4.0 - 7.5 m
        dsm[b_slice] += 6.5
        
        # Place sample GNSS boundary pegs near property corners
        p_corners = [(r1 - 15, c1 - 15), (r2 + 15, c2 + 15)]
        for pr, pc in p_corners:
            if 0 <= pr < size_px and 0 <= pc < size_px:
                gx, gy = rasterio.transform.xy(transform, pr, pc)
                gnss_points.append({
                    "id": f"PEG_{peg_id:03d}",
                    "type": "boundary_marker",
                    "geometry": Point(gx, gy)
                })
                peg_id += 1

    # 5. Write Drone ORI GeoTIFF
    ori_profile = {
        'driver': 'GTiff',
        'height': size_px,
        'width': size_px,
        'count': 3,
        'dtype': rasterio.uint8,
        'crs': crs,
        'transform': transform,
        'compress': 'deflate'
    }
    with rasterio.open(ori_path, 'w', **ori_profile) as dst:
        dst.write(r_band, 1)
        dst.write(g_band, 2)
        dst.write(b_band, 3)
        
    # 6. Write DSM GeoTIFF
    dsm_profile = {
        'driver': 'GTiff',
        'height': size_px,
        'width': size_px,
        'count': 1,
        'dtype': rasterio.float32,
        'crs': crs,
        'transform': transform,
        'compress': 'deflate'
    }
    with rasterio.open(dsm_path, 'w', **dsm_profile) as dst:
        dst.write(dsm, 1)
        
    # 7. Write GNSS survey pegs GeoJSON
    gnss_gdf = gpd.GeoDataFrame(gnss_points, crs=crs)
    gnss_gdf = gnss_gdf.to_crs("EPSG:4326") # Save in WGS84 for broad compatibility
    gnss_gdf.to_file(gnss_path, driver="GeoJSON")
    
    print(f"[OK] Sample drone dataset created in '{output_dir}':")
    print(f"     ORI:  {ori_path}")
    print(f"     DSM:  {dsm_path}")
    print(f"     GNSS: {gnss_path} ({len(gnss_gdf)} survey pegs)")
    return ori_path, dsm_path, gnss_path

if __name__ == "__main__":
    generate_sample_drone_data()
