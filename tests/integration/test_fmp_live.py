import os
import unittest

from trading_agent.market_data.fmp_provider import FMPFundamentalsProvider


def _has_fmp_key() -> bool:
    return bool(os.getenv("FMP_API_KEY"))


@unittest.skipUnless(_has_fmp_key(), "FMP_API_KEY not set")
class TestFMPLive(unittest.TestCase):
    def test_fundamentals_returns_metrics(self):
        provider = FMPFundamentalsProvider()
        data = provider.get_fundamentals(["AAPL"])
        self.assertNotIn("note", data)
        metrics = data.get("metrics", {})
        self.assertIn("AAPL", metrics)
        self.assertTrue(
            metrics["AAPL"].get("pe") is not None
            or metrics["AAPL"].get("pb") is not None
            or metrics["AAPL"].get("revenue_growth_yoy") is not None
        )

    def test_summary_not_empty(self):
        provider = FMPFundamentalsProvider()
        summary = provider.get_summary(["AAPL"])
        self.assertTrue(summary)
        self.assertNotEqual(summary, "FMP API key not configured")


if __name__ == "__main__":
    unittest.main()
