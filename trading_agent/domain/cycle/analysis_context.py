from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..signals.market_signals import MarketSignals
from ..portfolio.portfolio_snapshot import PortfolioSnapshot
from ..user.user_preferences import UserPreferences


@dataclass
class AnalysisContext:
    market_signals: MarketSignals
    portfolio: PortfolioSnapshot
    user_preferences: UserPreferences
    time_horizon: str = "medium-term"
    focus_areas: str = "all"
    regions: str = "US"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_signals": self.market_signals.to_dict(),
            "portfolio": self.portfolio.to_dict(),
            "user_preferences": self.user_preferences.to_dict(),
            "time_horizon": self.time_horizon,
            "focus_areas": self.focus_areas,
            "regions": self.regions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisContext":
        return cls(
            market_signals=MarketSignals.from_dict(data["market_signals"]),
            portfolio=PortfolioSnapshot.from_dict(data["portfolio"]),
            user_preferences=UserPreferences.from_dict(data["user_preferences"]),
            time_horizon=data.get("time_horizon", "medium-term"),
            focus_areas=data.get("focus_areas", "all"),
            regions=data.get("regions", "US"),
        )
