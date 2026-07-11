from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SymbolIndicators:
    symbol: str
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    trend: str = "neutral"
    current_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "rsi": self.rsi,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "sma20": self.sma20,
            "sma50": self.sma50,
            "trend": self.trend,
            "current_price": self.current_price,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolIndicators":
        return cls(
            symbol=data["symbol"],
            rsi=data.get("rsi"),
            macd=data.get("macd"),
            macd_signal=data.get("macd_signal"),
            sma20=data.get("sma20"),
            sma50=data.get("sma50"),
            trend=data.get("trend", "neutral"),
            current_price=data.get("current_price"),
        )


@dataclass
class TechnicalPayload:
    symbols: List[SymbolIndicators] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"symbols": [s.to_dict() for s in self.symbols]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TechnicalPayload":
        return cls(symbols=[SymbolIndicators.from_dict(s) for s in data.get("symbols", [])])
