import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .news_base import NewsDataProvider

logger = logging.getLogger(__name__)

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
MAX_SYMBOLS = 5
MAX_HEADLINES_PER_SYMBOL = 5
MAX_GENERAL_HEADLINES = 10

_BULLISH_KEYWORDS = {"rally", "surge", "gain", "beat", "growth", "upgrade", "record", "optimism"}
_BEARISH_KEYWORDS = {"fall", "drop", "decline", "miss", "cut", "downgrade", "crash", "warning", "layoff"}


class FinnhubNewsProvider(NewsDataProvider):
    """Finnhub news provider."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")

    def get_news(self, symbols: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            return {"headlines": [], "note": "Finnhub API key not configured"}

        headlines: List[Dict[str, Any]] = []
        seen_titles: set = set()

        for symbol in symbols[:MAX_SYMBOLS]:
            for item in self._fetch_company_news(symbol):
                title = item.get("title", "")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                headlines.append(item)
                if sum(1 for h in headlines if h.get("symbol") == symbol) >= MAX_HEADLINES_PER_SYMBOL:
                    break

        for item in self._fetch_general_news():
            title = item.get("title", "")
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            headlines.append(item)
            if len([h for h in headlines if not h.get("symbol")]) >= MAX_GENERAL_HEADLINES:
                break

        return {"headlines": headlines[:20], "symbols": symbols[:MAX_SYMBOLS]}

    def get_sentiment_summary(self, symbols: List[str]) -> str:
        news = self.get_news(symbols)
        if news.get("note"):
            return news["note"]

        headlines = news.get("headlines") or []
        if not headlines:
            return "No recent news sentiment available."

        bullish = 0
        bearish = 0
        for h in headlines:
            title = h.get("title", "").lower()
            if any(k in title for k in _BULLISH_KEYWORDS):
                bullish += 1
            if any(k in title for k in _BEARISH_KEYWORDS):
                bearish += 1

        if bullish > bearish:
            tone = "positive"
        elif bearish > bullish:
            tone = "negative"
        else:
            tone = "neutral"

        return f"{tone.capitalize()} news tone ({len(headlines)} headlines, {bullish} bullish / {bearish} bearish cues)"

    def _fetch_company_news(self, symbol: str) -> List[Dict[str, Any]]:
        end = datetime.now().date()
        start = end - timedelta(days=7)
        data = self._get_json(
            "company-news",
            symbol=symbol,
            from_=start.isoformat(),
            to=end.isoformat(),
        )
        if not isinstance(data, list):
            return []
        return [self._normalize_headline(item, symbol=symbol) for item in data[:MAX_HEADLINES_PER_SYMBOL]]

    def _fetch_general_news(self) -> List[Dict[str, Any]]:
        data = self._get_json("news", category="general")
        if not isinstance(data, list):
            return []
        return [self._normalize_headline(item) for item in data[:MAX_GENERAL_HEADLINES]]

    def _normalize_headline(self, item: Dict[str, Any], symbol: str = None) -> Dict[str, Any]:
        ts = item.get("datetime")
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        else:
            dt = str(ts) if ts else ""
        headline = {
            "title": item.get("headline") or item.get("title", ""),
            "source": item.get("source", ""),
            "datetime": dt,
            "url": item.get("url", ""),
        }
        if symbol:
            headline["symbol"] = symbol
        return headline

    def _get_json(self, path: str, **params: Any) -> Any:
        query = dict(params)
        if "from_" in query:
            query["from"] = query.pop("from_")
        query["token"] = self.api_key
        url = f"{FINNHUB_BASE_URL}/{path}?{urllib.parse.urlencode(query)}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            logger.warning("Finnhub request failed for %s: %s", path, exc)
            return None
