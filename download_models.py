"""
CLI Utility to download or synthesize pre-trained ONNX geospatial models for Cadastral AI.
Optimized for low-end CPU PCs.
"""

import sys
import argparse
from cadastral_ai.models import MODEL_CATALOG, get_model_path, CadastralModelEngine

def main():
    parser = argparse.ArgumentParser(description="Download or verify pre-trained ONNX models for Cadastral AI")
    parser.add_argument("--force-download", action="store_true", help="Force remote download from Hugging Face / URLs")
    parser.add_argument("--verify", action="store_true", default=True, help="Verify inference on CPU")
    args = parser.parse_args()

    print("==================================================")
    print(" Cadastral AI - Geospatial ONNX Model Downloader")
    print("==================================================")
    
    for model_name, info in MODEL_CATALOG.items():
        print(f"\n[+] Preparing: {model_name.upper()}")
        print(f"    Description: {info['description']}")
        path = get_model_path(model_name, download_if_missing=args.force_download)
        print(f"    Ready at: {path}")

    if args.verify:
        print("\n--- Verifying CPU Inference Engine ---")
        engine = CadastralModelEngine(num_threads=2)
        import numpy as np
        dummy_tile = np.zeros((3, 256, 256), dtype=np.float32)
        for model_name in MODEL_CATALOG.keys():
            output = engine.predict(model_name, dummy_tile)
            print(f"    [{model_name}] verified. Output shape: {output.shape}")

    print("\n[OK] All models ready for CPU-first cadastral inference!")

if __name__ == "__main__":
    main()
