# Agent documentation

Use these guides when implementing features, fixing bugs, or opening pull requests in **trading-agent**.

## Read order

1. **[codebase.md](codebase.md)** — what the repo does and how modules connect
2. **[development.md](development.md)** — env, commands, testing, coding conventions
3. **[trading-cycle.md](trading-cycle.md)** — the main runtime flow and where to hook changes
4. **[account-history.md](account-history.md)** — read-only account snapshot and equity history mode
5. **[market-signals.md](market-signals.md)** — Phase 2 signal slices, env keys, extension guide
6. **[backtesting.md](backtesting.md)** — Phase 3 historical replay, benchmarks, CLI
7. **[multi-agent.md](multi-agent.md)** — Phase 4 agents, coordinator, knowledge base
8. **[learning-loop.md](learning-loop.md)** — Phase 4.5 learning loop, `strategy_learning` boundary, sub-phases 4.5.1–4.5.5
9. **[multi-broker.md](multi-broker.md)** — Phase 5 broker abstraction, Alpaca/Robinhood/mock
10. **[pr-description.md](pr-description.md)** — required PR description format and [per-PR test requirements](pr-description.md#test-requirements-every-pr)

Also see [`strategy_learning/README.md`](../../strategy_learning/README.md) for the offline learning package scaffold, and **[../PROJECT_PLAN.md](../PROJECT_PLAN.md)** for roadmap, package diagrams, and the data-boundary table.

## Principles for agents

- **Minimize scope** — one concern per change; avoid drive-by refactors
- **Match conventions** — read surrounding code before adding abstractions
- **Package boundary** — `trading_agent` owns live trading + configs + backtest; `strategy_learning` owns KB/recommendations/sweep. Learning must not write `data/*.json` params — see [learning-loop.md](learning-loop.md)
- **Paper trading default** — `ALPACA_PAPER=true`; never commit `.env` or secrets
- **Test with mocks** — use `LLM_PROVIDER=mock` and `MockBrokerClient` in tests; CI has no API keys
- **No root-level test files** — put package unit tests in `strategy_learning/tests/` or `trading_agent/tests/`; cross-package under `tests/`; live API checks in `tests/integration/`
- **Per-PR tests** — run `bash scripts/run_tests.sh`; cover **main flow layers** you change (not only one submodule); include a Test plan checklist on every PR — see [development.md § Test coverage by flow](development.md#test-coverage-by-flow)
- **Parallel work** — when running multiple tasks at once, use [git worktrees](development.md#parallel-work-prefer-git-worktrees) (separate directories per branch); remove worktrees when done
- **Structured LLM output** — trading decisions must parse as JSON via `trading_agent/models.py`
