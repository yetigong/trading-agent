from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..serialization import parse_datetime
from .fundamentals import FundamentalsPayload
from .market_data import MarketDataPayload
from .news import NewsPayload
from .signal_status import SignalStatus
from .technical import TechnicalPayload

SignalPayload = Union[MarketDataPayload, TechnicalPayload, NewsPayload, FundamentalsPayload, None]

PAYLOAD_TYPES = {
    "market_data": MarketDataPayload,
    "technical": TechnicalPayload,
    "news": NewsPayload,
    "fundamentals": FundamentalsPayload,
}


@dataclass
class SignalSourceResult:
    source_id: str
    status: SignalStatus
    timestamp: datetime
    symbols: List[str]
    payload: SignalPayload = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload_dict = self.payload.to_dict() if self.payload else None
        return {
            "source_id": self.source_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "symbols": self.symbols,
            "payload": payload_dict,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalSourceResult":
        source_id = data["source_id"]
        payload_data = data.get("payload")
        payload: SignalPayload = None
        if payload_data and source_id in PAYLOAD_TYPES:
            payload = PAYLOAD_TYPES[source_id].from_dict(payload_data)
        return cls(
            source_id=source_id,
            status=SignalStatus(data.get("status", "failed")),
            timestamp=parse_datetime(data["timestamp"]),
            symbols=list(data.get("symbols") or []),
            payload=payload,
            error=data.get("error"),
        )
