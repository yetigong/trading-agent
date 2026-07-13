"""Knowledge base ownership (Phase 4.5.3).

``strategy_learning`` owns KB writes and recommendation records.
``trading_agent`` reads soft context for prompts and applies approved
config changes via promotion (config-owner path).
"""

from strategy_learning.knowledge.records import (
    KnowledgeBaseError,
    RECOMMENDATION_STATUSES,
    SIGNAL_WEIGHT_DELTA,
    TUNABLE_ENUMS,
    clamp_signal_weight,
    config_hash,
    make_event_ref,
    new_id,
)
from strategy_learning.knowledge.store import KnowledgeBase

__all__ = [
    "BacktestFeedbackAgent",
    "KnowledgeBase",
    "KnowledgeBaseError",
    "RECOMMENDATION_STATUSES",
    "SIGNAL_WEIGHT_DELTA",
    "TUNABLE_ENUMS",
    "clamp_signal_weight",
    "config_hash",
    "format_feedback_banner",
    "make_event_ref",
    "new_id",
]


def __getattr__(name: str):
    if name == "BacktestFeedbackAgent":
        from strategy_learning.knowledge.feedback import BacktestFeedbackAgent

        return BacktestFeedbackAgent
    if name == "format_feedback_banner":
        from strategy_learning.knowledge.feedback import format_feedback_banner

        return format_feedback_banner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
