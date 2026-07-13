"""Knowledge-base record helpers (schema v2) and EventRef validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

HARD_INFLUENCE_EVENT_TYPES = frozenset({"backtest_run", "trading_cycle", "sweep"})
EVENT_TYPES = frozenset({
    "backtest_run",
    "trading_cycle",
    "sweep",
    "live_underperformance_trigger",
    "operator_review",
})
RECORD_KINDS = frozenset({
    "lesson",
    "backtest_validation",
    "config_recommendation",
    "promotion",
})
RECOMMENDATION_STATUSES = frozenset({
    "pending_review",
    "approved",
    "rejected",
    "deferred",
    "superseded",
    "expired",
})

# Whitelist for hard config promotions (one discrete step per field).
TUNABLE_ENUMS: Dict[str, Dict[str, Sequence[str]]] = {
    "strategy_params": {
        "risk_management": ("conservative", "standard", "aggressive"),
        "position_sizing": ("conservative", "dynamic", "aggressive"),
        "timeframe": ("immediate", "short-term", "long-term"),
    },
    "preferences": {
        "risk_tolerance": ("conservative", "moderate", "aggressive"),
        "max_position_size": (),  # numeric steps handled separately
    },
    "rebalance_params": {
        "threshold": (),
    },
}

MAX_POSITION_SIZE_STEPS = (0.10, 0.15, 0.20, 0.25, 0.30)
REBALANCE_THRESHOLD_STEPS = (0.02, 0.05, 0.08, 0.10, 0.15)
SIGNAL_WEIGHT_DELTA = 0.1
SIGNAL_WEIGHT_MIN = 0.5
SIGNAL_WEIGHT_MAX = 1.5


class KnowledgeBaseError(ValueError):
    """Invalid KB write (missing provenance, bad status, etc.)."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def make_event_ref(
    *,
    event_type: str,
    event_id: str,
    artifact_path: Optional[str] = None,
    artifact_kind: Optional[str] = None,
    summary: str = "",
    user_id: str = "default",
    timestamp: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise KnowledgeBaseError(f"Unknown event_type: {event_type}")
    if not event_id:
        raise KnowledgeBaseError("event_id is required")
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "user_id": user_id,
        "timestamp": timestamp or utc_now_iso(),
        "artifact_path": artifact_path,
        "artifact_kind": artifact_kind,
        "summary": summary or "",
        "metadata": dict(metadata or {}),
        "persistence": {"phase": "file", "table": None, "row_id": None},
    }


def require_hard_event_ref(event: Optional[Dict[str, Any]], *, context: str) -> None:
    if not isinstance(event, dict):
        raise KnowledgeBaseError(f"{context}: missing EventRef")
    event_type = event.get("event_type")
    event_id = event.get("event_id")
    if event_type not in HARD_INFLUENCE_EVENT_TYPES:
        raise KnowledgeBaseError(
            f"{context}: EventRef.event_type must be one of "
            f"{sorted(HARD_INFLUENCE_EVENT_TYPES)}, got {event_type!r}"
        )
    if not event_id:
        raise KnowledgeBaseError(f"{context}: EventRef.event_id is required")


