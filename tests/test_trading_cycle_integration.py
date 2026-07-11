import unittest

from mock_alpaca_client import MockAlpacaTradingClient
from trading_agent.orchestrator.agent import TradingAgent
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.mock_provider import MockMarketDataProvider


class TestTradingCycleIntegration(unittest.TestCase):
    def test_full_cycle_with_mocks(self):
        agent = TradingAgent(
            llm_client=MockLLMClient(),
            market_data_provider=MockMarketDataProvider(),
            alpaca_client=MockAlpacaTradingClient(),
        )

        results = agent.run_trading_cycle(
            analysis_params={"time_horizon": "medium-term"},
            strategy_params={"timeframe": "immediate"},
            rebalance_params={"target_allocation": "balanced"},
        )

        self.assertEqual(results["status"], "success")
        self.assertIn("cycle_id", results)
        self.assertIn("market_conditions", results)
        self.assertIn("preparation", results)
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

        agent = TradingAgent(
            llm_client=llm,
            market_data_provider=MockMarketDataProvider(),
            alpaca_client=MockAlpacaTradingClient(),
        )

        results = agent.run_trading_cycle()
        self.assertEqual(results["status"], "success")
        self.assertTrue(results["hold"])
        self.assertEqual(len(results["executed_trades"]), 0)


if __name__ == "__main__":
    unittest.main()
