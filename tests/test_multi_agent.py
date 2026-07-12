import tempfile
import unittest
from pathlib import Path

from trading_agent.agents.coordinator import CycleCoordinator
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.learner import LearnerAgent
from trading_agent.agents.messages import (
    ExecutionReport,
    MarketSummary,
    StrategyOption,
    StrategyPlan,
)
from trading_agent.agents.registry import AgentRegistry, build_default_registry
from trading_agent.broker.mock_client import MockAlpacaTradingClient
from trading_agent.domain.cycle import MarketAnalysis, AnalysisResult, TradingDecision
from trading_agent.domain.portfolio.portfolio_snapshot import AccountSummary, PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.mock_provider import MockMarketDataProvider
from trading_agent.orchestrator.agent import TradingAgent
from trading_agent.signals.aggregator import SignalAggregator


class TestKnowledgeBase(unittest.TestCase):
    def test_load_save_and_append_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
            )
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            self.assertEqual(kb.lessons(), [])
            kb.append_lesson("first lesson")
            kb.update_weights_and_prefs(
                signal_weights={"news": 1.2},
                strategy_preferences={"recent_trade_bias": 0.1},
            )
            self.assertEqual(kb.lessons(), ["first lesson"])
            self.assertEqual(kb.signal_weights()["news"], 1.2)
            self.assertEqual(kb.strategy_preferences()["recent_trade_bias"], 0.1)


class TestLearnerAgent(unittest.TestCase):
    def test_appends_lesson_for_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
            )
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            learner = LearnerAgent(knowledge_base=kb)
            result = learner.run(
                {
                    "cycle_id": "abcdef12-3456",
                    "status": "success",
                    "hold": True,
                    "executed_trades": [],
                    "preparation": None,
                }
            )
            self.assertEqual(len(result["lessons_update"].lessons_added), 1)
            self.assertIn("held", result["lessons_update"].lessons_added[0])
            self.assertEqual(len(kb.lessons()), 1)


class TestCoordinatorWithMocks(unittest.TestCase):
    def test_pipeline_order_with_fake_agents(self):
        order = []

        class FakeAgent:
            def __init__(self, name):
                self.name = name

            def is_enabled(self):
                return True

            def run(self, ctx):
                order.append(self.name)
                if self.name == "market_analyzer":
                    conditions = MarketConditions(trend="bullish")
                    portfolio = PortfolioSnapshot(
                        account=AccountSummary(
                            buying_power=10000,
                            cash=10000,
                            portfolio_value=10000,
                        ),
                        positions=[],
                        open_orders=[],
                    )
                    analysis = MarketAnalysis(
                        general=AnalysisResult(
                            strategy_name="General",
                            status="success",
                            summary="bullish outlook",
                        ),
                        technical=AnalysisResult(
                            strategy_name="Technical",
                            status="success",
                            summary="uptrend",
                        ),
                        fundamental=AnalysisResult(
                            strategy_name="Fundamental",
                            status="success",
                            summary="solid",
                        ),
                    )
                    ctx["market_conditions"] = conditions
                    ctx["portfolio"] = portfolio
                    ctx["market_analysis"] = analysis
                    ctx["market_summary"] = MarketSummary(
                        market_conditions=conditions,
                        market_analysis=analysis,
                        portfolio=portfolio,
                        trend="bullish",
                        sentiment="positive",
                    )
                elif self.name == "trading_strategizer":
                    decision = TradingDecision(
                        action="BUY", symbol="AAPL", quantity=1, reasoning="test"
                    )
                    option = StrategyOption(
                        name="test", rationale="r", decisions=[decision]
                    )
                    ctx["strategy_plan"] = StrategyPlan(
                        options=[option],
                        selected=option,
                        decisions=[decision],
                        strategy_hold=False,
                    )
                    ctx["decisions"] = [decision]
                    ctx["rebalancing"] = {"status": "skipped"}
                    ctx["strategy_hold"] = False
                elif self.name == "trade_executor":
                    ctx["preparation"] = None
                    ctx["executed_trades"] = []
                    ctx["hold"] = False
                    ctx["execution_report"] = ExecutionReport(
                        preparation=None, executed_trades=[], hold=False
                    )
                elif self.name == "decision_logger":
                    from trading_agent.domain.cycle import CycleResult

                    ctx["cycle_result"] = CycleResult(
                        status="success",
                        cycle_id=ctx["cycle_id"],
                        timestamp=ctx["timestamp"],
                        hold=False,
                        decisions=[],
                        executed_trades=[],
                    ).to_dict()
                elif self.name == "learner":
                    ctx["lessons_update"] = {"lessons_added": ["ok"]}

        registry = AgentRegistry(
            agents={
                "market_analyzer": FakeAgent("market_analyzer"),
                "trading_strategizer": FakeAgent("trading_strategizer"),
                "trade_executor": FakeAgent("trade_executor"),
                "decision_logger": FakeAgent("decision_logger"),
                "learner": FakeAgent("learner"),
            }
        )
        result = CycleCoordinator(registry).run()
        self.assertEqual(
            order,
            [
                "market_analyzer",
                "trading_strategizer",
                "trade_executor",
                "decision_logger",
                "learner",
            ],
        )
        self.assertEqual(result["status"], "success")

    def test_registry_disable_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
            )
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            prefs = UserPreferences()
            llm = MockLLMClient()
            market = MockMarketDataProvider()
            alpaca = MockAlpacaTradingClient()
            aggregator = SignalAggregator(market)
            registry = build_default_registry(
                llm_client=llm,
                market_data_provider=market,
                alpaca_client=alpaca,
                signal_aggregator=aggregator,
                user_preferences=prefs,
                knowledge_base=kb,
                disabled=["learner"],
            )
            names = [a.name for a in registry.enabled_pipeline()]
            self.assertNotIn("learner", names)
            self.assertIn("market_analyzer", names)


class TestTradingAgentMultiAgentFacade(unittest.TestCase):
    def test_full_cycle_still_works_via_coordinator(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
            )
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            agent = TradingAgent(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=kb,
                write_artifact=False,
            )
            results = agent.run_trading_cycle()
            self.assertEqual(results["status"], "success")
            self.assertIn("agents", results)
            self.assertIsNotNone(agent.last_market_analysis)
            self.assertTrue(len(kb.lessons()) >= 1)


if __name__ == "__main__":
    unittest.main()
