# Backtesting (Phase 3)

Manual, repeatable evaluation of the live `TradingAgent` pipeline on historical data, compared against industry-standard benchmarks.

## Quick start

```bash
# Prefetch bars + news into data/cache/{alpaca,finnhub}/
.venv/bin/python run_backtest.py --start 2024-01-01 --end 2024-06-30 --prefetch-only

# Run weekly LLM backtest using current data/*.json user config
# Requires OPENAI_API_KEY (primary) and GOOGLE_API_KEY (Gemini fallback by default)
.venv/bin/python run_backtest.py \
  --start 2024-01-01 --end 2024-06-30 \
  --rebalance weekly \
  --symbols SPY,QQQ,XLK,XLV,XLE,XLI,XLY,IWM,TSLA,NVDA,MSFT,PLTR,GLD \
  --run-label baseline

# Optional: pause between weekly LLM cycles to reduce rate-limit pressure
.venv/bin/python run_backtest.py \
  --start 2026-01-01 --end 2026-06-30 \
  --symbols SPY,QQQ,XLK,XLV,XLE,XLI,XLY,IWM,TSLA,NVDA,MSFT,PLTR,GLD \
  --llm-pause-seconds 2 \
  --run-label clean-baseline

# Tune a parameter without editing data files, then re-run
.venv/bin/python run_backtest.py \
  --start 2024-01-01 --end 2024-06-30 \
  --override-strategy '{"risk_management": "aggressive"}' \
  --run-label aggressive-v2

# Compare saved artifacts (degraded/failed runs are excluded from highlights)
.venv/bin/python run_backtest.py --compare \
  logs/backtest_*_baseline.json \
  logs/backtest_*_aggressive-v2.json

# Score a completed run into the knowledge base (may create pending_review)
.venv/bin/python run_backtest.py --feedback logs/backtest_*_baseline.json
# Or run + feedback in one shot:
.venv/bin/python run_backtest.py --start 2024-01-01 --end 2024-06-30 --feedback
```

Learner is **disabled** during backtest replay so live `knowledge_base.json` is not polluted by per-cycle strings. Aggregate learning uses `--feedback` — see [learning-loop.md](learning-loop.md).

Artifacts are written to `logs/backtest_<timestamp>_<run_label>.json`.

## Trustworthy runs (read this before comparing to SPY)

A run is only a valid LLM-strategy evaluation when most rebalance cycles actually succeed:

| Run status | Meaning |
|------------|---------|
| `success` | All LLM cycles succeeded |
| `degraded` | Some cycles failed, but success rate ≥ 80% — **not** an authoritative baseline |
| `failed` | Success rate &lt; 80% (or zero successes) — do not compare to benchmarks |

The CLI summary prints cycle success rate, last trade date, and end-of-run cash / invested %. Require **≥80% cycle success** before treating SPY/QQQ comparisons as meaningful.

### Fair comparison to B&H SPY (invested %)

Buy-and-hold SPY is ~100% invested. If `data/preferences.json` keeps `max_position_size` at **0.1**, a diversified book can sit near **~65% invested** (~35% cash) even with a healthy LLM path — that cash drag alone can trail SPY without implying a bad signal stack.

For clean baselines meant to compete with fully invested SPY B&H:

- Prefer `max_position_size` **≥ 0.2** (code / example default is **0.25**)
- Check end-of-run **cash % / invested %** in the CLI summary and artifact before attributing underperformance to stock selection
- `rebalance_params.target_allocation`: **`balanced`** pushes toward equal-sector exposure; **`growth`** preserves growth/core overweights (SPY/QQQ/XLK-style) instead of forcing sector balance

### LLM primary / secondary failover

Default config (see `.env.example`):

- **Primary:** OpenAI (`LLM_PROVIDER=openai`, alias `financial` → `o4-mini`)
- **Fallback:** Gemini (`LLM_FALLBACK_PROVIDER=gemini`, alias `financial` → `gemini-3.5-flash`)
- Each provider gets up to `LLM_MAX_RETRIES` (default 3) attempts with exponential backoff / Retry-After
- If primary is exhausted, the client fails over to secondary automatically

Set `LLM_FALLBACK_PROVIDER=none` to disable failover.

## What it does

1. Loads the **same user stores** as a live cycle (`preferences`, `strategy_params`, `analysis_params`, `rebalance_params`, `signal_config`, watchlist symbols)
2. Ensures historical bars/news are cached under `data/cache/alpaca/` and `data/cache/finnhub/`
3. Steps each trading day: mark-to-market on `BacktestBroker`
4. On each **rebalance date** (weekly by default): runs `TradingAgent.run_trading_cycle()` with point-in-time providers; watchlist / `--symbols` are wired into the signal universe
5. Computes strategy metrics and benchmarks (SPY, QQQ, 60/40, SMA crossover, equal-weight B&H of configured symbols)
6. Saves a config snapshot + equity curve + cycle stats + metrics table for repeatable comparison

## Historical data layout

Shared across the platform (not backtest-only):

```
data/cache/
  alpaca/
    manifest.json
    bars/{SYMBOL}.csv
  finnhub/
    manifest.json
    news/{SYMBOL}/{YYYY-MM-DD}.json
  fmp/                    # existing day cache; TTM not true point-in-time
```

Providers:

| Module | Role |
|--------|------|
| `trading_agent/market_data/alpaca_historical.py` | Fetch/cache bars; `HistoricalAlpacaProvider(as_of_date)` |
| `trading_agent/market_data/finnhub_historical.py` | Fetch/cache news; `HistoricalFinnhubProvider(as_of_date)` |
| `trading_agent/market_data/historical_cache.py` | Shared manifest helpers |

## Benchmarks and metrics

**Passive:** SPY B&H, QQQ B&H, 60% SPY / 40% AGG  
**Active baselines:** SMA(20/50) on SPY, equal-weight B&H of the strategy universe (`--symbols` / watchlist)  

**Metrics:** total return, CAGR, max drawdown, volatility, Sharpe, alpha/beta vs SPY

## Package layout

```
trading_agent/backtest/
  engine.py       # loops period, invokes TradingAgent
  broker.py       # BacktestBroker (BrokerClient)
  benchmarks.py
  metrics.py
  comparison.py
  status.py       # cycle success → success/degraded/failed
  models.py
run_backtest.py   # manual CLI
```

## Known limitations (v1)

- FMP fundamentals are TTM — backtest uses an empty/mock fundamentals slice and records a note in the artifact
- Corporate actions (splits/dividends) are ignored
- LLM outputs are non-deterministic; snapshot provider/model (and failover stats) in the artifact when comparing runs
- `--rebalance daily` is available but expensive (full LLM cycle every trading day)
- Same-close fills and zero transaction costs remain optimistic vs live trading

## Tests

```bash
.venv/bin/python -m unittest \
  tests.test_historical_data \
  tests.test_backtest_broker_metrics \
  tests.test_backtest_engine \
  tests.test_backtest_status \
  tests.test_llm_failover \
  tests.test_backtest_comparison -v
```
