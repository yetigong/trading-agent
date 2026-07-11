import tempfile
import unittest
from pathlib import Path

from mock_alpaca_client import MockAlpacaTradingClient
from trader import TradingAgent
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.mock_provider import MockMarketDataProvider


class TestTradingCycleIntegration(unittest.TestCase):
    def _make_agent(self, llm_client=None):
        tmp = tempfile.mkdtemp()
        return TradingAgent(
            llm_client=llm_client or MockLLMClient(),
            market_data_provider=MockMarketDataProvider(),
            alpaca_client=MockAlpacaTradingClient(),
            userdata_dir=Path(tmp),
            use_mock_signals=True,
        )

    def test_full_cycle_with_mocks(self):
        agent = self._make_agent()

        results = agent.run_trading_cycle(
            analysis_params={"time_horizon": "medium-term"},
            strategy_params={"timeframe": "immediate"},
            rebalance_params={"target_allocation": "balanced"},
        )

        self.assertEqual(results["status"], "success")
        self.assertIn("cycle_id", results)
        self.assertIn("market_conditions", results)
        self.assertIn("market_signals", results)
        self.assertIsNotNone(results["analysis"])
        self.assertEqual(len(results["executed_trades"]), 1)
        self.assertEqual(results["executed_trades"][0]["status"], "executed")
        self.assertEqual(results["executed_trades"][0]["symbol"], "AAPL")

    def test_hold_when_no_decisions(self):
        llm = MockLLMClient(
            responses={
                "select": "general",
            }
        )

        original_generate = llm.generate_response

        def custom_generate(prompt, context=None):
            if "json object only" in prompt.lower():
                return '{"decisions": []}'
            return original_generate(prompt, context)

        llm.generate_response = custom_generate

        agent = self._make_agent(llm_client=llm)

        results = agent.run_trading_cycle()
        self.assertEqual(results["status"], "success")
        self.assertTrue(results["hold"])
        self.assertEqual(len(results["executed_trades"]), 0)


if __name__ == "__main__":
    unittest.main()
