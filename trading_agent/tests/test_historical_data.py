"""Tests for historical Alpaca/Finnhub cache and point-in-time providers."""

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from trading_agent.market_data.alpaca_historical import (
    HistoricalAlpacaProvider,
    merge_bars,
    read_cached_bars,
    slice_bars_as_of,
    write_cached_bars,
)
from trading_agent.market_data.finnhub_historical import (
    HistoricalFinnhubProvider,
    write_news_day,
)
from trading_agent.market_data.historical_cache import (
    coverage_contains,
    load_manifest,
    save_manifest,
    update_symbol_coverage,
)


def _make_bars(start: date, days: int, start_price: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=days, freq="B")
    closes = [start_price + i * 0.5 for i in range(days)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1_000_000] * days,
        },
        index=dates,
    )


class TestHistoricalCache(unittest.TestCase):
    def test_manifest_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            manifest = load_manifest(cache_dir)
            update_symbol_coverage(manifest, "SPY", date(2024, 1, 1), date(2024, 6, 30))
            save_manifest(cache_dir, manifest)
            loaded = load_manifest(cache_dir)
            self.assertTrue(coverage_contains(loaded, "SPY", date(2024, 2, 1), date(2024, 3, 1)))
            self.assertFalse(coverage_contains(loaded, "SPY", date(2023, 12, 1), date(2024, 3, 1)))

    def test_bar_cache_roundtrip_and_as_of_slice(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            bars = _make_bars(date(2024, 1, 1), 40)
            write_cached_bars("SPY", bars, cache_dir)
            loaded = read_cached_bars("SPY", cache_dir)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(len(loaded), 40)

            as_of = date(2024, 1, 15)
            sliced = slice_bars_as_of(loaded, as_of, days=5)
            self.assertIsNotNone(sliced)
            assert sliced is not None
            self.assertLessEqual(len(sliced), 5)
            self.assertLessEqual(sliced.index.max().date(), as_of)

    def test_merge_bars_dedupes(self):
        a = _make_bars(date(2024, 1, 1), 5, 100)
        b = _make_bars(date(2024, 1, 3), 5, 200)
        merged = merge_bars(a, b)
        self.assertFalse(merged.index.duplicated().any())
        # Overlapping dates keep latest (from b)
        overlap = pd.Timestamp("2024-01-03")
        if overlap in merged.index:
            self.assertAlmostEqual(float(merged.loc[overlap, "close"]), 200.0)

    def test_historical_alpaca_provider_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            write_cached_bars("SPY", _make_bars(date(2023, 10, 1), 120, 400), cache_dir)
            write_cached_bars("QQQ", _make_bars(date(2023, 10, 1), 120, 350), cache_dir)
            write_cached_bars("XLK", _make_bars(date(2023, 10, 1), 120, 180), cache_dir)

            provider = HistoricalAlpacaProvider(
                as_of_date=date(2024, 2, 1),
                cache_dir=cache_dir,
                sector_etfs=["XLK"],
            )
            conditions = provider.get_market_conditions()
            self.assertIn("volatility", conditions)
            self.assertIn("SPY", conditions["indices"])
            bars = provider.get_bars("SPY", days=20)
            self.assertIsNotNone(bars)
            assert bars is not None
            self.assertLessEqual(bars.index.max().date(), date(2024, 2, 1))

    def test_historical_finnhub_provider_as_of(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            write_news_day(
                "AAPL",
                date(2024, 3, 1),
                [{"title": "Apple rally continues", "source": "test", "datetime": "2024-03-01", "symbol": "AAPL"}],
                cache_dir,
            )
            write_news_day(
                "AAPL",
                date(2024, 3, 10),
                [{"title": "Future leak", "source": "test", "datetime": "2024-03-10", "symbol": "AAPL"}],
                cache_dir,
            )
            provider = HistoricalFinnhubProvider(
                as_of_date=date(2024, 3, 5),
                cache_dir=cache_dir,
                lookback_days=7,
            )
            news = provider.get_news(["AAPL"])
            titles = [h["title"] for h in news["headlines"]]
            self.assertIn("Apple rally continues", titles)
            self.assertNotIn("Future leak", titles)
            summary = provider.get_sentiment_summary(["AAPL"])
            self.assertIn("positive", summary.lower())


if __name__ == "__main__":
    unittest.main()
