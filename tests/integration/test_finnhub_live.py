import os
import unittest

from trading_agent.market_data.finnhub_provider import FinnhubNewsProvider


def _has_finnhub_key() -> bool:
    return bool(os.getenv("FINNHUB_API_KEY"))


@unittest.skipUnless(_has_finnhub_key(), "FINNHUB_API_KEY not set")
class TestFinnhubLive(unittest.TestCase):
    def test_company_news_returns_headlines(self):
        provider = FinnhubNewsProvider()
        news = provider.get_news(["AAPL"])
        self.assertNotIn("note", news)
        self.assertGreater(len(news.get("headlines", [])), 0)
        self.assertTrue(news["headlines"][0].get("title"))

    def test_sentiment_summary_not_empty(self):
        provider = FinnhubNewsProvider()
        summary = provider.get_sentiment_summary(["AAPL"])
        self.assertTrue(summary)
        self.assertNotEqual(summary, "Finnhub API key not configured")


if __name__ == "__main__":
    unittest.main()
