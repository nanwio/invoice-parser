"""
Build-time script to pre-download and cache PaddleOCR models.

This script is executed only during the `docker build` phase.
It initializes the OCR engine, which triggers the download of all necessary
models into the default cache directory. This ensures the final container image
already includes the models, significantly speeding up the application's
runtime startup (cold start).
"""
from paddleocr import PaddleOCR
from loguru import logger

logger.info("Starting PaddleOCR model caching script...")

try:
    # Initialize the engine to trigger the download. The engine object is discarded.
    # We use the same parameters as in the main app to ensure the correct models are cached.
    _ = PaddleOCR(
        use_angle_cls=False,
        lang='es',
        use_gpu=False,        # IMPORTANT: Must be False, as no GPU is available in the build environment.
        show_log=True,
        enable_mkldnn=True,   # Cache MKL-DNN optimized models if available
    )
    logger.success("PaddleOCR models have been successfully downloaded and cached.")

except Exception as e:
    logger.critical(f"Failed to cache PaddleOCR models: {e}", exc_info=True)
    # Exit with a non-zero status code to fail the Docker build if caching fails.
    exit(1)
