"""Learner & Summarizer — reflect on cycle outcomes into the knowledge base."""

from typing import Any, Dict, Optional

from trading_agent.agents.base import ConfigurableAgent
from trading_agent.agents.knowledge import KnowledgeBase
from trading_agent.agents.messages import LessonsUpdate


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

        if status != "success":
            lesson = f"cycle={cycle_id[:8]} failed: {ctx.get('error') or 'unknown'}"
        elif hold and not executed:
            lesson = f"cycle={cycle_id[:8]} held with no executable trades"
        elif executed:
            symbols = ",".join(sorted({t.get("symbol", "?") for t in executed}))
            lesson = (
                f"cycle={cycle_id[:8]} executed {len(executed)} trade(s) "
                f"symbols={symbols} skipped={len(skipped)}"
            )
        else:
            lesson = f"cycle={cycle_id[:8]} completed without fills"

        self.knowledge_base.append_lesson(lesson)

        # Lightweight preference nudge: track recent hold vs trade bias.
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
            lessons_added=[lesson],
            signal_weights=self.knowledge_base.signal_weights(),
            strategy_preferences=self.knowledge_base.strategy_preferences(),
        )
        ctx["lessons_update"] = update
        return {"lessons_update": update}
