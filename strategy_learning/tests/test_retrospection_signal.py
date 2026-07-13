"""Tests for retrospection signal I/O."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from strategy_learning.retrospection.models import RetrospectionEval
from strategy_learning.retrospection.signal import (
    claim_trigger,
    cooldown_active,
    has_pending_trigger,
    list_trigger_paths,
    load_trigger,
    mark_consumed,
    write_retrospection_signal,
)


class TestRetrospectionSignal(unittest.TestCase):
    def test_write_list_claim_consume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            eval_result = RetrospectionEval(
                triggered=True,
                reasons=["rolling_30d_equity_lags_spy_by_0.0900"],
                metrics={"spy_lag_pp": -0.09},
                cycle_id="cycle-abc",
            )
            path = write_retrospection_signal(
                eval_result,
                log_dir=root,
                cycle_artifact_path="logs/cycle_x.json",
            )
            self.assertTrue(path.exists())
            self.assertTrue(has_pending_trigger(root))
            pending = list_trigger_paths(root, status="pending")
            self.assertEqual(len(pending), 1)

            trigger = load_trigger(path)
            self.assertEqual(trigger.status, "pending")
            self.assertEqual(trigger.cycle_id, "cycle-abc")
            self.assertEqual(
                trigger.event_ref["event_type"], "live_underperformance_trigger"
            )

            claimed = claim_trigger(path)
            self.assertEqual(claimed.status, "in_progress")
            self.assertIsNotNone(claimed.claimed_at)
            self.assertTrue(has_pending_trigger(root))  # in_progress still blocks
            self.assertEqual(list_trigger_paths(root, status="pending"), [])

            with self.assertRaises(ValueError):
                claim_trigger(path)

            mark_consumed(
                path,
                sweep_artifact_path="logs/sweep_x.json",
                recommendation_id="cr-1",
            )
            refreshed = load_trigger(path)
            self.assertEqual(refreshed.status, "consumed")
            self.assertEqual(refreshed.recommendation_id, "cr-1")
            self.assertFalse(has_pending_trigger(root))

    def test_write_requires_triggered(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_retrospection_signal(
                    RetrospectionEval(triggered=False, reasons=[]),
                    log_dir=Path(tmp),
                )

    def test_cooldown_after_trigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_retrospection_signal(
                RetrospectionEval(triggered=True, reasons=["x"]),
                log_dir=root,
            )
            trigger = load_trigger(path)
            as_of = datetime.now(timezone.utc)
            self.assertTrue(cooldown_active(root, cooldown_days=7, as_of=as_of))
            future = as_of + timedelta(days=8)
            self.assertFalse(cooldown_active(root, cooldown_days=7, as_of=future))
            self.assertIsNotNone(trigger.trigger_id)


if __name__ == "__main__":
    unittest.main()
