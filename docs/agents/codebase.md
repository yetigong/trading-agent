# Codebase overview

## What this project does

LLM-driven **paper trading** on Alpaca. Each cycle:

1. Fetch market conditions + portfolio snapshot (buying power, positions, open orders)
2. Collect market signals (Alpaca + Finnhub stub)
3. Run **all three** analysis strategies (general, technical, fundamental) via `AnalysisRunner`
4. Build `StrategyContext` and run trading strategy + optional rebalancer
5. **Prepare trades** — consolidate, validate, clip, order SELLs before BUYs
6. Execute via `TradeExecutor` and save `logs/cycle_*.json`

## Architecture (layers → directories)

```mermaid
flowchart TB
    subgraph orchestrator [trading_agent/orchestrator]
        TC[TradingCycle]
        TA[TradingAgent]
    end

    subgraph domain [trading_agent/domain]
        PS[PortfolioSnapshot]
        MA[MarketAnalysis]
        SC[StrategyContext]
    end

    subgraph analysis [trading_agent/analysis]
        AR[AnalysisRunner]
    end

    subgraph execution [trading_agent/execution]
        PRE[TradePreparer]
        EXT[TradeExecutor]
    end

    TC --> TA
    TA --> AR --> MA
    TA --> SC
    TA --> PRE --> EXT
```

**Keep this diagram in sync** with `docs/PROJECT_PLAN.md` when changing the pipeline.

## Directory layout

```
trading-agent/
├── run_agent.py
├── trading_service.py
├── trader.py                 # backward-compat re-export → orchestrator.agent
├── alpaca_client.py
├── trading_agent/
│   ├── domain/               # Typed pipeline models
│   │   ├── signals/          # MarketConditions, MarketSignals
│   │   ├── portfolio/        # PortfolioSnapshot, Position, OpenOrder
│   │   ├── cycle/            # StrategyContext, MarketAnalysis, CycleResult
│   │   └── user/             # UserPreferences
│   ├── orchestrator/         # TradingAgent, TradingCycle
│   ├── execution/            # SnapshotBuilder, Consolidator, Validator, Preparer, Executor
│   ├── analysis/             # AnalysisRunner + general/technical/fundamental
│   ├── strategies/           # GeneralTradingStrategy
│   ├── portfolio/            # PortfolioRebalancer
│   ├── market_data/          # Alpaca + Finnhub + mock providers
│   ├── signals/              # SignalAggregator
│   ├── formatters/           # Domain → LLM prompt text
│   ├── models.py             # JSON parsing helpers
│   └── llm/
├── scheduler/
├── tests/
└── docs/
```

## Domain models (pipeline contract)

| Model | Package | Role |
|-------|---------|------|
| `MarketConditions` | `domain/signals` | Index trend, volatility from Alpaca |
| `MarketSignals` | `domain/signals` | Aggregated data/technical/news/fundamental slices |
| `PortfolioSnapshot` | `domain/portfolio` | Account, positions with qty, open orders |
| `MarketAnalysis` | `domain/cycle` | All three `AnalysisResult` entries |
| `StrategyContext` | `domain/cycle` | Single input to `make_trading_decisions` |
| `TradingDecision` | `domain/cycle` | Typed BUY/SELL with source tag |
| `TradePreparationResult` | `domain/cycle` | raw / consolidated / executable / adjusted / skipped |
| `CycleResult` | `domain/cycle` | Top-level artifact |

## Important interfaces

| Interface | Location | Implementations |
|-----------|----------|-----------------|
| `LLMClient` | `trading_agent/llm/base.py` | gemini, claude, openai, huggingface, mock |
| `MarketDataProvider` | `trading_agent/market_data/base.py` | alpaca, mock |
| `NewsDataProvider` | `trading_agent/market_data/news_base.py` | finnhub (stub) |
| `AnalysisStrategy` | `trading_agent/analysis/base.py` | general, technical, fundamental |
| `AnalysisRunner` | `trading_agent/analysis/runner.py` | runs all three per cycle |
| `TradingStrategy` | `trading_agent/strategies/base.py` | general |
| `TradePreparer` | `trading_agent/execution/preparer.py` | consolidate + validate |
| `AlpacaTradingClient` | `alpaca_client.py` | live; `mock_alpaca_client.py` for tests |

## Extension points

| Task | Where to change |
|------|-----------------|
| New LLM provider | `trading_agent/llm/` + `get_llm_client()` |
| New analysis strategy | `trading_agent/analysis/` + register in `AnalysisRunner` |
| New data/signal source | `trading_agent/market_data/` + `SignalAggregator` |
| Pre-trade rules | `trading_agent/execution/validator.py` |
| Trade consolidation | `trading_agent/execution/consolidator.py` |
| Cycle orchestration | `trading_agent/orchestrator/agent.py` |
| Prompt formatting | `trading_agent/formatters/` |
| Decision JSON schema | `trading_agent/models.py`, `GeneralTradingStrategy` |
