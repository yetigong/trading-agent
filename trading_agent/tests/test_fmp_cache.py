import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from trading_agent.market_data.fmp_cache import (
    build_cache_key,
    read_cache,
    write_cache,
)
from trading_agent.market_data.fmp_provider import FMPFundamentalsProvider


class TestFMPCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name) / "cache" / "fmp"
        os.environ["FMP_CACHE_DIR"] = str(self.cache_dir)
        os.environ["FMP_CACHE_ENABLED"] = "true"

    def tearDown(self):
        os.environ.pop("FMP_CACHE_DIR", None)
        os.environ.pop("FMP_CACHE_ENABLED", None)
        self.tmp.cleanup()

    def test_build_cache_key_excludes_apikey(self):
        key = build_cache_key("ratios-ttm", symbol="AAPL", apikey="secret")
        self.assertNotIn("apikey", key)
        self.assertIn("symbol_AAPL", key)

    def test_write_and_read_same_day(self):
        today = datetime.now(timezone.utc).date()
        payload = [{"peRatioTTM": 20.0}]
        write_cache("ratios-ttm", payload, day=today, symbol="AAPL")

        cached = read_cache("ratios-ttm", day=today, symbol="AAPL")
        self.assertEqual(cached, payload)

    def test_cache_miss_on_different_day(self):
        write_cache("ratios-ttm", [{"peRatioTTM": 20.0}], day=date(2026, 7, 11), symbol="AAPL")
        cached = read_cache("ratios-ttm", day=date(2026, 7, 12), symbol="AAPL")
        self.assertIsNone(cached)

    def test_cache_disabled_returns_none(self):
        os.environ["FMP_CACHE_ENABLED"] = "false"
        write_cache("ratios-ttm", [{"peRatioTTM": 20.0}], day=date(2026, 7, 11), symbol="AAPL")
        cached = read_cache("ratios-ttm", day=date(2026, 7, 11), symbol="AAPL")
        self.assertIsNone(cached)
        self.assertFalse(any(self.cache_dir.rglob("*.json")))

    @patch("trading_agent.market_data.fmp_provider.urllib.request.urlopen")
    def test_provider_skips_http_when_cache_hit(self, mock_urlopen):
        provider = FMPFundamentalsProvider(api_key="test-key")
        payload = [{"peRatioTTM": 25.0}]
        today = datetime.now(timezone.utc).date()
        write_cache("ratios-ttm", payload, day=today, symbol="AAPL")

        result = provider._get_json("ratios-ttm", symbol="AAPL")

        self.assertEqual(result, payload)
        mock_urlopen.assert_not_called()

    @patch("trading_agent.market_data.fmp_provider.urllib.request.urlopen")
    def test_provider_fetches_on_cache_miss(self, mock_urlopen):
        provider = FMPFundamentalsProvider(api_key="test-key")
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps([{"peRatioTTM": 30.0}]).encode()

        result = provider._get_json("ratios-ttm", symbol="MSFT")

        self.assertEqual(result, [{"peRatioTTM": 30.0}])
        mock_urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
