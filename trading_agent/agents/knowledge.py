"""File-backed knowledge base for Learner / BacktestFeedback (Phase 6 → DB)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from trading_agent.agents.kb_records import (
    KnowledgeBaseError,
    RECOMMENDATION_STATUSES,
    clamp_signal_weight,
    config_hash,
    empty_v2_document,
    ensure_v2,
    lesson_summaries,
    make_event_ref,
    new_id,
    require_hard_event_ref,
    referenced_lesson_ids,
    select_lessons_for_prompt,
    trim_lessons,
    utc_now_iso,
)
from trading_agent.storage.base import JsonFileStore

MAX_LESSONS = 100
MAX_VALIDATIONS = 50
MAX_RECOMMENDATIONS = 50
MAX_PROMOTIONS = 100


class KnowledgeBase:
    def __init__(
        self,
        filename: str = "knowledge_base.json",
        data_dir: Optional[Path] = None,
        example_dir: Optional[Path] = None,
        user_id: str = "default",
    ):
        self.user_id = user_id
        self._store = JsonFileStore(filename, data_dir=data_dir, example_dir=example_dir)

    def load(self) -> Dict[str, Any]:
        raw = self._store.load()
        doc = ensure_v2(raw, user_id=self.user_id)
        # Enforce scoped user — never return another user's document.
        if doc.get("user_id") and doc["user_id"] != self.user_id:
            raise KnowledgeBaseError(
                f"KB user_id mismatch: file has {doc['user_id']!r}, "
                f"instance expects {self.user_id!r}"
            )
        doc["user_id"] = self.user_id
        return doc

    def save(self, data: Dict[str, Any]) -> None:
        doc = ensure_v2(data, user_id=self.user_id)
        if doc.get("user_id") != self.user_id:
            raise KnowledgeBaseError("Refusing to save KB for a different user_id")
        doc["user_id"] = self.user_id
        doc["updated_at"] = utc_now_iso()
        doc["schema_version"] = 2
        # Keep top-level mirrors for older readers / tests
        derived = doc["derived_state"]
        payload = {
            "schema_version": 2,
            "user_id": self.user_id,
            "updated_at": doc["updated_at"],
            "derived_state": derived,
            "lessons": list(doc.get("lessons") or []),
            "backtest_validations": list(doc.get("backtest_validations") or []),
            "config_recommendations": list(doc.get("config_recommendations") or []),
            "promotions": list(doc.get("promotions") or []),
            # Compat mirrors
            "signal_weights": dict(derived.get("signal_weights") or {}),
            "strategy_preferences": dict(derived.get("strategy_preferences") or {}),
        }
        self._store.save(payload)

    def lessons(self, limit: int = 10) -> List[str]:
        return lesson_summaries(self.load().get("lessons") or [], limit=limit)

    def lessons_for_prompt(self, limit: int = 10) -> List[str]:
        doc = self.load()
        prefs = (doc.get("derived_state") or {}).get("strategy_preferences") or {}
        return select_lessons_for_prompt(
            [l for l in (doc.get("lessons") or []) if isinstance(l, dict)],
            last_validated_backtest_id=prefs.get("last_validated_backtest_id"),
            max_total=limit,
        )

    def signal_weights(self) -> Dict[str, float]:
        derived = self.load().get("derived_state") or {}
        return dict(derived.get("signal_weights") or {})

    def strategy_preferences(self) -> Dict[str, Any]:
        derived = self.load().get("derived_state") or {}
        return dict(derived.get("strategy_preferences") or {})

    def active_backtest_validation(self) -> Optional[Dict[str, Any]]:
        doc = self.load()
        prefs = (doc.get("derived_state") or {}).get("strategy_preferences") or {}
        vid = prefs.get("last_validated_backtest_id")
        if not vid:
            return None
        for item in doc.get("backtest_validations") or []:
            if isinstance(item, dict) and item.get("id") == vid:
                return dict(item)
        return None

    def append_lesson(self, lesson: str, max_lessons: int = MAX_LESSONS) -> None:
        """Compat: append a simple live lesson string (v1 API)."""
        self.append_live_lesson(
            summary=lesson,
            rationale="Compat append_lesson",
            cycle_id="unknown",
            artifact_path=None,
            tags=["compat"],
            max_lessons=max_lessons,
        )

    def append_live_lesson(
        self,
        *,
        summary: str,
        rationale: str,
        cycle_id: str,
        artifact_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_lessons: int = MAX_LESSONS,
    ) -> Dict[str, Any]:
        record = {
            "id": new_id("les-live"),
            "kind": "lesson",
            "user_id": self.user_id,
            "source": "live",
            "created_at": utc_now_iso(),
            "summary": summary,
            "rationale": rationale,
            "provenance": {
                "trigger_event": make_event_ref(
                    event_type="trading_cycle",
                    event_id=cycle_id or "unknown",
                    artifact_path=artifact_path,
                    artifact_kind="cycle" if artifact_path else None,
                    summary=summary,
                    user_id=self.user_id,
                )
            },
            "tags": list(tags or []),
            "supersedes": None,
        }
        doc = self.load()
        doc["lessons"].append(record)
        keep = referenced_lesson_ids(doc)
        doc["lessons"] = trim_lessons(doc["lessons"], max_lessons, keep)
        self.save(doc)
        return record

    def update_weights_and_prefs(
        self,
        signal_weights: Optional[Dict[str, float]] = None,
        strategy_preferences: Optional[Dict[str, Any]] = None,
    ) -> None:
        doc = self.load()
        derived = doc["derived_state"]
        if signal_weights is not None:
            weights = dict(derived.get("signal_weights") or {})
            for key, value in signal_weights.items():
                weights[key] = clamp_signal_weight(float(value))
            derived["signal_weights"] = weights
        if strategy_preferences is not None:
            prefs = dict(derived.get("strategy_preferences") or {})
            prefs.update(strategy_preferences)
            derived["strategy_preferences"] = prefs
        doc["derived_state"] = derived
        self.save(doc)

    def append_backtest_validation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        record.setdefault("id", new_id("bv"))
        record["kind"] = "backtest_validation"
        record["user_id"] = self.user_id
        record.setdefault("source", "backtest")
        record.setdefault("created_at", utc_now_iso())
        trigger = (record.get("provenance") or {}).get("trigger_event")
        require_hard_event_ref(trigger, context="backtest_validation")
        if not record.get("config_hash") and record.get("config_snapshot"):
            record["config_hash"] = config_hash(record["config_snapshot"])

        doc = self.load()
        doc["backtest_validations"].append(record)
        validations = list(doc["backtest_validations"])
        if len(validations) > MAX_VALIDATIONS:
            baselines = [v for v in validations if v.get("is_validated_baseline")]
            others = [v for v in validations if not v.get("is_validated_baseline")]
            room = max(0, MAX_VALIDATIONS - len(baselines))
            doc["backtest_validations"] = baselines + others[-room:]
        if record.get("is_validated_baseline"):
            prefs = dict(doc["derived_state"].get("strategy_preferences") or {})
            prefs["last_validated_backtest_id"] = record["id"]
            doc["derived_state"]["strategy_preferences"] = prefs
        self.save(doc)
        return record

    def append_lesson_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        record.setdefault("id", new_id("les"))
        record["kind"] = "lesson"
        record["user_id"] = self.user_id
        record.setdefault("created_at", utc_now_iso())
        if record.get("source") == "backtest":
            trigger = (record.get("provenance") or {}).get("trigger_event")
            require_hard_event_ref(trigger, context="backtest lesson")
        doc = self.load()
        doc["lessons"].append(record)
        keep = referenced_lesson_ids(doc)
        doc["lessons"] = trim_lessons(doc["lessons"], MAX_LESSONS, keep)
        self.save(doc)
        return record

    def append_config_recommendation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        record.setdefault("id", new_id("cr"))
        record["kind"] = "config_recommendation"
        record["user_id"] = self.user_id
        record.setdefault("source", "backtest")
        record.setdefault("created_at", utc_now_iso())
        record.setdefault("status", "pending_review")
        if record["status"] not in RECOMMENDATION_STATUSES:
            raise KnowledgeBaseError(f"Invalid recommendation status: {record['status']}")

        provenance = dict(record.get("provenance") or {})
        trigger = provenance.get("trigger_event")
        require_hard_event_ref(trigger, context="config_recommendation")
        record["provenance"] = provenance

        doc = self.load()
        # Supersede any existing pending recommendation
        for existing in doc.get("config_recommendations") or []:
            if (
                isinstance(existing, dict)
                and existing.get("status") == "pending_review"
                and existing.get("id") != record["id"]
            ):
                existing["status"] = "superseded"
                existing["superseded_by"] = record["id"]
                record["supersedes"] = existing.get("id")

        doc.setdefault("config_recommendations", []).append(record)
        recs = doc["config_recommendations"]
        if len(recs) > MAX_RECOMMENDATIONS:
            pending = [r for r in recs if r.get("status") == "pending_review"]
            terminal = [r for r in recs if r.get("status") != "pending_review"]
            doc["config_recommendations"] = pending + terminal[-20:]

        if record["status"] == "pending_review":
            doc["derived_state"]["active_recommendation_id"] = record["id"]
        self.save(doc)
        return record

    def get_pending_recommendation(self) -> Optional[Dict[str, Any]]:
        doc = self.load()
        active_id = (doc.get("derived_state") or {}).get("active_recommendation_id")
        pending = None
        for rec in doc.get("config_recommendations") or []:
            if not isinstance(rec, dict):
                continue
            if rec.get("status") == "pending_review":
                if active_id and rec.get("id") == active_id:
                    return dict(rec)
                pending = dict(rec)
        return pending

    def update_recommendation_review(
        self,
        recommendation_id: str,
        *,
        status: str,
        reviewed_by: str = "operator",
        reject_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status not in RECOMMENDATION_STATUSES:
            raise KnowledgeBaseError(f"Invalid status: {status}")
        doc = self.load()
        found = None
        for rec in doc.get("config_recommendations") or []:
            if isinstance(rec, dict) and rec.get("id") == recommendation_id:
                # Immutable fields stay; only status/review mutate.
                rec["status"] = status
                review = dict(rec.get("review") or {})
                review["reviewed_at"] = utc_now_iso()
                review["reviewed_by"] = reviewed_by
                review["decision"] = status
                review["reject_reason"] = reject_reason
                rec["review"] = review
                found = dict(rec)
                break
        if found is None:
            raise KnowledgeBaseError(f"Recommendation not found: {recommendation_id}")
        if status != "pending_review":
            if doc["derived_state"].get("active_recommendation_id") == recommendation_id:
                doc["derived_state"]["active_recommendation_id"] = None
        self.save(doc)
        return found

    def append_promotion(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        record.setdefault("id", new_id("prom"))
        record["kind"] = "promotion"
        record["user_id"] = self.user_id
        record.setdefault("source", "operator")
        record.setdefault("created_at", utc_now_iso())
        provenance = dict(record.get("provenance") or {})
        originating = provenance.get("originating_events") or []
        if not originating:
            raise KnowledgeBaseError(
                "promotion requires provenance.originating_events with EventRefs"
            )
        for event in originating:
            require_hard_event_ref(event, context="promotion.originating_events")
        record["provenance"] = provenance

        doc = self.load()
        doc.setdefault("promotions", []).append(record)
        if len(doc["promotions"]) > MAX_PROMOTIONS:
            doc["promotions"] = doc["promotions"][-MAX_PROMOTIONS:]
        doc["derived_state"]["last_promotion_id"] = record["id"]
        self.save(doc)
        return record

    def find_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        doc = self.load()
        for key in (
            "lessons",
            "backtest_validations",
            "config_recommendations",
            "promotions",
        ):
            for item in doc.get(key) or []:
                if isinstance(item, dict) and item.get("id") == record_id:
                    return dict(item)
        return None
