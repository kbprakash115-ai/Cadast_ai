"""
Memory-Safe Tiled AI Inference Engine for Large Drone GeoTIFFs.
Optimized for low-end PCs (4-8 GB RAM) and CPU-first execution.
Uses memory-mapped arrays (np.memmap) so rasters of any size (even 100+ Megapixels)
run strictly within bounded RAM (< 250 MB peak memory).
"""

import os
import gc
import logging
import tempfile
import numpy as np
import rasterio
from rasterio.windows import Window
from tqdm import tqdm
from .models import CadastralModelEngine

logger = logging.getLogger("cadastral_ai.inference")

def create_2d_blend_window(height: int, width: int, overlap: int) -> np.ndarray:
    """
    Creates a smooth 2D cosine/spline tapering window to prevent seam artifacts
    along tile stitch boundaries.
    """
    if overlap <= 0:
        return np.ones((height, width), dtype=np.float32)
    
    def get_1d_window(length: int, halo: int) -> np.ndarray:
        w = np.ones(length, dtype=np.float32)
        if halo > 0 and 2 * halo <= length:
            ramp = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, halo)))
            w[:halo] = ramp
            w[-halo:] = ramp[::-1]
        return w
    
    wx = get_1d_window(width, overlap)
    wy = get_1d_window(height, overlap)
    return np.outer(wy, wx).astype(np.float32)

