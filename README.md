# Alpaca Trading API Integration

This project provides a basic integration with the Alpaca Trading API, allowing you to interact with your Alpaca trading account programmatically.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your Alpaca API credentials:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=True  # Set to False for live trading
```

3. Replace `your_api_key_here` and `your_secret_key_here` with your actual Alpaca API credentials.

## Usage

The project provides a `AlpacaTradingClient` class with the following main functionalities:

- Get account information
- Get all positions
- Place market orders
- Get available assets

Example usage:
```python
from alpaca_client import AlpacaTradingClient

# Initialize the client
client = AlpacaTradingClient()

# Get account information
account = client.get_account()
print(f"Account Status: {account.status}")
print(f"Buying Power: ${account.buying_power}")

# Place a market order
order = client.place_market_order(
    symbol="AAPL",
    qty=1,
    side=OrderSide.BUY
)
```

## Features

- Secure API key management using environment variables
- Support for both paper and live trading
- Basic trading operations (market orders)
- Account and position management
- Asset information retrieval

## Security Note

Never commit your `.env` file to version control. Make sure it's listed in your `.gitignore` file.

## Requirements

- Python 3.7+
- Alpaca API credentials
- Required packages listed in `requirements.txt` 