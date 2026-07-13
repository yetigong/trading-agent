"""Tests for OAT param-sweep candidate expansion."""

from __future__ import annotations

import unittest

from strategy_learning.knowledge.records import (
    MAX_POSITION_SIZE_STEPS,
    REBALANCE_THRESHOLD_STEPS,
    TUNABLE_ENUMS,
)
from strategy_learning.sweep.candidates import (
    expand_oat_candidates,
    merge_proposed_changes,
)
from strategy_learning.sweep.runner import estimate_rebalance_cycles, format_sweep_plan


class TestOatCandidates(unittest.TestCase):
    def test_expands_whitelist_neighbors_skipping_baseline(self):
        baseline = {
            "strategy_params": {
                "risk_management": "standard",
                "position_sizing": "dynamic",
                "timeframe": "short-term",
            },
            "preferences": {
                "risk_tolerance": "moderate",
                "max_position_size": 0.25,
            },
            "rebalance_params": {"threshold": 0.05},
        }
        candidates = expand_oat_candidates(baseline)
        self.assertGreater(len(candidates), 0)

        # No noop / baseline-identical candidates
        for cand in candidates:
            proposed = cand["proposed_changes"]
            applied = merge_proposed_changes(baseline, proposed)
            self.assertNotEqual(applied, baseline)
            self.assertEqual(len(proposed), 1)
            section = next(iter(proposed))
            self.assertEqual(len(proposed[section]), 1)

        # Expected count: all enum alternatives + numeric steps excluding baseline
        expected = 0
        for section, fields in TUNABLE_ENUMS.items():
            for key, choices in fields.items():
                if not choices:
                    continue
                current = baseline[section][key]
                expected += sum(1 for v in choices if v != current)
        expected += sum(1 for v in MAX_POSITION_SIZE_STEPS if abs(v - 0.25) > 1e-12)
        expected += sum(1 for v in REBALANCE_THRESHOLD_STEPS if abs(v - 0.05) > 1e-12)
        self.assertEqual(len(candidates), expected)

    def test_merge_proposed_changes_merges_one_field(self):
        baseline = {
            "strategy_params": {"risk_management": "standard", "timeframe": "short-term"},
            "preferences": {"max_position_size": 0.25},
            "rebalance_params": {"threshold": 0.05},
        }
        merged = merge_proposed_changes(
            baseline, {"strategy_params": {"risk_management": "conservative"}}
        )
        self.assertEqual(merged["strategy_params"]["risk_management"], "conservative")
        self.assertEqual(merged["strategy_params"]["timeframe"], "short-term")
        self.assertEqual(baseline["strategy_params"]["risk_management"], "standard")


class TestSweepPlanLogging(unittest.TestCase):
    def test_format_plan_marks_sequential_and_counts(self):
        plan = format_sweep_plan(
            candidate_labels=[
                "strategy_params.risk_management=aggressive",
                "preferences.max_position_size=0.2",
            ],
            max_workers=1,
            period_start="2026-05-01",
            period_end="2026-06-30",
            rebalance_frequency="weekly",
        )
        self.assertIn("SEQUENTIAL", plan)
        self.assertIn("Backtest runs: 3 (1 baseline + 2 OAT candidates)", plan)
        self.assertIn("Est. LLM invocations", plan)
        self.assertIn("--max-workers", plan)

    def test_estimate_rebalance_cycles_weekly(self):
        cycles = estimate_rebalance_cycles(
            "2026-05-01", "2026-06-30", rebalance_frequency="weekly"
        )
        self.assertEqual(cycles, 8)


if __name__ == "__main__":
    unittest.main()
