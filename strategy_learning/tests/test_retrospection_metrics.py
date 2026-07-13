"""Tests for retrospection pure metrics."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from strategy_learning.retrospection.metrics import (
    closes_return,
    consecutive_hold_streak,
    hold_streak_with_spy_rise,
    lags_spy,
    load_recent_cycle_summaries,
    portfolio_history_period_for_window,
    series_return,
    spy_lag_pp,
    window_closes_return,
    window_equity_return,
)


class TestSeriesReturn(unittest.TestCase):
    def test_basic_return(self):
        self.assertAlmostEqual(series_return([100.0, 110.0]), 0.1)

    def test_insufficient(self):
        self.assertIsNone(series_return([100.0]))
        self.assertIsNone(series_return([]))

    def test_non_positive_start(self):
        self.assertIsNone(series_return([0.0, 10.0]))


class TestWindowEquityReturn(unittest.TestCase):
    def test_window_slice(self):
        end = datetime(2026, 7, 12, tzinfo=timezone.utc)
        points = [
            {"timestamp": end - timedelta(days=40), "equity": 80.0},
            {"timestamp": end - timedelta(days=20), "equity": 100.0},
            {"timestamp": end, "equity": 105.0},
        ]
        ret = window_equity_return(points, window_days=30, as_of=end)
        self.assertAlmostEqual(ret, 0.05)

    def test_empty(self):
        self.assertIsNone(window_equity_return([]))


class TestWindowClosesReturn(unittest.TestCase):
    def test_aligned_window_ignores_older_bars(self):
        end = datetime(2026, 7, 12, tzinfo=timezone.utc)
        closes = [
            {"timestamp": end - timedelta(days=40), "close": 50.0},
            {"timestamp": end - timedelta(days=20), "close": 100.0},
            {"timestamp": end, "close": 110.0},
        ]
        ret = window_closes_return(closes, window_days=30, as_of=end)
        self.assertAlmostEqual(ret, 0.10)

    def test_explicit_span(self):
        start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        mid = datetime(2026, 7, 5, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, tzinfo=timezone.utc)
        closes = [
            {"timestamp": start, "close": 100.0},
            {"timestamp": mid, "close": 102.0},
            {"timestamp": end, "close": 105.0},
            {"timestamp": end + timedelta(days=20), "close": 200.0},
        ]
        ret = window_closes_return(closes, start=start, end=end)
        self.assertAlmostEqual(ret, 0.05)


class TestSpyLag(unittest.TestCase):
    def test_lags_when_below_threshold(self):
        self.assertTrue(lags_spy(0.01, 0.10, lag_threshold_pp=0.05))
        self.assertFalse(lags_spy(0.08, 0.10, lag_threshold_pp=0.05))
        self.assertIsNone(spy_lag_pp(None, 0.1))


class TestHoldStreak(unittest.TestCase):
    def test_consecutive_holds(self):
        summaries = [
            {"status": "success", "hold": True},
            {"status": "success", "hold": True},
            {"status": "success", "hold": True},
            {"status": "success", "hold": False},
        ]
        self.assertEqual(consecutive_hold_streak(summaries), 3)

    def test_breaks_on_non_hold(self):
        summaries = [
            {"status": "success", "hold": True},
            {"status": "success", "hold": False},
        ]
        self.assertEqual(consecutive_hold_streak(summaries), 1)

    def test_hold_with_spy_rise_over_cycle_span(self):
        t0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
        t1 = datetime(2026, 7, 5, tzinfo=timezone.utc)
        t2 = datetime(2026, 7, 10, tzinfo=timezone.utc)
        summaries = [
            {"status": "success", "hold": True, "timestamp": t2.isoformat()},
            {"status": "success", "hold": True, "timestamp": t1.isoformat()},
            {"status": "success", "hold": True, "timestamp": t0.isoformat()},
        ]
        spy = [
            {"timestamp": t0 - timedelta(days=10), "close": 50.0},
            {"timestamp": t0, "close": 100.0},
            {"timestamp": t2, "close": 105.0},
            {"timestamp": t2 + timedelta(days=20), "close": 200.0},
        ]
        hit, metrics = hold_streak_with_spy_rise(
            summaries,
            spy,
            streak_required=3,
        )
        self.assertTrue(hit)
        self.assertEqual(metrics["hold_streak"], 3)
        self.assertAlmostEqual(metrics["spy_return_over_hold_span"], 0.05)

    def test_hold_without_spy_rise_over_span(self):
        t0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 7, 10, tzinfo=timezone.utc)
        summaries = [
            {"status": "success", "hold": True, "timestamp": t2.isoformat()},
            {"status": "success", "hold": True, "timestamp": t0.isoformat()},
            {"status": "success", "hold": True, "timestamp": t0.isoformat()},
        ]
        # Need two distinct timestamps for a span; use t0 and t2 only once each
        # with a third timestamp between — adjust:
        t1 = datetime(2026, 7, 5, tzinfo=timezone.utc)
        summaries = [
            {"status": "success", "hold": True, "timestamp": t2.isoformat()},
            {"status": "success", "hold": True, "timestamp": t1.isoformat()},
            {"status": "success", "hold": True, "timestamp": t0.isoformat()},
        ]
        spy = [
            {"timestamp": t0, "close": 105.0},
            {"timestamp": t2, "close": 100.0},
        ]
        hit, _ = hold_streak_with_spy_rise(summaries, spy, streak_required=3)
        self.assertFalse(hit)

    def test_hold_without_timestamps_does_not_trigger(self):
        summaries = [
            {"status": "success", "hold": True},
            {"status": "success", "hold": True},
            {"status": "success", "hold": True},
        ]
        hit, metrics = hold_streak_with_spy_rise(
            summaries,
            [100.0, 110.0],
            streak_required=3,
        )
        self.assertFalse(hit)
        self.assertTrue(metrics.get("hold_span_unavailable"))

    def test_closes_return(self):
        self.assertAlmostEqual(closes_return([100.0, 110.0]), 0.1)
        self.assertIsNone(closes_return([100.0]))


class TestPortfolioHistoryPeriod(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(portfolio_history_period_for_window(7), "1W")
        self.assertEqual(portfolio_history_period_for_window(30), "1M")
        self.assertEqual(portfolio_history_period_for_window(60), "3M")
        self.assertEqual(portfolio_history_period_for_window(120), "1A")


class TestLoadCycleSummaries(unittest.TestCase):
    def test_loads_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, hold in enumerate([False, True]):
                path = root / f"cycle_2026010{i}_abcd.json"
                path.write_text(
                    json.dumps(
                        {
                            "cycle_id": f"c-{i}",
                            "status": "success",
                            "hold": hold,
                            "timestamp": f"2026-01-0{i+1}T00:00:00Z",
                        }
                    )
                )
            summaries = load_recent_cycle_summaries(root, limit=10)
            self.assertEqual(len(summaries), 2)
            self.assertEqual(summaries[0]["cycle_id"], "c-1")


if __name__ == "__main__":
    unittest.main()