def config_hash(snapshot: Dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def empty_v2_document(user_id: str = "default") -> Dict[str, Any]:
    return {
        "schema_version": 2,
        "user_id": user_id,
        "updated_at": utc_now_iso(),
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


def migrate_v1_to_v2(data: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
    doc = empty_v2_document(user_id=user_id)
    lessons_raw = list(data.get("lessons") or [])
    for item in lessons_raw:
        if isinstance(item, dict) and item.get("kind") == "lesson":
            doc["lessons"].append(item)
            continue
        text = str(item)
        doc["lessons"].append({
            "id": new_id("les"),
            "kind": "lesson",
            "user_id": user_id,
            "source": "live",
            "created_at": utc_now_iso(),
            "summary": text,
            "rationale": "Migrated from schema v1 string lesson",
            "provenance": {
                "trigger_event": make_event_ref(
                    event_type="trading_cycle",
                    event_id="migrated",
                    summary="v1 migration placeholder",
                    user_id=user_id,
                )
            },
            "tags": ["migrated"],
            "supersedes": None,
        })
    doc["derived_state"]["signal_weights"] = dict(data.get("signal_weights") or {})
    doc["derived_state"]["strategy_preferences"] = dict(
        data.get("strategy_preferences") or {}
    )
    return doc


def ensure_v2(data: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
    version = int(data.get("schema_version") or 1)
    if version >= 2 and "derived_state" in data:
        doc = dict(data)
        doc.setdefault("user_id", user_id)
        doc.setdefault("lessons", [])
        doc.setdefault("backtest_validations", [])
        doc.setdefault("config_recommendations", [])
        doc.setdefault("promotions", [])
        derived = dict(doc.get("derived_state") or {})
        derived.setdefault("signal_weights", {})
        derived.setdefault("strategy_preferences", {})
        derived.setdefault("active_recommendation_id", None)
        derived.setdefault("last_promotion_id", None)
        # Compat: top-level weights/prefs from partial saves
        if not derived["signal_weights"] and data.get("signal_weights"):
            derived["signal_weights"] = dict(data["signal_weights"])
        if not derived["strategy_preferences"] and data.get("strategy_preferences"):
            derived["strategy_preferences"] = dict(data["strategy_preferences"])
        doc["derived_state"] = derived
        doc["schema_version"] = 2
        return doc
    return migrate_v1_to_v2(data, user_id=user_id)


def lesson_summaries(lessons: Sequence[Any], limit: int = 10) -> List[str]:
    out: List[str] = []
    for item in lessons[-limit:]:
        if isinstance(item, dict):
            text = item.get("summary") or ""
        else:
            text = str(item)
        if text:
            out.append(text)
    return out


def select_lessons_for_prompt(
    lessons: Sequence[Dict[str, Any]],
    *,
    last_validated_backtest_id: Optional[str] = None,
    max_total: int = 10,
) -> List[str]:
    """Last 5 backtest-linked + last 5 live, deduped, max 10."""
    backtest: List[str] = []
    live: List[str] = []
    for item in reversed(list(lessons)):
        if not isinstance(item, dict):
            continue
        summary = (item.get("summary") or "").strip()
        if not summary:
            continue
        source = item.get("source")
        lineage = (item.get("provenance") or {}).get("kb_lineage") or {}
        if source == "backtest":
            if last_validated_backtest_id and lineage.get("backtest_validation_id"):
                if lineage.get("backtest_validation_id") != last_validated_backtest_id:
                    # Still allow general backtest lessons
                    pass
            if summary not in backtest and len(backtest) < 5:
                backtest.append(summary)
        elif source == "live":
            if summary not in live and len(live) < 5:
                live.append(summary)
        if len(backtest) >= 5 and len(live) >= 5:
            break
    combined: List[str] = []
    for summary in backtest + live:
        if summary not in combined:
            combined.append(summary)
        if len(combined) >= max_total:
            break
    return combined


def referenced_lesson_ids(doc: Dict[str, Any]) -> set:
    """Lesson ids that must survive trim (linked from active/pending recommendations)."""
    keep: set = set()
    derived = doc.get("derived_state") or {}
    active_id = derived.get("active_recommendation_id")
    for rec in doc.get("config_recommendations") or []:
        if not isinstance(rec, dict):
            continue
        if rec.get("id") == active_id or rec.get("status") == "pending_review":
            lineage = (rec.get("provenance") or {}).get("kb_lineage") or {}
            for key in ("lesson_id", "lesson_ids"):
                val = lineage.get(key)
                if isinstance(val, str):
                    keep.add(val)
                elif isinstance(val, list):
                    keep.update(str(x) for x in val)
    return keep


def trim_lessons(lessons: List[Dict[str, Any]], max_n: int, keep_ids: set) -> List[Dict[str, Any]]:
    if len(lessons) <= max_n:
        return lessons
    kept_refs = [l for l in lessons if isinstance(l, dict) and l.get("id") in keep_ids]
    others = [l for l in lessons if not (isinstance(l, dict) and l.get("id") in keep_ids)]
    room = max(0, max_n - len(kept_refs))
    return kept_refs + others[-room:]


def step_enum(current: Optional[str], choices: Sequence[str], direction: int) -> Optional[str]:
    if not choices:
        return None
    cur = current if current in choices else choices[len(choices) // 2]
    idx = list(choices).index(cur)
    nxt = max(0, min(len(choices) - 1, idx + direction))
    return choices[nxt]


def step_numeric(current: float, steps: Sequence[float], direction: int) -> float:
    ordered = sorted(steps)
    # Find nearest step
    nearest = min(ordered, key=lambda s: abs(s - current))
    idx = ordered.index(nearest)
    nxt = max(0, min(len(ordered) - 1, idx + direction))
    return ordered[nxt]


def clamp_signal_weight(value: float) -> float:
    return max(SIGNAL_WEIGHT_MIN, min(SIGNAL_WEIGHT_MAX, round(value, 3)))
