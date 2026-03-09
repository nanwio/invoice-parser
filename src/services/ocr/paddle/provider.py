"""
PaddleOCR Provider - Dual-mode engine management for adaptive extraction.

TFG Edition (CPU-only):
- Two engines: layout mode (complex docs) and table mode (simple docs)
- Adaptive fallback strategy based on extraction quality
- CPU-optimized configuration
- Thread lock for concurrent request handling
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
    Manages dual PPStructure engines for adaptive document extraction.

    Two modes available:
    - layout_engine (layout=True): Better for complex layouts with headers/footers
    - table_engine (layout=False): Better for simple tabular documents

    The processor uses fallback logic to choose the best result.
    """
    _layout_engine: Optional[Any] = None  # layout=True
    _table_engine: Optional[Any] = None   # layout=False
    _engine_lock: Optional[Lock] = None
    _is_gpu_available: bool = False
    _initialized: bool = False

    # Threshold for fallback: if layout mode extracts less than this, try table mode
    FALLBACK_CHAR_THRESHOLD = 200

    @classmethod
    def _initialize(cls):
        """Initialize both PPStructure engines (layout and table modes)."""
        if cls._initialized:
            return

        if not PPSTRUCTURE_AVAILABLE:
            raise ImportError("PaddleOCR PPStructure not installed. Install with: pip install paddleocr>=2.7")

        logger.info("Initializing dual PPStructure engines (CPU mode)...")
        try:
            cls._is_gpu_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0

            if cls._is_gpu_available:
                logger.info(f"GPU detected: {paddle.device.cuda.device_count()} CUDA device(s)")
            else:
                logger.info("Running in CPU mode (paddlepaddle CPU version)")

            # Engine 1: Layout mode (layout=True)
            # Better for complex documents with headers, footers, customer boxes
            logger.info("  Initializing layout engine (layout=True)...")
            cls._layout_engine = PPStructure(
                show_log=False,
                table=True,
                ocr=True,
                layout=True,             # Full layout analysis
                image_orientation=False,
                use_angle_cls=False,
                lang='en',
                use_gpu=False,
                enable_mkldnn=False,
                cpu_threads=4,
            )

            # Engine 2: Table mode (layout=False)
            # Better for simple/tabular documents where layout detection fails
            logger.info("  Initializing table engine (layout=False)...")
            cls._table_engine = PPStructure(
                show_log=False,
                table=True,
                ocr=True,
                layout=False,            # Treat as table for full extraction
                image_orientation=False,
                use_angle_cls=False,
                lang='en',
                use_gpu=False,
                enable_mkldnn=False,
                cpu_threads=4,
            )

            cls._engine_lock = Lock()
            cls._initialized = True

            logger.success("Dual PPStructure engines initialized (layout + table modes)")

        except Exception as e:
            logger.critical(f"Failed to initialize PPStructure engines: {e}")
            raise RuntimeError(f"Could not initialize PPStructure Engines: {e}") from e

    @classmethod
    def get_engine(cls, mode: str = "layout") -> Any:
        """
        Get PPStructure engine by mode.

        Args:
            mode: "layout" for complex docs, "table" for simple docs

        Returns:
            PPStructure engine instance
        """
        cls._initialize()
        if mode == "table":
            return cls._table_engine
        return cls._layout_engine

    @classmethod
    def get_layout_engine(cls) -> Any:
        """Get the layout-mode engine (layout=True)."""
        cls._initialize()
        return cls._layout_engine

    @classmethod
    def get_table_engine(cls) -> Any:
        """Get the table-mode engine (layout=False)."""
        cls._initialize()
        return cls._table_engine

    @classmethod
    def get_lock(cls) -> Lock:
        """Get the engine lock for thread safety."""
        cls._initialize()
        if cls._engine_lock is None:
            raise RuntimeError("Engine lock was not initialized.")
        return cls._engine_lock

    @classmethod
    def is_gpu_available(cls) -> bool:
        """Returns whether GPU is available."""
        cls._initialize()
        return cls._is_gpu_available

    @classmethod
    def get_fallback_threshold(cls) -> int:
        """Get the character threshold for fallback logic."""
        return cls.FALLBACK_CHAR_THRESHOLD


# --- FastAPI Dependencies (for future use) ---

def get_engine() -> Any:
    """FastAPI dependency to get the PPStructure engine, initializing it on first use."""
    return PaddleOCRProvider.get_engine()


def get_lock() -> Lock:
    """FastAPI dependency to get the engine lock, ensuring it's initialized."""
    return PaddleOCRProvider.get_lock()
