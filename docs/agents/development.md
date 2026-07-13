# Development guide

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp -r data.example data
# Edit .env with BROKER_PROVIDER=alpaca, Alpaca paper keys, OPENAI_API_KEY (primary), and GOOGLE_API_KEY (Gemini fallback)
# Edit data/*.json for preferences, strategy params, sectors, watchlist
# Optional for richer market signals (Phase 2): FINNHUB_API_KEY, FMP_API_KEY
```

Always use the venv: `.venv/bin/python …`

## Local data files

Runtime configuration lives in `data/` (gitignored). Templates are committed under `data.example/`.

**Ownership:** `trading_agent` owns these config files (runtime **reads**; human / future UX **writes** after approving recommendations). `strategy_learning` must **not** modify them — it only proposes changes into the knowledge base (see [learning-loop.md](learning-loop.md)).

| File | Purpose |
|------|---------|
| `preferences.json` | Risk tolerance, investment goal, max position size |
| `analysis_params.json` | Analysis time horizon, focus areas, regions |
| `strategy_params.json` | Trading timeframe, risk management, position sizing |
| `rebalance_params.json` | Target allocation, rebalance threshold |
| `signal_config.json` | Sector ETFs to track, enabled signal sources |
| `watchlist.json` | Symbols of interest (wired into signal universe / backtest `--symbols` fallback) |
| `brokerage_config.json` | Broker provider default (`alpaca`, `robinhood`, `mock`) |
| `knowledge_base.json` | Learning KB (**owned by `strategy_learning`**; file still under `data/`) |

On first load each store seeds from `data.example/` if the file is missing. Override the directory with `DATA_DIR` (useful in tests).

FMP API responses are cached under `data/cache/fmp/YYYY-MM-DD/` (calendar-day TTL). See [market-signals.md](market-signals.md).

Historical bars/news for backtests (and other reuse) live under `data/cache/alpaca/` and `data/cache/finnhub/`. See [backtesting.md](backtesting.md).

Do not commit `data/` — only edit locally. API keys and LLM provider settings stay in `.env`.

## Packages

| Package | When to touch |
|---------|----------------|
| `trading_agent/` | Live cycle, brokers, signals, backtest engine, config stores |
| `strategy_learning/` | Offline learning (KB / feedback / sweep / retrospection — Phase 4.5 Done) |

Keep package diagrams in `docs/PROJECT_PLAN.md` and [codebase.md](codebase.md) in sync when changing boundaries.

## Run locally

**Single paper-trading cycle (MVP):**

```bash
.venv/bin/python run_agent.py
```

**Scheduled service:**

```bash
.venv/bin/python trading_service.py
```

**Account snapshot and equity history (read-only; uses configured broker):**

```bash
# Last month
.venv/bin/python run_account_history.py

# Past year, monthly breakdown
.venv/bin/python run_account_history.py --period 1A --group-by month
```

See **[account-history.md](account-history.md)** for CLI options and module layout.

**Backtest (Phase 3 — manual historical replay):**

```bash
.venv/bin/python run_backtest.py \
  --start 2024-01-01 --end 2024-06-30 \
  --symbols SPY,QQQ,XLK,XLV,XLE,XLI,XLY,IWM \
  --run-label baseline
