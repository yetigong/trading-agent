from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MarketConditions:
    volatility: str = "unknown"
    trend: str = "unknown"
    economic_cycle: str = "unknown"
    market_phase: str = "unknown"
    indices: Dict[str, Any] = field(default_factory=dict)
    sector_etfs: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketConditions":
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            volatility=data.get("volatility", "unknown"),
            trend=data.get("trend", "unknown"),
            economic_cycle=data.get("economic_cycle", "unknown"),
            market_phase=data.get("market_phase", "unknown"),
            indices=data.get("indices") or {},
            sector_etfs=data.get("sector_etfs") or {},
            timestamp=ts,
        )
