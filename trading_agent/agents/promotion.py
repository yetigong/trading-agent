"""Promote / reject pending config recommendations (human-in-the-loop)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.agents.kb_records import config_hash, make_event_ref
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.storage import (
    PreferencesStore,
    RebalanceConfigStore,
    StrategyConfigStore,
)

logger = logging.getLogger(__name__)
LOG_DIR = Path("logs")

# Soft KB-only keys must never be written to hard config stores.
SOFT_PREF_KEYS = frozenset({"recent_trade_bias", "last_validated_backtest_id"})


def snapshot_active_config() -> Dict[str, Any]:
    return {
        "strategy_params": StrategyConfigStore().load(),
        "preferences": PreferencesStore().load_preferences().to_dict(),
        "rebalance_params": RebalanceConfigStore().load(),
    }


def apply_proposed_changes(proposed: Dict[str, Any]) -> Dict[str, Any]:
    """Merge whitelist proposed_changes into config stores; preserve other keys."""
    applied: Dict[str, Any] = {}
    if "strategy_params" in proposed:
        store = StrategyConfigStore()
        current = store.load()
        merged = {**current, **dict(proposed["strategy_params"])}
        store.save(merged)
        applied["strategy_params"] = dict(proposed["strategy_params"])
    if "preferences" in proposed:
        store = PreferencesStore()
        prefs = store.load_preferences()
        data = prefs.to_dict()
        for key, value in dict(proposed["preferences"]).items():
            if key in SOFT_PREF_KEYS:
                continue
            data[key] = value
        store.save(data)
        applied["preferences"] = {
            k: v
            for k, v in dict(proposed["preferences"]).items()
            if k not in SOFT_PREF_KEYS
        }
    if "rebalance_params" in proposed:
        store = RebalanceConfigStore()
        current = store.load()
        merged = {**current, **dict(proposed["rebalance_params"])}
        store.save(merged)
        applied["rebalance_params"] = dict(proposed["rebalance_params"])
    return applied


def write_promotion_audit(record: Dict[str, Any]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_DIR / f"config_promotions_{stamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return path


def review_status(kb: Optional[KnowledgeBase] = None) -> Dict[str, Any]:
    kb = kb or KnowledgeBase()
    pending = kb.get_pending_recommendation()
    return {
        "pending": pending is not None,
        "recommendation": pending,
    }


def approve_recommendation(
    recommendation_id: Optional[str] = None,
    *,
    kb: Optional[KnowledgeBase] = None,
    reviewed_by: str = "operator",
    require_validate_window: bool = False,
    validate_artifact: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply proposed_changes after human approval.

    Walk-forward gate (Phase C): when require_validate_window is True, a second
    held-out backtest artifact must be provided and status==success.
    """
    kb = kb or KnowledgeBase()
    pending = kb.get_pending_recommendation()
    if pending is None:
        raise ValueError("No pending_review recommendation")
    if recommendation_id and pending.get("id") != recommendation_id:
        raise ValueError(
            f"Pending recommendation is {pending.get('id')}, not {recommendation_id}"
        )

    if require_validate_window:
        if not validate_artifact:
            raise ValueError(
                "Walk-forward gate: pass --validate-artifact PATH to a held-out "
                "backtest that meets objective constraints before --approve"
            )
        with Path(validate_artifact).open(encoding="utf-8") as f:
            validate_run = json.load(f)
        if validate_run.get("status") != "success":
            raise ValueError(
                f"Walk-forward gate blocked: validate run status="
                f"{validate_run.get('status')}"
            )

    before = snapshot_active_config()
    hash_before = config_hash(before)
    applied = apply_proposed_changes(pending.get("proposed_changes") or {})
    after = snapshot_active_config()
    hash_after = config_hash(after)

    updated = kb.update_recommendation_review(
        pending["id"],
        status="approved",
        reviewed_by=reviewed_by,
    )

    provenance = dict(pending.get("provenance") or {})
    originating = list(provenance.get("evidence_events") or [])
    trigger = provenance.get("trigger_event")
    if trigger and trigger not in originating:
        originating = [trigger] + originating

    promotion = kb.append_promotion({
        "summary": f"Approved {pending.get('id')}",
        "rationale": pending.get("rationale") or "Operator approved",
        "provenance": {
            "review_event": make_event_ref(
                event_type="operator_review",
                event_id=pending["id"],
                artifact_kind="promotion",
                summary=f"Approved {pending['id']}",
                user_id=kb.user_id,
            ),
            "config_recommendation_id": pending["id"],
            "kb_lineage": list(
                filter(
                    None,
                    [
                        pending["id"],
                        (provenance.get("kb_lineage") or {}).get("backtest_validation_id"),
                        (provenance.get("kb_lineage") or {}).get("baseline_validation_id"),
                    ],
                )
            ),
            "originating_events": originating,
            "review_command": (
                f"scripts/review_config_recommendation.py --approve "
                f"--recommendation-id {pending['id']}"
            ),
        },
        "decision": "approved",
        "reviewed_by": reviewed_by,
        "config_hash_before": hash_before,
        "config_hash_after": hash_after,
        "applied_changes": applied,
        "applied": True,
    })
    audit_path = write_promotion_audit(promotion)
    provenance = dict(promotion.get("provenance") or {})
    provenance["review_event"]["artifact_path"] = str(audit_path)
    promotion["provenance"] = provenance

    return {
        "recommendation": updated,
        "promotion": promotion,
        "audit_path": str(audit_path),
        "applied_changes": applied,
    }


