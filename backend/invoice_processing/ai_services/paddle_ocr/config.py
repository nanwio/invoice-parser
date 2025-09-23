from loguru import logger
from typing import Dict, Any

class PaddleConfig:
    """
    Manages a single, optimized configuration for PaddleOCR focused on speed.
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Returns a single, highly optimized configuration for ultra-fast processing.
        """
        logger.info("Loading PaddleOCR with ultra_fast configuration")
        
        # This configuration is fine-tuned for maximum CPU speed.
        # Based on official documentation and performance testing.
        return {
            # High-Performance Inference Engine (HPI)
            'enable_hpi': True,
            
            # Use MKL-DNN for significant CPU speed-up
            'enable_mkldnn': True,
            
            # Maximize CPU thread usage for parallel processing
            'cpu_threads': 8,
            
            # General settings
            'use_gpu': False,
            'lang': 'es',
            'show_log': False,
            'use_space_char': True,
            
            # Detection model parameters (tuned for speed)
            'det_db_thresh': 0.1,
            'det_db_box_thresh': 0.3,
            'det_db_unclip_ratio': 1.2,
            
            # Recognition model parameters (tuned for speed)
            'rec_batch_num': 10,
            'max_text_length': 30,
            
            # Disable angle classification for a significant speed boost
            'use_angle_cls': False,
        }
