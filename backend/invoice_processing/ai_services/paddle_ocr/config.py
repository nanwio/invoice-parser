from loguru import logger
from typing import Dict, Any
import platform

class PaddleConfig:
    """
    Manages a single, optimized configuration for PaddleOCR focused on speed.
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Returns optimized configuration for PaddleOCR 2.x (stable version).
        Platform-aware: MKLDNN only enabled on Linux (Cloud Run), disabled on macOS/Windows.
        """
        # CRITICAL: MKLDNN only works on Linux. Crashes on macOS with:
        # 'AnalysisConfig' object has no attribute 'set_mkldnn_cache_capacity'
        is_linux = platform.system() == 'Linux'

        logger.info(f"Loading PaddleOCR 2.x with optimized configuration (Platform: {platform.system()}, MKLDNN: {is_linux})")

        # PaddleOCR 2.x configuration - optimized for invoice documents
        # Special focus on complex financial tables and multi-column layouts
        return {
            'lang': 'es',
            'use_angle_cls': True,   # Detect rotated text (important for scanned docs)
            'use_gpu': False,
            'show_log': False,
            'enable_mkldnn': is_linux,   # ✅ ONLY on Linux (Cloud Run), NOT on macOS
            'cpu_threads': 8,
            # Detection parameters (optimized for dense text in tables)
            'det_db_thresh': 0.15,       # More sensitive (was 0.2) - better for small text
            'det_db_box_thresh': 0.25,   # Lower = detect smaller boxes (was 0.3)
            'det_limit_side_len': 1600,  # Higher resolution for better detection (was 1216, multiple of 32)
            'det_db_unclip_ratio': 1.6,  # Slightly expand boxes to avoid cutting text (default 1.5)
            'use_dilation': True,        # Dilate text boxes to merge nearby characters
            'rec_batch_num': 6,          # Batch size for recognition (more context)
            'drop_score': 0.25,          # Lower confidence threshold (was 0.3) - capture more text
            'max_text_length': 50,       # Allow longer text sequences in recognition
        }
