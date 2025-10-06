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

        # Balanced configuration: speed + quality for invoice processing
        return {
            # CPU Acceleration - MKL-DNN for Intel CPUs
            'enable_mkldnn': True,

            # Optimize CPU thread usage (24 threads for Cloud Run 8 vCPU - maximize parallelism)
            'cpu_threads': 24,

            # General settings
            'use_gpu': False,
            'lang': 'es',
            'show_log': False,
            'use_space_char': True,

            # Disable PaddleOCR 3.x extra models for speed (these are rarely needed)
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,

            # Detection parameters - balanced for invoices (tables, numbers, text)
            'det_db_thresh': 0.15,          # Balanced (0.1=slow/accurate, 0.3=fast/lossy)
            'det_db_box_thresh': 0.35,      # Balanced (0.3=more boxes, 0.5=fewer boxes)
            'det_db_unclip_ratio': 1.3,     # Slightly more padding for better recognition

            # Recognition parameters - optimized for invoice accuracy
            'rec_batch_num': 8,             # Balanced batch size
            'max_text_length': 30,          # Keep 30 for invoice numbers/IDs

            # Disable angle classification (invoices are usually straight)
            'use_angle_cls': False,
        }
