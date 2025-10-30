"""Base strategy for invoice corrections."""
from abc import ABC, abstractmethod
from src.domain.models import Invoice


class CorrectionStrategy(ABC):
    """Abstract base class for correction strategies."""

    @abstractmethod
    def apply(self, invoice: Invoice) -> Invoice:
        """Apply correction to invoice."""
        pass
