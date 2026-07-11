from typing import Any, Dict, List

from .news_base import NewsDataProvider


class MockNewsProvider(NewsDataProvider):
    """Mock news provider for tests."""

    def __init__(self, headlines: List[Dict[str, Any]] = None):
        self.headlines = headlines or [
            {
                "title": "Tech stocks rally on earnings optimism",
                "source": "MockWire",
                "datetime": "2026-07-10",
                "symbol": "AAPL",
                "url": "https://example.com/tech-rally",
            },
            {
                "title": "Fed signals steady rates amid cooling inflation",
                "source": "MockWire",
                "datetime": "2026-07-09",
                "url": "https://example.com/fed-rates",
            },
        ]

    def get_news(self, symbols: List[str]) -> Dict[str, Any]:
        return {"headlines": self.headlines, "symbols": symbols}

    def get_sentiment_summary(self, symbols: List[str]) -> str:
        bullish = sum(1 for h in self.headlines if "rally" in h.get("title", "").lower())
        bearish = sum(1 for h in self.headlines if "fall" in h.get("title", "").lower() or "crash" in h.get("title", "").lower())
        if bullish > bearish:
            return f"Mixed-positive sentiment ({len(self.headlines)} headlines, {bullish} bullish cues)"
        if bearish > bullish:
            return f"Mixed-negative sentiment ({len(self.headlines)} headlines, {bearish} bearish cues)"
        return f"Neutral sentiment ({len(self.headlines)} headlines)"
