# Backtesting (Phase 3)

Manual, repeatable evaluation of the live `TradingAgent` pipeline on historical data, compared against industry-standard benchmarks.

## Quick start

```bash
# Prefetch bars + news into data/cache/{alpaca,finnhub}/
.venv/bin/python run_backtest.py --start 2024-01-01 --end 2024-06-30 --prefetch-only

# Run weekly LLM backtest using current data/*.json user config
.venv/bin/python run_backtest.py \
  --start 2024-01-01 --end 2024-06-30 \
  --rebalance weekly \
  --run-label baseline

# Tune a parameter without editing data files, then re-run
.venv/bin/python run_backtest.py \
  --start 2024-01-01 --end 2024-06-30 \
  --override-strategy '{"risk_management": "aggressive"}' \
  --run-label aggressive-v2

# Compare saved artifacts
.venv/bin/python run_backtest.py --compare \
  logs/backtest_*_baseline.json \
  logs/backtest_*_aggressive-v2.json
```

Artifacts are written to `logs/backtest_<timestamp>_<run_label>.json`.

## What it does

1. Loads the **same user stores** as a live cycle (`preferences`, `strategy_params`, `analysis_params`, `rebalance_params`, `signal_config`, watchlist symbols)
2. Ensures historical bars/news are cached under `data/cache/alpaca/` and `data/cache/finnhub/`
3. Steps each trading day: mark-to-market on `BacktestBroker`
4. On each **rebalance date** (weekly by default): runs `TradingAgent.run_trading_cycle()` with point-in-time providers
5. Computes strategy metrics and benchmarks (SPY, QQQ, 60/40, SMA crossover, equal-weight B&H)
6. Saves a config snapshot + equity curve + metrics table for repeatable comparison

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
**Active baselines:** SMA(20/50) on SPY, equal-weight B&H of the strategy universe  

**Metrics:** total return, CAGR, max drawdown, volatility, Sharpe, alpha/beta vs SPY

## Package layout

```
trading_agent/backtest/
  engine.py       # loops period, invokes TradingAgent
  broker.py       # BacktestBroker (BrokerClient)
  benchmarks.py
  metrics.py
  comparison.py
  models.py
run_backtest.py   # manual CLI
```

## Known limitations (v1)

- FMP fundamentals are TTM — backtest uses an empty/mock fundamentals slice and records a note in the artifact
- Corporate actions (splits/dividends) are ignored
- LLM outputs are non-deterministic; snapshot provider/model in the artifact when comparing runs
- `--rebalance daily` is available but expensive (full LLM cycle every trading day)

## Tests

```bash
.venv/bin/python -m unittest \
  tests.test_historical_data \
  tests.test_backtest_broker_metrics \
  tests.test_backtest_engine -v
```
