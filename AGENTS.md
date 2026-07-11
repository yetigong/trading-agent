# Agent guide

This repository includes documentation for AI coding agents working in the codebase.

**Start here:** [`docs/agents/README.md`](docs/agents/README.md)

| Doc | Purpose |
|-----|---------|
| [Codebase overview](docs/agents/codebase.md) | Architecture, main modules, data flow |
| [Development guide](docs/agents/development.md) | Setup, run, test, conventions |
| [Trading cycle](docs/agents/trading-cycle.md) | End-to-end cycle behavior and extension points |
| [PR descriptions](docs/agents/pr-description.md) | How to write pull request summaries |
| [Project plan](docs/PROJECT_PLAN.md) | Roadmap and phase status |

When making changes, prefer minimal diffs, match existing patterns, and run tests before opening a PR:

```bash
.venv/bin/bash scripts/run_tests.sh
```

## Testing and test hygiene

- **No root-level `test_*.py`** — do not leave debugging scripts at the repo root; delete or move them before opening a PR
- **`tests/`** — unit tests and mock-based integration (must pass in CI without API keys)
- **`tests/integration/`** — live API connectivity checks; use `unittest.skipUnless` on env keys so CI auto-skips when secrets are absent
- **Ad-hoc debugging** — use `scripts/` or a local untracked file; never commit throwaway tests
- **Before PR** — run `scripts/run_tests.sh`; if you changed Alpaca or LLM providers, confirm integration tests ran (not skipped) locally
- **Prefer mocks** — use `MockLLMClient` and `MockAlpacaTradingClient` for CI-safe coverage

See [development guide](docs/agents/development.md) for setup and commands.
