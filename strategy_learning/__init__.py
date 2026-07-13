"""
Strategy learning — offline tuning separate from the live trading pipeline.

Ownership (Phase 4.5.3+):
  - Knowledge base and config *recommendations*
  - Param sweep and live retrospection triggers (4.5.4 / 4.5.5)

Does **not** own or write trading_agent config stores (`data/*.json` params).
Backtests stay in ``trading_agent.backtest`` for now; this package will call them.

See docs/agents/learning-loop.md and docs/PROJECT_PLAN.md (Phase 4.5).
"""

from strategy_learning.knowledge.store import KnowledgeBase
from strategy_learning.knowledge.records import KnowledgeBaseError

__all__ = [
    "KnowledgeBase",
    "KnowledgeBaseError",
    "BacktestFeedbackAgent",
    "format_feedback_banner",
]


def __getattr__(name: str):
    # Lazy: avoid importing feedback (and trading_agent.backtest) on soft reads.
    if name == "BacktestFeedbackAgent":
        from strategy_learning.knowledge.feedback import BacktestFeedbackAgent

        return BacktestFeedbackAgent
    if name == "format_feedback_banner":
        from strategy_learning.knowledge.feedback import format_feedback_banner

        return format_feedback_banner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
