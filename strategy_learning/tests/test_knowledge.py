"""Tests for strategy_learning knowledge store (schema v2, EventRef, writes)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from strategy_learning.knowledge import KnowledgeBase, KnowledgeBaseError, make_event_ref


def _seed_kb(tmp: str, user_id: str = "default") -> KnowledgeBase:
    data_dir = Path(tmp)
    example = data_dir / "example"
    example.mkdir(exist_ok=True)
    (example / "knowledge_base.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "user_id": user_id,
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
    return KnowledgeBase(data_dir=data_dir, example_dir=example, user_id=user_id)


class TestKnowledgeBaseStore(unittest.TestCase):
    def test_load_save_and_append_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            self.assertEqual(kb.lessons(), [])
            kb.append_lesson("first lesson")
            kb.update_weights_and_prefs(
                signal_weights={"news": 1.2},
                strategy_preferences={"recent_trade_bias": 0.1},
            )
            self.assertEqual(kb.lessons(), ["first lesson"])
            self.assertEqual(kb.signal_weights()["news"], 1.2)
            self.assertEqual(kb.strategy_preferences()["recent_trade_bias"], 0.1)

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
                        "proposed_changes": {
                            "strategy_params": {"risk_management": "aggressive"}
                        },
                    }
                )

    def test_pending_recommendation_supersedes_older(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            event = make_event_ref(
                event_type="backtest_run",
                event_id="run-1",
                artifact_path="logs/a.json",
                artifact_kind="backtest",
            )
            first = kb.append_config_recommendation(
                {
                    "summary": "first",
                    "rationale": "first",
                    "provenance": {
                        "generated_by": "test",
                        "trigger_event": event,
                        "evidence_events": [event],
                        "kb_lineage": {},
                    },
                    "proposed_changes": {
                        "strategy_params": {"risk_management": "conservative"}
                    },
                }
            )
            second = kb.append_config_recommendation(
                {
                    "summary": "second",
                    "rationale": "second",
                    "provenance": {
                        "generated_by": "test",
                        "trigger_event": event,
                        "evidence_events": [event],
                        "kb_lineage": {},
                    },
                    "proposed_changes": {
                        "strategy_params": {"risk_management": "aggressive"}
                    },
                }
            )
            pending = kb.get_pending_recommendation()
            self.assertEqual(pending["id"], second["id"])
            older = kb.find_record(first["id"])
            self.assertEqual(older["status"], "superseded")
            self.assertEqual(older["superseded_by"], second["id"])


if __name__ == "__main__":
    unittest.main()
