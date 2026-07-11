import os
from typing import Any, Dict, List

from .news_base import NewsDataProvider


class FinnhubNewsProvider(NewsDataProvider):
    """Finnhub news provider. Returns empty data when FINNHUB_API_KEY is unset."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")

    def get_news(self, symbols: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            return {"headlines": [], "note": "Finnhub API key not configured"}
        # Stub for Phase 2 — wire Finnhub REST when key is available.
        return {"headlines": [], "symbols": symbols, "note": "Finnhub integration pending"}

    def get_sentiment_summary(self, symbols: List[str]) -> str:
        news = self.get_news(symbols)
        if news.get("note"):
            return news["note"]
        return "No recent news sentiment available."
