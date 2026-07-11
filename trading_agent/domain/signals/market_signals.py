from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MarketDataSignals:
    indices: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MarketDataSignals":
        data = data or {}
        return cls(indices=data.get("indices") or {}, summary=data.get("summary", ""))


@dataclass
class TechnicalSignals:
    indicators: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TechnicalSignals":
        data = data or {}
        return cls(indicators=data.get("indicators") or {}, summary=data.get("summary", ""))


@dataclass
class NewsSignals:
    headlines: List[Dict[str, Any]] = field(default_factory=list)
    sentiment_summary: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "NewsSignals":
        data = data or {}
        return cls(
            headlines=data.get("headlines") or [],
            sentiment_summary=data.get("sentiment_summary", ""),
        )


@dataclass
class FundamentalSignals:
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "FundamentalSignals":
        data = data or {}
        return cls(metrics=data.get("metrics") or {}, summary=data.get("summary", ""))


@dataclass
class MarketSignals:
    market_data: MarketDataSignals = field(default_factory=MarketDataSignals)
    technical: TechnicalSignals = field(default_factory=TechnicalSignals)
    news: NewsSignals = field(default_factory=NewsSignals)
    fundamentals: FundamentalSignals = field(default_factory=FundamentalSignals)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MarketSignals":
        data = data or {}
        return cls(
            market_data=MarketDataSignals.from_dict(data.get("market_data")),
            technical=TechnicalSignals.from_dict(data.get("technical")),
            news=NewsSignals.from_dict(data.get("news")),
            fundamentals=FundamentalSignals.from_dict(data.get("fundamentals")),
        )
