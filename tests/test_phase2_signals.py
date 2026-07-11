import tempfile
import unittest
from pathlib import Path

from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.domain.user.watchlist import Watchlist
from trading_agent.formatters.market_signals import format_market_signals
from trading_agent.signals.mock_providers import build_mock_providers
from trading_agent.signals.aggregator import SignalAggregator
from trading_agent.storage import WatchlistStore


class TestDomainAndFormatters(unittest.TestCase):
    def test_market_signals_round_trip(self):
        aggregator = SignalAggregator(build_mock_providers())
        signals = aggregator.collect(["AAPL", "MSFT"])
        restored = MarketSignals.from_dict(signals.to_dict())
        self.assertEqual(restored.watchlist, ["AAPL", "MSFT"])
        self.assertEqual(len(restored.sources), 4)

    def test_format_market_signals_includes_sources(self):
        aggregator = SignalAggregator(build_mock_providers())
        signals = aggregator.collect(["AAPL"])
        text = format_market_signals(signals)
        self.assertIn("=== Signal Source: market_data ===", text)
        self.assertIn("=== Signal Source: fundamentals ===", text)
        self.assertIn("latest q:", text.lower())


class TestLocalStorage(unittest.TestCase):
    def test_watchlist_store_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WatchlistStore(Path(tmp))
            wl = Watchlist(symbols=["GOOG", "AAPL"], max_symbols=10)
            store.save(wl)
            reloaded = store.load()
            self.assertEqual(reloaded.symbols, ["GOOG", "AAPL"])


if __name__ == "__main__":
    unittest.main()
