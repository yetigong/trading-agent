"""Tests for backtest cycle status accounting."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from trading_agent.backtest.engine import BacktestEngine
from trading_agent.backtest.models import BacktestConfig
from trading_agent.backtest.status import resolve_run_status, summarize_cycles
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.alpaca_historical import write_cached_bars


class TestBacktestStatusHelpers(unittest.TestCase):
    def test_all_success(self):
        status, detail = resolve_run_status(
            [{"status": "success"}, {"status": "success"}]
        )
        self.assertEqual(status, "success")
        self.assertIsNone(detail)

    def test_degraded_when_mostly_ok(self):
        cycles = [{"status": "success"}] * 9 + [{"status": "failed", "error": "boom"}]
        status, detail = resolve_run_status(cycles)
        self.assertEqual(status, "degraded")
        self.assertIn("9/10", detail or "")

    def test_failed_when_below_threshold(self):
        cycles = (
            [{"status": "success"}] * 3
            + [{"status": "failed", "error": "All market analysis strategies failed"}] * 7
        )
        status, detail = resolve_run_status(cycles)
        self.assertEqual(status, "failed")
        self.assertIn("3/10", detail or "")
        summary = summarize_cycles(cycles)
        self.assertEqual(summary["cycles_ok"], 3)
        self.assertEqual(summary["cycles_failed"], 7)


def _write_fixture_bars(cache_dir: Path, symbols, start="2024-01-01", periods=80):
    dates = pd.date_range(start, periods=periods, freq="B")
    bases = {"SPY": 400, "QQQ": 350, "AGG": 100, "AAPL": 180, "XLK": 180}
    for symbol in symbols:
        base = bases.get(symbol, 100)
        closes = [base + i * 0.25 for i in range(len(dates))]
        df = pd.DataFrame(
            {
                "open": closes,
                "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes],
                "close": closes,
                "volume": [1_000_000] * len(dates),
            },
            index=dates,
        )
        write_cached_bars(symbol, df, cache_dir)
    return [d.date() for d in dates]


class FlakyAgent:
    """Stand-in TradingAgent that fails after the first successful cycle."""

    def __init__(self, *args, **kwargs):
        self.calls = 0

    def run_trading_cycle(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "status": "success",
                "hold": False,
                "decisions": [],
                "executed_trades": [],
            }
        return {
            "status": "failed",
            "hold": False,
            "decisions": [],
            "executed_trades": [],
            "error": "All market analysis strategies failed",
        }


class TestBacktestEngineStatus(unittest.TestCase):
    def test_engine_marks_run_failed_on_mostly_failed_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            alpaca_cache = Path(tmp) / "alpaca"
            finnhub_cache = Path(tmp) / "finnhub"
            alpaca_cache.mkdir()
            finnhub_cache.mkdir()
            days = _write_fixture_bars(
                alpaca_cache,
                ["SPY", "QQQ", "AGG", "AAPL", "XLK"],
            )

            config = BacktestConfig(
                start=days[50],
                end=days[-1],
                initial_cash=100_000,
                rebalance_frequency="weekly",
                run_label="flaky",
                symbols=["AAPL"],
                preferences={"max_position_size": 0.25},
                signal_config={"sector_etfs": ["XLK"]},
                alpaca_cache_dir=str(alpaca_cache),
                finnhub_cache_dir=str(finnhub_cache),
                llm_provider="mock",
            )

            with patch(
                "trading_agent.backtest.engine.TradingAgent",
                FlakyAgent,
            ):
                engine = BacktestEngine(
                    llm_client=MockLLMClient(),
                    skip_data_fetch=True,
                )
                result = engine.run(config)

            self.assertEqual(result.status, "failed", result.error)
            self.assertGreaterEqual(len(result.cycle_summaries), 2)
            failed = sum(1 for c in result.cycle_summaries if c.get("status") == "failed")
            self.assertGreater(failed, 0)
            self.assertIn("cycle_stats", result.config)


if __name__ == "__main__":
    unittest.main()
