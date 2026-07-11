import tempfile
import unittest
from pathlib import Path

import pandas as pd

from trading_agent.signals.indicators import compute_macd, compute_rsi, compute_sma


class TestTechnicalIndicators(unittest.TestCase):
    def test_rsi_and_macd_on_trending_series(self):
        closes = pd.Series([100.0 + i for i in range(80)])
        rsi = compute_rsi(closes)
        macd, signal = compute_macd(closes)
        sma20 = compute_sma(closes, 20)
        self.assertIsNotNone(rsi)
        self.assertIsNotNone(macd)
        self.assertIsNotNone(signal)
        self.assertIsNotNone(sma20)


if __name__ == "__main__":
    unittest.main()
