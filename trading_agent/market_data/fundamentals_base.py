from abc import ABC, abstractmethod
from typing import Any, Dict, List


class FundamentalDataProvider(ABC):
    @abstractmethod
    def get_fundamentals(self, symbols: List[str]) -> Dict[str, Any]:
        """Return fundamentals metrics keyed by symbol."""
        pass

    @abstractmethod
    def get_summary(self, symbols: List[str], data: Dict[str, Any] = None) -> str:
        """Human-readable fundamentals summary for prompts."""
        pass
