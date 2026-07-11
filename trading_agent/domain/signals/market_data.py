from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..serialization import parse_datetime, to_json_value


@dataclass
class IndexSnapshot:
    symbol: str
    current_price: float
    daily_change: float
    volume: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "daily_change": self.daily_change,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexSnapshot":
        return cls(
            symbol=data["symbol"],
            current_price=float(data["current_price"]),
            daily_change=float(data["daily_change"]),
            volume=float(data["volume"]) if data.get("volume") is not None else None,
        )


@dataclass
class SectorEtfSnapshot:
    symbol: str
    daily_change: float

    def to_dict(self) -> Dict[str, Any]:
        return {"symbol": self.symbol, "daily_change": self.daily_change}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectorEtfSnapshot":
        return cls(symbol=data["symbol"], daily_change=float(data["daily_change"]))


@dataclass
class MarketDataPayload:
    volatility: str
    trend: str
    economic_cycle: str
    market_phase: str
    indices: List[IndexSnapshot] = field(default_factory=list)
    sector_etfs: List[SectorEtfSnapshot] = field(default_factory=list)
    sentiment: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volatility": self.volatility,
            "trend": self.trend,
            "economic_cycle": self.economic_cycle,
            "market_phase": self.market_phase,
            "indices": [i.to_dict() for i in self.indices],
            "sector_etfs": [s.to_dict() for s in self.sector_etfs],
            "sentiment": self.sentiment,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketDataPayload":
        return cls(
            volatility=data.get("volatility", "unknown"),
            trend=data.get("trend", "unknown"),
            economic_cycle=data.get("economic_cycle", "unknown"),
            market_phase=data.get("market_phase", "unknown"),
            indices=[IndexSnapshot.from_dict(i) for i in data.get("indices", [])],
            sector_etfs=[SectorEtfSnapshot.from_dict(s) for s in data.get("sector_etfs", [])],
            sentiment=data.get("sentiment"),
            timestamp=parse_datetime(data["timestamp"]) if data.get("timestamp") else None,
        )

    def to_legacy_market_conditions(self) -> Dict[str, Any]:
        """Backward-compatible dict for Phase 1 consumers."""
        indices = {
            i.symbol: {
                "current_price": i.current_price,
                "daily_change": i.daily_change,
                "volume": i.volume,
            }
            for i in self.indices
        }
        sector_performance = {s.symbol: s.daily_change for s in self.sector_etfs}
        return {
            "volatility": self.volatility,
            "trend": self.trend,
            "economic_cycle": self.economic_cycle,
            "market_phase": self.market_phase,
            "timestamp": self.timestamp,
            "indices": indices,
            "sector_performance": sector_performance,
            "sentiment": self.sentiment or "unknown",
        }
