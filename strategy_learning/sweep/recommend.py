"""Map sweep winners to KB config recommendations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strategy_learning.knowledge.records import (
    config_hash,
    make_event_ref,
    new_id,
)
from strategy_learning.knowledge.store import KnowledgeBase
from strategy_learning.sweep.candidates import diff_summary
from strategy_learning.sweep.models import SweepCandidateResult, SweepResult, beats_baseline


def maybe_write_recommendation(
    knowledge_base: KnowledgeBase,
    result: SweepResult,
    *,
    artifact_path: Optional[str] = None,
    validate_artifact_path: Optional[str] = None,
    extra_evidence: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Write a pending recommendation when the winner beats baseline.

    Returns the recommendation record, or None when no hard change is warranted.
    """
    winner = result.winner
    if winner is None or winner.is_baseline:
        return None
    if not winner.proposed_changes:
        return None
    if not beats_baseline(
        winner.metrics,
        result.baseline.metrics,
        candidate_status=winner.status,
        baseline_status=result.baseline.status,
    ):
        return None

    diffs = diff_summary(winner.proposed_changes, result.baseline_config)
    if not diffs:
        return None

    evidence: List[Dict[str, Any]] = []
    if result.baseline.run_id:
        evidence.append(
            make_event_ref(
                event_type="backtest_run",
                event_id=str(result.baseline.run_id),
                artifact_path=result.baseline.artifact_path,
                artifact_kind="backtest",
                summary=f"baseline {result.baseline.label}",
                user_id=knowledge_base.user_id,
            )
        )
    if winner.run_id:
        evidence.append(
            make_event_ref(
                event_type="backtest_run",
                event_id=str(winner.run_id),
                artifact_path=winner.artifact_path,
                artifact_kind="backtest",
                summary=f"winner {winner.label}",
                user_id=knowledge_base.user_id,
            )
        )
    if validate_artifact_path:
        evidence.append(
            make_event_ref(
                event_type="backtest_run",
                event_id=f"validate:{result.sweep_id}",
                artifact_path=validate_artifact_path,
                artifact_kind="backtest",
                summary="held-out validate window",
                user_id=knowledge_base.user_id,
            )
        )
    if extra_evidence:
        evidence.extend(dict(ev) for ev in extra_evidence if isinstance(ev, dict))

    trigger = make_event_ref(
        event_type="sweep",
        event_id=result.sweep_id,
        artifact_path=artifact_path,
        artifact_kind="sweep",
        summary=(
            f"param sweep {result.run_label} "
            f"{result.period_start}→{result.period_end}; winner={winner.label}"
        ),
        user_id=knowledge_base.user_id,
        timestamp=result.timestamp,
        metadata={
            "run_label": result.run_label,
            "winner_candidate_id": winner.candidate_id,
            "candidate_count": len(result.candidates),
        },
    )

    c_hash = config_hash(result.baseline_config)
    b_sharpe = (result.baseline.metrics or {}).get("sharpe")
    w_sharpe = (winner.metrics or {}).get("sharpe")
    recommendation = knowledge_base.append_config_recommendation(
        {
            "id": new_id("cr"),
            "summary": f"Proposed config change from param sweep ({winner.label})",
            "rationale": (
                f"OAT sweep winner beat baseline on rank key "
                f"(baseline sharpe={b_sharpe}, winner sharpe={w_sharpe}). "
                f"Diff: " + "; ".join(diffs)
            ),
            "provenance": {
                "generated_by": "param_sweep",
                "trigger_event": trigger,
                "evidence_events": evidence,
                "kb_lineage": {
                    "sweep_id": result.sweep_id,
                    "winner_candidate_id": winner.candidate_id,
                },
            },
            "status": "pending_review",
            "baseline_config_hash": c_hash,
            "proposed_changes": dict(winner.proposed_changes),
            "diff_summary": diffs,
            "expected_impact": {
                "baseline_metrics": dict(result.baseline.metrics or {}),
                "winner_metrics": dict(winner.metrics or {}),
            },
            "review": {
                "reviewed_at": None,
                "reviewed_by": None,
                "decision": None,
                "reject_reason": None,
            },
            "supersedes": None,
            "superseded_by": None,
        }
    )
    return recommendation


def select_winner(
    baseline: SweepCandidateResult,
    candidates: List[SweepCandidateResult],
) -> SweepCandidateResult:
    """Return the best successful run among baseline + candidates."""
    pool = [baseline] + list(candidates)
    return max(pool, key=lambda c: c.rank_key())
