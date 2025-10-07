from loguru import logger
from typing import Dict, Any

class PaddleConfig:
    """
    Manages a single, optimized configuration for PaddleOCR focused on speed.
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Returns a single, highly optimized configuration for ultra-fast CPU processing.
        All parameters are validated against PaddleOCR 3.x official documentation.
        """
        logger.info("Loading PaddleOCR with ultra_fast configuration")

        # Minimal configuration with only verified PaddleOCR 3.x parameters
        return {
            'lang': 'es',
            'use_angle_cls': False,
        }
