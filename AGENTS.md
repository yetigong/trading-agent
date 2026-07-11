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

When making changes, prefer minimal diffs, match existing patterns, and run tests under `.venv/bin/python -m unittest discover tests -v`.
