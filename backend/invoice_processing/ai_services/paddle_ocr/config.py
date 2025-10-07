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

        # PaddleOCR 2.x configuration - stable and battle-tested
        return {
            'lang': 'es',
            'use_angle_cls': False,
            'use_gpu': False,
            'show_log': False,
            'enable_mkldnn': True,
            'cpu_threads': 8,
            'det_db_thresh': 0.3,
            'det_db_box_thresh': 0.5,
        }
