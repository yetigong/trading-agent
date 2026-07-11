from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.user.user_preferences import UserPreferences


class AnalysisStrategy(ABC):
    """Base class for market analysis strategies."""

    @abstractmethod
    def analyze(
        self,
        portfolio: PortfolioSnapshot,
        user_preferences: UserPreferences,
        analysis_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        pass

    @abstractmethod
    def get_supported_parameters(self) -> Dict[str, str]:
        pass
