import unittest
from unittest.mock import patch

from trading_agent.domain.portfolio.portfolio_snapshot import (
    AccountSummary,
    PortfolioSnapshot,
    Position,
)
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.market_data.mock_fundamentals_provider import MockFundamentalsProvider
from trading_agent.market_data.mock_news_provider import MockNewsProvider
from trading_agent.market_data.mock_provider import MockMarketDataProvider
from trading_agent.signals.aggregator import SignalAggregator
from trading_agent.market_data.finnhub_provider import FinnhubNewsProvider


def _sample_conditions() -> MarketConditions:
    return MarketConditions(
        volatility="moderate",
        trend="bullish",
        economic_cycle="expansion",
        market_phase="normal",
        indices={"SPY": {"current_price": 450.0, "daily_change": 1.2}},
        sector_etfs={
            "XLK": {"return_5d": 3.2, "vs_spy_5d": 2.1},
            "XLE": {"return_5d": -1.2, "vs_spy_5d": -2.3},
        },
    )


def _sample_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account=AccountSummary(buying_power=10000),
        positions=[Position(symbol="AAPL", qty=10, market_value=1750.0)],
        open_orders=[],
    )


class TestSignalAggregator(unittest.TestCase):
    def test_collect_populates_technical_indicators(self):
        agg = SignalAggregator(
            MockMarketDataProvider(),
            MockNewsProvider(),
            MockFundamentalsProvider(),
        )
        signals = agg.collect(_sample_conditions(), _sample_portfolio())

        self.assertIn("SPY", signals.technical.indicators)
        self.assertIn("AAPL", signals.technical.indicators)
        self.assertIn("rsi_14", signals.technical.indicators["SPY"])
        self.assertTrue(signals.technical.summary)

    def test_collect_includes_sector_data(self):
        agg = SignalAggregator(
            MockMarketDataProvider(),
            MockNewsProvider(),
            MockFundamentalsProvider(),
        )
        signals = agg.collect(_sample_conditions(), _sample_portfolio())

        self.assertIn("XLK", signals.market_data.sector_etfs)
        self.assertIn("Leading sector", signals.market_data.summary)

    def test_collect_includes_news_and_fundamentals(self):
        agg = SignalAggregator(
            MockMarketDataProvider(),
            MockNewsProvider(),
            MockFundamentalsProvider(),
        )
        signals = agg.collect(_sample_conditions(), _sample_portfolio())

        self.assertGreater(len(signals.news.headlines), 0)
        self.assertIn("AAPL", signals.fundamentals.metrics)
        self.assertIn("PE=", signals.fundamentals.summary)

    def test_finnhub_parses_company_news(self):
        provider = FinnhubNewsProvider(api_key="test-key")
        payload = [
            {
                "headline": "Apple beats earnings",
                "source": "Reuters",
                "datetime": 1720000000,
                "url": "https://example.com/aapl",
            }
        ]
        with patch.object(provider, "_get_json", return_value=payload):
            news = provider.get_news(["AAPL"])
        self.assertEqual(len(news["headlines"]), 1)
        self.assertEqual(news["headlines"][0]["title"], "Apple beats earnings")
        self.assertEqual(news["headlines"][0]["symbol"], "AAPL")

    def test_finnhub_sentiment_positive_on_bullish_headlines(self):
        provider = FinnhubNewsProvider(api_key="test-key")
        with patch.object(
            provider,
            "get_news",
            return_value={
                "headlines": [
                    {"title": "Stocks rally on strong earnings"},
                    {"title": "Tech surge continues"},
                ]
            },
        ):
            summary = provider.get_sentiment_summary(["AAPL"])
        self.assertIn("Positive", summary)

    def test_market_conditions_from_dict_includes_sectors(self):
        data = {
            "volatility": "low",
            "trend": "bullish",
            "sector_etfs": {"XLK": {"vs_spy_5d": 1.5}},
        }
        mc = SignalAggregator.market_conditions_from_dict(data)
        self.assertEqual(mc.sector_etfs["XLK"]["vs_spy_5d"], 1.5)


if __name__ == "__main__":
    unittest.main()
