"""Learner & Summarizer — reflect on cycle outcomes into the knowledge base."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.agents.base import ConfigurableAgent
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.messages import LessonsUpdate
from trading_agent.models import serialize_for_json

logger = logging.getLogger(__name__)


class LearnerAgent(ConfigurableAgent):
    name = "learner"

    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.knowledge_base = knowledge_base or KnowledgeBase()

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        cycle_id = ctx.get("cycle_id", "unknown")
        status = ctx.get("status", "success")
        hold = bool(ctx.get("hold"))
        executed = ctx.get("executed_trades") or []
        preparation = ctx.get("preparation")
        skipped = []
        if preparation is not None:
            skipped = list(getattr(preparation, "skipped", []) or [])

        decision_log = ctx.get("decision_log")
        artifact_path = None
        if decision_log is not None:
            artifact_path = getattr(decision_log, "artifact_path", None)

        if status != "success":
            summary = f"cycle={str(cycle_id)[:8]} failed: {ctx.get('error') or 'unknown'}"
            rationale = "Cycle failed before reliable execution outcomes"
            tags = ["failure"]
        elif hold and not executed:
            summary = f"cycle={str(cycle_id)[:8]} held with no executable trades"
            rationale = "No fills; nudge recent_trade_bias toward caution"
            tags = ["hold", "execution"]
        elif executed:
            symbols = ",".join(sorted({t.get("symbol", "?") for t in executed}))
            summary = (
                f"cycle={str(cycle_id)[:8]} executed {len(executed)} trade(s) "
                f"symbols={symbols} skipped={len(skipped)}"
            )
            rationale = "Cycle completed with fills; increases recent_trade_bias"
            tags = ["execution", "trade"]
        else:
            summary = f"cycle={str(cycle_id)[:8]} completed without fills"
            rationale = "Completed without fills"
            tags = ["execution"]

        lesson_record = self.knowledge_base.append_live_lesson(
            summary=summary,
            rationale=rationale,
            cycle_id=str(cycle_id),
            artifact_path=artifact_path,
            tags=tags,
        )

        # Soft preference nudge only — never writes hard config stores.
        prefs = self.knowledge_base.strategy_preferences()
        trade_bias = float(prefs.get("recent_trade_bias", 0.0))
        if hold and not executed:
            trade_bias = max(-1.0, trade_bias - 0.05)
        elif executed:
            trade_bias = min(1.0, trade_bias + 0.05)
        self.knowledge_base.update_weights_and_prefs(
            strategy_preferences={"recent_trade_bias": round(trade_bias, 3)}
        )

        update = LessonsUpdate(
            lessons_added=[summary],
            signal_weights=self.knowledge_base.signal_weights(),
            strategy_preferences=self.knowledge_base.strategy_preferences(),
            lesson_records=[lesson_record] if lesson_record else [],
        )
        ctx["lessons_update"] = update
        self._append_lessons_to_artifact(ctx, update)
        return {"lessons_update": update}

    def _append_lessons_to_artifact(
        self, ctx: Dict[str, Any], update: LessonsUpdate
    ) -> None:
        """Patch cycle artifact after logger so learning is auditable."""
        decision_log = ctx.get("decision_log")
        artifact_path = None
        if decision_log is not None:
            artifact_path = getattr(decision_log, "artifact_path", None)
        if not artifact_path:
            cycle_result = ctx.get("cycle_result") or {}
            artifact_path = cycle_result.get("artifact_path")
        if not artifact_path:
            return

        path = Path(artifact_path)
        if not path.exists():
            return
        try:
            with path.open(encoding="utf-8") as f:
                payload = json.load(f)
            agents = payload.setdefault("agents", {})
            agents["lessons_update"] = serialize_for_json(update.to_dict())
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.debug("Appended lessons_update to %s", path)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Could not append lessons_update to %s: %s", path, exc)
