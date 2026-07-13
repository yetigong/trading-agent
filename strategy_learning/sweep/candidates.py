"""One-at-a-time (OAT) candidate expansion for param sweep."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from strategy_learning.knowledge.records import (
    MAX_POSITION_SIZE_STEPS,
    REBALANCE_THRESHOLD_STEPS,
    TUNABLE_ENUMS,
    new_id,
)


def _baseline_value(baseline: Dict[str, Any], section: str, key: str) -> Any:
    return (baseline.get(section) or {}).get(key)


def _candidate(
    *,
    section: str,
    key: str,
    value: Any,
    baseline_value: Any,
) -> Dict[str, Any]:
    proposed = {section: {key: value}}
    return {
        "candidate_id": new_id("sc"),
        "label": f"{section}.{key}={value}",
        "field": f"{section}.{key}",
        "baseline_value": baseline_value,
        "value": value,
        "proposed_changes": proposed,
    }


def expand_oat_candidates(baseline: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand whitelist neighbors one field at a time (skip baseline-identical).

    ``baseline`` should include ``strategy_params``, ``preferences``, and
    ``rebalance_params`` keys (missing sections treated as empty).
    """
    candidates: List[Dict[str, Any]] = []

    for section, fields in TUNABLE_ENUMS.items():
        for key, choices in fields.items():
            if not choices:
                continue
            current = _baseline_value(baseline, section, key)
            for value in choices:
                if value == current:
                    continue
                candidates.append(
                    _candidate(
                        section=section,
                        key=key,
                        value=value,
                        baseline_value=current,
                    )
                )

    cur_size = _baseline_value(baseline, "preferences", "max_position_size")
    try:
        cur_size_f = float(cur_size) if cur_size is not None else None
    except (TypeError, ValueError):
        cur_size_f = None
    for value in MAX_POSITION_SIZE_STEPS:
        if cur_size_f is not None and abs(float(value) - cur_size_f) < 1e-12:
            continue
        candidates.append(
            _candidate(
                section="preferences",
                key="max_position_size",
                value=float(value),
                baseline_value=cur_size,
            )
        )

    cur_thr = _baseline_value(baseline, "rebalance_params", "threshold")
    try:
        cur_thr_f = float(cur_thr) if cur_thr is not None else None
    except (TypeError, ValueError):
        cur_thr_f = None
    for value in REBALANCE_THRESHOLD_STEPS:
        if cur_thr_f is not None and abs(float(value) - cur_thr_f) < 1e-12:
            continue
        candidates.append(
            _candidate(
                section="rebalance_params",
                key="threshold",
                value=float(value),
                baseline_value=cur_thr,
            )
        )

    return candidates


def merge_proposed_changes(
    baseline: Dict[str, Any], proposed_changes: Dict[str, Any]
) -> Dict[str, Any]:
    """Deep-merge nested proposed_changes onto a baseline config snapshot."""
    merged = deepcopy(baseline)
    for section, changes in (proposed_changes or {}).items():
        if not isinstance(changes, dict):
            continue
        bucket = dict(merged.get(section) or {})
        bucket.update(changes)
        merged[section] = bucket
    return merged


def diff_summary(proposed_changes: Dict[str, Any], baseline: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for section, changes in (proposed_changes or {}).items():
        if not isinstance(changes, dict):
            continue
        for key, value in changes.items():
            old = _baseline_value(baseline, section, key)
            lines.append(f"{section}.{key}: {old} → {value}")
    return lines


def config_snapshot_from_sections(
    *,
    strategy_params: Dict[str, Any] | None = None,
    preferences: Dict[str, Any] | None = None,
    rebalance_params: Dict[str, Any] | None = None,
    signal_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "strategy_params": dict(strategy_params or {}),
        "preferences": dict(preferences or {}),
        "rebalance_params": dict(rebalance_params or {}),
    }
    if signal_config is not None:
        snap["signal_config"] = {
            k: signal_config.get(k)
            for k in ("enabled_sources",)
            if signal_config.get(k) is not None
        }
    return snap
