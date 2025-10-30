"""
PaddleOCR Provider - Singleton pattern for managing PPStructure engine and GPU lock.

Based on maite-transcripto-gpu architecture:
- Single engine instance (singleton)
- GPU auto-detection
- Global GPU lock for thread-safety
- Lazy initialization
"""
from threading import Lock
from typing import Optional, Any
from loguru import logger
import paddle

try:
    from paddleocr import PPStructure
    PPSTRUCTURE_AVAILABLE = True
except ImportError:
    logger.warning("PaddleOCR PPStructure not available. Install paddleocr>=2.7")
    PPSTRUCTURE_AVAILABLE = False


class PaddleOCRProvider:
    """
    Manages the lifecycle of the PPStructure engine and its GPU lock as a singleton.
    
    This class ensures that the OCR engine is initialized only once (lazy initialization)
    when it's first requested by a dependency. This avoids race conditions and
    initializes the GPU at the correct time in the application lifecycle.
    
    Based on maite-transcripto-gpu OCRProvider pattern.
    """
    _engine: Optional[Any] = None
    _gpu_lock: Optional[Lock] = None
    _is_gpu_available: bool = False

    @classmethod
    def _initialize(cls):
        """
        Private method to initialize the PPStructure engine and lock if they haven't been already.
        This is called internally by the public getter methods.
        """
        if cls._engine is not None:
            return  # Already initialized

        if not PPSTRUCTURE_AVAILABLE:
            raise ImportError("PaddleOCR PPStructure not installed. Install with: pip install paddleocr>=2.7")

        logger.info("Lazy-initializing PPStructure engine on first request...")
        try:
            # Auto-detect GPU availability
            cls._is_gpu_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
            
            if cls._is_gpu_available:
                logger.info(f"✅ GPU detected: {paddle.device.cuda.device_count()} CUDA device(s) available")
            else:
                logger.info("❌ No GPU detected - running in CPU mode")

            # Initialize PPStructure with TensorRT acceleration
            cls._engine = PPStructure(
                show_log=False,
                table=True,              # Enable table recognition (critical for invoices)
                ocr=True,                # Enable OCR within tables
                layout=True,             # Enable layout analysis
                image_orientation=True,  # Enable rotation detection
                lang='en',               # Must be 'en' or 'ch' (layout model requirement)
                use_gpu=cls._is_gpu_available,  # Auto-detect GPU
                use_tensorrt=cls._is_gpu_available,  # TensorRT acceleration (10-20x faster)
                precision='fp16' if cls._is_gpu_available else 'fp32',  # FP16 for speed on GPU
                enable_mkldnn=False,     # Disabled for stability (not needed on GPU)
                cpu_threads=1,           # Single thread for stability
            )
            
            # This lock is crucial for serializing GPU access when handling concurrent requests.
            cls._gpu_lock = Lock()
            
            logger.success(
                f"PPStructure engine and GPU lock initialized successfully "
                f"({'GPU mode' if cls._is_gpu_available else 'CPU mode'})"
            )

        except Exception as e:
            logger.critical(f"Failed to initialize PPStructure engine: {e}")
            # Raising an exception here will prevent the application from starting if the engine fails.
            raise RuntimeError(f"Could not initialize PPStructure Engine: {e}") from e

    @classmethod
    def get_engine(cls) -> Any:
        """Initializes (if needed) and returns the singleton PPStructure engine instance."""
        cls._initialize()
        return cls._engine

    @classmethod
    def get_lock(cls) -> Lock:
        """Initializes (if needed) and returns the singleton GPU lock instance."""
        cls._initialize()
        if cls._gpu_lock is None:
            # This should be unreachable if _initialize() runs correctly.
            raise RuntimeError("GPU lock was not initialized.")
        return cls._gpu_lock

    @classmethod
    def is_gpu_available(cls) -> bool:
        """Returns whether GPU is available. Initializes engine if needed."""
        cls._initialize()
        return cls._is_gpu_available


# --- FastAPI Dependencies (for future use) ---

def get_engine() -> Any:
    """FastAPI dependency to get the PPStructure engine, initializing it on first use."""
    return PaddleOCRProvider.get_engine()


def get_lock() -> Lock:
    """FastAPI dependency to get the GPU lock, ensuring it's initialized."""
    return PaddleOCRProvider.get_lock()
