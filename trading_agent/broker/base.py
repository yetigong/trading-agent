from typing import List, Optional, Protocol, runtime_checkable

from trading_agent.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerOrderResult,
    BrokerPosition,
    OrderSide,
    PortfolioHistory,
)


@runtime_checkable
class BrokerClient(Protocol):
    """Broker API surface for account state, orders, and portfolio history."""

    @property
    def provider_name(self) -> str: ...

    def get_account(self) -> BrokerAccount: ...

    def get_positions(self) -> List[BrokerPosition]: ...

    def get_orders(self) -> List[BrokerOrder]: ...

    def place_market_order(
        self, symbol: str, qty: int, side: OrderSide
    ) -> BrokerOrderResult: ...

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> PortfolioHistory: ...
