"""Tests for learning-loop Phase A (prompts + backtest learner isolation)."""

import json
import tempfile
import unittest
from pathlib import Path

from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.learner import LearnerAgent
from trading_agent.analysis.general import GeneralAnalysisStrategy
from trading_agent.domain.cycle import StrategyContext
from trading_agent.domain.portfolio.portfolio_snapshot import AccountSummary, PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.formatters.knowledge import (
    format_analysis_knowledge_block,
    format_strategy_knowledge_block,
)
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.strategies.general import GeneralTradingStrategy


class TestKnowledgePromptFormatting(unittest.TestCase):
    def test_analysis_block_includes_lessons_and_weights(self):
        block = format_analysis_knowledge_block(
            {
                "knowledge_lessons": ["held cash in H1", "news noisy"],
                "signal_weights": {"news": 1.2, "technicals": 0.8},
            }
        )
        self.assertIn("held cash in H1", block)
        self.assertIn("news=1.20", block)
        self.assertIn("technicals=0.80", block)

    def test_strategy_block_includes_trade_bias(self):
        block = format_strategy_knowledge_block(
            {
                "recent_trade_bias": 0.25,
                "knowledge_lessons": ["backtest lagged SPY"],
                "backtest_validation_summary": "Sharpe 0.4 on 2024 H1",
            }
        )
        self.assertIn("Recent Trade Bias: +0.25", block)
        self.assertIn("backtest lagged SPY", block)
        self.assertIn("Sharpe 0.4 on 2024 H1", block)


class TestPromptsIncludeKnowledge(unittest.TestCase):
    def test_general_analysis_prompt_contains_kb_fields(self):
        captured = {}

        class CaptureLLM(MockLLMClient):
            def generate_response(self, prompt, **kwargs):
                captured["prompt"] = prompt
                return "overview ok"

        strategy = GeneralAnalysisStrategy(llm_client=CaptureLLM())
        portfolio = PortfolioSnapshot(
            account=AccountSummary(
                buying_power=10000, cash=10000, portfolio_value=10000
            ),
            positions=[],
            open_orders=[],
        )
        strategy.analyze(
            portfolio=portfolio,
            user_preferences=UserPreferences(),
            analysis_params={
                "market_conditions": MarketConditions(trend="bullish"),
                "knowledge_lessons": ["fixture lesson alpha"],
                "signal_weights": {"news": 1.1},
            },
        )
        self.assertIn("fixture lesson alpha", captured["prompt"])
        self.assertIn("news=1.10", captured["prompt"])

    def test_general_strategy_prompt_contains_bias(self):
        captured = {}

        class CaptureLLM(MockLLMClient):
            def generate_response(self, prompt, **kwargs):
                captured["prompt"] = prompt
                return "[]"

        strategy = GeneralTradingStrategy(llm_client=CaptureLLM())
        context = StrategyContext(
            market_conditions=MarketConditions(trend="bullish"),
            market_analysis=None,
            portfolio=PortfolioSnapshot(
                account=AccountSummary(
                    buying_power=10000, cash=10000, portfolio_value=10000
                ),
                positions=[],
                open_orders=[],
            ),
            user_preferences=UserPreferences(),
            strategy_params={"recent_trade_bias": -0.2},
        )
        strategy.make_decisions(context)
        self.assertIn("Recent Trade Bias: -0.20", captured["prompt"])


class TestBacktestLearnerIsolation(unittest.TestCase):
    def test_engine_disables_learner(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "user_id": "default",
                        "derived_state": {
                            "signal_weights": {},
                            "strategy_preferences": {},
                        },
                        "lessons": [],
                        "backtest_validations": [],
                        "config_recommendations": [],
                        "promotions": [],
                    }
                )
            )
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            self.assertEqual(kb.load()["lessons"], [])

            from trading_agent.orchestrator.agent import TradingAgent
            from trading_agent.broker.mock_client import MockAlpacaTradingClient
            from trading_agent.market_data.mock_provider import MockMarketDataProvider
            from trading_agent.market_data.mock_fundamentals_provider import (
                MockFundamentalsProvider,
            )

            agent = TradingAgent(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                fundamentals_provider=MockFundamentalsProvider(metrics={}),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=kb,
                disabled=["learner"],
            )
            self.assertFalse(agent.registry.get("learner").is_enabled())
            # Even if a cycle runs, disabled learner must not append lessons.
            agent.run_trading_cycle()
            self.assertEqual(len(kb.load()["lessons"]), 0)


class TestLessonsUpdateArtifact(unittest.TestCase):
    def test_learner_appends_lessons_update_to_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
            )
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            artifact = Path(tmp) / "cycle.json"
            artifact.write_text(json.dumps({"cycle_id": "abc", "agents": {}}))

            class FakeLog:
                artifact_path = str(artifact)

            learner = LearnerAgent(knowledge_base=kb)
            learner.run(
                {
                    "cycle_id": "abcdef12-3456",
                    "status": "success",
                    "hold": True,
                    "executed_trades": [],
                    "preparation": None,
                    "decision_log": FakeLog(),
                }
            )
            payload = json.loads(artifact.read_text())
            self.assertIn("lessons_update", payload["agents"])
            self.assertTrue(payload["agents"]["lessons_update"]["lessons_added"])


if __name__ == "__main__":
    unittest.main()
