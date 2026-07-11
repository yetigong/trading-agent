from datetime import datetime
from typing import List, Optional

from trading_agent.domain.signals.fundamentals import (
    CompanyProfile,
    FinancialRatios,
    FundamentalsPayload,
    FundamentalsSnapshot,
    QuarterlyEarnings,
)
from trading_agent.domain.signals.market_data import (
    IndexSnapshot,
    MarketDataPayload,
    SectorEtfSnapshot,
)
from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.domain.signals.news import NewsArticle, NewsPayload, SentimentSummary, SymbolNews
from trading_agent.domain.signals.signal_source_result import SignalSourceResult
from trading_agent.domain.signals.signal_status import SignalStatus
from trading_agent.domain.signals.technical import SymbolIndicators, TechnicalPayload
from trading_agent.signals.base import SignalProvider


class MockMarketDataSignalProvider(SignalProvider):
    @property
    def source_id(self) -> str:
        return "market_data"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        payload = MarketDataPayload(
            volatility="moderate",
            trend="bullish",
            economic_cycle="expansion",
            market_phase="normal",
            indices=[
                IndexSnapshot("SPY", 450.0, 1.2, 100000000),
                IndexSnapshot("QQQ", 380.0, 1.5, 80000000),
            ],
            sector_etfs=[
                SectorEtfSnapshot("XLK", 2.5),
                SectorEtfSnapshot("XLV", 1.8),
            ],
            sentiment="bullish",
            timestamp=now,
        )
        return SignalSourceResult(
            source_id=self.source_id,
            status=SignalStatus.SUCCESS,
            timestamp=now,
            symbols=symbols,
            payload=payload,
        )


class MockTechnicalSignalProvider(SignalProvider):
    @property
    def source_id(self) -> str:
        return "technical"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        indicators = [
            SymbolIndicators(
                symbol=sym,
                rsi=55.0,
                macd=1.2,
                macd_signal=0.8,
                sma20=180.0,
                sma50=175.0,
                trend="bullish",
                current_price=185.0,
            )
            for sym in (symbols or ["AAPL"])
        ]
        return SignalSourceResult(
            source_id=self.source_id,
            status=SignalStatus.SUCCESS,
            timestamp=now,
            symbols=symbols,
            payload=TechnicalPayload(symbols=indicators),
        )


class MockNewsSignalProvider(SignalProvider):
    @property
    def source_id(self) -> str:
        return "news"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        payload = NewsPayload(
            market_articles=[
                NewsArticle("Markets rise on strong earnings", "MockWire", now),
            ],
            symbol_news=[
                SymbolNews(
                    symbol=symbols[0] if symbols else "AAPL",
                    articles=[NewsArticle("Company beats EPS estimates", "MockNews", now)],
                )
            ],
            sentiment=SentimentSummary(overall="bullish", score=0.62),
        )
        return SignalSourceResult(
            source_id=self.source_id,
            status=SignalStatus.SUCCESS,
            timestamp=now,
            symbols=symbols,
            payload=payload,
        )


class MockFundamentalsSignalProvider(SignalProvider):
    @property
    def source_id(self) -> str:
        return "fundamentals"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        snapshots = []
        for sym in (symbols or ["AAPL"])[:5]:
            snapshots.append(
                FundamentalsSnapshot(
                    symbol=sym,
                    profile=CompanyProfile(sector="Technology", industry="Software", market_cap=2e12),
                    ratios=FinancialRatios(pe=28.4, pb=5.2, roe=147.0),
                    latest_quarterly_earnings=QuarterlyEarnings(
                        period="Q2 2026",
                        report_date="2026-05-01",
                        eps_actual=1.52,
                        eps_estimate=1.48,
                        eps_surprise_pct=2.7,
                        summary="Beat on EPS and revenue",
                    ),
                    peers_analyzed=["MSFT"],
                )
            )
        return SignalSourceResult(
            source_id=self.source_id,
            status=SignalStatus.SUCCESS,
            timestamp=now,
            symbols=symbols,
            payload=FundamentalsPayload(symbols=snapshots),
        )


def build_mock_providers() -> List[SignalProvider]:
    return [
        MockMarketDataSignalProvider(),
        MockTechnicalSignalProvider(),
        MockNewsSignalProvider(),
        MockFundamentalsSignalProvider(),
    ]
