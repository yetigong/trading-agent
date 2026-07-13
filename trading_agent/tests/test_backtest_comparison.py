"""Tests for backtest run comparison."""

import json
import tempfile
import unittest
from pathlib import Path

from trading_agent.backtest.comparison import compare_runs, format_comparison


class TestBacktestComparison(unittest.TestCase):
    def test_compare_two_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            a.write_text(
                json.dumps({
                    "run_id": "1",
                    "config": {"run_label": "baseline"},
                    "status": "success",
                    "metrics": {
                        "name": "LLM strategy (baseline)",
                        "total_return": 0.1,
                        "cagr": 0.1,
                        "max_drawdown": 0.05,
                        "sharpe": 1.2,
                        "alpha_vs_spy": 0.02,
                        "trade_count": 3,
                    },
                    "benchmarks": [],
                }),
                encoding="utf-8",
            )
            b.write_text(
                json.dumps({
                    "run_id": "2",
                    "config": {"run_label": "aggressive"},
                    "status": "success",
                    "metrics": {
                        "name": "LLM strategy (aggressive)",
                        "total_return": 0.15,
                        "cagr": 0.15,
                        "max_drawdown": 0.08,
                        "sharpe": 0.9,
                        "alpha_vs_spy": 0.04,
                        "trade_count": 5,
                    },
                    "benchmarks": [],
                }),
                encoding="utf-8",
            )
            comparison = compare_runs([a, b])
            self.assertEqual(comparison["highlights"]["best_sharpe"], "baseline")
            self.assertEqual(comparison["highlights"]["lowest_drawdown"], "baseline")
            self.assertEqual(comparison.get("warnings"), [])
            text = format_comparison(comparison)
            self.assertIn("BACKTEST RUN COMPARISON", text)
            self.assertIn("baseline", text)

    def test_compare_excludes_degraded_from_highlights(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            a.write_text(
                json.dumps({
                    "run_id": "1",
                    "config": {"run_label": "baseline"},
                    "status": "success",
                    "metrics": {
                        "name": "LLM strategy (baseline)",
                        "total_return": 0.1,
                        "cagr": 0.1,
                        "max_drawdown": 0.05,
                        "sharpe": 1.2,
                        "alpha_vs_spy": 0.02,
                        "trade_count": 3,
                    },
                    "benchmarks": [],
                }),
                encoding="utf-8",
            )
            b.write_text(
                json.dumps({
                    "run_id": "2",
                    "config": {"run_label": "broken"},
                    "status": "degraded",
                    "metrics": {
                        "name": "LLM strategy (broken)",
                        "total_return": 0.5,
                        "cagr": 0.5,
                        "max_drawdown": 0.01,
                        "sharpe": 9.0,
                        "alpha_vs_spy": 0.4,
                        "trade_count": 1,
                    },
                    "benchmarks": [],
                }),
                encoding="utf-8",
            )
            comparison = compare_runs([a, b])
            self.assertEqual(comparison["highlights"]["best_sharpe"], "baseline")
            self.assertTrue(comparison["warnings"])
            text = format_comparison(comparison)
            self.assertIn("WARNING", text)


if __name__ == "__main__":
    unittest.main()
