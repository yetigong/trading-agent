"""
Strategy learning — offline tuning separate from the live trading pipeline.

Ownership (target; populated across Phase 4.5.3–4.5.5):
  - Knowledge base and config *recommendations*
  - Param sweep and live retrospection triggers

Does **not** own or write trading_agent config stores (`data/*.json` params).
Backtests stay in ``trading_agent.backtest`` for now; this package will call them.

See docs/agents/learning-loop.md and docs/PROJECT_PLAN.md (Phase 4.5).
"""

__all__: list[str] = []
