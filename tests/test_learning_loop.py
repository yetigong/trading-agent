"""Tests for KB promotion path (config-owner) and learning-loop integration."""

import json
import tempfile
import unittest
from pathlib import Path

from strategy_learning.knowledge import (
    KnowledgeBase,
    KnowledgeBaseError,
    make_event_ref,
)
from trading_agent.agents.promotion import (
    approve_recommendation,
    format_pending_diff,
    reject_recommendation,
    review_status,
)


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


class TestPromotionReject(unittest.TestCase):
    def test_reject_leaves_config_untouched_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            event = make_event_ref(
                event_type="sweep",
                event_id="sw-test",
                artifact_path="logs/sweep_fake.json",
                artifact_kind="sweep",
            )
            kb.append_config_recommendation(
                {
                    "summary": "Proposed config change from param sweep",
                    "rationale": "OAT sweep winner beat baseline",
                    "provenance": {
                        "generated_by": "param_sweep",
                        "trigger_event": event,
                        "evidence_events": [event],
                        "kb_lineage": {"sweep_id": "sw-test"},
                    },
                    "proposed_changes": {
                        "strategy_params": {"risk_management": "conservative"}
                    },
                    "diff_summary": [
                        "strategy_params.risk_management: standard → conservative"
                    ],
                }
            )
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
                    "diff_summary": [
                        "strategy_params.risk_management: standard → conservative"
                    ],
                }
            )
            with self.assertRaises(ValueError):
                approve_recommendation(kb=kb, require_validate_window=True)


class TestKnowledgeBaseErrorExport(unittest.TestCase):
    def test_error_is_value_error(self):
        self.assertTrue(issubclass(KnowledgeBaseError, ValueError))


if __name__ == "__main__":
    unittest.main()
