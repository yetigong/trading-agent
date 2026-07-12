from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class BrokerClient(Protocol):
    """Broker API surface for account state, orders, and portfolio history."""

    def get_account(self) -> Any: ...

    def get_positions(self) -> Any: ...

    def get_orders(self) -> Any: ...

    def place_market_order(self, symbol: str, qty: int, side: Any) -> Any: ...

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> Any: ...
