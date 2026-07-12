import os
from typing import List, Optional

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetPortfolioHistoryRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce

from trading_agent.broker.mappers import (
    map_alpaca_account,
    map_alpaca_order,
    map_alpaca_order_result,
    map_alpaca_portfolio_history,
    map_alpaca_position,
)
from trading_agent.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerOrderResult,
    BrokerPosition,
    OrderSide,
    PortfolioHistory,
)


class AlpacaBrokerClient:
    """Alpaca trading client implementing the broker interface."""

    provider_name = "alpaca"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: Optional[bool] = None,
    ):
        load_dotenv()
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        if paper is None:
            paper = os.getenv("ALPACA_PAPER", "true").lower() in ("1", "true", "yes")

        if not self.api_key or not self.secret_key:
            raise ValueError("API keys not found in environment variables")

        self.client = TradingClient(self.api_key, self.secret_key, paper=paper)

    def get_account(self) -> BrokerAccount:
        return map_alpaca_account(self.client.get_account())

    def get_positions(self) -> List[BrokerPosition]:
        return [map_alpaca_position(p) for p in self.client.get_all_positions()]

    def get_orders(self) -> List[BrokerOrder]:
        return [map_alpaca_order(o) for o in self.client.get_orders()]

    def place_market_order(
        self, symbol: str, qty: int, side: OrderSide
    ) -> BrokerOrderResult:
        alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=alpaca_side,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(order_data)
        return map_alpaca_order_result(order, symbol=symbol, qty=qty, side=side)

    def get_assets(self):
        """Get all available assets (Alpaca-specific, not on BrokerClient protocol)."""
        return self.client.get_all_assets()

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> PortfolioHistory:
        request_kwargs = {
            "period": period,
            "extended_hours": extended_hours,
        }
        if timeframe:
            request_kwargs["timeframe"] = timeframe
        if date_end:
            request_kwargs["date_end"] = date_end

        history_filter = GetPortfolioHistoryRequest(**request_kwargs)
        return map_alpaca_portfolio_history(self.client.get_portfolio_history(history_filter))


# Backward-compatible alias
AlpacaTradingClient = AlpacaBrokerClient
