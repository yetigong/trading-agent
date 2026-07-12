"""Finnhub historical news cache and point-in-time news provider."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from trading_agent.market_data.historical_cache import (
    coverage_contains,
    get_provider_cache_dir,
    load_manifest,
    save_manifest,
    update_symbol_coverage,
)
from trading_agent.market_data.news_base import NewsDataProvider

logger = logging.getLogger(__name__)

MAX_SYMBOLS = 13
MAX_HEADLINES_PER_SYMBOL = 5
MAX_GENERAL_HEADLINES = 10

_BULLISH_KEYWORDS = {"rally", "surge", "gain", "beat", "growth", "upgrade", "record", "optimism"}
_BEARISH_KEYWORDS = {"fall", "drop", "decline", "miss", "cut", "downgrade", "crash", "warning", "layoff"}


def get_finnhub_cache_dir() -> Path:
    return get_provider_cache_dir("finnhub")


def news_day_path(symbol: str, day: date, cache_dir: Optional[Path] = None) -> Path:
    root = cache_dir or get_finnhub_cache_dir()
    return root / "news" / symbol.upper() / f"{day.isoformat()}.json"


def read_news_day(
    symbol: str,
    day: date,
    cache_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    path = news_day_path(symbol, day, cache_dir)
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("headlines"), list):
            return data["headlines"]
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read Finnhub news cache %s: %s", path, exc)
        return []


def write_news_day(
    symbol: str,
    day: date,
    headlines: List[Dict[str, Any]],
    cache_dir: Optional[Path] = None,
) -> None:
    path = news_day_path(symbol, day, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(headlines, f, indent=2)
        f.write("\n")


def _group_headlines_by_day(headlines: List[Dict[str, Any]]) -> Dict[date, List[Dict[str, Any]]]:
    grouped: Dict[date, List[Dict[str, Any]]] = {}
    for item in headlines:
        raw = str(item.get("datetime") or "")[:10]
        try:
            day = date.fromisoformat(raw)
        except ValueError:
            continue
        grouped.setdefault(day, []).append(item)
    return grouped


def fetch_and_cache_news(
    symbols: List[str],
    start: date,
    end: date,
    provider: Optional[Any] = None,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
    chunk_days: int = 30,
) -> Dict[str, Any]:
    """Ensure company news for symbols covering [start, end] is cached."""
    from trading_agent.market_data.finnhub_provider import FinnhubNewsProvider

    cache_dir = cache_dir or get_finnhub_cache_dir()
    manifest = load_manifest(cache_dir)
    summary = {"fetched": [], "skipped": [], "failed": [], "note": None}

    live = provider or FinnhubNewsProvider()
    if not getattr(live, "api_key", None):
        summary["note"] = "Finnhub API key not configured"
        return summary

    for symbol in symbols:
        sym = symbol.upper()
        if not refresh and coverage_contains(manifest, sym, start, end):
            summary["skipped"].append(sym)
            continue

        try:
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + timedelta(days=chunk_days - 1), end)
                headlines = live.fetch_company_news(
                    sym,
                    cursor,
                    chunk_end,
                    limit=500,
                )
                for day, day_items in _group_headlines_by_day(headlines).items():
                    if day < start or day > end:
                        continue
                    existing = read_news_day(sym, day, cache_dir)
                    titles = {h.get("title") for h in existing}
                    merged = list(existing)
                    for item in day_items:
                        if item.get("title") not in titles:
                            merged.append(item)
                            titles.add(item.get("title"))
                    write_news_day(sym, day, merged, cache_dir)
                cursor = chunk_end + timedelta(days=1)

            update_symbol_coverage(manifest, sym, start, end)
            summary["fetched"].append(sym)
        except Exception as exc:
            logger.warning("Failed to fetch Finnhub news for %s: %s", sym, exc)
            summary["failed"].append(sym)

    save_manifest(cache_dir, manifest)
    return summary


def _sentiment_from_headlines(headlines: List[Dict[str, Any]]) -> str:
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
    return (
        f"{tone.capitalize()} news tone "
        f"({len(headlines)} headlines, {bullish} bullish / {bearish} bearish cues)"
    )


class HistoricalFinnhubProvider(NewsDataProvider):
    """Point-in-time news from the Finnhub cache."""

    def __init__(
        self,
        as_of_date: date,
        cache_dir: Optional[Path] = None,
        lookback_days: int = 7,
    ):
        self.as_of_date = (
            as_of_date
            if isinstance(as_of_date, date)
            else date.fromisoformat(str(as_of_date)[:10])
        )
        self.cache_dir = cache_dir or get_finnhub_cache_dir()
        self.lookback_days = lookback_days

    def set_as_of_date(self, as_of_date: date) -> None:
        self.as_of_date = (
            as_of_date
            if isinstance(as_of_date, date)
            else date.fromisoformat(str(as_of_date)[:10])
        )

    def get_news_as_of(
        self,
        symbols: List[str],
        as_of: Optional[date] = None,
        lookback_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        as_of = as_of or self.as_of_date
        lookback = lookback_days if lookback_days is not None else self.lookback_days
        window_start = as_of - timedelta(days=lookback)

        headlines: List[Dict[str, Any]] = []
        seen: set = set()
        for symbol in symbols[:MAX_SYMBOLS]:
            day = window_start
            while day <= as_of:
                for item in read_news_day(symbol, day, self.cache_dir):
                    title = item.get("title", "")
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    headlines.append(item)
                    if sum(1 for h in headlines if h.get("symbol") == symbol.upper() or h.get("symbol") == symbol) >= MAX_HEADLINES_PER_SYMBOL:
                        break
                day += timedelta(days=1)

        return {
            "headlines": headlines[:20],
            "symbols": [s.upper() for s in symbols[:MAX_SYMBOLS]],
            "as_of": as_of.isoformat(),
        }

    def get_news(self, symbols: List[str]) -> Dict[str, Any]:
        return self.get_news_as_of(symbols)

    def get_sentiment_summary(self, symbols: List[str]) -> str:
        news = self.get_news(symbols)
        return _sentiment_from_headlines(news.get("headlines") or [])
