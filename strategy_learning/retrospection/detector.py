"""Live underperformance detector (Phase 4.5.5)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set

from strategy_learning.retrospection.metrics import (
    hold_streak_with_spy_rise,
    lags_spy,
    spy_lag_pp,
    window_closes_return,
    window_equity_return,
)
from strategy_learning.retrospection.models import RetrospectionEval

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 30
DEFAULT_SPY_LAG_PP = 0.05
DEFAULT_HOLD_STREAK = 3
DEFAULT_COOLDOWN_DAYS = 7

_warned_env: Set[str] = set()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        if name not in _warned_env:
            logger.warning(
                "Invalid %s=%r; using default %s", name, raw, default
            )
            _warned_env.add(name)
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        if name not in _warned_env:
            logger.warning(
                "Invalid %s=%r; using default %s", name, raw, default
            )
            _warned_env.add(name)
        return default


def default_thresholds() -> Dict[str, Any]:
    return {
        "window_days": _env_int("RETROSPECTION_WINDOW_DAYS", DEFAULT_WINDOW_DAYS),
        "spy_lag_pp": _env_float("RETROSPECTION_SPY_LAG_PP", DEFAULT_SPY_LAG_PP),
        "hold_streak": _env_int("RETROSPECTION_HOLD_STREAK", DEFAULT_HOLD_STREAK),
        "cooldown_days": _env_int("RETROSPECTION_COOLDOWN_DAYS", DEFAULT_COOLDOWN_DAYS),
    }


class RetrospectionDetector:
    """Evaluate live equity / hold-streak rules. Does not write configs or run sweeps."""

    def __init__(
        self,
        *,
        window_days: Optional[int] = None,
        spy_lag_pp: Optional[float] = None,
        hold_streak: Optional[int] = None,
    ) -> None:
        defaults = default_thresholds()
        self.window_days = int(window_days if window_days is not None else defaults["window_days"])
        self.spy_lag_pp = float(spy_lag_pp if spy_lag_pp is not None else defaults["spy_lag_pp"])
        self.hold_streak = int(hold_streak if hold_streak is not None else defaults["hold_streak"])

    def evaluate(
        self,
        *,
        equity_points: Sequence[Any],
        spy_closes: Sequence[Any],
        cycle_summaries: Sequence[Dict[str, Any]],
        cycle_id: Optional[str] = None,
        as_of: Optional[datetime] = None,
        cooldown_active: bool = False,
        pending_trigger_exists: bool = False,
    ) -> RetrospectionEval:
        if pending_trigger_exists:
            return RetrospectionEval(
                triggered=False,
                cycle_id=cycle_id,
                skipped_reason="pending_trigger_exists",
                metrics={"pending_trigger_exists": True},
            )
        if cooldown_active:
            return RetrospectionEval(
                triggered=False,
                cycle_id=cycle_id,
                skipped_reason="cooldown_active",
                metrics={"cooldown_active": True},
            )

        as_of = as_of or datetime.now(timezone.utc)
        equity_ret = window_equity_return(
            equity_points,
            window_days=self.window_days,
            as_of=as_of,
        )
        # Same calendar window as equity for the lag rule.
        spy_ret = window_closes_return(
            spy_closes,
            window_days=self.window_days,
            as_of=as_of,
        )
        lag = spy_lag_pp(equity_ret, spy_ret)
        lag_hit = lags_spy(equity_ret, spy_ret, lag_threshold_pp=self.spy_lag_pp)

        hold_hit, hold_metrics = hold_streak_with_spy_rise(
            cycle_summaries,
            spy_closes,
            streak_required=self.hold_streak,
            as_of=as_of,
        )

        reasons: List[str] = []
        if lag_hit:
            lag_str = f"{abs(lag):.4f}" if lag is not None else "?"
            reasons.append(
                f"rolling_{self.window_days}d_equity_lags_spy_by_{lag_str}"
            )
        if hold_hit:
            reasons.append(
                f"{self.hold_streak}_consecutive_holds_while_spy_rising"
            )

        metrics: Dict[str, Any] = {
            "window_days": self.window_days,
            "spy_lag_threshold_pp": self.spy_lag_pp,
            "equity_return": equity_ret,
            "spy_return": spy_ret,
            "spy_lag_pp": lag,
            "lag_rule_hit": lag_hit,
            "hold_rule_hit": hold_hit,
            **hold_metrics,
            "evaluated_at": as_of.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }

        return RetrospectionEval(
            triggered=bool(reasons),
            reasons=reasons,
            metrics=metrics,
            cycle_id=cycle_id,
        )
