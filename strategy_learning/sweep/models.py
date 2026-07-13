"""Param sweep result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def metric_rank_key(metrics: Dict[str, Any], status: str) -> Tuple[float, float, float]:
    """Higher is better: sharpe, alpha_vs_spy, then lower |max_drawdown|."""
    if status != "success":
        return (float("-inf"), float("-inf"), float("-inf"))
    sharpe = metrics.get("sharpe")
    alpha = metrics.get("alpha_vs_spy")
    max_dd = metrics.get("max_drawdown")
    sharpe_v = float(sharpe) if sharpe is not None else float("-inf")
    alpha_v = float(alpha) if alpha is not None else float("-inf")
    # Prefer smaller absolute drawdown → negate abs for higher-is-better ranking.
    dd_v = -abs(float(max_dd)) if max_dd is not None else float("-inf")
    return (sharpe_v, alpha_v, dd_v)


def beats_baseline(
    candidate_metrics: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    *,
    candidate_status: str = "success",
    baseline_status: str = "success",
) -> bool:
    """True when candidate strictly beats baseline on primary rank (sharpe first)."""
    if candidate_status != "success":
        return False
    c_key = metric_rank_key(candidate_metrics, candidate_status)
    b_key = metric_rank_key(baseline_metrics, baseline_status)
    return c_key > b_key


@dataclass
class SweepCandidateResult:
    candidate_id: str
    label: str
    proposed_changes: Dict[str, Any]
    status: str
    run_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifact_path: Optional[str] = None
    error: Optional[str] = None
    is_baseline: bool = False

    def rank_key(self) -> Tuple[float, float, float]:
        return metric_rank_key(self.metrics, self.status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "label": self.label,
            "proposed_changes": dict(self.proposed_changes),
            "status": self.status,
            "run_id": self.run_id,
            "metrics": dict(self.metrics),
            "artifact_path": self.artifact_path,
            "error": self.error,
            "is_baseline": self.is_baseline,
            "rank_key": list(self.rank_key()),
        }


@dataclass
class SweepResult:
    sweep_id: str
    timestamp: str
    run_label: str
    period_start: Optional[str]
    period_end: Optional[str]
    baseline_config: Dict[str, Any]
    baseline: SweepCandidateResult
    candidates: List[SweepCandidateResult] = field(default_factory=list)
    winner: Optional[SweepCandidateResult] = None
    recommendation_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sweep_id": self.sweep_id,
            "timestamp": self.timestamp,
            "run_label": self.run_label,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "baseline_config": dict(self.baseline_config),
            "baseline": self.baseline.to_dict(),
            "candidates": [c.to_dict() for c in self.candidates],
            "winner": self.winner.to_dict() if self.winner else None,
            "recommendation_id": self.recommendation_id,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SweepResult":
        def _cand(raw: Dict[str, Any]) -> SweepCandidateResult:
            return SweepCandidateResult(
                candidate_id=str(raw.get("candidate_id") or ""),
                label=str(raw.get("label") or ""),
                proposed_changes=dict(raw.get("proposed_changes") or {}),
                status=str(raw.get("status") or "unknown"),
                run_id=raw.get("run_id"),
                metrics=dict(raw.get("metrics") or {}),
                artifact_path=raw.get("artifact_path"),
                error=raw.get("error"),
                is_baseline=bool(raw.get("is_baseline")),
            )

        winner_raw = data.get("winner")
        return cls(
            sweep_id=str(data.get("sweep_id") or ""),
            timestamp=str(data.get("timestamp") or ""),
            run_label=str(data.get("run_label") or "sweep"),
            period_start=data.get("period_start"),
            period_end=data.get("period_end"),
            baseline_config=dict(data.get("baseline_config") or {}),
            baseline=_cand(dict(data.get("baseline") or {})),
            candidates=[_cand(c) for c in (data.get("candidates") or [])],
            winner=_cand(winner_raw) if winner_raw else None,
            recommendation_id=data.get("recommendation_id"),
            notes=list(data.get("notes") or []),
        )
