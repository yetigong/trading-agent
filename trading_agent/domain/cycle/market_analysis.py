from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..serialization import parse_datetime


@dataclass
class MarketAnalysisResult:
    status: str
    analysis: str = ""
    timestamp: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "analysis": self.analysis,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketAnalysisResult":
        ts = data.get("timestamp")
        return cls(
            status=data.get("status", "failed"),
            analysis=data.get("analysis", ""),
            timestamp=parse_datetime(ts) if ts else None,
            error=data.get("error"),
        )
