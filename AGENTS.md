# Agent guide

This repository includes documentation for AI coding agents working in the codebase.

**Start here:** [`docs/agents/README.md`](docs/agents/README.md)

| Doc | Purpose |
|-----|---------|
| [Codebase overview](docs/agents/codebase.md) | Architecture, main modules, data flow |
| [Development guide](docs/agents/development.md) | Setup, run, test, conventions |
| [Trading cycle](docs/agents/trading-cycle.md) | End-to-end cycle behavior and extension points |
| [Account history](docs/agents/account-history.md) | Read-only account snapshot and equity history mode |
| [Market signals](docs/agents/market-signals.md) | Phase 2 signal providers, env keys, extension guide |
| [Backtesting](docs/agents/backtesting.md) | Phase 3 historical replay, benchmarks, CLI |
| [Multi-agent](docs/agents/multi-agent.md) | Phase 4 agents, coordinator, knowledge base |
| [Learning loop](docs/agents/learning-loop.md) | Phase 4.5 learning loop + `strategy_learning` boundary |
| [strategy_learning README](strategy_learning/README.md) | Offline learning package scaffold |
| [Multi-broker](docs/agents/multi-broker.md) | Phase 5 broker abstraction, Robinhood optional adapter |
| [PR descriptions](docs/agents/pr-description.md) | How to write pull request summaries |
| [Project plan](docs/PROJECT_PLAN.md) | Roadmap, package diagrams, data boundary (`trading_agent` vs `strategy_learning`) |

**Package boundary:** `trading_agent` owns live trading, configs, and backtest; `strategy_learning` owns KB/recommendations/sweep (scaffold in 4.5.1). Learning must not write `data/*.json` params — see [learning-loop.md](docs/agents/learning-loop.md).

When making changes, prefer minimal diffs, match existing patterns, and run tests before opening a PR:

```bash
.venv/bin/bash scripts/run_tests.sh
```

When executing **multiple tasks in parallel**, prefer **git worktrees** (one directory per branch) instead of switching branches in a single checkout. See [Parallel work: prefer git worktrees](docs/agents/development.md#parallel-work-prefer-git-worktrees) for create/setup/cleanup commands.

## Per-PR test requirements

Every PR (except explicitly doc-only) must:

1. Pass `bash scripts/run_tests.sh` / CI `test` job
2. Add or update `tests/` coverage for changed business logic (main flow components, not 100% lines)
3. Keep unit tests mock-based (no API keys required in CI)
4. Run live `tests/integration/` locally when touching Alpaca / LLM / Finnhub / FMP providers
5. Leave no root-level `test_*.py` or committed throwaway scripts
6. Follow [PR description](docs/agents/pr-description.md) including the Test plan checklist

## Testing and test hygiene

- **No root-level `test_*.py`** — do not leave debugging scripts at the repo root; delete or move them before opening a PR
- **`tests/`** — unit tests and mock-based integration (must pass in CI without API keys)
- **`tests/integration/`** — live API connectivity checks; use `unittest.skipUnless` on env keys so CI auto-skips when secrets are absent
- **Ad-hoc debugging** — use `scripts/` or a local untracked file; never commit throwaway tests
- **Before PR** — run `scripts/run_tests.sh`; if you changed Alpaca or LLM providers, confirm integration tests ran (not skipped) locally
- **Prefer mocks** — use `MockLLMClient` and `MockAlpacaTradingClient` for CI-safe coverage

See [development guide](docs/agents/development.md) and [PR descriptions](docs/agents/pr-description.md) for setup and the full PR test checklist.
