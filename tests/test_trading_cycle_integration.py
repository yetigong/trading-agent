import unittest

from trading_agent.broker.mock_client import MockAlpacaTradingClient
from trading_agent.orchestrator.agent import TradingAgent
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.mock_fundamentals_provider import MockFundamentalsProvider
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
        self.assertIn("executed_trades", results)
        self.assertIsInstance(results["executed_trades"], list)
        self.assertIn("hold", results)

    def test_hold_when_no_decisions(self):
        llm = MockLLMClient()
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

    def test_fails_when_all_analysis_strategies_fail(self):
        """Empty fundamentals are skipped; remaining analysis failures must still fail the cycle."""
        class FailingLLM:
            def generate_response(self, prompt, context=None):
                raise RuntimeError("LLM unavailable")

        agent = TradingAgent(
            llm_client=FailingLLM(),
            market_data_provider=MockMarketDataProvider(),
            alpaca_client=MockAlpacaTradingClient(),
            fundamentals_provider=MockFundamentalsProvider(metrics={}),
        )

        results = agent.run_trading_cycle()
        self.assertEqual(results["status"], "failed")
        self.assertIn("analysis", results["error"].lower())
        analysis = agent.last_market_analysis
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.fundamental.status, "skipped")
        self.assertTrue(analysis.has_failure())


if __name__ == "__main__":
    unittest.main()
