"""Live retrospection (Phase 4.5.5).

Detects underperformance on live cycles and writes durable out-of-band
signals for sweep consumption. Must never run from BacktestAgentRun
(see Phase 4.5.2 circular-trigger rule).
"""

from strategy_learning.retrospection.detector import (
    DEFAULT_COOLDOWN_DAYS,
    DEFAULT_HOLD_STREAK,
    DEFAULT_SPY_LAG_PP,
    DEFAULT_WINDOW_DAYS,
    RetrospectionDetector,
    default_thresholds,
)
from strategy_learning.retrospection.metrics import (
    closes_return,
    consecutive_hold_streak,
    hold_streak_with_spy_rise,
    lags_spy,
    load_recent_cycle_summaries,
    portfolio_history_period_for_window,
    series_return,
    spy_lag_pp,
    window_closes_return,
    window_equity_return,
)
from strategy_learning.retrospection.models import RetrospectionEval, RetrospectionTrigger
from strategy_learning.retrospection.signal import (
    claim_trigger,
    cooldown_active,
    has_pending_trigger,
    list_trigger_paths,
    load_trigger,
    mark_consumed,
    write_retrospection_signal,
)

__all__ = [
    "DEFAULT_COOLDOWN_DAYS",
    "DEFAULT_HOLD_STREAK",
    "DEFAULT_SPY_LAG_PP",
    "DEFAULT_WINDOW_DAYS",
    "RetrospectionDetector",
    "RetrospectionEval",
    "RetrospectionTrigger",
    "claim_trigger",
    "closes_return",
    "consecutive_hold_streak",
    "cooldown_active",
    "default_thresholds",
    "has_pending_trigger",
    "hold_streak_with_spy_rise",
    "lags_spy",
    "list_trigger_paths",
    "load_recent_cycle_summaries",
    "load_trigger",
    "mark_consumed",
    "portfolio_history_period_for_window",
    "series_return",
    "spy_lag_pp",
    "window_closes_return",
    "window_equity_return",
    "write_retrospection_signal",
]
