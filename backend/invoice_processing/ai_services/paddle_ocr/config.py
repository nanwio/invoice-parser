from loguru import logger
from typing import Dict, Any

class PaddleConfig:
    """
    Manages optimized configurations for PaddleOCR.
    
    This class centralizes the parameter settings for different performance
    profiles, ensuring that the main processor class remains clean and focused.
    """

    @staticmethod
    def get_config(config_type: str = "balanced") -> Dict[str, Any]:
        """
        Returns an optimized configuration dictionary for PaddleOCR.
        
        Args:
            config_type: "ultra_fast", "balanced", or "high_quality".
        
        Returns:
            A dictionary with the selected configuration parameters.
        """
        base_config = {
            # HIGH PERFORMANCE SETTINGS
            'enable_hpi': True,
            'enable_mkldnn': True,
            'cpu_threads': 8,
            
            # GENERAL SETTINGS
            'use_gpu': False,
            'lang': 'es',
            'show_log': False,
            'use_space_char': True,
        }
        
        configs = {
            "ultra_fast": {
                **base_config,
                'det_db_thresh': 0.15,
                'det_db_box_thresh': 0.35,
                'det_db_unclip_ratio': 1.4,
                'det_max_candidates': 500,
                'rec_batch_num': 12,
                'max_text_length': 35,
                'rec_image_shape': "3, 32, 256",
                'use_angle_cls': False,
            },
            "balanced": {
                **base_config,
                'det_db_thresh': 0.2,
                'det_db_box_thresh': 0.4,
                'det_db_unclip_ratio': 1.6,
                'det_max_candidates': 700,
                'rec_batch_num': 8,
                'max_text_length': 40,
                'rec_image_shape': "3, 32, 320",
                'use_angle_cls': True,
                'cls_thresh': 0.8,
            },
            "high_quality": {
                **base_config,
                'det_db_thresh': 0.3,
                'det_db_box_thresh': 0.5,
                'det_db_unclip_ratio': 2.0,
                'det_max_candidates': 1000,
                'rec_batch_num': 6,
                'max_text_length': 50,
                'rec_image_shape': "3, 32, 320",
                'use_angle_cls': True,
                'cls_thresh': 0.7,
            }
        }
        
        config = configs.get(config_type, configs["balanced"])
        logger.info(f"Loading PaddleOCR with {config_type} configuration")
        return config
