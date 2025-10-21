from loguru import logger
from typing import Dict, Any

class PaddleConfig:
    """
    Manages a single, optimized configuration for PaddleOCR focused on speed.
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Returns optimized configuration for PaddleOCR 2.x (stable version).
        """
        logger.info("Loading PaddleOCR 2.x with optimized configuration")

        # PaddleOCR 2.x configuration - optimized for invoice documents
        return {
            'lang': 'es',
            'use_angle_cls': True,   # Detect rotated text (important for scanned docs)
            'use_gpu': False,
            'show_log': False,
            'enable_mkldnn': True,   # Optimized for Cloud Run (Linux)
            'cpu_threads': 8,
            # Detection parameters (optimized for dense text in tables)
            'det_db_thresh': 0.2,        # Lower = more sensitive (was 0.3)
            'det_db_box_thresh': 0.3,    # Lower = detect smaller boxes (was 0.5)
            'det_limit_side_len': 1216,  # Higher resolution for better detection (multiple of 32)
            'rec_batch_num': 6,          # Batch size for recognition (more context)
            'drop_score': 0.3,           # Confidence threshold (was default 0.5)
        }
