import os
from typing import Any, Optional

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetPortfolioHistoryRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


class AlpacaTradingClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')

        if not self.api_key or not self.secret_key:
            raise ValueError("API keys not found in environment variables")

        # Create trading client - paper trading is True by default
        self.client = TradingClient(self.api_key, self.secret_key)

    def get_account(self):
        """Get account information"""
        return self.client.get_account()

    def get_positions(self):
        """Get all positions"""
        return self.client.get_all_positions()

    def get_orders(self):
        """Get all orders"""
        return self.client.get_orders()

    def place_market_order(self, symbol: str, qty: int, side: OrderSide):
        """Place a market order"""
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY
        )
        return self.client.submit_order(order_data)

    def get_assets(self):
        """Get all available assets"""
        return self.client.get_all_assets()

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> Any:
        """Get portfolio equity history for the account."""
        request_kwargs = {
            "period": period,
            "extended_hours": extended_hours,
        }
        if timeframe:
            request_kwargs["timeframe"] = timeframe
        if date_end:
            request_kwargs["date_end"] = date_end

        history_filter = GetPortfolioHistoryRequest(**request_kwargs)
        return self.client.get_portfolio_history(history_filter)
