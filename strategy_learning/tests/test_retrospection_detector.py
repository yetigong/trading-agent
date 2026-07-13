"""Tests for RetrospectionDetector."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from strategy_learning.retrospection.detector import RetrospectionDetector


def _equity_series(*, start: float, end: float, days: int = 30):
    as_of = datetime(2026, 7, 12, tzinfo=timezone.utc)
    points = []
    for i in range(days + 1):
        t = i / days
        equity = start + (end - start) * t
        points.append(
            {
                "timestamp": as_of - timedelta(days=days - i),
                "equity": equity,
            }
        )
    return points, as_of


def _spy_series(*, start: float, end: float, days: int = 30, as_of: datetime):
    points = []
    for i in range(days + 1):
        t = i / days
        close = start + (end - start) * t
        points.append(
            {
                "timestamp": as_of - timedelta(days=days - i),
                "close": close,
            }
        )
    return points


class TestRetrospectionDetector(unittest.TestCase):
    def test_triggers_on_spy_lag_same_window(self):
        equity, as_of = _equity_series(start=100.0, end=101.0)  # +1%
        # Extra older SPY bars that would distort an unwindowed compare.
        spy = (
            [{"timestamp": as_of - timedelta(days=60), "close": 10.0}]
            + _spy_series(start=100.0, end=110.0, days=30, as_of=as_of)
        )
        det = RetrospectionDetector(window_days=30, spy_lag_pp=0.05, hold_streak=3)
        result = det.evaluate(
            equity_points=equity,
            spy_closes=spy,
            cycle_summaries=[],
            cycle_id="c-1",
            as_of=as_of,
        )
        self.assertTrue(result.triggered)
        self.assertTrue(any("lags_spy" in r for r in result.reasons))
        # Reason uses rounded lag.
        self.assertTrue(any("0.0900" in r for r in result.reasons))

    def test_no_trigger_when_tracking_spy(self):
        equity, as_of = _equity_series(start=100.0, end=109.0)  # +9%
        spy = _spy_series(start=100.0, end=110.0, days=30, as_of=as_of)  # +10%
        det = RetrospectionDetector(window_days=30, spy_lag_pp=0.05, hold_streak=3)
        result = det.evaluate(
            equity_points=equity,
            spy_closes=spy,
            cycle_summaries=[],
            as_of=as_of,
        )
        self.assertFalse(result.triggered)

    def test_triggers_on_hold_streak(self):
        equity, as_of = _equity_series(start=100.0, end=110.0)
        t0 = as_of - timedelta(days=6)
        t1 = as_of - timedelta(days=3)
        t2 = as_of
        summaries = [
            {"status": "success", "hold": True, "timestamp": t2.isoformat()},
            {"status": "success", "hold": True, "timestamp": t1.isoformat()},
            {"status": "success", "hold": True, "timestamp": t0.isoformat()},
        ]
        spy = [
            {"timestamp": t0, "close": 100.0},
            {"timestamp": t2, "close": 105.0},
        ]
        det = RetrospectionDetector(window_days=30, spy_lag_pp=0.05, hold_streak=3)
        result = det.evaluate(
            equity_points=equity,
            spy_closes=spy,
            cycle_summaries=summaries,
            as_of=as_of,
        )
        self.assertTrue(result.triggered)
        self.assertTrue(any("consecutive_holds" in r for r in result.reasons))

    def test_skips_when_pending(self):
        det = RetrospectionDetector()
        result = det.evaluate(
            equity_points=[],
            spy_closes=[],
            cycle_summaries=[],
            pending_trigger_exists=True,
        )
        self.assertFalse(result.triggered)
        self.assertEqual(result.skipped_reason, "pending_trigger_exists")

    def test_skips_when_cooldown(self):
        det = RetrospectionDetector()
        result = det.evaluate(
            equity_points=[],
            spy_closes=[],
            cycle_summaries=[],
            cooldown_active=True,
        )
        self.assertFalse(result.triggered)
        self.assertEqual(result.skipped_reason, "cooldown_active")


if __name__ == "__main__":
    unittest.main()
