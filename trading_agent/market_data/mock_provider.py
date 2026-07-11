import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """Mock market data provider for testing."""

    def __init__(self):
        self.mock_data = {
            "volatility": "moderate",
            "trend": "bullish",
            "economic_cycle": "expansion",
            "market_phase": "normal",
            "timestamp": datetime.now(),
            "indices": {
                "SPY": {
                    "current_price": 450.0,
                    "daily_change": 1.2,
                    "volume": 100000000,
                },
                "QQQ": {
                    "current_price": 380.0,
                    "daily_change": 1.5,
                    "volume": 80000000,
                },
                "DIA": {
                    "current_price": 350.0,
                    "daily_change": 0.8,
                    "volume": 60000000,
                },
                "IWM": {
                    "current_price": 200.0,
                    "daily_change": 1.0,
                    "volume": 40000000,
                },
            },
            "sector_etfs": {
                "XLK": {"current_price": 180.0, "daily_change": 2.1, "volume": 5000000, "return_5d": 3.2, "vs_spy_5d": 2.1},
                "XLV": {"current_price": 140.0, "daily_change": 0.5, "volume": 4000000, "return_5d": 1.0, "vs_spy_5d": -0.1},
                "XLF": {"current_price": 42.0, "daily_change": 0.3, "volume": 3000000, "return_5d": 0.8, "vs_spy_5d": -0.3},
                "XLE": {"current_price": 88.0, "daily_change": -0.5, "volume": 2500000, "return_5d": -1.2, "vs_spy_5d": -2.3},
            },
        }

        self._bar_prices = {
            "SPY": 450.0,
            "AAPL": 175.0,
            "MSFT": 380.0,
            "GOOGL": 140.0,
        }

    def get_market_conditions(self) -> Dict[str, Any]:
        """Get mock market conditions."""
        return self.mock_data

    def get_market_volatility(self) -> str:
        return self.mock_data["volatility"]

    def get_market_trend(self) -> str:
        return self.mock_data["trend"]

    def get_economic_cycle(self) -> str:
        return self.mock_data["economic_cycle"]

    def get_market_phase(self) -> str:
        return self.mock_data["market_phase"]

    def get_bars(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        """Generate synthetic uptrending bars for indicator computation."""
        base = self._bar_prices.get(symbol, 100.0)
        n = max(days, 60)
        dates = pd.date_range(end=datetime.now(), periods=n, freq="D")
        noise = np.random.default_rng(42 if symbol == "SPY" else hash(symbol) % 10000).normal(0, 0.5, n)
        trend = np.linspace(-2, 2, n)
        closes = base + trend + np.cumsum(noise) * 0.1
        return pd.DataFrame({
            "close": closes,
            "volume": np.full(n, 1_000_000),
        }, index=dates)

    def get_supported_indicators(self) -> Dict[str, str]:
        return {
            "volatility": "Market volatility level (low, moderate, high)",
            "trend": "Market trend (bullish, neutral, bearish)",
            "economic_cycle": "Economic cycle phase (expansion, peak, contraction, trough)",
            "market_phase": "Market phase (normal, bubble, crash, recovery)",
            "indices": "Major market indices (SPY, QQQ, DIA, IWM)",
            "sector_etfs": "Sector SPDR ETFs with relative strength vs SPY",
        }
