from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..serialization import parse_datetime
from .signal_source_result import SignalSourceResult


@dataclass
class MarketSignals:
    watchlist: List[str]
    sources: List[SignalSourceResult] = field(default_factory=list)
    collected_at: Optional[datetime] = None

    def get_source(self, source_id: str) -> Optional[SignalSourceResult]:
        for source in self.sources:
            if source.source_id == source_id:
                return source
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "watchlist": self.watchlist,
            "sources": [s.to_dict() for s in self.sources],
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketSignals":
        return cls(
            watchlist=list(data.get("watchlist") or []),
            sources=[SignalSourceResult.from_dict(s) for s in data.get("sources", [])],
            collected_at=parse_datetime(data["collected_at"]) if data.get("collected_at") else None,
        )

    def to_legacy_market_conditions(self) -> Dict[str, Any]:
        """Extract Phase 1-compatible market_conditions from market_data source."""
        source = self.get_source("market_data")
        if source and source.payload and hasattr(source.payload, "to_legacy_market_conditions"):
            return source.payload.to_legacy_market_conditions()
        news = self.get_source("news")
        if news and news.payload and news.payload.sentiment:
            return {
                "volatility": "unknown",
                "trend": "unknown",
                "economic_cycle": "unknown",
                "market_phase": "unknown",
                "sentiment": news.payload.sentiment.overall,
                "indices": {},
                "sector_performance": {},
            }
        return {
            "volatility": "unknown",
            "trend": "unknown",
            "economic_cycle": "unknown",
            "market_phase": "unknown",
            "sentiment": "unknown",
            "indices": {},
            "sector_performance": {},
        }
