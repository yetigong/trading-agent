from datetime import datetime
from typing import List, Optional

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.domain.signals.market_signals import (
    FundamentalSignals,
    MarketDataSignals,
    MarketSignals,
    NewsSignals,
    TechnicalSignals,
)
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.market_data.finnhub_provider import FinnhubNewsProvider


class SignalAggregator:
    """Collect structured market signals from data providers."""

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        news_provider: Optional[FinnhubNewsProvider] = None,
    ):
        self.market_data_provider = market_data_provider
        self.news_provider = news_provider or FinnhubNewsProvider()

    def collect(
        self,
        market_conditions: MarketConditions,
        portfolio: Optional[PortfolioSnapshot] = None,
    ) -> MarketSignals:
        symbols = [p.symbol for p in portfolio.positions] if portfolio else []
        news = self.news_provider.get_news(symbols)

        return MarketSignals(
            market_data=MarketDataSignals(
                indices=market_conditions.indices,
                summary=f"Trend={market_conditions.trend}, volatility={market_conditions.volatility}",
            ),
            technical=TechnicalSignals(
                indicators={"trend": market_conditions.trend, "volatility": market_conditions.volatility},
                summary=f"Market trend is {market_conditions.trend} with {market_conditions.volatility} volatility.",
            ),
            news=NewsSignals(
                headlines=news.get("headlines", []),
                sentiment_summary=self.news_provider.get_sentiment_summary(symbols),
            ),
            fundamentals=FundamentalSignals(
                metrics={},
                summary="Fundamental data provider not yet configured.",
            ),
        )

    @staticmethod
    def market_conditions_from_dict(data: dict) -> MarketConditions:
        ts = data.get("timestamp")
        if not isinstance(ts, datetime):
            ts = datetime.now()
        return MarketConditions(
            volatility=data.get("volatility", "unknown"),
            trend=data.get("trend", "unknown"),
            economic_cycle=data.get("economic_cycle", "unknown"),
            market_phase=data.get("market_phase", "unknown"),
            indices=data.get("indices") or {},
            timestamp=ts,
        )
