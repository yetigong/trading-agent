"""Tests for ParamSweepRunner with a mock backtest callable."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

from strategy_learning.knowledge import KnowledgeBase
from strategy_learning.sweep import ParamSweepRunner
from trading_agent.storage import (
    PreferencesStore,
    RebalanceConfigStore,
    StrategyConfigStore,
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


def _mock_runner_factory(scores: Dict[str, float]):
    """scores keyed by risk_management value (or 'baseline')."""

    counter = {"n": 0}

    def run_backtest(config_snapshot: Dict[str, Any], run_label: str) -> Dict[str, Any]:
        counter["n"] += 1
        rm = (config_snapshot.get("strategy_params") or {}).get("risk_management")
        key = str(rm) if rm is not None else "baseline"
        sharpe = scores.get(key, scores.get("baseline", 0.1))
        return {
            "run_id": f"run-{counter['n']}",
            "status": "success",
            "metrics": {
                "sharpe": sharpe,
                "alpha_vs_spy": sharpe - 0.5,
                "max_drawdown": -0.1,
            },
            "artifact_path": f"/tmp/{run_label}.json",
        }

    return run_backtest


class TestParamSweepRunner(unittest.TestCase):
    def test_ranks_winner_and_writes_sweep_recommendation(self):
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
            "start": "2024-01-01",
            "end": "2024-06-30",
        }
        # Only expand one field to keep the mock focused.
        candidates = [
            {
                "candidate_id": "sc-agg",
                "label": "strategy_params.risk_management=aggressive",
                "proposed_changes": {
                    "strategy_params": {"risk_management": "aggressive"}
                },
            },
            {
                "candidate_id": "sc-con",
                "label": "strategy_params.risk_management=conservative",
                "proposed_changes": {
                    "strategy_params": {"risk_management": "conservative"}
                },
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            data_dir = Path(tmp) / "cfg"
            example = Path(tmp) / "cfg_example"
            data_dir.mkdir()
            example.mkdir()
            for name, payload in (
                ("strategy_params.json", {"risk_management": "standard"}),
                ("preferences.json", {"max_position_size": 0.25}),
                ("rebalance_params.json", {"threshold": 0.05}),
            ):
                (data_dir / name).write_text(json.dumps(payload))
                (example / name).write_text(json.dumps(payload))

            strategy_before = StrategyConfigStore(data_dir=data_dir, example_dir=example).load()
            prefs_before = PreferencesStore(data_dir=data_dir, example_dir=example).load_preferences().to_dict()
            rebalance_before = RebalanceConfigStore(data_dir=data_dir, example_dir=example).load()

            runner = ParamSweepRunner(
                knowledge_base=kb,
                run_backtest=_mock_runner_factory(
                    {"standard": 0.2, "aggressive": 0.9, "conservative": 0.1}
                ),
                max_workers=1,
            )
            result = runner.run(
                baseline,
                period_start="2024-01-01",
                period_end="2024-06-30",
                run_label="unit",
                write_kb=True,
                artifact_path="/tmp/sweep.json",
                candidates=candidates,
            )

            self.assertEqual(result.winner.label, "strategy_params.risk_management=aggressive")
            self.assertIsNotNone(result.recommendation_id)
            pending = kb.get_pending_recommendation()
            self.assertIsNotNone(pending)
            self.assertEqual(pending["id"], result.recommendation_id)
            self.assertEqual(
                pending["provenance"]["trigger_event"]["event_type"], "sweep"
            )
            self.assertEqual(pending["provenance"]["generated_by"], "param_sweep")
            self.assertEqual(
                pending["proposed_changes"]["strategy_params"]["risk_management"],
                "aggressive",
            )

            # Learning must not write config stores
            self.assertEqual(
                StrategyConfigStore(data_dir=data_dir, example_dir=example).load(),
                strategy_before,
            )
            self.assertEqual(
                PreferencesStore(data_dir=data_dir, example_dir=example)
                .load_preferences()
                .to_dict(),
                prefs_before,
            )
            self.assertEqual(
                RebalanceConfigStore(data_dir=data_dir, example_dir=example).load(),
                rebalance_before,
            )

    def test_no_recommendation_when_baseline_wins(self):
        baseline = {
            "strategy_params": {"risk_management": "standard"},
            "preferences": {"max_position_size": 0.25},
            "rebalance_params": {"threshold": 0.05},
        }
        candidates = [
            {
                "candidate_id": "sc-agg",
                "label": "strategy_params.risk_management=aggressive",
                "proposed_changes": {
                    "strategy_params": {"risk_management": "aggressive"}
                },
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            runner = ParamSweepRunner(
                knowledge_base=kb,
                run_backtest=_mock_runner_factory(
                    {"standard": 1.0, "aggressive": 0.2}
                ),
            )
            result = runner.run(
                baseline,
                write_kb=True,
                candidates=candidates,
            )
            self.assertTrue(result.winner.is_baseline)
            self.assertIsNone(result.recommendation_id)
            self.assertIsNone(kb.get_pending_recommendation())


if __name__ == "__main__":
    unittest.main()
