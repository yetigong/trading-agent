from abc import ABC, abstractmethod
from typing import List

from trading_agent.domain.signals.signal_source_result import SignalSourceResult


class SignalProvider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str:
        pass

    @abstractmethod
    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        pass
