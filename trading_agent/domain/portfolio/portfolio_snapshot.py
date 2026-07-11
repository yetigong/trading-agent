from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..serialization import parse_datetime


@dataclass
class PortfolioSnapshot:
    portfolio_value: float
    cash: float
    positions: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_value": self.portfolio_value,
            "cash": self.cash,
            "positions": self.positions,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortfolioSnapshot":
        ts = data.get("timestamp")
        return cls(
            portfolio_value=float(data.get("portfolio_value", 0)),
            cash=float(data.get("cash", 0)),
            positions=list(data.get("positions") or []),
            timestamp=parse_datetime(ts) if ts else None,
        )

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "PortfolioSnapshot":
        return cls(
            portfolio_value=float(data.get("portfolio_value", 0)),
            cash=float(data.get("cash", 0)),
            positions=list(data.get("positions") or []),
            timestamp=data.get("timestamp") if isinstance(data.get("timestamp"), datetime) else None,
        )
