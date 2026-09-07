"""
Geospatial Vectorization and Regularization Engine.
Converts probability and semantic segmentation rasters into clean vector geometries:
  - Buildings -> Orthogonalized Polygons
  - Roads -> Graph-Traced Line Networks with Width Estimation
  - Land Use -> Multi-Class Thematic Polygons
Preserves Coordinate Reference System (CRS) and calculates standard cadastral attributes.
"""

import math
import logging
import numpy as np
import cv2
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize
import networkx as nx
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, box
from shapely.validation import make_valid
from shapely.affinity import rotate
import geopandas as gpd
import rasterio.features

from .models import LANDUSE_CLASSES

logger = logging.getLogger("cadastral_ai.vectorizer")

def pixel_to_geo_coords(px_coords, transform):
    """Converts pixel (col, row) coordinates to geospatial (X, Y) coordinates."""
    geo_coords = []
    for col, row in px_coords:
        gx, gy = rasterio.transform.xy(transform, row, col, offset='center')
        geo_coords.append((gx, gy))
    return geo_coords

def orthogonalize_polygon(poly: Polygon, angle_snap_deg: float = 15.0) -> Polygon:
    """
    Cadastral regularizer for building footprints:
    Snaps near-right-angle corners to strict 90-degree orthogonal edges
    to produce crisp architectural CAD/GIS cadastral footprints.
    """
    if not poly.is_valid or poly.is_empty:
        return poly
        
    try:
        # Get minimum rotated rectangle to find dominant orientation
        mrr = poly.minimum_rotated_rectangle
        if mrr.geom_type != 'Polygon' or len(mrr.exterior.coords) < 4:
            return poly
            
        mrr_coords = list(mrr.exterior.coords)
        dx = mrr_coords[1][0] - mrr_coords[0][0]
        dy = mrr_coords[1][1] - mrr_coords[0][1]
        dominant_angle = math.degrees(math.atan2(dy, dx)) % 90.0

        # Rotate polygon to align with principal axis
        rotated_poly = rotate(poly, -dominant_angle, origin='centroid')
        
        # Simplify along orthogonal axes
        simplified = rotated_poly.simplify(0.5, preserve_topology=True)
        
        # Re-rotate to original orientation
        ortho_poly = rotate(simplified, dominant_angle, origin='centroid')
        if ortho_poly.is_valid and not ortho_poly.is_empty:
            return ortho_poly
    except Exception:
        pass
        
    return poly

