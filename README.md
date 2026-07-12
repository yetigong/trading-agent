# AI-Powered Trading Agent

This project implements an AI-powered trading agent that uses LLMs to make trading decisions and execute them through broker APIs (Alpaca by default), plus a separate **`strategy_learning`** package for offline tuning (knowledge base, recommendations, sweeps).

See **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** for package boundaries and roadmap, and **[docs/agents/README.md](docs/agents/README.md)** for agent-oriented docs.

## Features

- **AI-Powered Trading Decisions**: Uses Claude to analyze market conditions and make trading decisions
- **Portfolio Management**: Automatic portfolio rebalancing and position sizing
- **Market Analysis**: Comprehensive market analysis with multiple strategies
- **Risk Management**: Configurable risk tolerance and position limits
- **Real-time Trading**: Integration with Alpaca for real-time trading execution
- **Account History**: Read-only account snapshot and equity history over time (margin-aware)
- **Paper Trading Support**: Safe testing environment with paper trading
- **AWS Deployment**: Automated deployment to AWS ECS Fargate
- **Comprehensive Logging**: Detailed logging of trades, errors, and system events
- **Robust Error Handling**: Graceful handling of API failures and market disruptions
- **Local Development**: Support for local development using Podman

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Copy the example env file and add your API credentials:
```bash
cp .env.example .env
```

Required variables for the MVP paper-trading demo:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true
OPENAI_API_KEY=your_openai_api_key_here   # primary (default)
GOOGLE_API_KEY=your_google_api_key_here   # Gemini failover (default)
LLM_PROVIDER=openai
LLM_MODEL=financial
LLM_FALLBACK_PROVIDER=gemini
```

3. Replace the API keys with your actual credentials.

## MVP Demo (Paper Trading E2E)

Run a single end-to-end paper trading cycle:

```bash
python run_agent.py
```

This will:
1. Validate your `.env` configuration
2. Fetch live market conditions from Alpaca
3. Run LLM market analysis and trading decisions
4. Execute paper trades via Alpaca
5. Save a JSON artifact to `logs/cycle_<timestamp>_<id>.json`
6. Print a human-readable summary

Expected success output includes `Status: success`, analysis strategy used, and any executed trades with order IDs.

### Account history (read-only)

Fetch your Alpaca account snapshot and equity history. Requires only Alpaca API keys (no LLM key):

```bash
python run_account_history.py

# Past year, monthly breakdown
python run_account_history.py --period 1A --group-by month
```

Saves `logs/account_history_<timestamp>.json` and prints equity, cash, margin debt, and monthly changes. See **[Account history guide](docs/agents/account-history.md)** for details.

### Backtesting (Phase 3)

Replay the trading agent on historical data and compare against SPY/QQQ and other benchmarks:

```bash
.venv/bin/python run_backtest.py \
  --start 2024-01-01 --end 2024-06-30 \
  --symbols SPY,QQQ,XLK,XLV,XLE,XLI,XLY,IWM \
  --run-label baseline
