"""Live retrospection evaluation and trigger models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetrospectionEval:
    """Result of evaluating live underperformance rules."""

    triggered: bool
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    cycle_id: Optional[str] = None
    skipped_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": self.triggered,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
            "cycle_id": self.cycle_id,
            "skipped_reason": self.skipped_reason,
        }


@dataclass
class RetrospectionTrigger:
    """Durable out-of-band retrospection signal (logs/retrospection_*.json)."""

    trigger_id: str
    timestamp: str
    status: str  # pending | in_progress | consumed
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    cycle_id: Optional[str] = None
    cycle_artifact_path: Optional[str] = None
    event_ref: Optional[Dict[str, Any]] = None
    claimed_at: Optional[str] = None
    consumed_at: Optional[str] = None
    sweep_artifact_path: Optional[str] = None
    recommendation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
            "cycle_id": self.cycle_id,
            "cycle_artifact_path": self.cycle_artifact_path,
            "event_ref": dict(self.event_ref) if self.event_ref else None,
            "claimed_at": self.claimed_at,
            "consumed_at": self.consumed_at,
            "sweep_artifact_path": self.sweep_artifact_path,
            "recommendation_id": self.recommendation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrospectionTrigger":
        return cls(
            trigger_id=str(data.get("trigger_id") or ""),
            timestamp=str(data.get("timestamp") or ""),
            status=str(data.get("status") or "pending"),
            reasons=list(data.get("reasons") or []),
            metrics=dict(data.get("metrics") or {}),
            cycle_id=data.get("cycle_id"),
            cycle_artifact_path=data.get("cycle_artifact_path"),
            event_ref=dict(data["event_ref"]) if data.get("event_ref") else None,
            claimed_at=data.get("claimed_at"),
            consumed_at=data.get("consumed_at"),
            sweep_artifact_path=data.get("sweep_artifact_path"),
            recommendation_id=data.get("recommendation_id"),
        )
