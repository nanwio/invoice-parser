"""
Build-time script to pre-download and cache PaddleOCR models.

This script is executed only during the `docker build` phase.
It initializes the OCR engine and PPStructure for table recognition,
which triggers the download of all necessary models into the default cache directory.
This ensures the final container image already includes the models,
significantly speeding up the application's runtime startup (cold start).
"""
from paddleocr import PaddleOCR, PPStructure
from loguru import logger

logger.info("Starting PaddleOCR model caching script (v2.7.3)...")

try:
    # 1. Cache standard OCR models (fallback mode)
    logger.info("Caching standard OCR models (lang='es')...")
    _ = PaddleOCR(
        lang='es',
        use_angle_cls=True,
        use_gpu=False,
        show_log=False,
        enable_mkldnn=True
    )
    logger.success("✓ Standard OCR models cached")

    # 2. Cache PPStructure models (primary for invoice table recognition)
    logger.info("Caching PPStructure models with table recognition...")
    _ = PPStructure(
        show_log=False,
        table=True,              # Enable table recognition
        ocr=True,                # Enable OCR within tables
        layout=False,            # No full layout analysis needed
        image_orientation=True,  # Enable rotation detection
        lang='es',
        use_gpu=False,
        enable_mkldnn=True
    )
    logger.success("✓ PPStructure table recognition models cached")

    logger.success("All PaddleOCR models have been successfully downloaded and cached!")

except Exception as e:
    logger.critical(f"Failed to cache PaddleOCR models: {e}", exc_info=True)
    # Exit with a non-zero status code to fail the Docker build if caching fails.
    exit(1)
