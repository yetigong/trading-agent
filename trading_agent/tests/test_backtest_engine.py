"""End-to-end backtest engine tests with fixture bars and mock LLM."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from trading_agent.backtest.engine import BacktestEngine, select_rebalance_dates
from trading_agent.backtest.models import BacktestConfig
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.alpaca_historical import write_cached_bars


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


class TestBacktestEngine(unittest.TestCase):
    def test_select_rebalance_dates_weekly(self):
        days = [date(2024, 1, d) for d in range(1, 15) if date(2024, 1, d).weekday() < 5]
        weekly = select_rebalance_dates(days, "weekly")
        self.assertTrue(len(weekly) >= 2)
        self.assertEqual(weekly[-1], days[-1] if days[-1].isocalendar()[:2] == weekly[-1].isocalendar()[:2] else weekly[-1])
        daily = select_rebalance_dates(days, "daily")
        self.assertEqual(daily, days)

    def test_engine_run_with_mock_llm(self):
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
                run_label="mock-test",
                symbols=["AAPL"],
                analysis_params={"time_horizon": "short_term"},
                strategy_params={"risk_management": "standard"},
                rebalance_params={"threshold": 0.05},
                preferences={
                    "risk_tolerance": "moderate",
                    "investment_goal": "growth",
                    "max_position_size": 0.2,
                },
                signal_config={"sector_etfs": ["XLK"]},
                alpaca_cache_dir=str(alpaca_cache),
                finnhub_cache_dir=str(finnhub_cache),
                llm_provider="mock",
            )

            engine = BacktestEngine(
                llm_client=MockLLMClient(),
                skip_data_fetch=True,
            )
            result = engine.run(config)
            self.assertEqual(result.status, "success", result.error)
            self.assertGreater(len(result.equity_curve), 0)
            self.assertIn("total_return", result.metrics)
            self.assertTrue(any(b["name"].startswith("SPY") for b in result.benchmarks))
            self.assertGreater(len(result.cycle_summaries), 0)


if __name__ == "__main__":
    unittest.main()
