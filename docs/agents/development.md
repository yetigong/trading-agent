# Development guide

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Alpaca paper keys and GOOGLE_API_KEY (or other LLM key)
```

Always use the venv: `.venv/bin/python …`

## Run locally

**Single paper-trading cycle (MVP):**

```bash
.venv/bin/python run_agent.py
```

**Scheduled service:**

```bash
.venv/bin/python trading_service.py
```

**Account snapshot and equity history (read-only, Alpaca keys only):**

```bash
# Last month
.venv/bin/python run_account_history.py

# Past year, monthly breakdown
.venv/bin/python run_account_history.py --period 1A --group-by month
```

See **[account-history.md](account-history.md)** for CLI options and module layout.

**Verify Gemini API / model:**

```bash
.venv/bin/python scripts/verify_gemini_setup.py
```

## Tests

```bash
.venv/bin/bash scripts/run_tests.sh
```

Or:

```bash
.venv/bin/python -m unittest discover tests -v
```

Unit tests in `tests/` use mock LLM/Alpaca and do not require API keys. Live integration tests in `tests/integration/` run when keys are present.

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

## Git / PR workflow

- Branch from `main`; keep PRs focused
- Follow [pr-description.md](pr-description.md) for PR body format
- Do not commit `.env`, credentials, or `logs/` cycle artifacts
- Run tests before pushing — `.venv/bin/bash scripts/run_tests.sh`

## Docker

```bash
podman build -t trading-agent -f aws/deployment/Dockerfile .
```

See `aws/deployment/README.md` for ECS deployment.
