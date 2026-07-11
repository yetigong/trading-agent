from abc import ABC, abstractmethod
from typing import Dict

from trading_agent.domain.cycle.analysis_context import AnalysisContext
from trading_agent.domain.cycle.market_analysis import MarketAnalysisResult


class AnalysisStrategy(ABC):
    """Base class for market analysis strategies."""

    @abstractmethod
    def analyze(self, context: AnalysisContext) -> MarketAnalysisResult:
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        pass

    @abstractmethod
    def get_supported_parameters(self) -> Dict[str, str]:
        pass
