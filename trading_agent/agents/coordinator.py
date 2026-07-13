"""Cycle coordinator — runs Phase 4 agents in order and returns CycleResult dict."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from trading_agent.agents.registry import AgentRegistry
from trading_agent.domain.cycle import CycleResult

logger = logging.getLogger(__name__)


class CycleCoordinator:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.last_ctx: Dict[str, Any] = {}

    def run(
        self,
        analysis_params: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        rebalance_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cycle_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        ctx: Dict[str, Any] = {
            "cycle_id": cycle_id,
            "timestamp": timestamp,
            "status": "success",
            "analysis_params": analysis_params or {},
            "strategy_params": strategy_params or {},
            "rebalance_params": rebalance_params or {},
        }
        self.last_ctx = ctx

        try:
            for agent in self.registry.enabled_pipeline():
                if agent.name == "trading_strategizer":
                    market_analysis = ctx.get("market_analysis")
                    if market_analysis is not None and market_analysis.has_failure():
                        ctx["status"] = "failed"
                        ctx["error"] = "All market analysis strategies failed"
                        for name in ("decision_logger", "live_lesson"):
                            follow = self.registry.get(name)
                            if follow and follow.is_enabled():
                                follow.run(ctx)
                        return ctx.get("cycle_result") or CycleResult(
                            status="failed",
                            cycle_id=cycle_id,
                            timestamp=timestamp,
                            error=ctx["error"],
                        ).to_dict()

                agent.run(ctx)

            return ctx.get("cycle_result") or CycleResult(
                status=ctx.get("status", "failed"),
                cycle_id=cycle_id,
                timestamp=timestamp,
                error=ctx.get("error"),
            ).to_dict()

        except Exception as exc:
            logger.error("Trading cycle failed: %s", exc)
            ctx["status"] = "failed"
            ctx["error"] = str(exc)
            logger_agent = self.registry.get("decision_logger")
            if logger_agent and logger_agent.is_enabled():
                try:
                    logger_agent.run(ctx)
                    if "cycle_result" in ctx:
                        return ctx["cycle_result"]
                except Exception:
                    logger.exception("Decision logger failed during error handling")
            live_lesson = self.registry.get("live_lesson")
            if live_lesson and live_lesson.is_enabled():
                try:
                    live_lesson.run(ctx)
                except Exception:
                    logger.exception("LiveLessonAgent failed during error handling")
            return CycleResult(
                status="failed",
                cycle_id=cycle_id,
                timestamp=timestamp,
                error=str(exc),
            ).to_dict()
