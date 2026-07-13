"""Tests for run_retrospection.py CLI (consume trigger → out-of-band sweep)."""

from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from strategy_learning.retrospection import (
    list_trigger_paths,
    load_trigger,
    write_retrospection_signal,
)
from strategy_learning.retrospection.models import RetrospectionEval
from strategy_learning.sweep.models import SweepCandidateResult, SweepResult


def _write_pending(log_dir: Path, *, cycle_id: str = "c-cli") -> Path:
    return write_retrospection_signal(
        RetrospectionEval(
            triggered=True,
            reasons=["rolling_30d_equity_lags_spy_by_0.08"],
            metrics={"spy_lag_pp": -0.08},
            cycle_id=cycle_id,
        ),
        log_dir=log_dir,
        cycle_artifact_path="logs/cycle_c-cli.json",
    )


def _fake_sweep_result(*, period_start: str, period_end: str) -> SweepResult:
    baseline = SweepCandidateResult(
        candidate_id="baseline",
        label="baseline",
        proposed_changes={},
        status="success",
        run_id="run-base",
        metrics={"sharpe": 0.5, "alpha_vs_spy": 0.0, "max_drawdown": -0.1},
        is_baseline=True,
    )
    return SweepResult(
        sweep_id="sw-test",
        timestamp="2026-07-12T00:00:00Z",
        run_label="retrospection_sweep",
        period_start=period_start,
        period_end=period_end,
        baseline_config={},
        baseline=baseline,
        candidates=[],
        winner=baseline,
        notes=[],
    )


class TestResolveAndList(unittest.TestCase):
    def test_list_prints_pending(self):
        import run_retrospection as cli

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            path = _write_pending(log_dir)
            with patch.object(cli, "LOG_DIR", log_dir):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    with patch("sys.argv", ["run_retrospection.py", "--list"]):
                        cli.main()
                out = buf.getvalue()
            self.assertIn("Pending triggers", out)
            self.assertIn(str(path), out)
            self.assertIn("lags_spy", out)

    def test_dry_run_does_not_consume(self):
        import run_retrospection as cli

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            path = _write_pending(log_dir)
            with patch.object(cli, "LOG_DIR", log_dir):
                with patch("run_retrospection.validate_config"):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        with patch(
                            "sys.argv",
                            [
                                "run_retrospection.py",
                                "--dry-run",
                                "--trigger",
                                str(path),
                                "--start",
                                "2026-07-01",
                                "--end",
                                "2026-07-07",
                            ],
                        ):
                            cli.main()
                    out = buf.getvalue()
            self.assertIn("Would consume", out)
            self.assertIn("2026-07-01", out)
            self.assertIn("2026-07-07", out)
            self.assertEqual(load_trigger(path).status, "pending")

    def test_resolve_oldest_pending(self):
        import run_retrospection as cli

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            first = _write_pending(log_dir, cycle_id="older")
            second = _write_pending(log_dir, cycle_id="newer")
            args = SimpleNamespace(trigger=None)
            with patch.object(cli, "LOG_DIR", log_dir):
                resolved = cli.resolve_trigger_path(args)
            self.assertEqual(resolved, first)
            self.assertNotEqual(resolved, second)


class TestConsumeWithMockSweep(unittest.TestCase):
    def test_consume_marks_trigger_and_passes_short_window(self):
        import run_retrospection as cli

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            trigger_path = _write_pending(log_dir)
            captured: dict = {}

            fake_result = _fake_sweep_result(
                period_start="2026-07-01",
                period_end="2026-07-07",
            )

            class FakeRunner:
                def __init__(self, **kwargs):
                    captured["runner_kwargs"] = kwargs

                def run(self, baseline_snapshot, **kwargs):
                    captured["baseline"] = baseline_snapshot
                    captured["run_kwargs"] = kwargs
                    return fake_result

            base_cfg = SimpleNamespace(
                start=date(2026, 7, 1),
                end=date(2026, 7, 7),
                strategy_params={"risk_management": "standard"},
                preferences={"risk_tolerance": "moderate", "max_position_size": 0.25},
                rebalance_params={"threshold": 0.05},
                signal_config={},
                to_dict=lambda: {"start": "2026-07-01", "end": "2026-07-07"},
            )

            args = SimpleNamespace(
                start="2026-07-01",
                end="2026-07-07",
                rebalance="weekly",
                initial_cash=100_000.0,
                risk_free_rate=0.04,
                symbols="AAPL",
                run_label="retrospection_sanity",
                refresh=False,
                llm_pause_seconds=0.0,
                override_strategy=None,
                override_analysis=None,
                override_preferences=None,
                max_workers=1,
                write_kb=False,
                validate_artifact=None,
            )

            with (
                patch.object(cli, "LOG_DIR", log_dir),
                patch.object(cli, "build_base_config", return_value=base_cfg),
                patch.object(cli, "ParamSweepRunner", FakeRunner),
                patch.object(cli, "save_sweep_artifact") as save_art,
                patch("run_retrospection.get_config"),
                patch("run_retrospection.config_summary", return_value={}),
            ):
                save_art.return_value = log_dir / "sweep_test.json"
                (log_dir / "sweep_test.json").write_text("{}\n")
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli.run_sweep_for_trigger(
                        args,
                        trigger_path,
                        logging.getLogger("test.run_retrospection"),
                    )
                out = buf.getvalue()

            self.assertIn("RETROSPECTION → SWEEP SUMMARY", out)
            self.assertEqual(load_trigger(trigger_path).status, "consumed")
            self.assertEqual(list_trigger_paths(log_dir, status="pending"), [])
            self.assertEqual(
                captured["run_kwargs"]["period_start"],
                "2026-07-01",
            )
            self.assertEqual(
                captured["run_kwargs"]["period_end"],
                "2026-07-07",
            )
            refreshed = load_trigger(trigger_path)
            self.assertEqual(
                refreshed.sweep_artifact_path,
                str(log_dir / "sweep_test.json"),
            )
            self.assertIsNotNone(refreshed.claimed_at)

    def test_rejects_non_pending_trigger(self):
        import run_retrospection as cli

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            path = _write_pending(log_dir)
            data = json.loads(path.read_text())
            data["status"] = "consumed"
            path.write_text(json.dumps(data) + "\n")

            args = SimpleNamespace(
                write_kb=False,
                max_workers=1,
                rebalance="weekly",
                run_label="x",
                validate_artifact=None,
            )
            with self.assertRaises(SystemExit) as ctx:
                cli.run_sweep_for_trigger(
                    args,
                    path,
                    logging.getLogger("test.run_retrospection"),
                )
            self.assertIn("not pending", str(ctx.exception))


class TestDefaultSweepWindow(unittest.TestCase):
    def test_default_window_is_lookback(self):
        from strategy_learning.sweep.operator_cli import default_sweep_window

        start, end = default_sweep_window(lookback_days=7)
        self.assertEqual((end - start).days, 7)


if __name__ == "__main__":
    unittest.main()