```

Uses your current `data/*.json` configuration. Prefer OpenAI primary + Gemini fallback (see `.env.example`). Require ≥80% cycle success before comparing to benchmarks. See **[Backtesting guide](docs/agents/backtesting.md)**.

For the scheduled service (runs every `TRADING_CYCLE_INTERVAL` minutes, default 30):

```bash
python trading_service.py
```

4. For local development with Podman:
```bash
# Build the container
podman build -t trading-agent -f aws/deployment/Dockerfile .

# Run the container
podman run -d --name trading-agent \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env \
  trading-agent
```

## Project Structure

```
trading-agent/
├── trading_agent/
│   ├── domain/             # Typed pipeline models (portfolio, account, cycle, …)
│   ├── orchestrator/       # TradingAgent, TradingCycle, AccountHistoryMode
│   ├── broker/             # Alpaca trading client + mock
│   ├── scheduler/          # TradingScheduler for trading_service.py
│   ├── account/            # Account history fetcher, query resolver, aggregation
│   ├── execution/          # Trade preparation + broker submit
│   ├── analysis/           # AnalysisRunner (all 3 strategies)
│   ├── strategies/         # Trading decision strategies
│   ├── market_data/        # Alpaca, Finnhub, FMP + historical caches
│   ├── signals/            # SignalAggregator, RSI/MACD indicators
│   ├── backtest/           # BacktestEngine, broker, benchmarks
│   └── formatters/         # Domain → LLM prompts
├── aws/deployment/         # Docker + ECS deployment
├── docs/                   # Project plan and agent guides
├── tests/
├── run_agent.py            # Single trading cycle
├── run_account_history.py  # Account snapshot + equity history
├── run_backtest.py         # Historical backtest + benchmarks
└── trading_service.py      # Scheduled trading service
```

See **[Project plan](docs/PROJECT_PLAN.md)** for the full layered architecture diagram.

## Documentation

- **[Project plan](docs/PROJECT_PLAN.md)** — roadmap and phase status (Phases 1–3 complete)
- **[Agent guides](docs/agents/README.md)** — for AI assistants and contributors
- **[Account history](docs/agents/account-history.md)** — read-only account snapshot and equity tracking
- **[PR description guide](docs/agents/pr-description.md)** — how to write pull request summaries

## Usage

The project provides a `TradingAgent` class that handles the entire trading cycle:

```python
from trading_agent.orchestrator.agent import TradingAgent
from trading_agent.llm.client import get_llm_client
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.broker.alpaca_client import AlpacaTradingClient

# Initialize components
llm_client = get_llm_client("claude", model="financial")
market_data_provider = AlpacaMarketDataProvider()
alpaca_client = AlpacaTradingClient()

# Create trading agent
agent = TradingAgent(
    risk_tolerance="moderate",
    investment_goal="growth",
    max_position_size=0.1,
    llm_client=llm_client,
    market_data_provider=market_data_provider,
    alpaca_client=alpaca_client
)

# Run a trading cycle
results = agent.run_trading_cycle(
    analysis_params={
        "time_horizon": "medium-term",
        "focus_areas": "tech, healthcare",
        "regions": "US"
    },
    strategy_params={
        "timeframe": "immediate",
        "risk_management": "standard",
        "position_sizing": "dynamic"
    },
    rebalance_params={
        "target_allocation": "balanced",
        "threshold": 5,
        "sector_weights": "market_cap"
    }
)
```

## Components

### Trading Agent
- Manages the entire trading cycle
- Integrates market analysis, decision making, and trade execution
- Handles portfolio rebalancing

### Market Analysis
- Multiple analysis strategies (General, Technical, Fundamental)
- Real-time market data through Alpaca
- Sector-specific analysis

### LLM Integration
- Uses Claude for market analysis and trading decisions
- Configurable system prompts for different tasks
- Structured output parsing

### Portfolio Management
- Automatic portfolio rebalancing
- Position sizing based on risk tolerance
- Diversification management

### Account History
- Read-only Alpaca account snapshot (equity, cash, margin debt)
- Portfolio equity history with optional monthly aggregation
- Separate entry point: `run_account_history.py` (no LLM required)

## Security Note

Never commit your `.env` file to version control. Make sure it's listed in your `.gitignore` file.

## Requirements

- Python 3.7+
- Alpaca API credentials
- Anthropic API key
- Required packages listed in `requirements.txt`
- For deployment: AWS CLI, Podman

## AWS Deployment

The trading agent can be deployed to AWS ECS Fargate using the provided deployment scripts in the `aws/deployment/` directory.

### Prerequisites

1. AWS CLI installed and configured
2. Podman installed (for container builds)
3. AWS resources set up:
   - ECS cluster
   - ECR repository
   - VPC and subnets
   - IAM roles and permissions

### Deployment Steps

1. Review the configuration in `aws/deployment/README.md` for detailed setup instructions.

2. Deploy using the automated script:
```bash
./aws/deployment/deploy.sh
```

This will:
- Build the container image
- Push to ECR
- Update the ECS task definition
- Deploy to Fargate

### Monitoring

- CloudWatch Logs: `/ecs/trading-agent`
- ECS Console: Check task status and service health
- CloudWatch Metrics: Monitor CPU, memory, and network usage

For detailed deployment instructions and troubleshooting, see `aws/deployment/README.md`.

## Logging

The trading agent implements comprehensive logging:

- Trade execution logs in `logs/trading_service.log`
- Cycle artifacts in `logs/cycle_<timestamp>_<id>.json`
- Account history artifacts in `logs/account_history_<timestamp>.json`
- System events and errors in `logs/system.log`
- Market data and analysis in `logs/market_data.log`

Logs are automatically rotated and archived.

## Error Handling

The system implements robust error handling:

- Automatic retries for transient API failures
- Graceful degradation during market disruptions
- Detailed error logging and monitoring
- Automatic recovery from common failure scenarios

## Testing

The project uses Python's unittest framework for testing. Tests are located in the `tests/` directory; live API checks live in `tests/integration/`.

### Running Tests Locally

To run all tests (live integration tests skip automatically without API keys):

```bash
.venv/bin/bash scripts/run_tests.sh
```

Or:

```bash
python -m unittest discover tests -v
```

To run only live integration tests (requires `.env` keys):

```bash
python -m unittest discover tests/integration -v
```

### CI/CD Pipeline

The project uses GitHub Actions for continuous integration. Tests are automatically run on:
- Every push to the main branch
- Every pull request to the main branch

Live integration tests are discovered but skipped in CI when API keys are not configured.

### Before opening a PR

Run the full test suite locally before pushing:

```bash
.venv/bin/bash scripts/run_tests.sh
```

If your change touches Alpaca or LLM providers, confirm the integration tests in `tests/integration/` executed (not skipped).

### Optional pre-commit hook

Install the tracked hook to run tests before each commit:

```bash
cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
``` 