# Agent documentation

Use these guides when implementing features, fixing bugs, or opening pull requests in **trading-agent**.

## Read order

1. **[codebase.md](codebase.md)** — what the repo does and how modules connect
2. **[development.md](development.md)** — env, commands, testing, coding conventions
3. **[trading-cycle.md](trading-cycle.md)** — the main runtime flow and where to hook changes
4. **[account-history.md](account-history.md)** — read-only account snapshot and equity history mode
5. **[market-signals.md](market-signals.md)** — Phase 2 signal slices, env keys, extension guide
6. **[pr-description.md](pr-description.md)** — required PR description format

Also see **[../PROJECT_PLAN.md](../PROJECT_PLAN.md)** for roadmap and phase status.

## Principles for agents

- **Minimize scope** — one concern per change; avoid drive-by refactors
- **Match conventions** — read surrounding code before adding abstractions
- **Paper trading default** — `ALPACA_PAPER=true`; never commit `.env` or secrets
- **Test with mocks** — use `LLM_PROVIDER=mock` and `trading_agent.broker.mock_client` in tests; CI has no API keys
- **No root-level test files** — put unit/mock tests in `tests/` and live API checks in `tests/integration/`
- **Structured LLM output** — trading decisions must parse as JSON via `trading_agent/models.py`
