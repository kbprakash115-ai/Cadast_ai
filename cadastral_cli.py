"""
CadastralAI - Command Line Interface (CLI)
Automated batch processing of drone GeoTIFFs for cadastral mapping on low-end CPU PCs.
"""

import sys
import argparse
import os
import json
from cadastral_ai.pipeline import CadastralPipeline
from cadastral_ai.sample_data import generate_sample_drone_data

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    parser = argparse.ArgumentParser(
        description="CadastralAI - CPU-First Geospatial AI Cadastral Mapping System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--ori", type=str, help="Path to Drone ORI GeoTIFF (RGB or RGBA)")
    parser.add_argument("--dsm", type=str, default=None, help="Path to optional DSM GeoTIFF")
    parser.add_argument("--dtm", type=str, default=None, help="Path to optional DTM GeoTIFF")
    parser.add_argument("--gnss", type=str, default=None, help="Path to optional GNSS survey pegs (.geojson or .csv)")
    parser.add_argument("--output", type=str, default="output", help="Directory for GeoPackage and GeoJSON exports")
    parser.add_argument("--threads", type=int, default=2, help="Number of CPU worker threads")
    parser.add_argument("--tile-size", type=int, default=512, help="Sliding window tile size in pixels")
    parser.add_argument("--overlap", type=int, default=64, help="Tile overlap halo in pixels")
    parser.add_argument("--bld-thresh", type=float, default=0.50, help="Confidence threshold for buildings")
    parser.add_argument("--road-thresh", type=float, default=0.45, help="Confidence threshold for roads")
    parser.add_argument("--no-ortho", action="store_true", help="Disable building 90-degree orthogonalization")
    parser.add_argument("--generate-sample", action="store_true", help="Generate sample synthetic drone dataset and exit")
    
    args = parser.parse_args()

    print("==================================================================")
    print(" CadastralAI - CPU Geospatial Cadastral Mapping System")
    print("==================================================================")

    if args.generate_sample:
        print("[*] Generating synthetic drone survey dataset in 'sample_data'...")
        generate_sample_drone_data("sample_data")
        print("[OK] Sample dataset generated successfully.")
        return

    if not args.ori:
        # Default to sample if exists, else ask
        sample_ori = "sample_data/drone_ori.tif"
        if os.path.exists(sample_ori):
            print(f"[*] No input specified. Using demo dataset at: {sample_ori}")
            args.ori = sample_ori
            args.dsm = "sample_data/drone_dsm.tif"
            args.gnss = "sample_data/gnss_survey_pegs.geojson"
        else:
            parser.error("Please provide --ori <path-to-geotiff> or use --generate-sample")

    print(f"\n[+] Input ORI:      {args.ori}")
    print(f"[+] DSM Model:      {args.dsm if args.dsm else 'None'}")
    print(f"[+] GNSS Survey:    {args.gnss if args.gnss else 'None'}")
    print(f"[+] Output Folder:  {args.output}")
    print(f"[+] CPU Threads:    {args.threads}")
    print(f"[+] Window Tiling:  {args.tile_size}x{args.tile_size} px (overlap: {args.overlap} px)")

    pipeline = CadastralPipeline(
        num_threads=args.threads,
        tile_size=args.tile_size,
        overlap=args.overlap,
        orthogonalize_buildings=not args.no_ortho
    )

    results = pipeline.run(
        ori_path=args.ori,
        dsm_path=args.dsm,
        dtm_path=args.dtm,
        gnss_path=args.gnss,
        output_dir=args.output,
        building_threshold=args.bld_thresh,
        road_threshold=args.road_thresh
    )

    summary = results["summary"]
    counts = summary["counts"]
    metrics = summary["metrics"]

    print("\n------------------------------------------------------------------")
    print(" [OK] CADASTRAL EXTRACTION COMPLETED SUCCESSFULLY")
    print("------------------------------------------------------------------")
    print(f"Execution Duration:   {summary['processing_time_seconds']} seconds")
    print(f"Native Map CRS:       {summary['crs']}")
    print(f"Buildings Extracted:  {counts['buildings']} (Total Area: {metrics['total_building_footprint_sqm']:,.1f} m²)")
    print(f"Road Network Length:  {metrics['total_road_network_km']:.3f} km ({counts['roads']} corridors)")
    print(f"Parcels Delineated:   {counts['parcels']} (Total Area: {metrics['total_parcel_area_hectares']:.3f} ha)")
    print(f"Land Use Polygons:    {counts['land_use_polygons']}")
    print("\nGenerated GIS Outputs:")
    for key, path in summary["outputs"].items():
        print(f"  - {key:<20}: {path}")
    print("==================================================================")

if __name__ == "__main__":
    main()
