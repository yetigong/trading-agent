from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..serialization import parse_datetime


@dataclass
class NewsArticle:
    headline: str
    source: str
    datetime: Optional[datetime] = None
    url: Optional[str] = None
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "source": self.source,
            "datetime": self.datetime.isoformat() if self.datetime else None,
            "url": self.url,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsArticle":
        return cls(
            headline=data["headline"],
            source=data.get("source", "unknown"),
            datetime=parse_datetime(data["datetime"]) if data.get("datetime") else None,
            url=data.get("url"),
            summary=data.get("summary"),
        )


@dataclass
class SentimentSummary:
    overall: str
    score: Optional[float] = None
    bullish: Optional[int] = None
    bearish: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "score": self.score,
            "bullish": self.bullish,
            "bearish": self.bearish,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SentimentSummary":
        return cls(
            overall=data.get("overall", "neutral"),
            score=data.get("score"),
            bullish=data.get("bullish"),
            bearish=data.get("bearish"),
        )


@dataclass
class SymbolNews:
    symbol: str
    articles: List[NewsArticle] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"symbol": self.symbol, "articles": [a.to_dict() for a in self.articles]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolNews":
        return cls(
            symbol=data["symbol"],
            articles=[NewsArticle.from_dict(a) for a in data.get("articles", [])],
        )


@dataclass
class NewsPayload:
    market_articles: List[NewsArticle] = field(default_factory=list)
    symbol_news: List[SymbolNews] = field(default_factory=list)
    sentiment: Optional[SentimentSummary] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_articles": [a.to_dict() for a in self.market_articles],
            "symbol_news": [s.to_dict() for s in self.symbol_news],
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsPayload":
        sentiment = data.get("sentiment")
        return cls(
            market_articles=[NewsArticle.from_dict(a) for a in data.get("market_articles", [])],
            symbol_news=[SymbolNews.from_dict(s) for s in data.get("symbol_news", [])],
            sentiment=SentimentSummary.from_dict(sentiment) if sentiment else None,
        )
