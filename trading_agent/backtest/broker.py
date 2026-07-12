"""Simulated broker for backtesting — fills at bar close prices."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional


class BacktestBroker:
    """In-memory broker that fills market orders at the current day's close."""

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        seed_positions: Optional[Dict[str, int]] = None,
        price_fn: Optional[Callable[[str], Optional[float]]] = None,
    ):
        self.cash = float(initial_cash)
        self.initial_cash = float(initial_cash)
        self.price_fn = price_fn or (lambda _symbol: None)
        self.as_of_date: Optional[date] = None
        self.orders: List[Dict[str, Any]] = []
        self.positions: Dict[str, Dict[str, Any]] = {}
        self._order_seq = 0

        for symbol, qty in (seed_positions or {}).items():
            if qty <= 0:
                continue
            price = self._price(symbol) or 0.0
            self.positions[symbol.upper()] = {
                "symbol": symbol.upper(),
                "qty": int(qty),
                "available_qty": int(qty),
                "avg_entry_price": float(price),
                "current_price": float(price),
                "market_value": float(qty) * float(price),
            }
        self.mark_to_market()

    def set_price_fn(self, price_fn: Callable[[str], Optional[float]]) -> None:
        self.price_fn = price_fn

    def set_as_of_date(self, as_of: date) -> None:
        self.as_of_date = as_of
        self.mark_to_market()

    def _price(self, symbol: str) -> Optional[float]:
        try:
            return self.price_fn(symbol.upper())
        except Exception:
            return None

    def mark_to_market(self) -> float:
        long_mv = 0.0
        for symbol, pos in list(self.positions.items()):
            price = self._price(symbol)
            if price is None:
                price = float(pos.get("current_price") or 0.0)
            qty = int(pos["qty"])
            pos["current_price"] = float(price)
            pos["market_value"] = qty * float(price)
            pos["available_qty"] = qty
            long_mv += pos["market_value"]
            if qty <= 0:
                del self.positions[symbol]
        self._long_market_value = long_mv
        self._equity = self.cash + long_mv
        return self._equity

    @property
    def equity(self) -> float:
        return float(getattr(self, "_equity", self.cash))

    def get_account(self) -> Any:
        self.mark_to_market()
        return type(
            "Account",
            (),
            {
                "id": "backtest-account",
                "account_number": "BT0001",
                "status": "ACTIVE",
                "currency": "USD",
                "portfolio_value": self.equity,
                "cash": self.cash,
                "buying_power": self.cash,
                "equity": self.equity,
                "last_equity": self.equity,
                "long_market_value": getattr(self, "_long_market_value", 0.0),
                "short_market_value": 0.0,
                "initial_margin": 0.0,
                "maintenance_margin": 0.0,
                "multiplier": 1.0,
            },
        )()

    def get_positions(self) -> List[Any]:
        self.mark_to_market()
        return [
            type(
                "Position",
                (),
                {
                    "symbol": p["symbol"],
                    "qty": p["qty"],
                    "qty_available": p["available_qty"],
                    "market_value": p["market_value"],
                    "current_price": p["current_price"],
                    "avg_entry_price": p["avg_entry_price"],
                },
            )()
            for p in self.positions.values()
            if p["qty"] > 0
        ]

    def get_orders(self) -> List[Any]:
        return []

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> Any:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        return type(
            "PortfolioHistory",
            (),
            {
                "timestamp": [now],
                "equity": [self.equity],
                "profit_loss": [0.0],
                "profit_loss_pct": [0.0],
                "base_value": self.initial_cash,
                "timeframe": timeframe or "1D",
            },
        )()

    def place_market_order(self, symbol: str, qty: int, side: Any) -> Any:
        symbol = symbol.upper()
        qty = int(qty)
        if qty <= 0:
            raise ValueError("Order quantity must be positive")

        side_value = getattr(side, "value", str(side)).upper()
        price = self._price(symbol)
        if price is None or price <= 0:
            raise Exception(f'{{"message": "no price available for {symbol}"}}')

        if side_value == "BUY":
            cost = qty * price
            if cost > self.cash + 1e-6:
                raise Exception(
                    f'{{"message": "insufficient buying power (requested: {cost}, available: {self.cash})"}}'
                )
            self.cash -= cost
            existing = self.positions.get(symbol)
            if existing:
                total_qty = existing["qty"] + qty
                avg = (
                    (existing["avg_entry_price"] * existing["qty"] + price * qty) / total_qty
                    if total_qty
                    else price
                )
                existing["qty"] = total_qty
                existing["available_qty"] = total_qty
                existing["avg_entry_price"] = avg
                existing["current_price"] = price
                existing["market_value"] = total_qty * price
            else:
                self.positions[symbol] = {
                    "symbol": symbol,
                    "qty": qty,
                    "available_qty": qty,
                    "avg_entry_price": price,
                    "current_price": price,
                    "market_value": qty * price,
                }
        elif side_value == "SELL":
            existing = self.positions.get(symbol)
            available = int(existing["qty"]) if existing else 0
            if available < qty:
                raise Exception(
                    f'{{"message": "insufficient qty available for order (requested: {qty}, available: {available})"}}'
                )
            self.cash += qty * price
            remaining = available - qty
            if remaining <= 0:
                del self.positions[symbol]
            else:
                existing["qty"] = remaining
                existing["available_qty"] = remaining
                existing["current_price"] = price
                existing["market_value"] = remaining * price
        else:
            raise ValueError(f"Unsupported side: {side_value}")

        self._order_seq += 1
        order = {
            "id": f"bt_order_{self._order_seq}",
            "symbol": symbol,
            "qty": qty,
            "side": side_value,
            "status": "filled",
            "filled_at": datetime.combine(self.as_of_date or date.today(), datetime.min.time()),
            "filled_price": price,
        }
        self.orders.append(order)
        self.mark_to_market()
        return type("Order", (), {"id": order["id"]})()
