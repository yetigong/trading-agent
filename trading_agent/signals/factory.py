from typing import Optional

import pandas as pd

from trading_agent.market_data.base import MarketDataProvider
from trading_agent.signals.fundamentals import FundamentalsSignalProvider
from trading_agent.signals.market_data import MarketDataSignalProvider
from trading_agent.signals.mock_providers import build_mock_providers
from trading_agent.signals.news import FinnhubClient, NewsSignalProvider
from trading_agent.signals.technical import TechnicalSignalProvider


def build_signal_providers(
    market_data_provider: MarketDataProvider,
    use_mock: bool = False,
) -> list:
    if use_mock:
        return build_mock_providers()
    finnhub = FinnhubClient()
    return [
        MarketDataSignalProvider(market_data_provider),
        TechnicalSignalProvider(market_data_provider),
        NewsSignalProvider(finnhub),
        FundamentalsSignalProvider(finnhub),
    ]
