import unittest

import numpy as np
import pandas as pd

from trading_agent.signals.indicators import (
    compute_indicators_for_bars,
    compute_macd,
    compute_rsi,
    compute_sma,
    summarize_technical_indicators,
)


def _uptrend_closes(n: int = 80, start: float = 100.0) -> pd.Series:
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.3, n)
    trend = np.linspace(0, 20, n)
    return pd.Series(start + trend + noise)


class TestIndicators(unittest.TestCase):
    def test_compute_sma(self):
        close = _uptrend_closes()
        sma = compute_sma(close, 20)
        self.assertIsNotNone(sma)
        self.assertGreater(sma, 100)

    def test_compute_rsi_in_range(self):
        close = _uptrend_closes()
        rsi = compute_rsi(close)
        self.assertIsNotNone(rsi)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)

    def test_compute_rsi_overbought_on_strong_uptrend(self):
        close = pd.Series(np.linspace(100, 200, 60))
        rsi = compute_rsi(close)
        self.assertIsNotNone(rsi)
        self.assertGreater(rsi, 50)

    def test_compute_macd_returns_keys(self):
        close = _uptrend_closes()
        macd = compute_macd(close)
        self.assertIn("macd", macd)
        self.assertIn("signal", macd)
        self.assertIn("histogram", macd)
        self.assertIsNotNone(macd["macd"])

    def test_compute_indicators_for_bars(self):
        close = _uptrend_closes()
        bars = pd.DataFrame({"close": close, "volume": np.ones(len(close))})
        result = compute_indicators_for_bars(bars)
        self.assertIn("rsi_14", result)
        self.assertIn("sma_20", result)
        self.assertIn("macd", result)

    def test_summarize_technical_indicators(self):
        indicators = {
            "SPY": {"rsi_14": 65.0, "macd": {"histogram": 0.5}, "sma_20": 450.0, "sma_50": 440.0},
        }
        summary = summarize_technical_indicators(indicators)
        self.assertIn("SPY", summary)
        self.assertIn("RSI=65.0", summary)

    def test_insufficient_data_returns_none_or_empty(self):
        short = pd.Series([100, 101, 102])
        self.assertIsNone(compute_rsi(short))
        self.assertEqual(compute_macd(short), {"macd": None, "signal": None, "histogram": None})


if __name__ == "__main__":
    unittest.main()
