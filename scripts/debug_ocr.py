"""
Standalone OCR test script - bypasses API/async to isolate the bottleneck.

Usage:
    poetry run python scripts/debug_ocr.py facturas/varios_igic/1.pdf
"""
import sys
import time
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_ocr.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"ERROR: file not found: {pdf_path}")
        sys.exit(1)

    print(f"[1/5] Importing PaddleOCR PPStructure...")
    t0 = time.perf_counter()
    from paddleocr import PPStructure
    print(f"    Imported in {time.perf_counter() - t0:.2f}s")

    print(f"[2/5] Initializing PPStructure (layout=True, lang='en')...")
    t0 = time.perf_counter()
    engine = PPStructure(
        show_log=True,  # Enable internal logs to see paddle activity
        table=True,
        ocr=True,
        layout=True,
        image_orientation=False,
        use_angle_cls=False,
        lang='en',
        use_gpu=False,
        enable_mkldnn=False,
        cpu_threads=4,
    )
    print(f"    Initialized in {time.perf_counter() - t0:.2f}s")

    dpi = int(os.environ.get("DEBUG_OCR_DPI", "200"))
    print(f"[3/5] Converting PDF to images at {dpi} DPI...")
    t0 = time.perf_counter()
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi)
    print(f"    Got {len(images)} page(s) in {time.perf_counter() - t0:.2f}s")

    print(f"[4/5] Converting first page to numpy array...")
    t0 = time.perf_counter()
    import numpy as np
    import cv2
    img_array = np.array(images[0].convert('RGB'))
    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    print(f"    Image shape: {img_array.shape}, time: {time.perf_counter() - t0:.2f}s")

    print(f"[5/5] Running PPStructure inference on first page (this is where it hangs)...")
    t0 = time.perf_counter()
    result = engine(img_array)
    elapsed = time.perf_counter() - t0
    print(f"    Inference completed in {elapsed:.2f}s")
    print(f"    Got {len(result)} regions")
    print(f"    Region types: {set(r.get('type') for r in result)}")


if __name__ == "__main__":
    main()