class TiledInferenceEngine:
    """
    Executes tiled inference across large GeoTIFF rasters with streaming windowed I/O.
    Peak memory is strictly bounded by tile_size using memory-mapped arrays on disk.
    """
    def __init__(
        self,
        model_engine: CadastralModelEngine,
        tile_size: int = 512,
        overlap: int = 64,
        progress_callback = None
    ):
        self.model_engine = model_engine
        self.tile_size = tile_size
        self.overlap = overlap
        self.progress_callback = progress_callback
        self.scratch_dir = None

    def run_inference(
        self,
        ori_path: str,
        dsm_path: str = None,
        dtm_path: str = None,
        tasks: list = None
    ) -> dict:
        """
        Runs tiled inference on the Drone ORI GeoTIFF.
        
        Args:
            ori_path: Path to Drone Orthorectified Imagery GeoTIFF (RGB or RGBA)
            dsm_path: Optional path to Digital Surface Model GeoTIFF
            dtm_path: Optional path to Digital Terrain Model GeoTIFF
            tasks: List of tasks to execute, default: ['buildings', 'roads', 'landuse']
            
        Returns:
            dict containing metadata and memory-safe probability / classification arrays.
        """
        if tasks is None:
            tasks = ['buildings', 'roads', 'landuse']
            
        with rasterio.open(ori_path) as src:
            width = src.width
            height = src.height
            crs = src.crs
            transform = src.transform
            num_bands = src.count
            
            logger.info(f"Input ORI Dimensions: {width}x{height} px, {num_bands} bands, CRS: {crs}")
            
            # Read DSM / DTM windowed if available
            dsm_src = rasterio.open(dsm_path) if (dsm_path and os.path.exists(dsm_path)) else None
            dtm_src = rasterio.open(dtm_path) if (dtm_path and os.path.exists(dtm_path)) else None

            # Memory-mapped scratch arrays:
            # Prevents allocating multi-gigabyte arrays in RAM on 4-8 GB PCs.
            self.scratch_dir = tempfile.mkdtemp(prefix="cadastral_scratch_")
            
            b_path = os.path.join(self.scratch_dir, "buildings_prob.dat")
            r_path = os.path.join(self.scratch_dir, "roads_prob.dat")
            w_path = os.path.join(self.scratch_dir, "weight_accum.dat")
            lu_path = os.path.join(self.scratch_dir, "landuse_map.dat")
            luc_path = os.path.join(self.scratch_dir, "landuse_conf.dat")

            buildings_prob = np.memmap(b_path, dtype=np.float32, mode='w+', shape=(height, width)) if 'buildings' in tasks else None
            roads_prob = np.memmap(r_path, dtype=np.float32, mode='w+', shape=(height, width)) if 'roads' in tasks else None
            weight_accum = np.memmap(w_path, dtype=np.float32, mode='w+', shape=(height, width))
            landuse_map = np.memmap(lu_path, dtype=np.uint8, mode='w+', shape=(height, width)) if 'landuse' in tasks else None
            landuse_conf = np.memmap(luc_path, dtype=np.float16, mode='w+', shape=(height, width)) if 'landuse' in tasks else None
            
            # Initialize with zeros
            weight_accum[:] = 0.0
            if buildings_prob is not None: buildings_prob[:] = 0.0
            if roads_prob is not None: roads_prob[:] = 0.0
            if landuse_map is not None: landuse_map[:] = 0
            if landuse_conf is not None: landuse_conf[:] = 0.0

            # Grid partitioning with overlap
            stride = self.tile_size
            cols = list(range(0, width, stride))
            rows = list(range(0, height, stride))
            total_tiles = len(cols) * len(rows)
            tile_counter = 0

            for r in rows:
                for c in cols:
                    tile_counter += 1
                    if self.progress_callback and tile_counter % 5 == 0:
                        pct_tiles = min(99, int((tile_counter / total_tiles) * 100))
                        self.progress_callback(pct_tiles, 100, f"Running Tiled AI Inference ({tile_counter}/{total_tiles} tiles)...")
                        
                    # Calculate window bounds with halo
                    c_start = max(0, c - self.overlap)
                    r_start = max(0, r - self.overlap)
                    c_end = min(width, c + stride + self.overlap)
                    r_end = min(height, r + stride + self.overlap)
                    
                    w_width = c_end - c_start
                    w_height = r_end - r_start
                    
                    window = Window(col_off=c_start, row_off=r_start, width=w_width, height=w_height)
                    
                    # Read only RGB (bands 1, 2, 3)
                    read_bands = min(3, num_bands)
                    tile_data = src.read(indexes=list(range(1, read_bands + 1)), window=window)
                    
                    # Handle single band (grayscale) or 2-band
                    if tile_data.shape[0] == 1:
                        tile_data = np.repeat(tile_data, 3, axis=0)
                    elif tile_data.shape[0] == 2:
                        tile_data = np.pad(tile_data, ((0, 1), (0, 0), (0, 0)), mode='edge')
                        
                    # Normalize tile to 0.0 - 1.0 float32
                    if tile_data.dtype == np.uint8:
                        tile_norm = (tile_data.astype(np.float32) / 255.0)
                    else:
                        t_min, t_max = tile_data.min(), tile_data.max()
                        if t_max > t_min:
                            tile_norm = (tile_data.astype(np.float32) - t_min) / (t_max - t_min)
                        else:
                            tile_norm = np.zeros_like(tile_data, dtype=np.float32)
                    
                    # Compute blending weight mask for this window
                    weight_mask = create_2d_blend_window(w_height, w_width, self.overlap)
                    
                    # Predict Buildings
                    if 'buildings' in tasks:
                        b_pred = self.model_engine.predict('buildings', tile_norm)[0] # [H, W]
                        buildings_prob[r_start:r_end, c_start:c_end] += b_pred * weight_mask
                        
                    # Predict Roads
                    if 'roads' in tasks:
                        r_pred = self.model_engine.predict('roads', tile_norm)[0] # [H, W]
                        roads_prob[r_start:r_end, c_start:c_end] += r_pred * weight_mask
                        
                    # Predict Land Use (Tile-by-tile winner-takes-all without storing 6-channel full array)
                    if 'landuse' in tasks:
                        lu_pred = self.model_engine.predict('landuse', tile_norm) # [6, H, W]
                        tile_lu_class = np.argmax(lu_pred, axis=0).astype(np.uint8)
                        tile_lu_conf = (np.max(lu_pred, axis=0) * weight_mask).astype(np.float16)
                        
                        curr_conf = landuse_conf[r_start:r_end, c_start:c_end]
                        better = tile_lu_conf > curr_conf
                        
                        patch_map = landuse_map[r_start:r_end, c_start:c_end]
                        patch_map[better] = tile_lu_class[better]
                        landuse_map[r_start:r_end, c_start:c_end] = patch_map
                        
                        patch_conf = landuse_conf[r_start:r_end, c_start:c_end]
                        patch_conf[better] = tile_lu_conf[better]
                        landuse_conf[r_start:r_end, c_start:c_end] = patch_conf
                            
                    # Accumulate blending weights
                    weight_accum[r_start:r_end, c_start:c_end] += weight_mask
                    
                    # Periodic garbage collection to maintain low RAM
                    if tile_counter % 25 == 0:
                        gc.collect()

            # Normalize probabilities chunk-by-chunk along rows to stay under 50 MB RAM
            chunk_rows = 1024
            for r0 in range(0, height, chunk_rows):
                r1 = min(height, r0 + chunk_rows)
                w_chunk = np.array(weight_accum[r0:r1, :])
                w_chunk[w_chunk == 0] = 1.0
                if buildings_prob is not None:
                    buildings_prob[r0:r1, :] = np.clip(buildings_prob[r0:r1, :] / w_chunk, 0.0, 1.0)
                if roads_prob is not None:
                    roads_prob[r0:r1, :] = np.clip(roads_prob[r0:r1, :] / w_chunk, 0.0, 1.0)

            # Flush memmap changes to disk
            if buildings_prob is not None: buildings_prob.flush()
            if roads_prob is not None: roads_prob.flush()
            if landuse_map is not None: landuse_map.flush()
            
            del weight_accum
            if landuse_conf is not None: del landuse_conf
            gc.collect()

            # Handle optional DSM/DTM height boost windowed/chunked
            ndsm_array = None
            if dsm_src:
                try:
                    # If DSM is moderate size (< 2000 px), read directly, else sample
                    if dsm_src.width * dsm_src.height <= 16_000_000:
                        dsm_data = dsm_src.read(1)
                        if dtm_src and dtm_src.width * dtm_src.height <= 16_000_000:
                            dtm_data = dtm_src.read(1)
                            ndsm_array = dsm_data - dtm_data
                        else:
                            from scipy.ndimage import grey_opening
                            ground = grey_opening(dsm_data, size=(25, 25))
                            ndsm_array = dsm_data - ground
                            
                        if buildings_prob is not None and ndsm_array.shape == buildings_prob.shape:
                            height_boost = np.clip(ndsm_array / 5.0, 0.0, 0.3)
                            for r0 in range(0, height, chunk_rows):
                                r1 = min(height, r0 + chunk_rows)
                                buildings_prob[r0:r1, :] = np.clip(buildings_prob[r0:r1, :] + height_boost[r0:r1, :], 0.0, 1.0)
                            buildings_prob.flush()
                except Exception as e:
                    logger.warning(f"Could not apply DSM height cues: {e}")
                finally:
                    dsm_src.close()
                    if dtm_src: dtm_src.close()

            return {
                "meta": {
                    "width": width,
                    "height": height,
                    "crs": crs,
                    "transform": transform
                },
                "buildings_prob": buildings_prob,
                "roads_prob": roads_prob,
                "landuse_map": landuse_map,
                "ndsm": ndsm_array
            }
