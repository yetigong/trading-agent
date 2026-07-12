from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from trading_agent.domain.broker import (
    BrokerAccount,
    BrokerError,
    BrokerOrder,
    BrokerOrderResult,
    BrokerPosition,
    OrderSide,
    OrderStatus,
    PortfolioHistory,
)


class MockBrokerClient:
    """Provider-agnostic mock broker client for testing."""

    provider_name = "mock"

    def __init__(self):
        self.mock_account = {
            "portfolio_value": 100000.0,
            "cash": 50000.0,
            "buying_power": 50000.0,
            "equity": 100000.0,
            "positions": [
                {
                    "symbol": "AAPL",
                    "qty": 1,
                    "available_qty": 1,
                    "market_value": 200.0,
                    "current_price": 200.0,
                },
                {
                    "symbol": "MSFT",
                    "qty": 0,
                    "available_qty": 0,
                    "market_value": 0.0,
                    "current_price": 0.0,
                },
            ],
        }
        self.orders: List[Dict[str, Any]] = []

    def get_account(self) -> BrokerAccount:
        data = self.mock_account
        return BrokerAccount(
            account_id="mock-account-id",
            account_number="MOCK0001",
            status="ACTIVE",
            currency="USD",
            portfolio_value=float(data["portfolio_value"]),
            cash=float(data["cash"]),
            buying_power=float(data["buying_power"]),
            equity=float(data["equity"]),
            last_equity=float(data.get("last_equity", data["equity"])),
            long_market_value=float(data.get("long_market_value", 50000.0)),
        )

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> PortfolioHistory:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        day = 86400
        equities = [98000.0, 99500.0, 100000.0]
        timestamps = [now - (2 * day), now - day, now]
        return PortfolioHistory(
            timestamps=timestamps,
            equity=equities,
            profit_loss=[0.0, 1500.0, 500.0],
            profit_loss_pct=[0.0, 0.0153, 0.005],
            base_value=equities[0],
            timeframe=timeframe or "1D",
        )

    def get_positions(self) -> List[BrokerPosition]:
        positions: List[BrokerPosition] = []
        for p in self.mock_account["positions"]:
            if p["qty"] <= 0:
                continue
            positions.append(
                BrokerPosition(
                    symbol=p["symbol"],
                    qty=float(p["qty"]),
                    available_qty=float(p.get("available_qty", p["qty"])),
                    market_value=float(p.get("market_value", 0.0)),
                    current_price=float(p.get("current_price", 0.0)),
                    avg_entry_price=float(p.get("current_price", 0.0)),
                )
            )
        return positions

    def get_orders(self) -> List[BrokerOrder]:
        return [
            BrokerOrder(
                order_id=o["id"],
                symbol=o["symbol"],
                side=OrderSide.BUY if o["side"] == "BUY" else OrderSide.SELL,
                qty=float(o["qty"]),
                status=OrderStatus.from_raw(o["status"]),
            )
            for o in self.orders
        ]

    def place_market_order(
        self, symbol: str, qty: int, side: OrderSide
    ) -> BrokerOrderResult:
        position = next(
            (p for p in self.mock_account["positions"] if p["symbol"] == symbol),
            None,
        )

        if side == OrderSide.SELL:
            if not position or position["qty"] < qty:
                available = position["qty"] if position else 0
                raise BrokerError(
                    f"insufficient qty available for order (requested: {qty}, available: {available})",
                    code="40310000",
                    provider=self.provider_name,
                    details={
                        "existing_qty": position["qty"] if position else 0,
                        "available": available,
                        "symbol": symbol,
                    },
                )

        order = {
            "id": f"order_{len(self.orders) + 1}",
            "symbol": symbol,
            "qty": qty,
            "side": side.value.upper(),
            "status": "filled",
            "filled_at": datetime.now(),
        }
        self.orders.append(order)

        if position:
            if side == OrderSide.BUY:
                position["qty"] += qty
            else:
                position["qty"] -= qty
        elif side == OrderSide.BUY:
            self.mock_account["positions"].append(
                {
                    "symbol": symbol,
                    "qty": qty,
                    "available_qty": qty,
                    "market_value": 0.0,
                    "current_price": 0.0,
                }
            )

        return BrokerOrderResult(
            order_id=order["id"],
            symbol=symbol,
            side=side,
            qty=float(qty),
            status=OrderStatus.FILLED,
        )

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        for order in self.orders:
            if order["id"] == order_id:
                return order
        return None


# Backward-compatible alias
MockAlpacaTradingClient = MockBrokerClient


def json_error(message: str, **extra) -> str:
    import json

    payload = {"code": 40310000, "message": message}
    payload.update(extra)
    return json.dumps(payload)
