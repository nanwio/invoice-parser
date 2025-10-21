"""
Build-time script to pre-download and cache PaddleOCR models.

This script is executed only during the `docker build` phase.
It initializes the OCR engine and specialized table recognition models,
which triggers the download of all necessary models into the default cache directory.
This ensures the final container image already includes the models,
significantly speeding up the application's runtime startup (cold start).
"""
from paddleocr import PaddleOCR, TableStructureRecognition, DocImgOrientationClassification
from loguru import logger

logger.info("Starting model caching script...")

try:
    # 1. Cache standard OCR models (fallback)
    logger.info("Caching standard OCR models (lang='es')...")
    _ = PaddleOCR(lang='es')
    logger.success("✓ Standard OCR models cached")

    # 2. Cache table structure recognition models (primary for invoices)
    logger.info("Caching table structure recognition models (SLANet_plus)...")
    _ = TableStructureRecognition(model_name="SLANet_plus", enable_hpi=True)
    logger.success("✓ Table structure recognition models cached (SLANet_plus)")

    # 3. Cache document orientation classification models
    logger.info("Caching document orientation classification models...")
    _ = DocImgOrientationClassification(model_name="PP-LCNet_x1_0_doc_ori", enable_hpi=True)
    logger.success("✓ Document orientation models cached")

    logger.success("All PaddleOCR models have been successfully downloaded and cached!")

except Exception as e:
    logger.critical(f"Failed to cache PaddleOCR models: {e}", exc_info=True)
    # Exit with a non-zero status code to fail the Docker build if caching fails.
    exit(1)