```

See **[backtesting.md](backtesting.md)** for prefetch, OpenAI→Gemini failover, cycle success status, overrides, and `--compare`.

**Verify Gemini API / model:**

```bash
.venv/bin/python scripts/verify_gemini_setup.py
```

## Tests

```bash
.venv/bin/bash scripts/run_tests.sh
```

Live API checks under `tests/integration/` are opt-in:

```bash
RUN_INTEGRATION=1 .venv/bin/bash scripts/run_tests.sh
```

Or:

```bash
.venv/bin/python -m unittest discover -s strategy_learning/tests -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s trading_agent/tests -p 'test_*.py' -v
.venv/bin/python -m unittest tests/test_*.py -v
```

Unit tests live next to their packages (`strategy_learning/tests/`, `trading_agent/tests/`); cross-package tests stay under `tests/` (top-level only — `tests/integration/` is opt-in). All use mock LLM/broker clients and do not require API keys. Live integration tests in `tests/integration/` run when keys are present.

**Optional Robinhood broker** (live only, unofficial API):

```bash
pip install -r requirements-optional.txt
# Set ROBINHOOD_* vars and ROBINHOOD_LIVE_TRADING_ACK=true — see multi-broker.md
```

See **[multi-broker.md](multi-broker.md)** for broker architecture, env vars, and risks.

### Per-PR expectations

Before opening or merging a PR:

- Unit / mock suite must pass (`scripts/run_tests.sh` and CI `test`)
- Changed logic should have regression coverage under the matching package `tests/` (or `tests/` for cross-package) — **main flow layers**, not 100% line coverage
- No root-level `test_*.py` or committed throwaways
- Provider changes: run integration tests locally and confirm they were not skipped

Full checklist: [pr-description.md](pr-description.md#test-requirements-every-pr).

### Test coverage by flow

**Rule:** cover every layer you change in a multi-step flow — pure logic, package wiring, orchestrator/hook, and operator CLI when present. Source-only assertions (“file mentions symbol X”) are not enough for behavior.

| Flow | Layers that need tests when touched | Canonical tests |
|------|-------------------------------------|-----------------|
| Live trading cycle | Decision parse → prepare/execute → cycle smoke | `trading_agent/tests/test_trading_cycle_*.py`, `test_trade_*.py`, `test_decision_parsing.py` |
| Live vs backtest modes | Mode flags, live_lesson on/off, circular-trigger guard | `trading_agent/tests/test_agent_run_modes.py` |
| Live retrospection (4.5.5) | Metrics → detector → signal I/O → `TradingCycle` emit hook → `run_retrospection.py` CLI (list / dry-run / consume with **mocked** sweep) | See table below |
| Param sweep | OAT candidates → runner → recommendation write | `strategy_learning/tests/test_sweep_*.py` |
| KB / feedback / promotion | Store + EventRef; feedback does not rewrite configs; approve/reject | `strategy_learning/tests/test_knowledge.py`, `test_feedback.py`, `test_boundary.py`; `tests/test_learning_loop.py` |
| Brokers / providers | Mock unit + optional live integration | package `tests/` + `tests/integration/` |

#### Retrospection coverage checklist (required when changing that path)

| Layer | Must assert | Test module |
|-------|-------------|-------------|
| Metrics | lag vs SPY, hold-streak, cycle summary load | `strategy_learning/tests/test_retrospection_metrics.py` |
| Detector | trigger / no-trigger / pending / cooldown skips | `strategy_learning/tests/test_retrospection_detector.py` |
| Signal I/O | write pending → list → mark consumed; cooldown window | `strategy_learning/tests/test_retrospection_signal.py` |
| Cycle hook | `_maybe_emit_retrospection` emits on hit, skips otherwise, **never fails the cycle** | `trading_agent/tests/test_retrospection_cycle_hook.py` |
| Mode guard | live may emit; backtest raises | `trading_agent/tests/test_agent_run_modes.py` |
| Consumer CLI | `--list`, `--dry-run` (no consume), consume marks trigger consumed; pass short `--start`/`--end` in tests | `strategy_learning/tests/test_run_retrospection_cli.py` |
| Boundary | TradingCycle must not import / run `ParamSweepRunner` in-process | `test_agent_run_modes.TestTradingCycleDoesNotImportSweep` |

Feature inventory: [learning-loop.md](learning-loop.md#tests).

#### Automated vs local sanity

- **CI / `scripts/run_tests.sh`:** mock-based only. Inject fake `run_backtest` / `ParamSweepRunner` for sweep and retrospection consume paths.
- **Optional local e2e:** `--list` / `--dry-run` against a temp or real trigger; if you run a real backtest or sweep, use a **short window** and few symbols, e.g.:

```bash
.venv/bin/python run_retrospection.py --dry-run \
  --start 2026-07-06 --end 2026-07-10 --symbols AAPL
