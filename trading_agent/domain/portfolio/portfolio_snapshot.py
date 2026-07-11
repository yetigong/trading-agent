from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AccountSummary:
    portfolio_value: float = 0.0
    cash: float = 0.0
    buying_power: float = 0.0
    equity: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountSummary":
        return cls(
            portfolio_value=float(data.get("portfolio_value", 0)),
            cash=float(data.get("cash", 0)),
            buying_power=float(data.get("buying_power", 0)),
            equity=float(data.get("equity", 0)),
        )


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    available_qty: float = 0.0
    market_value: float = 0.0
    current_price: float = 0.0
    avg_entry_price: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        return cls(
            symbol=str(data.get("symbol", "")),
            qty=float(data.get("qty", 0)),
            available_qty=float(data.get("available_qty", data.get("qty", 0))),
            market_value=float(data.get("market_value", 0)),
            current_price=float(data.get("current_price", 0)),
            avg_entry_price=float(data.get("avg_entry_price", 0)),
        )


@dataclass
class OpenOrder:
    order_id: str
    symbol: str
    side: str
    qty: float
    status: str = "open"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenOrder":
        return cls(
            order_id=str(data.get("order_id", "")),
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "")),
            qty=float(data.get("qty", 0)),
            status=str(data.get("status", "open")),
        )


@dataclass
class PortfolioSnapshot:
    account: AccountSummary = field(default_factory=AccountSummary)
    positions: List[Position] = field(default_factory=list)
    open_orders: List[OpenOrder] = field(default_factory=list)
    timestamp: Optional[datetime] = None

    def position_for(self, symbol: str) -> Optional[Position]:
        for pos in self.positions:
            if pos.symbol == symbol:
                return pos
        return None

    def open_order_for(self, symbol: str, action: str) -> Optional[OpenOrder]:
        opposite = "sell" if action.upper() == "BUY" else "buy"
        for order in self.open_orders:
            if order.symbol == symbol and order.side.lower() == opposite:
                return order
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortfolioSnapshot":
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            account=AccountSummary.from_dict(data.get("account") or {}),
            positions=[Position.from_dict(p) for p in data.get("positions") or []],
            open_orders=[OpenOrder.from_dict(o) for o in data.get("open_orders") or []],
            timestamp=ts,
        )

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Backward-compatible thin portfolio dict for legacy callers."""
        return {
            "portfolio_value": self.account.portfolio_value,
            "cash": self.account.cash,
            "buying_power": self.account.buying_power,
            "positions": [p.symbol for p in self.positions],
            "timestamp": self.timestamp,
        }
