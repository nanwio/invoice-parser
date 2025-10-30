from loguru import logger
from typing import Dict, Any
import platform

class PaddleConfig:
    """
    Manages a single, optimized configuration for PaddleOCR with GPU auto-detection.
    """

    @staticmethod
    def is_gpu_available() -> bool:
        """
        Auto-detect GPU availability using PaddlePaddle.

        Returns:
            True if CUDA-enabled GPU is available, False otherwise
        """
        try:
            import paddle
            is_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
            logger.info(f"GPU auto-detection: {'✅ AVAILABLE' if is_available else '❌ NOT AVAILABLE'}")
            return is_available
        except Exception as e:
            logger.warning(f"GPU detection failed: {e}. Defaulting to CPU.")
            return False

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Returns optimized configuration for PaddleOCR 2.x with GPU auto-detection.

        GPU mode (Cloud Run with NVIDIA L4):
        - Faster inference (~5-10x speedup)
        - No MKLDNN issues
        - No malloc corruption
        - No segfaults

        CPU mode (local development):
        - Fallback for environments without GPU
        - MKLDNN disabled for stability
        """
        # Auto-detect GPU availability
        use_gpu = PaddleConfig.is_gpu_available()

        # GPU mode: no MKLDNN needed (GPU acceleration replaces it)
        # CPU mode: MKLDNN disabled to prevent "could not execute a primitive" errors
        enable_mkldnn = False

        logger.info(
            f"Loading PaddleOCR 2.x configuration: "
            f"Platform={platform.system()}, "
            f"GPU={'ENABLED ✅' if use_gpu else 'DISABLED (CPU)'}, "
            f"MKLDNN={enable_mkldnn}"
        )

        # PaddleOCR 2.x configuration - optimized for invoice documents
        # Special focus on complex financial tables and multi-column layouts
        return {
            'lang': 'es',
            'use_angle_cls': True,   # Detect rotated text (important for scanned docs)
            'use_gpu': use_gpu,      # ✅ Auto-detect GPU
            'show_log': False,
            'enable_mkldnn': enable_mkldnn,   # Disabled for stability
            'cpu_threads': 8 if not use_gpu else 1,  # More threads on CPU, single thread on GPU
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