```

Do not require a full multi-week OAT LLM sweep in the PR checklist — it is slow and expensive; mock coverage is the bar.

## Coding conventions

- **Python 3.9+** compatible
- **Logging** over `print()` in library/orchestration code
- **Domain models** in `trading_agent/domain/` — pass between layers; use `formatters/` for LLM prompts
- **LLM decisions** — JSON under `"decisions"`; parsed by `parse_trading_decisions()`
- **Trade preparation** — always run through `TradePreparer` before `TradeExecutor`
- **JSON artifacts** — use `serialize_for_json()` for UUID/datetime/dataclass safety

## Architecture documentation

When changing the trading pipeline (new layer, moved module, new data provider):

1. Update the mermaid diagram in [`docs/PROJECT_PLAN.md`](../PROJECT_PLAN.md)
2. Update [`codebase.md`](codebase.md) directory layout and domain model table
3. Update [`trading-cycle.md`](trading-cycle.md) sequence diagram

When changing account history mode, update [`account-history.md`](account-history.md) and the account sections in [`codebase.md`](codebase.md).

When changing market signal providers or indicators, update [`market-signals.md`](market-signals.md).

## Git / PR workflow

- Branch from `main`; keep PRs focused
- Follow [pr-description.md](pr-description.md) for PR body format **and** the [per-PR test requirements](pr-description.md#test-requirements-every-pr)
- Do not commit `.env`, credentials, `data/`, or `logs/` cycle artifacts
- Run tests before pushing — `.venv/bin/bash scripts/run_tests.sh`

### Parallel work: prefer git worktrees

When running **multiple tasks in parallel** (several agents, best-of-N attempts, or overlapping PRs), prefer **git worktrees** over repeatedly checking out branches in a single working directory. Each worktree gets its own checkout path, so parallel runs do not fight over uncommitted changes, build artifacts, or branch switches.

Use a **single checkout** only for one focused task at a time.

#### Create a worktree

From the primary repo checkout (usually the main clone at `trading-agent/`):

```bash
# New branch from latest main
git fetch origin main
git worktree add ../trading-agent-<slug> -b cursor/<descriptive-name>-6b7c origin/main

# Existing branch (e.g. resume or second agent on same PR branch)
git worktree add ../trading-agent-<slug> cursor/<descriptive-name>-6b7c
```

Conventions:

- Put sibling worktrees next to the main clone: `../trading-agent-<slug>/` (short, filesystem-safe slug)
- Keep branch names under `cursor/<descriptive-name>-6b7c` (same as single-checkout workflow)
- One branch per worktree — do not check out the same branch in two worktrees

#### Per-worktree setup

Each worktree is an independent directory. Repeat local setup there (gitignored files are not shared):

```bash
cd ../trading-agent-<slug>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # or copy/symlink from the main checkout
cp -r data.example data  # or copy/symlink from the main checkout
```

Run tests and commits from inside that worktree path.

#### Inspect and clean up

When a task is done (PR merged or abandoned):

```bash
# From any checkout of this repo
git worktree list

# Remove the extra checkout (use --force if there are uncommitted changes you are discarding)
git worktree remove ../trading-agent-<slug>

# Delete the branch after merge, or if abandoning work
git branch -d cursor/<descriptive-name>-6b7c

# Drop stale worktree metadata if a directory was deleted manually
git worktree prune
```

Do not leave orphaned worktrees under `../trading-agent-*` after work finishes.

## Docker

```bash
podman build -t trading-agent -f aws/deployment/Dockerfile .
```

See `aws/deployment/README.md` for ECS deployment.