def reject_recommendation(
    recommendation_id: Optional[str] = None,
    *,
    reason: str = "",
    kb: Optional[KnowledgeBase] = None,
    reviewed_by: str = "operator",
) -> Dict[str, Any]:
    kb = kb or KnowledgeBase()
    pending = kb.get_pending_recommendation()
    if pending is None:
        raise ValueError("No pending_review recommendation")
    if recommendation_id and pending.get("id") != recommendation_id:
        raise ValueError(
            f"Pending recommendation is {pending.get('id')}, not {recommendation_id}"
        )

    before = snapshot_active_config()
    updated = kb.update_recommendation_review(
        pending["id"],
        status="rejected",
        reviewed_by=reviewed_by,
        reject_reason=reason or None,
    )
    provenance = dict(pending.get("provenance") or {})
    originating = list(provenance.get("evidence_events") or [])
    trigger = provenance.get("trigger_event")
    if trigger and trigger not in originating:
        originating = [trigger] + originating

    promotion = kb.append_promotion({
        "summary": f"Rejected {pending.get('id')}",
        "rationale": reason or "Operator rejected",
        "provenance": {
            "review_event": make_event_ref(
                event_type="operator_review",
                event_id=pending["id"],
                artifact_kind="promotion",
                summary=f"Rejected {pending['id']}",
                user_id=kb.user_id,
            ),
            "config_recommendation_id": pending["id"],
            "kb_lineage": [pending["id"]],
            "originating_events": originating,
            "review_command": (
                f"scripts/review_config_recommendation.py --reject "
                f"--recommendation-id {pending['id']}"
            ),
        },
        "decision": "rejected",
        "reviewed_by": reviewed_by,
        "config_hash_before": config_hash(before),
        "config_hash_after": config_hash(before),
        "applied_changes": {},
        "applied": False,
    })
    audit_path = write_promotion_audit(promotion)
    return {
        "recommendation": updated,
        "promotion": promotion,
        "audit_path": str(audit_path),
    }


def defer_recommendation(
    recommendation_id: Optional[str] = None,
    *,
    kb: Optional[KnowledgeBase] = None,
    reviewed_by: str = "operator",
) -> Dict[str, Any]:
    kb = kb or KnowledgeBase()
    pending = kb.get_pending_recommendation()
    if pending is None:
        raise ValueError("No pending_review recommendation")
    if recommendation_id and pending.get("id") != recommendation_id:
        raise ValueError(
            f"Pending recommendation is {pending.get('id')}, not {recommendation_id}"
        )
    updated = kb.update_recommendation_review(
        pending["id"],
        status="deferred",
        reviewed_by=reviewed_by,
    )
    # Keep active pointer cleared; operator can re-run feedback for a new proposal.
    return {"recommendation": updated}


def format_pending_diff(pending: Dict[str, Any]) -> str:
    lines = [
        "=" * 72,
        "PENDING CONFIG RECOMMENDATION",
        "=" * 72,
        f"id: {pending.get('id')}",
        f"summary: {pending.get('summary')}",
        f"rationale: {pending.get('rationale')}",
        "Proposed changes:",
    ]
    for diff in pending.get("diff_summary") or []:
        lines.append(f"  - {diff}")
    if not pending.get("diff_summary"):
        lines.append(f"  {json.dumps(pending.get('proposed_changes') or {}, indent=2)}")
    active = snapshot_active_config()
    lines.append("Active config hashes:")
    lines.append(f"  current: {config_hash(active)}")
    lines.append(f"  baseline: {pending.get('baseline_config_hash')}")
    lines.append("=" * 72)
    return "\n".join(lines)
