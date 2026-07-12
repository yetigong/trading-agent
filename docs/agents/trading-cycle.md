# Trading cycle flow

## Entry points

| Script | Behavior |
|--------|----------|
| `run_agent.py` | One **live** cycle; validates config; saves artifact; prints summary |
| `run_account_history.py` | One account history fetch; Alpaca keys only; saves `logs/account_history_*.json` |
| `trading_service.py` | Loops forever via `TradingScheduler` every `TRADING_CYCLE_INTERVAL` minutes (**live** deploy path) |
| `run_backtest.py` | Historical replay — **not** the live path; must not trigger retrospection/sweep (Phase 4.5.2) |

Live trading scripts delegate to `trading_agent/orchestrator/`. Account history is separate — see **[account-history.md](account-history.md)**. Offline learning lives in [`strategy_learning/`](../../strategy_learning/) — see **[learning-loop.md](learning-loop.md)**.

## Sequence

Phase 4: `TradingAgent` delegates to `CycleCoordinator` (see **[multi-agent.md](multi-agent.md)**). The layered modules below still do the work inside each agent. Phase 4.5.2: `TradingCycle` uses `LiveAgentRun`; backtests use `BacktestAgentRun` — only live may signal `strategy_learning` retrospection.

```mermaid
sequenceDiagram
    participant RA as run_agent / TradingCycle
    participant Live as LiveAgentRun
    participant TA as TradingAgent
    participant CC as CycleCoordinator
    participant MA as MarketAnalyzer
    participant TS as Strategizer
    participant TE as ExecutorAgent
    participant DL as DecisionLogger

    RA->>Live: run_trading_cycle(params)
    Live->>TA: run_trading_cycle(params)
    TA->>CC: run(params)
    CC->>MA: signals + analysis
    CC->>TS: strategy + rebalancer
    CC->>TE: prepare + execute
    CC->>DL: CycleResult (+ artifact when enabled)
    CC-->>TA: CycleResult dict
    TA-->>Live: CycleResult
    Live-->>RA: CycleResult + preparation + executed_trades
```

## Cycle result shape

Successful cycles return a dict including:

- `status`: `"success"` or `"failed"`
- `cycle_id`, `timestamp`
- `market_conditions`, `market_analysis`
- `analysis`, `analysis_strategy` (`"All Analysis Strategies"`)
- `decisions`: consolidated list after preparation
- `preparation`: `{raw, consolidated, executable, adjusted, skipped}`
- `hold`: bool
- `rebalancing`: plan dict or null
- `executed_trades`: list with `status`, `order_id` or `failure_detail`

Artifacts are written to `logs/cycle_<timestamp>_<id>.json`.

## HOLD semantics

An empty decision list from the strategy is **valid** — treated as HOLD. Rebalancing may still append orders; preparation may skip or clip them.

## Common failure modes (live paper)

| Symptom | Mitigation |
|---------|------------|
| `insufficient qty` | `TradeValidator` clips SELL to available shares |
| `insufficient buying power` | Validator clips BUY; prompt shows buying power |
| Wash trade | Validator skips when open opposite order exists |
| Duplicate symbol orders | `TradeConsolidator` merges before submit |

## Safe places to change behavior

- **Prompts** — `trading_agent/formatters/`, `strategies/general.py`, `analysis/*.py`
- **Domain models** — `trading_agent/domain/`
- **Pre-trade rules** — `trading_agent/execution/validator.py`, `consolidator.py`
- **Broker submit** — `trading_agent/execution/executor.py`
- **Orchestration** — `trading_agent/orchestrator/agent.py`
- **Summary output** — `run_agent.py`, `orchestrator/trading_cycle.py`
