"""Live vs backtest agent-run modes (Phase 4.5.2).

Wrappers around TradingAgent that encode mode policy: learner/artifacts and the
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
    """Live trading cycle run — learner on, artifacts on, retrospection allowed."""

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

    def emit_retrospection_signal(self, **payload: Any) -> None:
        """Stub for Phase 4.5.5 — live underperformance → strategy_learning."""
        logger.debug(
            "LiveAgentRun.emit_retrospection_signal stub (payload keys=%s)",
            sorted(payload.keys()),
        )
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)


class BacktestAgentRun:
    """Historical replay run — learner off; must not trigger retrospection."""

    mode = AgentRunMode.BACKTEST
    may_trigger_retrospection = False

    def __init__(self, **kwargs: Any) -> None:
        disabled: List[str] = list(kwargs.pop("disabled", None) or [])
        if "learner" not in disabled:
            disabled.append("learner")
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
