"""Mutable accumulator for DataForSEO money_spent across API calls."""
import logging

logger = logging.getLogger(__name__)


class CostTracker:
    """Accumulates money_spent from DataForSEO responses into a single float."""

    def __init__(self) -> None:
        self._total: float = 0.0

    @property
    def total(self) -> float:
        return self._total

    def add(self, amount: float | None) -> None:
        """Add a cost amount. Safely ignores None, negative, and non-numeric values."""
        if amount is None:
            return
        try:
            val = float(amount)
        except (TypeError, ValueError):
            logger.warning(f"CostTracker: ignoring non-numeric value: {amount!r}")
            return
        if val < 0:
            return
        self._total += val
