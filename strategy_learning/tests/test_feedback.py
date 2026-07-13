"""Tests for strategy_learning BacktestFeedbackAgent."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from strategy_learning.knowledge import BacktestFeedbackAgent, KnowledgeBase
from trading_agent.backtest.models import BacktestRun
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


def _underperforming_run() -> BacktestRun:
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
        trade_log=[
            {"date": "2024-02-01", "symbol": "SPY", "side": "buy", "qty": 1, "price": 100}
        ],
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


class TestBacktestFeedback(unittest.TestCase):
    def test_feedback_writes_validation_not_hard_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            kb = _seed_kb(tmp)
            artifact = Path(tmp) / "backtest.json"
            artifact.write_text(json.dumps(_underperforming_run().to_dict()))
            result = BacktestFeedbackAgent(knowledge_base=kb).reflect_on_artifact(artifact)
            self.assertTrue(result["underperformance"])
            self.assertIsNotNone(result["validation"])
            self.assertIsNone(result["recommendation"])
            self.assertIsNone(kb.get_pending_recommendation())
            weights = kb.signal_weights()
            self.assertIn("news", weights)

    def test_feedback_does_not_write_config_stores(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            example = Path(tmp) / "example"
            data_dir.mkdir()
            example.mkdir()
            for name, payload in (
                ("strategy_params.json", {"risk_management": "standard"}),
                ("preferences.json", {"max_position_size": 0.25}),
                ("rebalance_params.json", {"threshold": 0.05}),
                (
                    "knowledge_base.json",
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
                    },
                ),
            ):
                (example / name).write_text(json.dumps(payload))

            import os

            os.environ["DATA_DIR"] = str(data_dir)
            os.environ["EXAMPLE_DATA_DIR"] = str(example)
            try:
                before_strategy = StrategyConfigStore().load()
                before_prefs = PreferencesStore().load_preferences().to_dict()
                before_rebalance = RebalanceConfigStore().load()

                kb = KnowledgeBase(data_dir=data_dir, example_dir=example)
                artifact = Path(tmp) / "backtest.json"
                artifact.write_text(json.dumps(_underperforming_run().to_dict()))
                result = BacktestFeedbackAgent(knowledge_base=kb).reflect_on_artifact(
                    artifact
                )
                self.assertIsNone(result["recommendation"])

                self.assertEqual(StrategyConfigStore().load(), before_strategy)
                self.assertEqual(
                    PreferencesStore().load_preferences().to_dict(), before_prefs
                )
                self.assertEqual(RebalanceConfigStore().load(), before_rebalance)
            finally:
                os.environ.pop("DATA_DIR", None)
                os.environ.pop("EXAMPLE_DATA_DIR", None)


if __name__ == "__main__":
    unittest.main()
