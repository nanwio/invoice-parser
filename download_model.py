#!/usr/bin/env python3
"""
Pre-download DeepSeek-OCR model files during Docker build.
Uses HF_TOKEN for authenticated downloads (avoids rate limiting).
"""

import os
from huggingface_hub import snapshot_download
from loguru import logger

MODEL_NAME = "deepseek-ai/DeepSeek-OCR"

if __name__ == "__main__":
    token = os.environ.get("HF_TOKEN")
    logger.info(f"Pre-downloading {MODEL_NAME} (authenticated: {bool(token)})...")

    try:
        cache_dir = snapshot_download(
            repo_id=MODEL_NAME,
            token=token,
            allow_patterns=["*.safetensors", "*.json", "*.txt", "*.py", "*.model"],
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],
        )
        logger.success(f"Model files downloaded to: {cache_dir}")
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        raise
