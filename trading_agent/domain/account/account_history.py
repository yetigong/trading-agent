from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AccountSnapshot:
    """Current Alpaca account state with margin-aware fields."""

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
    timestamp: Optional[datetime] = None

    @property
    def margin_debt(self) -> float:
        """Approximate borrowed cash when cash balance is negative."""
        return abs(self.cash) if self.cash < 0 else 0.0

    @property
    def daily_equity_change(self) -> float:
        return self.equity - self.last_equity

    @classmethod
    def from_broker_account(cls, account: Any, timestamp: Optional[datetime] = None) -> "AccountSnapshot":
        return cls(
            account_id=str(getattr(account, "id", "")),
            account_number=str(getattr(account, "account_number", "")),
            status=str(getattr(account, "status", "")),
            currency=str(getattr(account, "currency", "USD")),
            cash=float(getattr(account, "cash", 0)),
            equity=float(getattr(account, "equity", getattr(account, "portfolio_value", 0))),
            portfolio_value=float(getattr(account, "portfolio_value", getattr(account, "equity", 0))),
            buying_power=float(getattr(account, "buying_power", 0)),
            last_equity=float(getattr(account, "last_equity", 0)),
            long_market_value=float(getattr(account, "long_market_value", 0)),
            short_market_value=float(getattr(account, "short_market_value", 0)),
            initial_margin=float(getattr(account, "initial_margin", 0)),
            maintenance_margin=float(getattr(account, "maintenance_margin", 0)),
            multiplier=float(getattr(account, "multiplier", 1)),
            timestamp=timestamp or datetime.now(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "account_number": self.account_number,
            "status": self.status,
            "currency": self.currency,
            "cash": self.cash,
            "equity": self.equity,
            "portfolio_value": self.portfolio_value,
            "buying_power": self.buying_power,
            "last_equity": self.last_equity,
            "long_market_value": self.long_market_value,
            "short_market_value": self.short_market_value,
            "initial_margin": self.initial_margin,
            "maintenance_margin": self.maintenance_margin,
            "multiplier": self.multiplier,
            "margin_debt": self.margin_debt,
            "daily_equity_change": self.daily_equity_change,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class AccountHistoryPoint:
    timestamp: datetime
    equity: float
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
        }


@dataclass
class AccountHistoryQuery:
    period: str = "1M"
    timeframe: Optional[str] = None
    date_end: Optional[str] = None
    extended_hours: bool = False
    group_by: Optional[str] = None


@dataclass
class AccountHistoryResult:
    status: str
    snapshot: Optional[AccountSnapshot] = None
    history: List[AccountHistoryPoint] = field(default_factory=list)
    query: Optional[AccountHistoryQuery] = None
    base_value: float = 0.0
    timeframe: str = ""
    group_by: Optional[str] = None
    period_change: float = 0.0
    period_change_pct: float = 0.0
    error: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "history": [point.to_dict() for point in self.history],
            "query": {
                "period": self.query.period,
                "timeframe": self.query.timeframe,
                "date_end": self.query.date_end,
                "extended_hours": self.query.extended_hours,
                "group_by": self.query.group_by,
            }
            if self.query
            else None,
            "base_value": self.base_value,
            "timeframe": self.timeframe,
            "group_by": self.group_by,
            "period_change": self.period_change,
            "period_change_pct": self.period_change_pct,
            "error": self.error,
            "timestamp": self.timestamp,
        }
