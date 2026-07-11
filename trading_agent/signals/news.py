import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from trading_agent.domain.signals.news import NewsArticle, NewsPayload, SentimentSummary, SymbolNews
from trading_agent.domain.signals.signal_source_result import SignalSourceResult
from trading_agent.domain.signals.signal_status import SignalStatus
from trading_agent.signals.base import SignalProvider

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"


class FinnhubClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, params: Dict[str, Any]) -> Any:
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY not configured")
        params = {**params, "token": self.api_key}
        url = f"{FINNHUB_BASE}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def company_news(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        end = datetime.now()
        start = end - timedelta(days=days)
        return self._get(
            "/company-news",
            {"symbol": symbol, "from": start.strftime("%Y-%m-%d"), "to": end.strftime("%Y-%m-%d")},
        )

    def general_news(self, category: str = "general") -> List[Dict[str, Any]]:
        return self._get("/news", {"category": category})

    def news_sentiment(self, symbol: str) -> Dict[str, Any]:
        return self._get("/news-sentiment", {"symbol": symbol})


class NewsSignalProvider(SignalProvider):
    def __init__(self, finnhub: Optional[FinnhubClient] = None):
        self.finnhub = finnhub or FinnhubClient()

    @property
    def source_id(self) -> str:
        return "news"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        if not self.finnhub.configured:
            return SignalSourceResult(
                source_id=self.source_id,
                status=SignalStatus.FAILED,
                timestamp=now,
                symbols=symbols,
                payload=NewsPayload(),
                error="FINNHUB_API_KEY not configured",
            )

        try:
            market_articles = []
            for item in self.finnhub.general_news()[:5]:
                market_articles.append(self._parse_article(item))

            symbol_news: List[SymbolNews] = []
            scores: List[float] = []
            for symbol in symbols[:8]:
                articles = []
                for item in self.finnhub.company_news(symbol)[:3]:
                    articles.append(self._parse_article(item))
                if articles:
                    symbol_news.append(SymbolNews(symbol=symbol, articles=articles))
                try:
                    sent = self.finnhub.news_sentiment(symbol)
                    if sent.get("sentiment") is not None:
                        scores.append(float(sent["sentiment"].get("bullishPercent", 0)))
                except Exception:
                    pass

            overall = "neutral"
            score = None
            if scores:
                score = sum(scores) / len(scores)
                overall = "bullish" if score > 0.55 else "bearish" if score < 0.45 else "neutral"

            payload = NewsPayload(
                market_articles=market_articles,
                symbol_news=symbol_news,
                sentiment=SentimentSummary(overall=overall, score=score),
            )
            status = SignalStatus.SUCCESS if symbol_news or market_articles else SignalStatus.PARTIAL
            return SignalSourceResult(
                source_id=self.source_id,
                status=status,
                timestamp=now,
                symbols=symbols,
                payload=payload,
            )
        except Exception as exc:
            logger.exception("News signal fetch failed")
            return SignalSourceResult(
                source_id=self.source_id,
                status=SignalStatus.FAILED,
                timestamp=now,
                symbols=symbols,
                payload=NewsPayload(),
                error=str(exc),
            )

    def _parse_article(self, item: Dict[str, Any]) -> NewsArticle:
        ts = item.get("datetime")
        dt = datetime.fromtimestamp(ts) if ts else None
        return NewsArticle(
            headline=item.get("headline", ""),
            source=item.get("source", "unknown"),
            datetime=dt,
            url=item.get("url"),
            summary=item.get("summary"),
        )
