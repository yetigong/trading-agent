"""Live vs backtest agent-run modes (Phase 4.5.2).

Wrappers around TradingAgent that encode mode policy: live_lesson/artifacts and the
circular-trigger rule (only live runs may emit retrospection signals).
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from trading_agent.orchestrator.agent import TradingAgent

logger = logging.getLogger(__name__)


class AgentRunMode(str, Enum):
    LIVE = "live"
    BACKTEST = "backtest"


class LiveAgentRun:
    """Live trading cycle run — live_lesson on, artifacts on, retrospection allowed."""

    mode = AgentRunMode.LIVE
    may_trigger_retrospection = True

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("write_artifact", True)
        self._agent = TradingAgent(**kwargs)

    @property
    def agent(self) -> TradingAgent:
        return self._agent

    def run_trading_cycle(
        self,
        analysis_params: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        rebalance_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._agent.run_trading_cycle(
            analysis_params=analysis_params,
            strategy_params=strategy_params,
            rebalance_params=rebalance_params,
        )

    def emit_retrospection_signal(self, **payload: Any) -> Optional[str]:
        """Write a durable retrospection signal for out-of-band sweep (Phase 4.5.5).

        Returns the artifact path, or None when nothing was written.
        """
        from strategy_learning.retrospection import (
            RetrospectionEval,
            write_retrospection_signal,
        )

        eval_result = payload.get("eval")
        if not isinstance(eval_result, RetrospectionEval):
            reasons = list(payload.get("reasons") or [])
            if not reasons and payload.get("reason"):
                reasons = [str(payload["reason"])]
            eval_result = RetrospectionEval(
                triggered=bool(payload.get("triggered", True)),
                reasons=reasons,
                metrics=dict(payload.get("metrics") or {}),
                cycle_id=payload.get("cycle_id"),
            )
        if not eval_result.triggered:
            logger.debug("emit_retrospection_signal skipped (not triggered)")
            return None
        path = write_retrospection_signal(
            eval_result,
            log_dir=payload.get("log_dir") or "logs",
            cycle_artifact_path=payload.get("cycle_artifact_path"),
            user_id=str(payload.get("user_id") or "default"),
            extra=dict(payload.get("extra") or {}),
        )
        logger.info("LiveAgentRun emitted retrospection signal → %s", path)
        return str(path)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)


class BacktestAgentRun:
    """Historical replay run — live_lesson off; must not trigger retrospection."""

    mode = AgentRunMode.BACKTEST
    may_trigger_retrospection = False

    def __init__(self, **kwargs: Any) -> None:
        disabled: List[str] = list(kwargs.pop("disabled", None) or [])
        if "live_lesson" not in disabled:
            disabled.append("live_lesson")
        kwargs["disabled"] = disabled
        kwargs.setdefault("write_artifact", False)
        self._agent = TradingAgent(**kwargs)

    @property
    def agent(self) -> TradingAgent:
        return self._agent

    def run_trading_cycle(
        self,
        analysis_params: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        rebalance_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._agent.run_trading_cycle(
            analysis_params=analysis_params,
            strategy_params=strategy_params,
            rebalance_params=rebalance_params,
        )

    def emit_retrospection_signal(self, **payload: Any) -> None:
        raise RuntimeError(
            "Backtest runs must not trigger retrospection or sweep "
            "(circular-trigger rule; Phase 4.5.2)"
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)
