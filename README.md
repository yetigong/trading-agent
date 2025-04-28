# AI-Powered Trading Agent

This project implements an AI-powered trading agent that uses Claude (Anthropic's LLM) to make trading decisions and execute them through the Alpaca Trading API.

## Features

- **AI-Powered Trading Decisions**: Uses Claude to analyze market conditions and make trading decisions
- **Portfolio Management**: Automatic portfolio rebalancing and position sizing
- **Market Analysis**: Comprehensive market analysis with multiple strategies
- **Risk Management**: Configurable risk tolerance and position limits
- **Real-time Trading**: Integration with Alpaca for real-time trading execution
- **Paper Trading Support**: Safe testing environment with paper trading

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your API credentials:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=True  # Set to False for live trading
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

3. Replace the API keys with your actual credentials.

## Usage

The project provides a `TradingAgent` class that handles the entire trading cycle:

```python
from trader import TradingAgent
from trading_agent.llm.client import get_llm_client
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from alpaca_client import AlpacaTradingClient

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

## Security Note

Never commit your `.env` file to version control. Make sure it's listed in your `.gitignore` file.

## Requirements

- Python 3.7+
- Alpaca API credentials
- Anthropic API key
- Required packages listed in `requirements.txt` 