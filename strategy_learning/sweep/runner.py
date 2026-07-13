"""Param sweep runner — N backtests → SweepResult (+ optional KB recommendation)."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from strategy_learning.knowledge.records import new_id, utc_now_iso
from strategy_learning.knowledge.store import KnowledgeBase
from strategy_learning.sweep.candidates import expand_oat_candidates, merge_proposed_changes
from strategy_learning.sweep.models import SweepCandidateResult, SweepResult
from strategy_learning.sweep.recommend import maybe_write_recommendation, select_winner

logger = logging.getLogger(__name__)

# Rough LLM calls per rebalance cycle (3 analysis + strategy + optional rebalance).
_EST_LLM_CALLS_PER_CYCLE = 5

# (proposed_changes, run_label) → run-like object with run_id/status/metrics (+ optional artifact_path)
BacktestCallable = Callable[[Dict[str, Any], str], Any]


def _as_run_fields(run: Any) -> Tuple[Optional[str], str, Dict[str, Any], Optional[str], Optional[str]]:
    if isinstance(run, dict):
        return (
            run.get("run_id"),
            str(run.get("status") or "unknown"),
            dict(run.get("metrics") or {}),
            run.get("artifact_path"),
            run.get("error"),
        )
    return (
        getattr(run, "run_id", None),
        str(getattr(run, "status", None) or "unknown"),
        dict(getattr(run, "metrics", None) or {}),
        getattr(run, "artifact_path", None),
        getattr(run, "error", None),
    )


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def estimate_rebalance_cycles(
    period_start: Optional[str],
    period_end: Optional[str],
    *,
    rebalance_frequency: str = "weekly",
) -> Optional[int]:
    """Calendar estimate of rebalance cycles (not market-calendar exact)."""
    start = _parse_iso_date(period_start)
    end = _parse_iso_date(period_end)
    if start is None or end is None or end < start:
        return None
    days = (end - start).days + 1
    if rebalance_frequency == "daily":
        return max(1, days)
    return max(1, days // 7)


def format_sweep_plan(
    *,
    candidate_labels: List[str],
    max_workers: int,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    rebalance_frequency: str = "weekly",
) -> str:
    """Human-readable plan banner for operators."""
    n_candidates = len(candidate_labels)
    n_backtests = n_candidates + 1  # baseline + candidates
    mode = "SEQUENTIAL" if max_workers <= 1 else f"PARALLEL (max_workers={max_workers})"
    cycles = estimate_rebalance_cycles(
        period_start, period_end, rebalance_frequency=rebalance_frequency
    )
    lines = [
        "=" * 72,
        "PARAM SWEEP PLAN",
        "=" * 72,
        f"Execution mode: {mode}",
        f"Backtest runs: {n_backtests} (1 baseline + {n_candidates} OAT candidates)",
        (
            "Note: default --max-workers=1 runs candidates one after another. "
            "Pass --max-workers N to overlap candidate backtests."
            if max_workers <= 1
            else "Candidate backtests may overlap; LLM calls within each backtest stay sequential."
        ),
    ]
    if cycles is not None:
        est_llm_per_run = cycles * _EST_LLM_CALLS_PER_CYCLE
        est_llm_total = est_llm_per_run * n_backtests
        lines.extend(
            [
                (
                    f"Est. rebalance cycles / run: ~{cycles} "
                    f"({rebalance_frequency}, calendar estimate)"
                ),
                (
                    f"Est. LLM invocations: ~{est_llm_per_run}/run × {n_backtests} runs "
                    f"≈ {est_llm_total} total (rough; actual varies)"
                ),
            ]
        )
    lines.append("Candidates to test:")
    for i, label in enumerate(candidate_labels, start=1):
        lines.append(f"  {i:2d}. {label}")
    if not candidate_labels:
        lines.append("  (none — baseline only)")
    lines.append("=" * 72)
    return "\n".join(lines)


class ParamSweepRunner:
    """Run baseline + OAT candidates via an injected backtest callable."""

    def __init__(
        self,
        *,
        knowledge_base: Optional[KnowledgeBase] = None,
        run_backtest: Optional[BacktestCallable] = None,
        max_workers: int = 1,
        rebalance_frequency: str = "weekly",
    ):
        self.knowledge_base = knowledge_base
        self.run_backtest = run_backtest
        self.max_workers = max(1, int(max_workers))
        self.rebalance_frequency = rebalance_frequency
        self._progress_lock = threading.Lock()
        self._completed = 0
        self._total_runs = 0

    def run(
        self,
        baseline_config: Dict[str, Any],
        *,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        run_label: str = "sweep",
        write_kb: bool = False,
        artifact_path: Optional[str] = None,
        validate_artifact_path: Optional[str] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> SweepResult:
        if self.run_backtest is None:
            raise ValueError("ParamSweepRunner requires run_backtest callable")

        sweep_id = new_id("sw")
        timestamp = utc_now_iso()
        oat = candidates if candidates is not None else expand_oat_candidates(baseline_config)
        notes: List[str] = []

        jobs: List[Dict[str, Any]] = []
        for raw in oat:
            proposed = dict(raw.get("proposed_changes") or {})
            if not proposed:
                continue
            jobs.append(
                {
                    "candidate_id": str(raw.get("candidate_id") or new_id("sc")),
                    "label": str(raw.get("label") or "candidate"),
                    "proposed_changes": proposed,
                    "config_snapshot": merge_proposed_changes(baseline_config, proposed),
                }
            )

        plan = format_sweep_plan(
            candidate_labels=[j["label"] for j in jobs],
            max_workers=self.max_workers,
            period_start=period_start
            or (
                baseline_config.get("start")
                if isinstance(baseline_config.get("start"), str)
                else None
            ),
            period_end=period_end
            or (
                baseline_config.get("end")
                if isinstance(baseline_config.get("end"), str)
                else None
            ),
            rebalance_frequency=self.rebalance_frequency,
        )
        logger.info("\n%s", plan)
        # Also print so progress is visible even when httpx INFO dominates logs.
        print(plan, flush=True)

        self._completed = 0
        self._total_runs = 1 + len(jobs)

        baseline_result = self._execute_one(
            candidate_id=f"{sweep_id}-baseline",
            label="baseline",
            proposed_changes={},
            config_snapshot=baseline_config,
            is_baseline=True,
            run_label=f"{run_label}_baseline",
            progress_index=1,
        )

        candidate_results = self._execute_many(jobs, run_label=run_label)
        winner = select_winner(baseline_result, candidate_results)
        if winner.is_baseline:
            notes.append("No candidate beat baseline; no recommendation written")
        elif winner.status != "success":
            notes.append("Best-ranked run was not successful; no recommendation written")

        result = SweepResult(
            sweep_id=sweep_id,
            timestamp=timestamp,
            run_label=run_label,
            period_start=period_start or (baseline_config.get("start") if isinstance(baseline_config.get("start"), str) else None),
            period_end=period_end or (baseline_config.get("end") if isinstance(baseline_config.get("end"), str) else None),
            baseline_config=dict(baseline_config),
            baseline=baseline_result,
            candidates=candidate_results,
            winner=winner,
            notes=notes,
        )

        if write_kb:
            kb = self.knowledge_base or KnowledgeBase()
            rec = maybe_write_recommendation(
                kb,
                result,
                artifact_path=artifact_path,
                validate_artifact_path=validate_artifact_path,
            )
            if rec:
                result.recommendation_id = rec.get("id")
                notes.append(f"Pending recommendation {rec.get('id')}")
            else:
                notes.append("write_kb set but no recommendation produced")

        return result

    def _mark_complete(self, label: str, status: str, *, progress_index: Optional[int]) -> None:
        with self._progress_lock:
            self._completed += 1
            done = self._completed
            total = self._total_runs
        idx = f"{progress_index}/" if progress_index is not None else ""
        msg = (
            f"Sweep progress: completed {done}/{total} backtest runs "
            f"({idx}{label} → {status})"
        )
        logger.info(msg)
        print(msg, flush=True)

    def _execute_one(
        self,
        *,
        candidate_id: str,
        label: str,
        proposed_changes: Dict[str, Any],
        config_snapshot: Dict[str, Any],
        is_baseline: bool,
        run_label: str,
        progress_index: Optional[int] = None,
    ) -> SweepCandidateResult:
        assert self.run_backtest is not None
        start_msg = (
            f"Sweep starting backtest "
            f"{progress_index}/{self._total_runs}: {label}"
            if progress_index is not None
            else f"Sweep starting backtest: {label}"
        )
        logger.info(start_msg)
        print(start_msg, flush=True)
        started = datetime.now()
        try:
            run = self.run_backtest(config_snapshot, run_label)
            run_id, status, metrics, artifact_path, error = _as_run_fields(run)
            result = SweepCandidateResult(
                candidate_id=candidate_id,
                label=label,
                proposed_changes=proposed_changes,
                status=status,
                run_id=str(run_id) if run_id else None,
                metrics=metrics,
                artifact_path=artifact_path,
                error=error,
                is_baseline=is_baseline,
            )
        except Exception as exc:  # noqa: BLE001 — isolate one candidate failure
            logger.exception("Sweep candidate %s failed", label)
            result = SweepCandidateResult(
                candidate_id=candidate_id,
                label=label,
                proposed_changes=proposed_changes,
                status="failed",
                error=str(exc),
                is_baseline=is_baseline,
            )
        elapsed = (datetime.now() - started).total_seconds()
        logger.info(
            "Sweep finished backtest %s in %.1fs (status=%s sharpe=%s)",
            label,
            elapsed,
            result.status,
            (result.metrics or {}).get("sharpe"),
        )
        self._mark_complete(label, result.status, progress_index=progress_index)
        return result

    def _execute_many(
        self, jobs: List[Dict[str, Any]], *, run_label: str
    ) -> List[SweepCandidateResult]:
        if not jobs:
            return []
        # progress_index: 1=baseline already done; candidates are 2..N
        if self.max_workers == 1:
            return [
                self._execute_one(
                    candidate_id=job["candidate_id"],
                    label=job["label"],
                    proposed_changes=job["proposed_changes"],
                    config_snapshot=job["config_snapshot"],
                    is_baseline=False,
                    run_label=f"{run_label}_{job['candidate_id']}",
                    progress_index=i + 2,
                )
                for i, job in enumerate(jobs)
            ]

        results: List[SweepCandidateResult] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(
                    self._execute_one,
                    candidate_id=job["candidate_id"],
                    label=job["label"],
                    proposed_changes=job["proposed_changes"],
                    config_snapshot=job["config_snapshot"],
                    is_baseline=False,
                    run_label=f"{run_label}_{job['candidate_id']}",
                    progress_index=i + 2,
                ): job
                for i, job in enumerate(jobs)
            }
            for fut in as_completed(futures):
                results.append(fut.result())
        # Stable order: match input job order
        by_id = {r.candidate_id: r for r in results}
        return [by_id[job["candidate_id"]] for job in jobs if job["candidate_id"] in by_id]
