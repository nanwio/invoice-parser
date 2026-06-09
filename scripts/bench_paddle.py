"""
Aislated benchmark of PaddleOCR PP-Structure on a single page.

Bypasses ALL the project's wrapping code so we can see if the slowness
is in PaddleOCR itself or in our code.
"""
import sys
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    if len(sys.argv) < 2:
        print("Usage: poetry run python scripts/bench_paddle.py <pdf>")
        sys.exit(1)

    pdf = sys.argv[1]

    print(f"=== Benchmark: PaddleOCR PP-Structure ===")
    print(f"File: {pdf}")
    print()

    t0 = time.perf_counter()
    from pdf2image import convert_from_path
    images = convert_from_path(pdf, dpi=120)
    print(f"[1] PDF→image (DPI 120): {time.perf_counter() - t0:.2f}s, {len(images)} page(s), size {images[0].size}")

    t0 = time.perf_counter()
    import numpy as np
    import cv2
    img = np.array(images[0].convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    print(f"[2] Image array: {time.perf_counter() - t0:.2f}s, shape {img_bgr.shape}")

    t0 = time.perf_counter()
    from paddleocr import PaddleOCR
    print(f"[3] Import PaddleOCR: {time.perf_counter() - t0:.2f}s")

    t0 = time.perf_counter()
    ocr = PaddleOCR(
        use_angle_cls=False,
        lang='en',
        use_gpu=False,
        show_log=False,
        enable_mkldnn=False,
        cpu_threads=4,
    )
    print(f"[4] Init PaddleOCR (no PP-Structure): {time.perf_counter() - t0:.2f}s")

    t0 = time.perf_counter()
    result = ocr.ocr(img_bgr, cls=False)
    elapsed = time.perf_counter() - t0
    n_lines = len(result[0]) if result and result[0] else 0
    print(f"[5] OCR only inference: {elapsed:.2f}s, {n_lines} text lines")

    print()
    print("=== Now with PP-Structure (full layout + table) ===")
    t0 = time.perf_counter()
    from paddleocr import PPStructure
    pp = PPStructure(
        show_log=False,
        table=True,
        ocr=True,
        layout=True,
        use_angle_cls=False,
        lang='en',
        use_gpu=False,
        enable_mkldnn=False,
        cpu_threads=4,
    )
    print(f"[6] Init PPStructure: {time.perf_counter() - t0:.2f}s")

    t0 = time.perf_counter()
    result = pp(img_bgr)
    elapsed = time.perf_counter() - t0
    print(f"[7] PPStructure inference: {elapsed:.2f}s, {len(result)} regions")
    region_types = [r.get('type') for r in result]
    print(f"    Region types: {region_types}")


if __name__ == "__main__":
    main()
