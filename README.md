# 🛰️ CadastralAI — CPU-Friendly Geospatial AI Cadastral Mapping System

An end-to-end, high-performance geospatial AI cadastral mapping system designed specifically for **low-end PCs (4–8 GB RAM) and CPU-first inference**.

It processes high-resolution **Drone Orthorectified Imagery (ORI GeoTIFF)**, with optional **DSM/DTM** elevation models and **GNSS survey pegs**, automatically extracting:
- **Buildings $\to$ Polygons** (with cadastral 90° orthogonalization)
- **Roads & Pathways $\to$ Line Networks** (centerlines + road width estimation)
- **Cadastral Parcels $\to$ Planar Polygons** (road-constrained watershed/Voronoi delineation + GNSS peg vertex snapping)
- **Land Use $\to$ Multi-Class Polygons** (Buildings, Roads, Tree Canopy, Agriculture, Water)

All outputs preserve the native GeoTIFF Coordinate Reference System (CRS) and are exported to both OGC-standard multi-layer **GeoPackage (`.gpkg`)** and **GeoJSON (`.geojson`)** with complete attributes: `area_sqm`, `perimeter_m`, `length_m`, `width_m`, `class`, and `confidence`.

Includes an interactive **Streamlit Web-GIS dashboard** for layer toggling, visual inspection, attribute queries, and one-click GIS dataset downloads.

---

## ⚡ Key Architectural Optimizations for 4–8 GB RAM PCs

1. **Streaming Windowed Tiling**: Reads input rasters chunk-by-chunk using `rasterio.windows.Window` (512×512 tiles with 64px overlap halo) so multi-gigabyte drone orthomosaics can be processed without Out-Of-Memory (OOM) crashes.
2. **CPU-First ONNX Runtime Engine**: Uses `onnxruntime` with `CPUExecutionProvider` and configurable thread limits (`intra_op_num_threads = 2` or `4`). Zero GPU or CUDA dependencies.
3. **Quantized / Lightweight Graph Execution**: Memory consumption during inference stays strictly bounded under 200 MB RAM.
4. **Resilient Dual Model Engine**: Capable of downloading pre-trained geospatial ONNX weights from open repositories, with an integrated calibrated offline model synthesizer that guarantees full operation even without internet access.
5. **Cadastral Topology Validation**: Applies `shapely.validation.make_valid()`, removes sliver polygons, and enforces cadastral planar partitioning (no overlapping parcels).

---

## 📁 System Architecture & Directory Structure

```
├── cadastral_ai/
│   ├── __init__.py           # Package initialization
│   ├── app.py                # Streamlit Web-GIS Interactive Dashboard
│   ├── inference.py          # Windowed tiled streaming AI inference engine
│   ├── models.py             # Pre-trained ONNX model loader, catalog & synthesizer
│   ├── parcel_delineator.py  # Road-constrained Voronoi/watershed parcel delineator
│   ├── pipeline.py           # Master end-to-end CadastralPipeline orchestrator
│   ├── sample_data.py        # Realistic drone survey dataset generator
│   ├── topology.py           # Topology validator & planar partition resolver
│   └── vectorizer.py         # Regularized vectorization (orthogonalization & skeletonization)
├── download_models.py        # CLI tool to download / verify ONNX models
├── requirements.txt          # Minimal CPU-friendly dependencies
├── sample_data/              # Generated demo drone dataset (ORI, DSM, GNSS)
└── output/                   # Output GeoPackage (.gpkg) and GeoJSON layers
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- 4–8 GB RAM
- Dual-core or Quad-core CPU

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Download / Verify Pre-trained Models
```bash
python download_models.py
```

### 4. Launch the Streamlit Web-GIS Dashboard
```bash
streamlit run cadastral_ai/app.py
```
Open your browser at `http://localhost:8501`.

---

## 💻 Running the Pipeline via Python API or CLI

### Python API Example
```python
from cadastral_ai.pipeline import CadastralPipeline

# Initialize CPU pipeline with 2 threads and 512px sliding window
pipeline = CadastralPipeline(
    num_threads=2,
    tile_size=512,
    overlap=64,
    orthogonalize_buildings=True
)

# Run end-to-end extraction
results = pipeline.run(
    ori_path="sample_data/drone_ori.tif",
    dsm_path="sample_data/drone_dsm.tif",              # Optional
    gnss_path="sample_data/gnss_survey_pegs.geojson",  # Optional
    output_dir="output",
    building_threshold=0.50,
    road_threshold=0.45,
    min_building_area=15.0,
    min_parcel_area=80.0
)

print("Pipeline summary:", results["summary"])
```

### Generating Demo Drone Data
If you don't have a drone GeoTIFF on hand, generate a synthetic scene complete with ORI, DSM, and GNSS pegs:
```bash
python -m cadastral_ai.sample_data
```

---

## 📊 Output GIS Specifications

### 1. OGC GeoPackage (`output/cadastral_output.gpkg`)
SQLite container with native spatial index (RTree) containing 4 layers:
- `buildings`: Polygon geometry with orthogonalized building boundaries.
- `roads`: LineString geometry with road network centerlines.
- `parcels`: Polygon geometry with planar partitioned cadastral property boundaries.
- `land_use`: Polygon geometry with multi-class thematic land use categories.

### 2. GeoJSON Files
- `output/buildings.geojson`
- `output/roads.geojson`
- `output/parcels.geojson`
- `output/land_use.geojson`
- `output/cadastral_summary.json`

### 3. Feature Attribute Schema
| Attribute Name | Data Type | Units / Format | Description |
|---|---|---|---|
| `id` | String | e.g. `PRCL_0001`, `BLD_0001` | Unique feature cadastral identifier |
| `class` | String | `building`, `road`, `parcel`, etc. | Feature classification |
| `confidence` | Float | $0.00 - 1.00$ | AI model prediction confidence index |
| `area_sqm` | Float | Square meters ($m^2$) | Planar geometric area |
| `perimeter_m` | Float | Meters ($m$) | Boundary perimeter length |
| `length_m` | Float | Meters ($m$) | Minimum bounding box length |
| `width_m` | Float | Meters ($m$) | Minimum bounding box / road width |
| `buildings_count` | Integer | Count | Number of buildings situated within parcel |

---

## 🛰️ Dashboard Features
- **Live Memory & Hardware Monitor**: Shows host RAM consumption and active thread allocation.
- **Interactive Map**: Folium viewer with OpenStreetMap, Esri World Imagery (satellite), and CartoDB basemaps.
- **Layer Toggles**: Turn on/off buildings, roads, parcels, land use, and GNSS survey pegs.
- **Hover Tooltips**: Inspect area, dimensions, confidence, and parcel ID directly on the map.
- **Attribute Inspector**: Tabbed data tables with sorting and filtering across all layers.
- **One-Click Downloads**: Direct export of `.gpkg` and `.geojson` layers.
