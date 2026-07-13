"""Phase 4.5.2 / 4.5.5 — LiveAgentRun / BacktestAgentRun mode policy."""

import tempfile
import unittest
from pathlib import Path

from strategy_learning.knowledge import KnowledgeBase
from strategy_learning.retrospection import list_trigger_paths, load_trigger
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
    def test_mode_and_retrospection_emit_writes_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            run = LiveAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=_temp_kb(tmp),
                write_artifact=False,
            )
            self.assertEqual(run.mode, AgentRunMode.LIVE)
            self.assertTrue(run.may_trigger_retrospection)
            self.assertTrue(run.agent.registry.get("live_lesson").is_enabled())
            path = run.emit_retrospection_signal(
                reasons=["rolling_30d_equity_lags_spy_by_0.09"],
                metrics={"spy_lag_pp": -0.09},
                cycle_id="c-live",
                log_dir=str(log_dir),
            )
            self.assertIsNotNone(path)
            pending = list_trigger_paths(log_dir, status="pending")
            self.assertEqual(len(pending), 1)
            trigger = load_trigger(pending[0])
            self.assertEqual(trigger.cycle_id, "c-live")
            self.assertIn("lags_spy", trigger.reasons[0])

    def test_emit_skips_when_not_triggered(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = LiveAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=_temp_kb(tmp),
                write_artifact=False,
            )
            path = run.emit_retrospection_signal(
                triggered=False,
                reasons=[],
                log_dir=str(Path(tmp) / "logs"),
            )
            self.assertIsNone(path)

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
    def test_forces_live_lesson_disabled_and_blocks_retrospection(self):
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
            self.assertFalse(run.agent.registry.get("live_lesson").is_enabled())
            with self.assertRaises(RuntimeError) as ctx:
                run.emit_retrospection_signal(reason="should_fail")
            self.assertIn("must not trigger retrospection", str(ctx.exception))

    def test_forces_live_lesson_even_when_caller_omits_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = BacktestAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=_temp_kb(tmp),
                disabled=[],
            )
            self.assertFalse(run.agent.registry.get("live_lesson").is_enabled())

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


class TestTradingCycleDoesNotImportSweep(unittest.TestCase):
    def test_trading_cycle_source_avoids_param_sweep_runner(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "orchestrator"
            / "trading_cycle.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ParamSweepRunner", source)
        self.assertNotIn("run_sweep", source)
        self.assertIn("_maybe_emit_retrospection", source)


if __name__ == "__main__":
    unittest.main()
