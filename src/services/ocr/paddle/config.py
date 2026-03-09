from loguru import logger
from typing import Dict, Any
import platform

class PaddleConfig:
    """
    Manages a single, optimized configuration for PaddleOCR (CPU version for TFG).

    This version is optimized for CPU-only deployment, providing simpler setup
    and compatibility without requiring CUDA/GPU infrastructure.
    """

    @staticmethod
    def is_gpu_available() -> bool:
        """
        Check GPU availability using PaddlePaddle.

        Note: With paddlepaddle (CPU version), this will always return False.

        Returns:
            True if CUDA-enabled GPU is available, False otherwise
        """
        try:
            import paddle
            # paddlepaddle CPU version: is_compiled_with_cuda() returns False
            is_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
            logger.info(f"Device detection: {'GPU ✅' if is_available else 'CPU mode'}")
            return is_available
        except Exception as e:
            logger.warning(f"Device detection failed: {e}. Using CPU.")
            return False

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Returns optimized configuration for PaddleOCR 2.x (CPU mode).

        CPU-optimized settings:
        - Multi-threaded inference for better performance
        - MKLDNN disabled for stability (avoids "could not execute a primitive" errors)
        - Parameters tuned for invoice document processing
        """
        # Check GPU availability (will be False with paddlepaddle CPU)
        use_gpu = PaddleConfig.is_gpu_available()

        # MKLDNN disabled to prevent segfaults and primitive errors on some systems
        enable_mkldnn = False

        # CPU threads: use multiple threads for parallel processing
        cpu_threads = 4

        logger.info(
            f"Loading PaddleOCR 2.x configuration: "
            f"Platform={platform.system()}, "
            f"Mode={'GPU' if use_gpu else 'CPU'}, "
            f"Threads={cpu_threads}"
        )

        # PaddleOCR 2.x configuration - optimized for invoice documents
        # Special focus on complex financial tables and multi-column layouts
        return {
            'lang': 'es',
            'use_angle_cls': True,   # Detect rotated text (important for scanned docs)
            'use_gpu': use_gpu,      # False with CPU-only paddlepaddle
            'show_log': False,
            'enable_mkldnn': enable_mkldnn,   # Disabled for stability
            'cpu_threads': cpu_threads,       # Multi-threaded for CPU performance
            # Detection parameters (optimized for dense text in tables)
            'det_db_thresh': 0.15,       # More sensitive - better for small text
            'det_db_box_thresh': 0.25,   # Lower = detect smaller boxes
            'det_limit_side_len': 1600,  # Higher resolution for better detection
            'det_db_unclip_ratio': 1.6,  # Slightly expand boxes to avoid cutting text
            'use_dilation': True,        # Dilate text boxes to merge nearby characters
            'rec_batch_num': 6,          # Batch size for recognition
            'drop_score': 0.25,          # Lower confidence threshold - capture more text
            'max_text_length': 50,       # Allow longer text sequences in recognition
        }
