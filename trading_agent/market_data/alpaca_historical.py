"""Alpaca historical bar cache and point-in-time market data provider."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from trading_agent.domain.user.signal_config import DEFAULT_SECTOR_ETFS
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.market_data.historical_cache import (
    coverage_contains,
    get_provider_cache_dir,
    load_manifest,
    parse_date,
    save_manifest,
    update_symbol_coverage,
)

logger = logging.getLogger(__name__)

DEFAULT_INDICES = ["SPY", "QQQ", "DIA", "IWM"]


def get_alpaca_cache_dir() -> Path:
    return get_provider_cache_dir("alpaca")


def bars_path(symbol: str, cache_dir: Optional[Path] = None) -> Path:
    root = cache_dir or get_alpaca_cache_dir()
    return root / "bars" / f"{symbol.upper()}.csv"


def read_cached_bars(
    symbol: str,
    cache_dir: Optional[Path] = None,
) -> Optional[pd.DataFrame]:
    path = bars_path(symbol, cache_dir)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df.sort_index()
    except (OSError, ValueError) as exc:
        logger.warning("Failed to read Alpaca bar cache %s: %s", path, exc)
        return None


def write_cached_bars(
    symbol: str,
    df: pd.DataFrame,
    cache_dir: Optional[Path] = None,
) -> None:
    path = bars_path(symbol, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out = out.sort_index()
    out.to_csv(path)


def merge_bars(existing: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        merged = new.copy()
    else:
        merged = pd.concat([existing, new])
        merged = merged[~merged.index.duplicated(keep="last")]
    merged.index = pd.to_datetime(merged.index).tz_localize(None)
    return merged.sort_index()


def slice_bars_as_of(
    df: Optional[pd.DataFrame],
    as_of: date,
    days: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    cutoff = pd.Timestamp(as_of)
    sliced = df[df.index.normalize() <= cutoff]
    if sliced.empty:
        return None
    if days is not None and days > 0:
        sliced = sliced.tail(days)
    return sliced


def fetch_and_cache_bars(
    symbols: List[str],
    start: date,
    end: date,
    provider: Optional[Any] = None,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """
    Ensure bars for symbols covering [start, end] are in the Alpaca cache.

    When provider is None and credentials exist, creates AlpacaMarketDataProvider.
    Returns a summary dict with fetched/skipped symbols.
    """
    from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider

    cache_dir = cache_dir or get_alpaca_cache_dir()
    manifest = load_manifest(cache_dir)
    summary = {"fetched": [], "skipped": [], "failed": []}

    live = provider
    if live is None:
        live = AlpacaMarketDataProvider()

    # Warmup buffer so indicators have enough history at start
    fetch_start = start - timedelta(days=90)
    start_dt = datetime.combine(fetch_start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    for symbol in symbols:
        sym = symbol.upper()
        if not refresh and coverage_contains(manifest, sym, fetch_start, end):
            summary["skipped"].append(sym)
            continue

        try:
            new_df = live.get_historical_bars(sym, start_dt, end_dt)
            if new_df is None or new_df.empty:
                summary["failed"].append(sym)
                continue

            existing = read_cached_bars(sym, cache_dir)
            merged = merge_bars(existing, new_df)
            write_cached_bars(sym, merged, cache_dir)

            earliest = parse_date(merged.index.min())
            latest = parse_date(merged.index.max())
            if earliest and latest:
                update_symbol_coverage(manifest, sym, earliest, latest)
            summary["fetched"].append(sym)
        except Exception as exc:
            logger.warning("Failed to fetch bars for %s: %s", sym, exc)
            summary["failed"].append(sym)

    save_manifest(cache_dir, manifest)
    return summary


def _period_return(data: pd.DataFrame, days: int) -> Optional[float]:
    if data is None or len(data) < days + 1:
        return None
    start_price = float(data["close"].iloc[-(days + 1)])
    end_price = float(data["close"].iloc[-1])
    if start_price == 0:
        return None
    return (end_price / start_price - 1) * 100


class HistoricalAlpacaProvider(MarketDataProvider):
    """Point-in-time market data from the Alpaca bar cache."""

    def __init__(
        self,
        as_of_date: date,
        cache_dir: Optional[Path] = None,
        sector_etfs: Optional[List[str]] = None,
        indices: Optional[List[str]] = None,
    ):
        self.as_of_date = as_of_date if isinstance(as_of_date, date) else date.fromisoformat(str(as_of_date)[:10])
        self.cache_dir = cache_dir or get_alpaca_cache_dir()
        self.sector_etfs = list(sector_etfs) if sector_etfs is not None else list(DEFAULT_SECTOR_ETFS)
        self.indices = list(indices) if indices is not None else list(DEFAULT_INDICES)
        self._bars: Dict[str, pd.DataFrame] = {}

    def set_as_of_date(self, as_of_date: date) -> None:
        self.as_of_date = as_of_date if isinstance(as_of_date, date) else date.fromisoformat(str(as_of_date)[:10])

    def _load_bars(self, symbol: str) -> Optional[pd.DataFrame]:
        sym = symbol.upper()
        if sym not in self._bars:
            cached = read_cached_bars(sym, self.cache_dir)
            if cached is not None:
                self._bars[sym] = cached
        return self._bars.get(sym)

    def get_bars(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        return slice_bars_as_of(self._load_bars(symbol), self.as_of_date, days=days)

    def get_close_price(self, symbol: str) -> Optional[float]:
        bars = slice_bars_as_of(self._load_bars(symbol), self.as_of_date)
        if bars is None or bars.empty:
            return None
        return float(bars["close"].iloc[-1])

    def get_market_conditions(self) -> Dict[str, Any]:
        return {
            "volatility": self.get_market_volatility(),
            "trend": self.get_market_trend(),
            "economic_cycle": self.get_economic_cycle(),
            "market_phase": self.get_market_phase(),
            "timestamp": datetime.combine(self.as_of_date, datetime.min.time()),
            "indices": self._get_indices_data(),
            "sector_etfs": self._get_sector_etfs_data(),
        }

    def get_market_volatility(self) -> str:
        spy = self.get_bars("SPY", days=30)
        if spy is None or len(spy) < 20:
            return "moderate"
        returns = spy["close"].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252))
        if volatility < 0.15:
            return "low"
        if volatility < 0.25:
            return "moderate"
        return "high"

    def get_market_trend(self) -> str:
        spy = self.get_bars("SPY", days=100)
        if spy is None or len(spy) < 50:
            return "neutral"
        sma20 = spy["close"].rolling(window=20).mean().iloc[-1]
        sma50 = spy["close"].rolling(window=50).mean().iloc[-1]
        current = spy["close"].iloc[-1]
        if current > sma20 and sma20 > sma50:
            return "bullish"
        if current < sma20 and sma20 < sma50:
            return "bearish"
        return "neutral"

    def get_economic_cycle(self) -> str:
        spy = self.get_bars("SPY", days=365)
        if spy is None or len(spy) < 200:
            return "expansion"
        yoy = (float(spy["close"].iloc[-1]) / float(spy["close"].iloc[0]) - 1) * 100
        if yoy > 15:
            return "expansion"
        if yoy > 5:
            return "peak"
        if yoy > -5:
            return "contraction"
        return "trough"

    def get_market_phase(self) -> str:
        spy = self.get_bars("SPY", days=30)
        if spy is None or len(spy) < 20:
            return "normal"
        returns = spy["close"].pct_change().dropna()
        recent_vol = float(returns.std() * np.sqrt(252))
        recent_return = (float(spy["close"].iloc[-1]) / float(spy["close"].iloc[0]) - 1) * 100
        if recent_vol > 0.3 and recent_return > 10:
            return "bubble"
        if recent_vol > 0.3 and recent_return < -10:
            return "crash"
        if recent_vol > 0.2 and recent_return > 0:
            return "recovery"
        return "normal"

    def get_supported_indicators(self) -> Dict[str, str]:
        return {
            "volatility": "Market volatility level (low, moderate, high)",
            "trend": "Market trend (bullish, neutral, bearish)",
            "economic_cycle": "Economic cycle phase (expansion, peak, contraction, trough)",
            "market_phase": "Market phase (normal, bubble, crash, recovery)",
            "indices": "Major market indices (SPY, QQQ, DIA, IWM)",
            "sector_etfs": "Sector SPDR ETFs with relative strength vs SPY",
        }

    def trading_days(self, start: date, end: date, symbol: str = "SPY") -> List[date]:
        bars = self._load_bars(symbol)
        if bars is None or bars.empty:
            return []
        mask = (bars.index.normalize() >= pd.Timestamp(start)) & (
            bars.index.normalize() <= pd.Timestamp(end)
        )
        return [ts.date() for ts in bars.index[mask]]

    def _snapshot_from_bars(self, data: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
        if data is None or data.empty:
            return None
        entry: Dict[str, Any] = {
            "current_price": float(data["close"].iloc[-1]),
            "daily_change": float(
                (data["close"].iloc[-1] / data["close"].iloc[-2] - 1) * 100
            )
            if len(data) >= 2
            else 0.0,
            "volume": int(data["volume"].iloc[-1]) if "volume" in data.columns else 0,
        }
        return_5d = _period_return(data, 5)
        entry["return_5d"] = round(return_5d, 2) if return_5d is not None else None
        return entry

    def _get_indices_data(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for index in self.indices:
            snap = self._snapshot_from_bars(self.get_bars(index, days=10))
            if snap:
                result[index] = snap
        return result

    def _get_sector_etfs_data(self) -> Dict[str, Any]:
        sector_data: Dict[str, Any] = {}
        spy = self.get_bars("SPY", days=30)
        spy_return_5d = _period_return(spy, 5) if spy is not None else None
        for etf in self.sector_etfs:
            data = self.get_bars(etf, days=30)
            snap = self._snapshot_from_bars(data)
            if not snap:
                continue
            if snap.get("return_5d") is not None and spy_return_5d is not None:
                snap["vs_spy_5d"] = round(snap["return_5d"] - spy_return_5d, 2)
            sector_data[etf] = snap
        return sector_data
