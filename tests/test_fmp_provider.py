import unittest
from unittest.mock import patch

from trading_agent.market_data.fmp_provider import FMPFundamentalsProvider, _first_record


class TestFMPProvider(unittest.TestCase):
    def test_first_record_from_list(self):
        self.assertEqual(_first_record([{"peRatioTTM": 20}]), {"peRatioTTM": 20})

    def test_builds_stable_api_url(self):
        provider = FMPFundamentalsProvider(api_key="test-key")
        with patch.object(provider, "_get_json", return_value=[{"peRatioTTM": 25.0}]) as mock_get:
            metrics = provider._fetch_symbol_metrics("AAPL")
        mock_get.assert_any_call("ratios-ttm", symbol="AAPL")
        mock_get.assert_any_call("key-metrics-ttm", symbol="AAPL")
        mock_get.assert_any_call("financial-growth", symbol="AAPL", limit=1)
        self.assertEqual(metrics.get("pe"), 25.0)

    def test_get_summary_reuses_prefetched_data(self):
        provider = FMPFundamentalsProvider(api_key="test-key")
        prefetched = {
            "metrics": {"AAPL": {"pe": 30.0, "revenue_growth_yoy": 5.0}},
            "symbols": ["AAPL"],
        }
        with patch.object(provider, "get_fundamentals") as mock_fetch:
            summary = provider.get_summary(["AAPL"], prefetched)
        mock_fetch.assert_not_called()
        self.assertIn("AAPL", summary)
        self.assertIn("PE=30.0", summary)


if __name__ == "__main__":
    unittest.main()
