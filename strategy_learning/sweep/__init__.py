"""Param sweep runner (Phase 4.5.4).

Runs N backtests via ``trading_agent.backtest``, aggregates a SweepResult,
and is the sole producer of hard config recommendations.
"""

from strategy_learning.sweep.candidates import (
    config_snapshot_from_sections,
    expand_oat_candidates,
    merge_proposed_changes,
)
from strategy_learning.sweep.models import (
    SweepCandidateResult,
    SweepResult,
    beats_baseline,
    metric_rank_key,
)
from strategy_learning.sweep.recommend import maybe_write_recommendation, select_winner
from strategy_learning.sweep.runner import (
    ParamSweepRunner,
    estimate_rebalance_cycles,
    format_sweep_plan,
)

__all__ = [
    "ParamSweepRunner",
    "SweepCandidateResult",
    "SweepResult",
    "beats_baseline",
    "config_snapshot_from_sections",
    "estimate_rebalance_cycles",
    "expand_oat_candidates",
    "format_sweep_plan",
    "maybe_write_recommendation",
    "merge_proposed_changes",
    "metric_rank_key",
    "select_winner",
]
