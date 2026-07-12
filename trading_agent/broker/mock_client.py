from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class MockAlpacaTradingClient:
    """Mock Alpaca trading client for testing."""

    def __init__(self):
        self.mock_account = {
            "portfolio_value": 100000.0,
            "cash": 50000.0,
            "buying_power": 50000.0,
            "equity": 100000.0,
            "positions": [
                {"symbol": "AAPL", "qty": 1, "available_qty": 1, "market_value": 200.0, "current_price": 200.0},
                {"symbol": "MSFT", "qty": 0, "available_qty": 0, "market_value": 0.0, "current_price": 0.0},
            ],
        }
        self.orders: List[Dict[str, Any]] = []

    def get_account(self) -> Any:
        return type(
            "Account",
            (),
            {
                "id": "mock-account-id",
                "account_number": "MOCK0001",
                "status": "ACTIVE",
                "currency": "USD",
                "portfolio_value": self.mock_account["portfolio_value"],
                "cash": self.mock_account["cash"],
                "buying_power": self.mock_account["buying_power"],
                "equity": self.mock_account["equity"],
                "last_equity": self.mock_account.get("last_equity", self.mock_account["equity"]),
                "long_market_value": self.mock_account.get("long_market_value", 50000.0),
                "short_market_value": 0.0,
                "initial_margin": 0.0,
                "maintenance_margin": 0.0,
                "multiplier": 1.0,
            },
        )()

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> Any:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        day = 86400
        equities = [98000.0, 99500.0, 100000.0]
        timestamps = [now - (2 * day), now - day, now]
        return type(
            "PortfolioHistory",
            (),
            {
                "timestamp": timestamps,
                "equity": equities,
                "profit_loss": [0.0, 1500.0, 500.0],
                "profit_loss_pct": [0.0, 0.0153, 0.005],
                "base_value": equities[0],
                "timeframe": timeframe or "1D",
            },
        )()

    def get_positions(self) -> List[Any]:
        return [
            type(
                "Position",
                (),
                {
                    "symbol": p["symbol"],
                    "qty": p["qty"],
                    "qty_available": p.get("available_qty", p["qty"]),
                    "market_value": p.get("market_value", 0.0),
                    "current_price": p.get("current_price", 0.0),
                    "avg_entry_price": p.get("current_price", 0.0),
                },
            )()
            for p in self.mock_account["positions"]
            if p["qty"] > 0
        ]

    def get_orders(self) -> List[Any]:
        return [
            type(
                "Order",
                (),
                {
                    "id": o["id"],
                    "symbol": o["symbol"],
                    "side": o["side"],
                    "qty": o["qty"],
                    "status": o["status"],
                },
            )()
            for o in self.orders
        ]

    def place_market_order(self, symbol: str, qty: int, side: str) -> Any:
        position = next((p for p in self.mock_account["positions"] if p["symbol"] == symbol), None)
        side_value = getattr(side, "value", str(side)).upper()

        if side_value == "SELL":
            if not position or position["qty"] < qty:
                raise Exception(
                    json_error(
                        f"insufficient qty available for order (requested: {qty}, available: {position['qty'] if position else 0})",
                        existing_qty=position["qty"] if position else 0,
                        available=position["qty"] if position else 0,
                        symbol=symbol,
                    )
                )

        order = {
            "id": f"order_{len(self.orders) + 1}",
            "symbol": symbol,
            "qty": qty,
            "side": side_value,
            "status": "filled",
            "filled_at": datetime.now(),
        }
        self.orders.append(order)

        if position:
            if side_value == "BUY":
                position["qty"] += qty
            else:
                position["qty"] -= qty
        elif side_value == "BUY":
            self.mock_account["positions"].append(
                {
                    "symbol": symbol,
                    "qty": qty,
                    "available_qty": qty,
                    "market_value": 0.0,
                    "current_price": 0.0,
                }
            )

        return type("Order", (), {"id": order["id"]})()

    def get_order(self, order_id: str) -> Dict[str, Any]:
        for order in self.orders:
            if order["id"] == order_id:
                return order
        return None


def json_error(message: str, **extra) -> str:
    import json

    payload = {"code": 40310000, "message": message}
    payload.update(extra)
    return json.dumps(payload)
