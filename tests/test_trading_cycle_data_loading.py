import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trading_agent.orchestrator.trading_cycle import TradingCycle


class TestTradingCycleDataLoading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.example_dir = Path(self.tmp.name) / "data.example"
        self.example_dir.mkdir()
        os.environ["DATA_DIR"] = str(self.data_dir)
        os.environ["EXAMPLE_DATA_DIR"] = str(self.example_dir)
        self._write_examples()

    def tearDown(self):
        os.environ.pop("DATA_DIR", None)
        os.environ.pop("EXAMPLE_DATA_DIR", None)
        self.tmp.cleanup()

    def _write_examples(self):
        files = {
            "preferences.json": {
                "risk_tolerance": "conservative",
                "investment_goal": "preservation",
                "max_position_size": 0.05,
                "investment_horizon": "long-term",
            },
            "analysis_params.json": {
                "time_horizon": "long-term",
                "focus_areas": "utilities",
                "regions": "US",
            },
            "strategy_params.json": {
                "timeframe": "weekly",
                "risk_management": "strict",
                "position_sizing": "fixed",
            },
            "rebalance_params.json": {
                "target_allocation": "growth",
                "threshold": 10,
                "sector_weights": "equal",
            },
            "signal_config.json": {
                "sector_etfs": ["XLK", "XLF"],
                "enabled_sources": ["market_data", "technical"],
            },
            "watchlist.json": {"symbols": ["TSLA"]},
        }
        for name, payload in files.items():
            (self.example_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_cycle_loads_config_from_data_dir(self):
        cycle = TradingCycle()
        self.assertEqual(cycle.user_preferences.risk_tolerance, "conservative")
        self.assertEqual(cycle.analysis_params["focus_areas"], "utilities")
        self.assertEqual(cycle.strategy_params["timeframe"], "weekly")
        self.assertEqual(cycle.rebalance_params["threshold"], 10)
        self.assertEqual(cycle.signal_config.sector_etfs, ["XLK", "XLF"])
        self.assertEqual(cycle.watchlist.symbols, ["TSLA"])

    @patch("trading_agent.orchestrator.trading_cycle.AlpacaMarketDataProvider")
    @patch("trading_agent.orchestrator.trading_cycle.AlpacaTradingClient")
    @patch("trading_agent.orchestrator.trading_cycle.get_llm_client")
    def test_initialize_components_passes_preferences_and_sectors(
        self, mock_llm, mock_alpaca, mock_market
    ):
        cycle = TradingCycle()
        cycle.initialize_components()

        mock_market.assert_called_once_with(sector_etfs=["XLK", "XLF"])
        self.assertEqual(cycle.agent.user_preferences.risk_tolerance, "conservative")
        self.assertEqual(cycle.agent.user_preferences.max_position_size, 0.05)


if __name__ == "__main__":
    unittest.main()