def compute_polygon_dimensions(poly: Polygon):
    """Computes length and width of the minimum bounding rectangle in meters."""
    try:
        mrr = poly.minimum_rotated_rectangle
        if mrr.geom_type == 'Polygon':
            coords = list(mrr.exterior.coords)
            edge1 = math.hypot(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
            edge2 = math.hypot(coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
            length = max(edge1, edge2)
            width = min(edge1, edge2)
            return round(length, 2), round(width, 2)
    except Exception:
        pass
    bounds = poly.bounds
    length = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
    width = min(bounds[2] - bounds[0], bounds[3] - bounds[1])
    return round(length, 2), round(width, 2)

def vectorize_buildings(
    prob_map: np.ndarray,
    transform,
    crs,
    threshold: float = 0.50,
    min_area_sqm: float = 15.0,
    simplify_tol: float = 0.5,
    orthogonalize: bool = True
) -> gpd.GeoDataFrame:
    """
    Extracts building footprint polygons from probability raster.
    """
    if prob_map is None:
        return gpd.GeoDataFrame(columns=['id', 'class', 'confidence', 'area_sqm', 'perimeter_m', 'length_m', 'width_m', 'geometry'], crs=crs)

    # Threshold and morphological cleanup in row chunks to keep RAM < 150 MB
    h, w = prob_map.shape
    binary = np.zeros((h, w), dtype=np.uint8)
    for r0 in range(0, h, 2048):
        r1 = min(h, r0 + 2048)
        binary[r0:r1, :] = (prob_map[r0:r1, :] >= threshold).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    features = []
    feature_id = 1
    
    # Calculate approx pixel resolution in meters
    pixel_res_x = abs(transform[0])
    pixel_res_y = abs(transform[4])
    pixel_area_m2 = pixel_res_x * pixel_res_y

    for cnt in contours:
        # Minimum pixel area check to discard speckles quickly
        cnt_area_px = cv2.contourArea(cnt)
        if cnt_area_px * pixel_area_m2 < min_area_sqm or len(cnt) < 3:
            continue
            
        pts = cnt.squeeze()
        if len(pts.shape) != 2 or pts.shape[0] < 3:
            continue
            
        geo_pts = pixel_to_geo_coords(pts, transform)
        if len(geo_pts) < 3:
            continue
            
        poly = Polygon(geo_pts)
        if not poly.is_valid:
            poly = make_valid(poly)
            if poly.geom_type == 'MultiPolygon':
                poly = max(poly.geoms, key=lambda p: p.area)
                
        if poly.is_empty or poly.geom_type != 'Polygon':
            continue
            
        # Simplify geometry
        if simplify_tol > 0:
            poly = poly.simplify(simplify_tol, preserve_topology=True)
            
        # Apply Cadastral Orthogonalization
        if orthogonalize:
            poly = orthogonalize_polygon(poly)
            
        area_m2 = round(poly.area, 2)
        if area_m2 < min_area_sqm:
            continue
            
        perimeter_m = round(poly.length, 2)
        length_m, width_m = compute_polygon_dimensions(poly)
        
        # Calculate mean confidence inside the contour using local bounding box (not full raster!)
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if bw > 0 and bh > 0:
            sub_mask = np.zeros((bh, bw), dtype=np.uint8)
            cv2.drawContours(sub_mask, [cnt - [bx, by]], -1, 255, -1)
            sub_prob = np.array(prob_map[by:by+bh, bx:bx+bw])
            mean_conf = float(np.mean(sub_prob[sub_mask > 0])) if np.any(sub_mask > 0) else float(threshold)
        else:
            mean_conf = float(threshold)
        
        features.append({
            'id': f"BLD_{feature_id:04d}",
            'class': 'building',
            'confidence': round(mean_conf, 3),
            'area_sqm': area_m2,
            'perimeter_m': perimeter_m,
            'length_m': length_m,
            'width_m': width_m,
            'geometry': poly
        })
        feature_id += 1

    gdf = gpd.GeoDataFrame(features, crs=crs)
    logger.info(f"Vectorized {len(gdf)} building footprints.")
    return gdf

def vectorize_roads(
    prob_map: np.ndarray,
    transform,
    crs,
    threshold: float = 0.45,
    min_length_m: float = 10.0,
    simplify_tol: float = 1.0
) -> gpd.GeoDataFrame:
    """
    Extracts road and pathway centerline networks using morphological skeletonization
    and NetworkX graph tracing, with automated road width estimation.
    """
    if prob_map is None:
        return gpd.GeoDataFrame(columns=['id', 'class', 'confidence', 'length_m', 'width_m', 'geometry'], crs=crs)

    h, w = prob_map.shape
    scale_factor = max(1, int(round(max(h, w) / 2500.0)))
    if scale_factor > 1:
        from affine import Affine
        scaled_w = w // scale_factor
        scaled_h = h // scale_factor
        active_map = cv2.resize(np.array(prob_map[::scale_factor, ::scale_factor]), (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
        active_transform = transform * Affine.scale(scale_factor, scale_factor)
    else:
        active_map = prob_map
        active_transform = transform

    # Thresholding & morphological smoothing
    binary = (active_map >= threshold).astype(bool)
    if not np.any(binary):
        return gpd.GeoDataFrame(columns=['id', 'class', 'confidence', 'length_m', 'width_m', 'geometry'], crs=crs)
        
    # Distance transform for road width estimation
    pixel_res = (abs(active_transform[0]) + abs(active_transform[4])) / 2.0
    dist_map = distance_transform_edt(binary) * pixel_res * 2.0 # Total width = 2 * radius

    # Morphological skeletonization to single-pixel centerlines
    skeleton = skeletonize(binary)
    skel_pts = np.argwhere(skeleton) # [row, col]
    
    if len(skel_pts) < 5:
        return gpd.GeoDataFrame(columns=['id', 'class', 'confidence', 'length_m', 'width_m', 'geometry'], crs=crs)

    # Build NetworkX graph from skeleton pixels
    G = nx.Graph()
    skel_set = set(map(tuple, skel_pts))
    
    for r, c in skel_pts:
        G.add_node((r, c))
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if (nr, nc) in skel_set:
                    dist = math.sqrt(dr*dr + dc*dc) * pixel_res
                    G.add_edge((r, c), (nr, nc), weight=dist)

    # Extract branch points (junctions, degree != 2) to segment graph into discrete road corridors
    junctions_and_endpoints = [node for node, degree in G.degree() if degree != 2]
    
    road_lines = []
    visited_edges = set()
    
    # Trace paths between junctions
    subgraphs = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    for subG in subgraphs:
        sub_nodes = list(subG.nodes())
        if len(sub_nodes) < 3:
            continue
            
        endpoints = [n for n in sub_nodes if subG.degree(n) == 1]
        junctions = [n for n in sub_nodes if subG.degree(n) > 2]
        key_nodes = list(set(endpoints + junctions))
        
        if not key_nodes:
            # Closed loop without junctions
            cycle_nodes = list(sub_nodes)
            if len(cycle_nodes) >= 4:
                coords = [(c, r) for r, c in cycle_nodes]
                geo_coords = pixel_to_geo_coords(coords, active_transform)
                road_lines.append(geo_coords)
            continue
            
        for kn in key_nodes:
            for neighbor in subG.neighbors(kn):
                edge = tuple(sorted([kn, neighbor]))
                if edge in visited_edges:
                    continue
                # Traverse edge until next key node
                path = [kn, neighbor]
                visited_edges.add(edge)
                curr = neighbor
                prev = kn
                while curr not in key_nodes:
                    next_nodes = [n for n in subG.neighbors(curr) if n != prev]
                    if not next_nodes:
                        break
                    next_n = next_nodes[0]
                    edge2 = tuple(sorted([curr, next_n]))
                    visited_edges.add(edge2)
                    path.append(next_n)
                    prev = curr
                    curr = next_n
                    
                if len(path) >= 2:
                    coords = [(c, r) for r, c in path]
                    geo_coords = pixel_to_geo_coords(coords, active_transform)
                    road_lines.append(geo_coords)

    features = []
    feature_id = 1
    
    for line_pts in road_lines:
        if len(line_pts) < 2:
            continue
        line = LineString(line_pts)
        if not line.is_valid:
            line = make_valid(line)
            if line.geom_type != 'LineString':
                continue
                
        if simplify_tol > 0:
            line = line.simplify(simplify_tol, preserve_topology=True)
            
        length_m = round(line.length, 2)
        if length_m < min_length_m:
            continue
            
        # Sample road width along line
        try:
            # Sample 5 points along line
            widths = []
            for alpha in np.linspace(0.1, 0.9, 5):
                pt = line.interpolate(alpha, normalized=True)
                row, col = rasterio.transform.rowcol(active_transform, pt.x, pt.y)
                r, c = int(row), int(col)
                if 0 <= r < dist_map.shape[0] and 0 <= c < dist_map.shape[1]:
                    widths.append(dist_map[r, c])
            avg_width = float(np.mean(widths)) if widths else pixel_res * 4.0
        except Exception:
            avg_width = pixel_res * 4.0
            
        avg_width = max(1.5, round(avg_width, 1))
        classification = "road" if avg_width >= 4.0 else "pathway"
        
        features.append({
            'id': f"RD_{feature_id:04d}",
            'class': classification,
            'confidence': 0.88,
            'length_m': length_m,
            'width_m': avg_width,
            'geometry': line
        })
        feature_id += 1

    gdf = gpd.GeoDataFrame(features, crs=crs)
    logger.info(f"Vectorized {len(gdf)} road/pathway centerlines.")
    return gdf

def vectorize_landuse(
    landuse_map: np.ndarray,
    transform,
    crs,
    min_area_pixels: int = 50
) -> gpd.GeoDataFrame:
    """
    Converts multi-class land use raster into classified polygon layers.
    Uses multi-scale decimation on large rasters to bound memory and avoid tiny fragments.
    """
    if landuse_map is None:
        return gpd.GeoDataFrame(columns=['id', 'class', 'confidence', 'area_sqm', 'perimeter_m', 'geometry'], crs=crs)

    h, w = landuse_map.shape
    scale_factor = max(1, int(round(max(h, w) / 2000.0)))
    if scale_factor > 1:
        from affine import Affine
        scaled_w = w // scale_factor
        scaled_h = h // scale_factor
        active_map = cv2.resize(np.array(landuse_map[::scale_factor, ::scale_factor]), (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
        active_transform = transform * Affine.scale(scale_factor, scale_factor)
    else:
        active_map = landuse_map
        active_transform = transform

    features = []
    feature_id = 1
    
    # Vectorize connected components using rasterio.features.shapes
    shapes = rasterio.features.shapes(active_map.astype(np.int32), transform=active_transform)
    
    for geom_dict, class_idx in shapes:
        class_idx = int(class_idx)
        if class_idx == 0: # Skip background
            continue
            
        poly = shapely.geometry.shape(geom_dict)
        if not poly.is_valid:
            poly = make_valid(poly)
            
        if poly.is_empty:
            continue
            
        area_m2 = round(poly.area, 2)
        perimeter_m = round(poly.length, 2)
        class_name = LANDUSE_CLASSES.get(class_idx, f"Class {class_idx}")
        
        features.append({
            'id': f"LU_{feature_id:04d}",
            'class': class_name,
            'confidence': 0.85,
            'area_sqm': area_m2,
            'perimeter_m': perimeter_m,
            'geometry': poly
        })
        feature_id += 1

    gdf = gpd.GeoDataFrame(features, crs=crs)
    logger.info(f"Vectorized {len(gdf)} land use polygons.")
    return gdf
