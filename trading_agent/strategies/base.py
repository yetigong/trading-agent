from abc import ABC, abstractmethod
from typing import Dict, List

from trading_agent.domain.cycle.strategy_context import StrategyContext


class TradingStrategy(ABC):
    @abstractmethod
    def make_decisions(self, context: StrategyContext) -> List[Dict]:
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        pass

    @abstractmethod
    def get_supported_parameters(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def validate_decisions(self, decisions: List[Dict]) -> List[Dict]:
        pass
