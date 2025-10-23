"""
Build-time script to pre-download and cache PaddleOCR PPStructure models.

This script runs during Docker build (no GPU available) to download all required models:
- OCR detection and recognition models
- Table recognition models (PPStructure)
- Layout analysis models

Models are cached to /root/.paddleocr and copied to final image.
"""
import os

# CRITICAL: Force CPU usage during Docker build (no GPU available)
# This must be set BEFORE importing paddleocr/paddlepaddle
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from paddleocr import PPStructure
from loguru import logger

logger.info("🔄 Starting PPStructure model caching script...")

try:
    # Initialize PPStructure to trigger model downloads
    # IMPORTANT: use_gpu=False because GPU is not available during build
    # At runtime, the code will auto-detect GPU and switch to GPU mode
    logger.info("Initializing PPStructure (CPU mode for build)...")

    engine = PPStructure(
        show_log=True,           # Show download progress
        table=True,              # Download table recognition models
        ocr=True,                # Download OCR models
        layout=True,             # Download layout analysis models (paddleclas)
        image_orientation=True,  # Download rotation detection models
        lang='en',               # English models (can also cache 'es' if needed)
        use_gpu=False,           # No GPU during build
        enable_mkldnn=False,     # Disable MKLDNN for build compatibility
    )

    logger.success("✅ PPStructure models successfully cached to /root/.paddleocr/")
    logger.info("Models will be available at runtime without re-downloading")

    # Print model cache location
    import os
    cache_dir = os.path.expanduser("~/.paddleocr")
    if os.path.exists(cache_dir):
        logger.info(f"📁 Model cache directory: {cache_dir}")
        # List downloaded models
        for root, dirs, files in os.walk(cache_dir):
            for file in files:
                if file.endswith('.pdparams') or file.endswith('.tar'):
                    logger.info(f"  - {os.path.join(root, file)}")

except Exception as e:
    logger.critical(f"❌ Failed to cache PPStructure models: {e}", exc_info=True)
    exit(1)
