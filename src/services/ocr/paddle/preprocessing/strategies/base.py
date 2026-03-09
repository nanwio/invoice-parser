"""Base strategy for image preprocessing."""
from abc import ABC, abstractmethod
import numpy as np


class PreprocessingStrategy(ABC):
    """Abstract base class for preprocessing strategies."""

    @abstractmethod
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Apply preprocessing to image."""
        pass
