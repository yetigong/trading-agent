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
from trading_agent.market_data.fmp_provider import FMPFundamentalsProvider
from trading_agent.market_data.fundamentals_base import FundamentalDataProvider
from trading_agent.market_data.news_base import NewsDataProvider
from trading_agent.signals.indicators import (
    compute_indicators_for_bars,
    summarize_technical_indicators,
)
from trading_agent.signals.sources import (
    BAR_LOOKBACK_DAYS,
    SignalCollectionContext,
    summarize_sector_rotation,
)


class SignalAggregator:
    """Collect structured market signals from data providers."""

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        news_provider: Optional[NewsDataProvider] = None,
        fundamentals_provider: Optional[FundamentalDataProvider] = None,
    ):
        self.market_data_provider = market_data_provider
        self.news_provider = news_provider or FinnhubNewsProvider()
        self.fundamentals_provider = fundamentals_provider or FMPFundamentalsProvider()

    def collect(
        self,
        market_conditions: MarketConditions,
        portfolio: Optional[PortfolioSnapshot] = None,
    ) -> MarketSignals:
        ctx = SignalCollectionContext.from_inputs(market_conditions, portfolio)
        technical_indicators = self._collect_technical_indicators(ctx)
        sector_summary = summarize_sector_rotation(market_conditions.sector_etfs)

        market_summary_parts = [
            f"Trend={market_conditions.trend}, volatility={market_conditions.volatility}",
        ]
        if sector_summary:
            market_summary_parts.append(sector_summary)

        news = self.news_provider.get_news(ctx.symbols)
        fundamentals_data = self.fundamentals_provider.get_fundamentals(ctx.symbols)

        return MarketSignals(
            market_data=MarketDataSignals(
                indices=market_conditions.indices,
                sector_etfs=market_conditions.sector_etfs,
                summary="; ".join(market_summary_parts),
            ),
            technical=TechnicalSignals(
                indicators=technical_indicators,
                summary=summarize_technical_indicators(technical_indicators),
            ),
            news=NewsSignals(
                headlines=news.get("headlines", []),
                sentiment_summary=self.news_provider.get_sentiment_summary(ctx.symbols),
            ),
            fundamentals=FundamentalSignals(
                metrics=fundamentals_data.get("metrics") or {},
                summary=self.fundamentals_provider.get_summary(
                    ctx.symbols, fundamentals_data
                ),
            ),
        )

    def _collect_technical_indicators(self, ctx: SignalCollectionContext) -> dict:
        symbols = ["SPY"] + [s for s in ctx.symbols if s != "SPY"]
        indicators = {}

        for symbol in symbols:
            if symbol in ctx.bar_cache:
                bars = ctx.bar_cache[symbol]
            else:
                bars = self.market_data_provider.get_bars(symbol, BAR_LOOKBACK_DAYS)
                ctx.bar_cache[symbol] = bars

            computed = compute_indicators_for_bars(bars)
            if computed:
                indicators[symbol] = computed

        return indicators

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
            sector_etfs=data.get("sector_etfs") or {},
            timestamp=ts,
        )
