"""Phase 4.5.2 — LiveAgentRun / BacktestAgentRun mode policy."""

import tempfile
import unittest
from pathlib import Path

from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.broker.mock_client import MockAlpacaTradingClient
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.market_data.mock_fundamentals_provider import MockFundamentalsProvider
from trading_agent.market_data.mock_provider import MockMarketDataProvider
from trading_agent.orchestrator.agent_run import (
    AgentRunMode,
    BacktestAgentRun,
    LiveAgentRun,
)


def _temp_kb(tmp: str) -> KnowledgeBase:
    data_dir = Path(tmp)
    example = data_dir / "example"
    example.mkdir()
    (example / "knowledge_base.json").write_text(
        '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
    )
    return KnowledgeBase(data_dir=data_dir, example_dir=example)


class TestLiveAgentRun(unittest.TestCase):
    def test_mode_and_retrospection_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = LiveAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=_temp_kb(tmp),
                write_artifact=False,
            )
            self.assertEqual(run.mode, AgentRunMode.LIVE)
            self.assertTrue(run.may_trigger_retrospection)
            self.assertTrue(run.agent.registry.get("learner").is_enabled())
            self.assertIsNone(run.emit_retrospection_signal(reason="underperf"))

    def test_smoke_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _temp_kb(tmp)
            run = LiveAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=kb,
                write_artifact=False,
            )
            results = run.run_trading_cycle()
            self.assertEqual(results["status"], "success")
            self.assertGreaterEqual(len(kb.lessons()), 1)


class TestBacktestAgentRun(unittest.TestCase):
    def test_forces_learner_disabled_and_blocks_retrospection(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _temp_kb(tmp)
            run = BacktestAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                fundamentals_provider=MockFundamentalsProvider(metrics={}),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=kb,
            )
            self.assertEqual(run.mode, AgentRunMode.BACKTEST)
            self.assertFalse(run.may_trigger_retrospection)
            self.assertFalse(run.agent.registry.get("learner").is_enabled())
            with self.assertRaises(RuntimeError) as ctx:
                run.emit_retrospection_signal(reason="should_fail")
            self.assertIn("must not trigger retrospection", str(ctx.exception))

    def test_forces_learner_even_when_caller_omits_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = BacktestAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=_temp_kb(tmp),
                disabled=[],
            )
            self.assertFalse(run.agent.registry.get("learner").is_enabled())

    def test_smoke_cycle_does_not_write_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _temp_kb(tmp)
            run = BacktestAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                fundamentals_provider=MockFundamentalsProvider(metrics={}),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=kb,
            )
            results = run.run_trading_cycle()
            self.assertEqual(results["status"], "success")
            self.assertEqual(len(kb.load()["lessons"]), 0)


if __name__ == "__main__":
    unittest.main()
