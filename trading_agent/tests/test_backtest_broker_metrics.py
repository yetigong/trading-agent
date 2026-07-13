"""Tests for BacktestBroker, metrics, and benchmarks."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from trading_agent.domain.broker import OrderSide

from trading_agent.backtest.benchmarks import run_benchmarks
from trading_agent.backtest.broker import BacktestBroker
from trading_agent.backtest.metrics import compute_metrics, max_drawdown, total_return
from trading_agent.market_data.alpaca_historical import write_cached_bars


class TestBacktestBroker(unittest.TestCase):
    def test_buy_sell_and_equity(self):
        prices = {"AAPL": 100.0}

        def price_fn(symbol):
            return prices.get(symbol)

        broker = BacktestBroker(initial_cash=10_000, price_fn=price_fn)
        broker.set_as_of_date(date(2024, 1, 2))
        broker.place_market_order("AAPL", 10, OrderSide.BUY)
        self.assertAlmostEqual(broker.cash, 9000.0)
        self.assertEqual(len(broker.get_positions()), 1)
        prices["AAPL"] = 110.0
        equity = broker.mark_to_market()
        self.assertAlmostEqual(equity, 9000 + 1100)

        broker.place_market_order("AAPL", 10, OrderSide.SELL)
        self.assertAlmostEqual(broker.cash, 10100.0)
        self.assertEqual(len(broker.get_positions()), 0)

    def test_insufficient_funds(self):
        broker = BacktestBroker(initial_cash=100, price_fn=lambda s: 50.0)
        with self.assertRaises(Exception):
            broker.place_market_order("AAPL", 10, OrderSide.BUY)


class TestMetrics(unittest.TestCase):
    def test_total_return_and_drawdown(self):
        curve = [
            {"date": "2024-01-01", "equity": 100},
            {"date": "2024-01-02", "equity": 110},
            {"date": "2024-01-03", "equity": 99},
            {"date": "2024-01-04", "equity": 120},
        ]
        self.assertAlmostEqual(total_return(curve, 100), 0.2)
        self.assertAlmostEqual(max_drawdown(curve), (110 - 99) / 110)

        metrics = compute_metrics("test", curve, 100, spy_curve=curve)
        self.assertEqual(metrics.name, "test")
        self.assertAlmostEqual(metrics.total_return, 0.2)


class TestBenchmarks(unittest.TestCase):
    def test_run_benchmarks_on_fixture_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            dates = pd.date_range("2024-01-01", periods=80, freq="B")
            for symbol, base in [("SPY", 400), ("QQQ", 350), ("AGG", 100), ("AAPL", 180)]:
                closes = [base + i * 0.2 for i in range(len(dates))]
                df = pd.DataFrame(
                    {"open": closes, "high": closes, "low": closes, "close": closes, "volume": 1_000_000},
                    index=dates,
                )
                write_cached_bars(symbol, df, cache_dir)

            trading_days = [d.date() for d in dates[50:]]

            def price_fn(symbol, day):
                from trading_agent.market_data.alpaca_historical import read_cached_bars, slice_bars_as_of

                bars = slice_bars_as_of(read_cached_bars(symbol, cache_dir), day)
                if bars is None or bars.empty:
                    return None
                return float(bars["close"].iloc[-1])

            results = run_benchmarks(
                trading_days,
                initial_cash=100_000,
                price_fn=price_fn,
                universe=["AAPL"],
                cache_dir=cache_dir,
            )
            names = {r.name for r in results}
            self.assertIn("SPY buy-and-hold", names)
            self.assertIn("SMA(20/50) SPY", names)
            for r in results:
                self.assertIsInstance(r.total_return, float)


if __name__ == "__main__":
    unittest.main()
