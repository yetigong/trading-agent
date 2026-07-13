import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trading_agent.domain.user.signal_config import SignalConfig
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.domain.user.watchlist import Watchlist
from trading_agent.storage import (
    AnalysisConfigStore,
    PreferencesStore,
    SignalConfigStore,
    WatchlistStore,
)


class TestJsonFileStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.example_dir = Path(self.tmp.name) / "data.example"
        self.example_dir.mkdir()
        (self.example_dir / "preferences.json").write_text(
            json.dumps(
                {
                    "risk_tolerance": "aggressive",
                    "investment_goal": "income",
                    "max_position_size": 0.2,
                    "investment_horizon": "long-term",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_seeds_from_example_on_first_load(self):
        store = PreferencesStore(data_dir=self.data_dir, example_dir=self.example_dir)
        prefs = store.load_preferences()
        self.assertEqual(prefs.risk_tolerance, "aggressive")
        self.assertTrue((self.data_dir / "preferences.json").exists())

    def test_save_and_reload_round_trip(self):
        store = WatchlistStore(data_dir=self.data_dir, example_dir=self.example_dir)
        store.save({"symbols": ["AAPL", "MSFT"]})
        watchlist = store.load_watchlist()
        self.assertEqual(watchlist.symbols, ["AAPL", "MSFT"])

    def test_analysis_config_store_loads_seeded_data(self):
        (self.example_dir / "analysis_params.json").write_text(
            json.dumps({"time_horizon": "short-term", "focus_areas": "energy"}),
            encoding="utf-8",
        )
        store = AnalysisConfigStore(data_dir=self.data_dir, example_dir=self.example_dir)
        data = store.load()
        self.assertEqual(data["time_horizon"], "short-term")
        self.assertEqual(data["focus_areas"], "energy")


class TestDomainModels(unittest.TestCase):
    def test_signal_config_defaults(self):
        config = SignalConfig.from_dict({})
        self.assertEqual(len(config.sector_etfs), 10)
        self.assertIn("fundamentals", config.enabled_sources)

    def test_watchlist_from_dict(self):
        watchlist = Watchlist.from_dict({"symbols": ["NVDA"]})
        self.assertEqual(watchlist.symbols, ["NVDA"])

    def test_user_preferences_round_trip(self):
        prefs = UserPreferences(risk_tolerance="conservative", investment_goal="preservation")
        restored = UserPreferences.from_dict(prefs.to_dict())
        self.assertEqual(restored.risk_tolerance, "conservative")
        self.assertEqual(restored.investment_goal, "preservation")


class TestSignalConfigStore(unittest.TestCase):
    def test_load_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            example_dir = Path(tmp) / "data.example"
            example_dir.mkdir()
            (example_dir / "signal_config.json").write_text(
                json.dumps({"sector_etfs": ["XLK", "XLF"], "enabled_sources": ["technical"]}),
                encoding="utf-8",
            )
            store = SignalConfigStore(data_dir=data_dir, example_dir=example_dir)
            config = store.load_config()
            self.assertEqual(config.sector_etfs, ["XLK", "XLF"])
            self.assertEqual(config.enabled_sources, ["technical"])


if __name__ == "__main__":
    unittest.main()
