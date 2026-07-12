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

Runtime configuration lives in `data/` (gitignored). Templates are committed under `data.example/`:

| File | Purpose |
|------|---------|
| `preferences.json` | Risk tolerance, investment goal, max position size |
| `analysis_params.json` | Analysis time horizon, focus areas, regions |
| `strategy_params.json` | Trading timeframe, risk management, position sizing |
| `rebalance_params.json` | Target allocation, rebalance threshold |
| `signal_config.json` | Sector ETFs to track, enabled signal sources |
| `watchlist.json` | Symbols of interest (wired into signal universe / backtest `--symbols` fallback) |
| `brokerage_config.json` | Broker provider default (`alpaca`, `robinhood`, `mock`) |

On first load each store seeds from `data.example/` if the file is missing. Override the directory with `DATA_DIR` (useful in tests).

FMP API responses are cached under `data/cache/fmp/YYYY-MM-DD/` (calendar-day TTL). See [market-signals.md](market-signals.md).

Historical bars/news for backtests (and other reuse) live under `data/cache/alpaca/` and `data/cache/finnhub/`. See [backtesting.md](backtesting.md).

Do not commit `data/` — only edit locally. API keys and LLM provider settings stay in `.env`.

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
.venv/bin/python -m unittest discover tests -v
```

Unit tests in `tests/` use mock LLM/broker clients and do not require API keys. Live integration tests in `tests/integration/` run when keys are present.

**Optional Robinhood broker** (live only, unofficial API):

```bash
pip install -r requirements-optional.txt
# Set ROBINHOOD_* vars and ROBINHOOD_LIVE_TRADING_ACK=true — see multi-broker.md
```

See **[multi-broker.md](multi-broker.md)** for broker architecture, env vars, and risks.

### Per-PR expectations

Before opening or merging a PR:

- Unit / mock suite must pass (`scripts/run_tests.sh` and CI `test`)
- Changed logic should have regression coverage under `tests/` (main components of the flow, not 100% coverage)
- No root-level `test_*.py` or committed throwaways
- Provider changes: run integration tests locally and confirm they were not skipped

Full checklist: [pr-description.md](pr-description.md#test-requirements-every-pr).

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

## Docker

```bash
podman build -t trading-agent -f aws/deployment/Dockerfile .
```

See `aws/deployment/README.md` for ECS deployment.
