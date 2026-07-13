"""Durable retrospection signal I/O (logs/retrospection_*.json)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from strategy_learning.knowledge.records import make_event_ref, new_id, utc_now_iso
from strategy_learning.retrospection.detector import default_thresholds
from strategy_learning.retrospection.models import RetrospectionEval, RetrospectionTrigger

logger = logging.getLogger(__name__)

DEFAULT_LOG_DIR = Path("logs")
ACTIVE_TRIGGER_STATUSES = frozenset({"pending", "in_progress"})


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    text = str(ts).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _write_trigger(path: Path, trigger: RetrospectionTrigger) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(trigger.to_dict(), f, indent=2)
        f.write("\n")


def write_retrospection_signal(
    eval_result: RetrospectionEval,
    *,
    log_dir: Union[str, Path] = DEFAULT_LOG_DIR,
    cycle_artifact_path: Optional[str] = None,
    user_id: str = "default",
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """Persist a pending retrospection trigger artifact.

    Requires ``eval_result.triggered`` to be True. Returns the path written.
    """
    if not eval_result.triggered:
        raise ValueError(
            "write_retrospection_signal requires eval_result.triggered=True"
        )
    root = Path(log_dir)
    root.mkdir(parents=True, exist_ok=True)
    trigger_id = new_id("rt")
    timestamp = utc_now_iso()
    event_ref = make_event_ref(
        event_type="live_underperformance_trigger",
        event_id=trigger_id,
        artifact_kind="retrospection",
        summary="; ".join(eval_result.reasons) or "live underperformance",
        user_id=user_id,
        timestamp=timestamp,
        metadata={
            "cycle_id": eval_result.cycle_id,
            "reasons": list(eval_result.reasons),
            **dict(extra or {}),
        },
    )
    trigger = RetrospectionTrigger(
        trigger_id=trigger_id,
        timestamp=timestamp,
        status="pending",
        reasons=list(eval_result.reasons),
        metrics=dict(eval_result.metrics),
        cycle_id=eval_result.cycle_id,
        cycle_artifact_path=cycle_artifact_path,
        event_ref=event_ref,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = root / f"retrospection_{stamp}_{trigger_id[-12:]}.json"
    event_ref["artifact_path"] = str(path)
    trigger.event_ref = event_ref
    _write_trigger(path, trigger)
    logger.info("Wrote retrospection trigger %s → %s", trigger_id, path)
    return path


def load_trigger(path: Union[str, Path]) -> RetrospectionTrigger:
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)
    return RetrospectionTrigger.from_dict(data)


def list_trigger_paths(
    log_dir: Union[str, Path] = DEFAULT_LOG_DIR,
    *,
    status: Optional[str] = "pending",
) -> List[Path]:
    root = Path(log_dir)
    if not root.exists():
        return []
    paths = sorted(root.glob("retrospection_*.json"), key=lambda p: p.stat().st_mtime)
    if status is None:
        return paths
    matched: List[Path] = []
    for path in paths:
        try:
            trigger = load_trigger(path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if trigger.status == status:
            matched.append(path)
    return matched


def has_pending_trigger(log_dir: Union[str, Path] = DEFAULT_LOG_DIR) -> bool:
    """True when a pending or in-progress trigger exists (blocks new emits)."""
    root = Path(log_dir)
    if not root.exists():
        return False
    for path in root.glob("retrospection_*.json"):
        try:
            trigger = load_trigger(path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if trigger.status in ACTIVE_TRIGGER_STATUSES:
            return True
    return False


def latest_trigger_timestamp(
    log_dir: Union[str, Path] = DEFAULT_LOG_DIR,
) -> Optional[datetime]:
    root = Path(log_dir)
    if not root.exists():
        return None
    latest: Optional[datetime] = None
    for path in root.glob("retrospection_*.json"):
        try:
            trigger = load_trigger(path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        ts = _parse_iso(trigger.timestamp)
        if ts is None:
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


def cooldown_active(
    log_dir: Union[str, Path] = DEFAULT_LOG_DIR,
    *,
    cooldown_days: Optional[int] = None,
    as_of: Optional[datetime] = None,
) -> bool:
    """True when a trigger was written within the cooldown window."""
    days = cooldown_days
    if days is None:
        days = int(default_thresholds()["cooldown_days"])
    last = latest_trigger_timestamp(log_dir)
    if last is None:
        return False
    now = as_of or datetime.now(timezone.utc)
    return last >= now - timedelta(days=days)


def claim_trigger(path: Union[str, Path]) -> RetrospectionTrigger:
    """Atomically claim a pending trigger for consumption (lease → in_progress).

    Raises ValueError if the trigger is not pending (e.g. already claimed/consumed).
    """
    path = Path(path)
    trigger = load_trigger(path)
    if trigger.status != "pending":
        raise ValueError(
            f"Trigger is not pending (status={trigger.status}): {path}"
        )
    trigger.status = "in_progress"
    trigger.claimed_at = utc_now_iso()
    _write_trigger(path, trigger)
    # Re-read to reduce double-claim races: if another writer won, status may differ.
    refreshed = load_trigger(path)
    if refreshed.status != "in_progress" or refreshed.claimed_at != trigger.claimed_at:
        raise ValueError(f"Failed to claim trigger (lost race): {path}")
    logger.info("Claimed retrospection trigger %s → in_progress", path)
    return refreshed


def mark_consumed(
    path: Union[str, Path],
    *,
    sweep_artifact_path: Optional[str] = None,
    recommendation_id: Optional[str] = None,
) -> RetrospectionTrigger:
    path = Path(path)
    trigger = load_trigger(path)
    if trigger.status not in {"pending", "in_progress"}:
        raise ValueError(
            f"Trigger cannot be consumed (status={trigger.status}): {path}"
        )
    trigger.status = "consumed"
    trigger.consumed_at = utc_now_iso()
    if sweep_artifact_path is not None:
        trigger.sweep_artifact_path = sweep_artifact_path
    if recommendation_id is not None:
        trigger.recommendation_id = recommendation_id
    _write_trigger(path, trigger)
    logger.info("Marked retrospection trigger consumed: %s", path)
    return trigger
