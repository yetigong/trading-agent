# Codebase overview

## What this project does

LLM-driven **paper trading** on Alpaca. Each cycle:

1. Load portfolio and market conditions
2. Run LLM market analysis (selector picks general / technical / fundamental)
3. Run LLM trading strategy → JSON list of decisions
4. Optionally run portfolio rebalancing → more decisions
5. Submit market orders to Alpaca
6. Return a cycle result dict (saved to `logs/cycle_*.json` by `run_agent.py`)

## Directory layout

```
trading-agent/
├── run_agent.py              # Single-cycle MVP entry (start here for manual runs)
├── trading_service.py        # Long-running scheduler
├── trader.py                 # TradingAgent — core orchestrator
├── alpaca_client.py          # Alpaca REST wrapper
├── agent/trading_cycle.py    # Wires config + clients → TradingAgent
├── trading_agent/
│   ├── config.py             # Env-based AppConfig
│   ├── models.py             # JSON parsing, serialization, trade failure formatting
│   ├── analysis/             # LLM analysis strategies + selector
│   ├── strategies/           # LLM trading strategies (GeneralTradingStrategy)
│   ├── portfolio/            # Rebalancer
│   ├── market_data/          # Alpaca + mock providers
│   └── llm/                  # Provider clients (gemini, claude, openai, mock, …)
├── scheduler/                # Periodic TradingCycle runner
├── tests/                    # unittest suite
├── scripts/                  # Utilities (e.g. verify_gemini_setup.py)
├── aws/deployment/           # Docker + ECS
└── docs/                     # Project plan + agent docs
```

## Important interfaces (ABCs)

| Interface | Location | Implementations |
|-----------|----------|-----------------|
| `LLMClient` | `trading_agent/llm/base.py` | gemini, claude, openai, huggingface, mock |
| `MarketDataProvider` | `trading_agent/market_data/base.py` | alpaca, mock |
| `AnalysisStrategy` | `trading_agent/analysis/base.py` | general, technical, fundamental |
| `TradingStrategy` | `trading_agent/strategies/base.py` | general |
| `AlpacaTradingClient` | `alpaca_client.py` | live; `mock_alpaca_client.py` for tests |

## Configuration

All runtime config flows through `trading_agent/config.py` and `.env` (see `.env.example`).

Key variables: `LLM_PROVIDER`, `LLM_MODEL`, `ALPACA_*`, `TRADING_CYCLE_INTERVAL`, `LOG_LEVEL`.

Gemini default model is `gemini-3.1-flash-lite-preview` (see `trading_agent/llm/gemini_client.py`).

## Extension points (common tasks)

| Task | Where to change |
|------|-----------------|
| New LLM provider | `trading_agent/llm/` + register in `get_llm_client()` |
| New analysis strategy | `trading_agent/analysis/` + selector |
| New trading strategy | `trading_agent/strategies/` + wire in `TradingAgent` |
| Pre-trade checks | `trader.py` → `execute_trades()` |
| Cycle output / summary | `run_agent.py`, `agent/trading_cycle.py` |
| Decision JSON schema | `trading_agent/models.py`, `GeneralTradingStrategy` prompt |
