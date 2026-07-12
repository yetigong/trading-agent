from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    OPEN = "open"
    NEW = "new"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"

    @classmethod
    def from_raw(cls, value: str) -> "OrderStatus":
        normalized = (value or "").strip().lower().replace("-", "_")
        for status in cls:
            if status.value == normalized:
                return status
        return cls.UNKNOWN


@dataclass
class BrokerAccount:
    account_id: str = ""
    account_number: str = ""
    status: str = ""
    currency: str = "USD"
    cash: float = 0.0
    equity: float = 0.0
    portfolio_value: float = 0.0
    buying_power: float = 0.0
    last_equity: float = 0.0
    long_market_value: float = 0.0
    short_market_value: float = 0.0
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    multiplier: float = 1.0


@dataclass
class BrokerPosition:
    symbol: str
    qty: float = 0.0
    available_qty: float = 0.0
    market_value: float = 0.0
    current_price: float = 0.0
    avg_entry_price: float = 0.0


@dataclass
class BrokerOrder:
    order_id: str
    symbol: str
    side: OrderSide
    qty: float
    status: OrderStatus = OrderStatus.OPEN


@dataclass
class BrokerOrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    qty: float
    status: OrderStatus = OrderStatus.FILLED


@dataclass
class PortfolioHistory:
    timestamps: List[int] = field(default_factory=list)
    equity: List[float] = field(default_factory=list)
    profit_loss: List[float] = field(default_factory=list)
    profit_loss_pct: List[float] = field(default_factory=list)
    base_value: float = 0.0
    timeframe: str = ""


class BrokerError(Exception):
    """Broker operation failed with a provider-specific error payload."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        provider: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.provider = provider
        self.details = details or {}

    def to_json(self) -> str:
        import json

        payload = {"message": self.message}
        if self.code:
            payload["code"] = self.code
        if self.provider:
            payload["provider"] = self.provider
        payload.update(self.details)
        return json.dumps(payload)
