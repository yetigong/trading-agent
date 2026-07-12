"""Tests for KB schema v2, EventRef validation, and backtest feedback."""

import json
import tempfile
import unittest
from pathlib import Path

from trading_agent.agents.backtest_feedback import BacktestFeedbackAgent
from trading_agent.agents.kb_records import KnowledgeBaseError, make_event_ref
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.promotion import (
    approve_recommendation,
    format_pending_diff,
    reject_recommendation,
    review_status,
)
from trading_agent.backtest.models import BacktestRun


def _seed_kb(tmp: str) -> KnowledgeBase:
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
                    "active_recommendation_id": None,
                    "last_promotion_id": None,
                },
                "lessons": [],
                "backtest_validations": [],
                "config_recommendations": [],
                "promotions": [],
            }
        )
    )
    return KnowledgeBase(data_dir=data_dir, example_dir=example, user_id="default")


class TestKnowledgeBaseV2(unittest.TestCase):
    def test_v1_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            example = data_dir / "example"
            example.mkdir()
            (example / "knowledge_base.json").write_text(
                json.dumps(
                    {
                        "lessons": ["old string lesson"],
                        "signal_weights": {"news": 1.2},
                        "strategy_preferences": {"recent_trade_bias": 0.1},
                    }
                )
            )
            # Copy example to data path by loading
            kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
            doc = kb.load()
            self.assertEqual(doc["schema_version"], 2)
            self.assertEqual(doc["user_id"], "default")
            self.assertEqual(len(doc["lessons"]), 1)
            self.assertEqual(doc["lessons"][0]["summary"], "old string lesson")
            self.assertEqual(kb.signal_weights()["news"], 1.2)
            kb.append_lesson("new lesson")
            reloaded = kb.load()
            self.assertEqual(reloaded["schema_version"], 2)
            self.assertGreaterEqual(len(reloaded["lessons"]), 2)

    def test_user_isolation_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb_a = _seed_kb(tmp)
            kb_a.append_lesson("alice lesson")
            with self.assertRaises(KnowledgeBaseError):
                KnowledgeBase(
                    data_dir=Path(tmp),
                    example_dir=Path(tmp) / "example",
                    user_id="bob",
                ).load()

    def test_recommendation_requires_event_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            with self.assertRaises(KnowledgeBaseError):
                kb.append_config_recommendation(
                    {
                        "summary": "bad",
                        "rationale": "no event",
                        "provenance": {},
                        "proposed_changes": {"strategy_params": {"risk_management": "aggressive"}},
                    }
                )


class TestBacktestFeedback(unittest.TestCase):
    def _underperforming_run(self) -> BacktestRun:
        return BacktestRun(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            timestamp="2026-07-12T08:00:00",
            config={
                "start": "2024-01-01",
                "end": "2024-06-30",
                "run_label": "baseline",
                "strategy_params": {"risk_management": "standard"},
                "preferences": {"max_position_size": 0.25},
                "rebalance_params": {"threshold": 0.05},
            },
            status="success",
            equity_curve=[
                {"date": "2024-01-01", "equity": 100000, "cash": 50000},
                {"date": "2024-06-30", "equity": 102000, "cash": 60000},
            ],
            trade_log=[{"date": "2024-02-01", "symbol": "SPY", "side": "buy", "qty": 1, "price": 100}],
            cycle_summaries=[
                {"date": "2024-01-05", "cycle_id": "c1", "status": "success", "hold": False}
            ],
            metrics={
                "name": "strategy",
                "total_return": 0.02,
                "cagr": 0.04,
                "max_drawdown": -0.05,
                "volatility": 0.1,
                "sharpe": 0.2,
                "alpha_vs_spy": -0.05,
                "trade_count": 1,
            },
            benchmarks=[
                {
                    "name": "SPY buy&hold",
                    "total_return": 0.1,
                    "sharpe": 0.9,
                    "max_drawdown": -0.08,
                }
            ],
        )

    def test_feedback_creates_pending_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            artifact = Path(tmp) / "backtest.json"
            run = self._underperforming_run()
            artifact.write_text(json.dumps(run.to_dict()))
            result = BacktestFeedbackAgent(knowledge_base=kb).reflect_on_artifact(artifact)
            self.assertTrue(result["underperformance"])
            self.assertIsNotNone(result["validation"])
            self.assertIsNotNone(result["recommendation"])
            self.assertEqual(result["recommendation"]["status"], "pending_review")
            pending = kb.get_pending_recommendation()
            self.assertEqual(pending["id"], result["recommendation"]["id"])
            # signal weights nudged
            weights = kb.signal_weights()
            self.assertIn("news", weights)

    def test_reject_leaves_config_untouched_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            artifact = Path(tmp) / "backtest.json"
            artifact.write_text(json.dumps(self._underperforming_run().to_dict()))
            BacktestFeedbackAgent(knowledge_base=kb).reflect_on_artifact(artifact)
            status = review_status(kb)
            self.assertTrue(status["pending"])
            text = format_pending_diff(status["recommendation"])
            self.assertIn("PENDING CONFIG RECOMMENDATION", text)
            result = reject_recommendation(kb=kb, reason="drawdown risk")
            self.assertEqual(result["recommendation"]["status"], "rejected")
            self.assertFalse(result["promotion"]["applied"])
            self.assertIsNone(kb.get_pending_recommendation())


class TestApproveWalkForwardGate(unittest.TestCase):
    def test_approve_blocked_without_validate_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            event = make_event_ref(
                event_type="backtest_run",
                event_id="run-1",
                artifact_path="logs/fake.json",
                artifact_kind="backtest",
            )
            kb.append_config_recommendation(
                {
                    "summary": "test",
                    "rationale": "test",
                    "provenance": {
                        "generated_by": "test",
                        "trigger_event": event,
                        "evidence_events": [event],
                        "kb_lineage": {},
                    },
                    "proposed_changes": {
                        "strategy_params": {"risk_management": "conservative"}
                    },
                    "diff_summary": ["strategy_params.risk_management: standard → conservative"],
                }
            )
            with self.assertRaises(ValueError):
                approve_recommendation(kb=kb, require_validate_window=True)


if __name__ == "__main__":
    unittest.main()
