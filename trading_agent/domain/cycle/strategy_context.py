from dataclasses import dataclass
from typing import Any, Dict

from ..signals.market_signals import MarketSignals
from ..portfolio.portfolio_snapshot import PortfolioSnapshot
from ..user.user_preferences import UserPreferences
from .market_analysis import MarketAnalysisResult


@dataclass
class StrategyContext:
    market_signals: MarketSignals
    portfolio: PortfolioSnapshot
    user_preferences: UserPreferences
    market_analysis: MarketAnalysisResult
    timeframe: str = "immediate"
    risk_management: str = "standard"
    position_sizing: str = "dynamic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_signals": self.market_signals.to_dict(),
            "portfolio": self.portfolio.to_dict(),
            "user_preferences": self.user_preferences.to_dict(),
            "market_analysis": self.market_analysis.to_dict(),
            "timeframe": self.timeframe,
            "risk_management": self.risk_management,
            "position_sizing": self.position_sizing,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyContext":
        return cls(
            market_signals=MarketSignals.from_dict(data["market_signals"]),
            portfolio=PortfolioSnapshot.from_dict(data["portfolio"]),
            user_preferences=UserPreferences.from_dict(data["user_preferences"]),
            market_analysis=MarketAnalysisResult.from_dict(data["market_analysis"]),
            timeframe=data.get("timeframe", "immediate"),
            risk_management=data.get("risk_management", "standard"),
            position_sizing=data.get("position_sizing", "dynamic"),
        )
