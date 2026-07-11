from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from trading_agent.domain.cycle import StrategyContext, TradingDecision


class TradingStrategy(ABC):
    """Base class for trading strategies."""

    @abstractmethod
    def make_decisions(self, context: StrategyContext) -> List[TradingDecision]:
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        pass

    @abstractmethod
    def get_supported_parameters(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def validate_decisions(self, decisions: List[TradingDecision]) -> List[TradingDecision]:
        pass
