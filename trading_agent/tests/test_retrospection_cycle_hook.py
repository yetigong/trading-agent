"""TradingCycle live retrospection hook (Phase 4.5.5) — detect/emit only."""

from __future__ import annotations

import logging
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from strategy_learning.retrospection import list_trigger_paths, load_trigger
from strategy_learning.retrospection.models import RetrospectionEval
from trading_agent.domain.broker import PortfolioHistory
from trading_agent.orchestrator.trading_cycle import TradingCycle


def _bare_cycle(*, agent=None, broker=None, market=None) -> TradingCycle:
    cycle = TradingCycle.__new__(TradingCycle)
    cycle.logger = logging.getLogger("test.retrospection_cycle_hook")
    cycle.agent = agent or MagicMock()
    cycle.broker_client = broker or MagicMock()
    cycle.market_data_provider = market
    return cycle


class TestMaybeEmitRetrospection(unittest.TestCase):
    def test_emits_when_detector_triggers(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            agent = MagicMock()
            agent.emit_retrospection_signal.return_value = str(
                log_dir / "retrospection_fake.json"
            )
            cycle = _bare_cycle(agent=agent)
            evaluation = RetrospectionEval(
                triggered=True,
                reasons=["rolling_30d_equity_lags_spy_by_0.09"],
                metrics={"spy_lag_pp": -0.09},
                cycle_id="c-1",
            )
            detector = MagicMock()
            detector.evaluate.return_value = evaluation

            with (
                patch(
                    "trading_agent.orchestrator.trading_cycle.LOG_DIR",
                    log_dir,
                ),
                patch(
                    "strategy_learning.retrospection.RetrospectionDetector",
                    return_value=detector,
                ),
                patch(
                    "strategy_learning.retrospection.has_pending_trigger",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.cooldown_active",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.load_recent_cycle_summaries",
                    return_value=[],
                ),
                patch(
                    "strategy_learning.retrospection.default_thresholds",
                    return_value={
                        "window_days": 30,
                        "spy_lag_pp": 0.05,
                        "hold_streak": 3,
                        "cooldown_days": 7,
                    },
                ),
            ):
                cycle._portfolio_equity_points = MagicMock(  # type: ignore[method-assign]
                    return_value=[{"timestamp": datetime.now(timezone.utc), "equity": 1.0}]
                )
                cycle._spy_closes = MagicMock(return_value=[100.0, 110.0])  # type: ignore[method-assign]
                cycle._maybe_emit_retrospection(
                    {
                        "cycle_id": "c-1",
                        "artifact_path": "logs/cycle_c-1.json",
                        "status": "success",
                    }
                )

            agent.emit_retrospection_signal.assert_called_once()
            kwargs = agent.emit_retrospection_signal.call_args.kwargs
            self.assertIs(kwargs["eval"], evaluation)
            self.assertEqual(kwargs["log_dir"], str(log_dir))
            self.assertEqual(kwargs["cycle_artifact_path"], "logs/cycle_c-1.json")

    def test_skips_emit_when_not_triggered(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            agent = MagicMock()
            cycle = _bare_cycle(agent=agent)
            detector = MagicMock()
            detector.evaluate.return_value = RetrospectionEval(
                triggered=False,
                reasons=[],
                metrics={"equity_return": 0.05, "spy_return": 0.06},
            )

            with (
                patch(
                    "trading_agent.orchestrator.trading_cycle.LOG_DIR",
                    log_dir,
                ),
                patch(
                    "strategy_learning.retrospection.RetrospectionDetector",
                    return_value=detector,
                ),
                patch(
                    "strategy_learning.retrospection.has_pending_trigger",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.cooldown_active",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.load_recent_cycle_summaries",
                    return_value=[],
                ),
                patch(
                    "strategy_learning.retrospection.default_thresholds",
                    return_value={
                        "window_days": 30,
                        "spy_lag_pp": 0.05,
                        "hold_streak": 3,
                        "cooldown_days": 7,
                    },
                ),
            ):
                cycle._portfolio_equity_points = MagicMock(return_value=[])  # type: ignore[method-assign]
                cycle._spy_closes = MagicMock(return_value=[])  # type: ignore[method-assign]
                cycle._maybe_emit_retrospection({"cycle_id": "c-2", "status": "success"})

            agent.emit_retrospection_signal.assert_not_called()

    def test_skips_when_pending_or_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            agent = MagicMock()
            cycle = _bare_cycle(agent=agent)
            detector = MagicMock()
            detector.evaluate.return_value = RetrospectionEval(
                triggered=False,
                skipped_reason="pending_trigger_exists",
            )

            with (
                patch(
                    "trading_agent.orchestrator.trading_cycle.LOG_DIR",
                    log_dir,
                ),
                patch(
                    "strategy_learning.retrospection.RetrospectionDetector",
                    return_value=detector,
                ),
                patch(
                    "strategy_learning.retrospection.has_pending_trigger",
                    return_value=True,
                ),
                patch(
                    "strategy_learning.retrospection.cooldown_active",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.load_recent_cycle_summaries",
                    return_value=[],
                ),
                patch(
                    "strategy_learning.retrospection.default_thresholds",
                    return_value={
                        "window_days": 30,
                        "spy_lag_pp": 0.05,
                        "hold_streak": 3,
                        "cooldown_days": 7,
                    },
                ),
            ):
                cycle._portfolio_equity_points = MagicMock(return_value=[])  # type: ignore[method-assign]
                cycle._spy_closes = MagicMock(return_value=[])  # type: ignore[method-assign]
                cycle._maybe_emit_retrospection({"cycle_id": "c-3", "status": "success"})

            agent.emit_retrospection_signal.assert_not_called()
            detector.evaluate.assert_called_once()
            self.assertTrue(detector.evaluate.call_args.kwargs["pending_trigger_exists"])

    def test_failures_do_not_propagate(self):
        cycle = _bare_cycle()
        cycle._portfolio_equity_points = MagicMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("broker down")
        )
        # Must not raise — cycle continues after retrospection failures.
        cycle._maybe_emit_retrospection({"cycle_id": "c-err", "status": "success"})

    def test_end_to_end_emit_writes_pending_artifact(self):
        """Wire real LiveAgentRun.emit through the hook with forced detector hit."""
        from trading_agent.broker.mock_client import MockAlpacaTradingClient
        from trading_agent.llm.mock_client import MockLLMClient
        from trading_agent.market_data.mock_provider import MockMarketDataProvider
        from trading_agent.orchestrator.agent_run import LiveAgentRun
        from strategy_learning.knowledge import KnowledgeBase

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            example = data_dir / "example"
            example.mkdir(parents=True)
            (example / "knowledge_base.json").write_text(
                '{"lessons": [], "signal_weights": {}, "strategy_preferences": {}}\n'
            )
            log_dir = Path(tmp) / "logs"
            run = LiveAgentRun(
                llm_client=MockLLMClient(),
                market_data_provider=MockMarketDataProvider(),
                alpaca_client=MockAlpacaTradingClient(),
                knowledge_base=KnowledgeBase(data_dir=data_dir, example_dir=example),
                write_artifact=False,
            )
            cycle = _bare_cycle(agent=run)
            evaluation = RetrospectionEval(
                triggered=True,
                reasons=["3_consecutive_holds_while_spy_rising"],
                metrics={"hold_streak": 3},
                cycle_id="c-live-hook",
            )
            detector = MagicMock()
            detector.evaluate.return_value = evaluation

            with (
                patch(
                    "trading_agent.orchestrator.trading_cycle.LOG_DIR",
                    log_dir,
                ),
                patch(
                    "strategy_learning.retrospection.RetrospectionDetector",
                    return_value=detector,
                ),
                patch(
                    "strategy_learning.retrospection.has_pending_trigger",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.cooldown_active",
                    return_value=False,
                ),
                patch(
                    "strategy_learning.retrospection.load_recent_cycle_summaries",
                    return_value=[],
                ),
                patch(
                    "strategy_learning.retrospection.default_thresholds",
                    return_value={
                        "window_days": 30,
                        "spy_lag_pp": 0.05,
                        "hold_streak": 3,
                        "cooldown_days": 7,
                    },
                ),
            ):
                cycle._portfolio_equity_points = MagicMock(return_value=[])  # type: ignore[method-assign]
                cycle._spy_closes = MagicMock(return_value=[])  # type: ignore[method-assign]
                cycle._maybe_emit_retrospection(
                    {
                        "cycle_id": "c-live-hook",
                        "artifact_path": "logs/cycle_c-live-hook.json",
                        "status": "success",
                    }
                )

            pending = list_trigger_paths(log_dir, status="pending")
            self.assertEqual(len(pending), 1)
            trigger = load_trigger(pending[0])
            self.assertEqual(trigger.cycle_id, "c-live-hook")
            self.assertIn("consecutive_holds", trigger.reasons[0])


class TestEquityAndSpyHelpers(unittest.TestCase):
    def test_portfolio_equity_points_from_broker_history(self):
        broker = MagicMock()
        broker.get_portfolio_history.return_value = PortfolioHistory(
            timestamps=[1_700_000_000, 1_700_086_400],
            equity=[100_000.0, 101_000.0],
            profit_loss=[0.0, 1000.0],
            profit_loss_pct=[0.0, 0.01],
            base_value=100_000.0,
            timeframe="1D",
        )
        cycle = _bare_cycle(broker=broker)
        points = cycle._portfolio_equity_points(window_days=30)
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["equity"], 100_000.0)
        self.assertIsInstance(points[0]["timestamp"], datetime)
        broker.get_portfolio_history.assert_called_once_with(
            period="1M", timeframe="1D"
        )

    def test_portfolio_history_period_follows_window(self):
        broker = MagicMock()
        broker.get_portfolio_history.return_value = PortfolioHistory(
            timestamps=[1_700_000_000],
            equity=[100_000.0],
        )
        cycle = _bare_cycle(broker=broker)
        cycle._portfolio_equity_points(window_days=60)
        broker.get_portfolio_history.assert_called_once_with(
            period="3M", timeframe="1D"
        )

    def test_spy_closes_from_provider_bars(self):
        import pandas as pd

        idx = pd.to_datetime(["2026-07-01", "2026-07-02"], utc=True)
        bars = pd.DataFrame({"close": [400.0, 410.0]}, index=idx)
        market = SimpleNamespace(get_bars=MagicMock(return_value=bars))
        cycle = _bare_cycle(market=market)
        closes = cycle._spy_closes(window_days=30)
        self.assertEqual(len(closes), 2)
        self.assertEqual(closes[0]["close"], 400.0)
        market.get_bars.assert_called_once()

    def test_spy_closes_empty_without_provider(self):
        cycle = _bare_cycle(market=None)
        self.assertEqual(cycle._spy_closes(), [])


if __name__ == "__main__":
    unittest.main()
