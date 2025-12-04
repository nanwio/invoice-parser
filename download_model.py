#!/usr/bin/env python3
"""
Pre-download DeepSeek-OCR model files during Docker build.
Downloads model weights without initializing (no GPU required).
"""

from huggingface_hub import snapshot_download
from loguru import logger

MODEL_NAME = "deepseek-ai/DeepSeek-OCR"

if __name__ == "__main__":
    logger.info(f"Pre-downloading {MODEL_NAME} model files...")

    try:
        cache_dir = snapshot_download(
            repo_id=MODEL_NAME,
            allow_patterns=["*.safetensors", "*.json", "*.txt", "*.py", "*.model"],
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],
        )
        logger.success(f"Model files downloaded to: {cache_dir}")
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        raise
