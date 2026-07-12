"""Map broker-native SDK objects to domain broker models."""

from typing import Any, List, Optional

from trading_agent.domain.broker import (
    BrokerAccount,
    BrokerOrder,
    BrokerOrderResult,
    BrokerPosition,
    OrderSide,
    OrderStatus,
    PortfolioHistory,
)


def _side_from_raw(side: Any) -> OrderSide:
    value = getattr(side, "value", str(side)).strip().lower()
    if value in {"buy", "b"}:
        return OrderSide.BUY
    return OrderSide.SELL


def map_alpaca_account(account: Any) -> BrokerAccount:
    equity = float(getattr(account, "equity", getattr(account, "portfolio_value", 0)) or 0)
    portfolio_value = float(
        getattr(account, "portfolio_value", getattr(account, "equity", 0)) or 0
    )
    return BrokerAccount(
        account_id=str(getattr(account, "id", "")),
        account_number=str(getattr(account, "account_number", "")),
        status=str(getattr(account, "status", "")),
        currency=str(getattr(account, "currency", "USD")),
        cash=float(getattr(account, "cash", 0) or 0),
        equity=equity,
        portfolio_value=portfolio_value,
        buying_power=float(getattr(account, "buying_power", 0) or 0),
        last_equity=float(getattr(account, "last_equity", equity) or 0),
        long_market_value=float(getattr(account, "long_market_value", 0) or 0),
        short_market_value=float(getattr(account, "short_market_value", 0) or 0),
        initial_margin=float(getattr(account, "initial_margin", 0) or 0),
        maintenance_margin=float(getattr(account, "maintenance_margin", 0) or 0),
        multiplier=float(getattr(account, "multiplier", 1) or 1),
    )


def map_alpaca_position(position: Any) -> BrokerPosition:
    qty = float(getattr(position, "qty", 0) or 0)
    available = float(
        getattr(position, "qty_available", getattr(position, "available_qty", qty)) or qty
    )
    return BrokerPosition(
        symbol=str(getattr(position, "symbol", "")),
        qty=qty,
        available_qty=available,
        market_value=float(getattr(position, "market_value", 0) or 0),
        current_price=float(getattr(position, "current_price", 0) or 0),
        avg_entry_price=float(getattr(position, "avg_entry_price", 0) or 0),
    )


def map_alpaca_order(order: Any) -> BrokerOrder:
    return BrokerOrder(
        order_id=str(getattr(order, "id", "")),
        symbol=str(getattr(order, "symbol", "")),
        side=_side_from_raw(getattr(order, "side", "")),
        qty=float(getattr(order, "qty", 0) or 0),
        status=OrderStatus.from_raw(str(getattr(order, "status", ""))),
    )


def map_alpaca_order_result(order: Any, *, symbol: str, qty: float, side: OrderSide) -> BrokerOrderResult:
    return BrokerOrderResult(
        order_id=str(getattr(order, "id", "")),
        symbol=symbol,
        side=side,
        qty=qty,
        status=OrderStatus.from_raw(str(getattr(order, "status", "filled"))),
    )


def map_alpaca_portfolio_history(payload: Any) -> PortfolioHistory:
    if payload is None:
        return PortfolioHistory()
    return PortfolioHistory(
        timestamps=[int(ts) for ts in (getattr(payload, "timestamp", None) or [])],
        equity=[float(v) for v in (getattr(payload, "equity", None) or [])],
        profit_loss=[float(v) for v in (getattr(payload, "profit_loss", None) or [])],
        profit_loss_pct=[float(v) for v in (getattr(payload, "profit_loss_pct", None) or [])],
        base_value=float(getattr(payload, "base_value", 0) or 0),
        timeframe=str(getattr(payload, "timeframe", "") or ""),
    )


def map_robinhood_account(profile: dict, account_data: Optional[dict] = None) -> BrokerAccount:
    account_data = account_data or {}
    equity = float(profile.get("equity") or account_data.get("equity") or 0)
    cash = float(
        profile.get("cash")
        or account_data.get("cash")
        or profile.get("withdrawable_amount")
        or 0
    )
    buying_power = float(
        profile.get("buying_power")
        or account_data.get("buying_power")
        or cash
    )
    return BrokerAccount(
        account_id=str(profile.get("id") or profile.get("user_id") or ""),
        account_number=str(profile.get("account_number") or ""),
        status=str(profile.get("status") or "ACTIVE"),
        currency="USD",
        cash=cash,
        equity=equity,
        portfolio_value=equity,
        buying_power=buying_power,
        last_equity=float(profile.get("last_equity") or equity),
        long_market_value=float(profile.get("long_market_value") or 0),
    )


def map_robinhood_position(position: dict) -> BrokerPosition:
    symbol = str(position.get("symbol") or "")
    qty = float(position.get("quantity") or position.get("shares_held_for_buys") or 0)
    if qty == 0:
        qty = float(position.get("shares_held") or 0)
    current_price = float(position.get("last_trade_price") or position.get("current_price") or 0)
    avg_entry = float(position.get("average_buy_price") or position.get("avg_entry_price") or 0)
    market_value = float(position.get("equity") or (qty * current_price))
    return BrokerPosition(
        symbol=symbol,
        qty=qty,
        available_qty=qty,
        market_value=market_value,
        current_price=current_price,
        avg_entry_price=avg_entry,
    )


def map_robinhood_order(order: dict) -> BrokerOrder:
    state = str(order.get("state") or order.get("status") or "open")
    side_raw = str(order.get("side") or "").lower()
    return BrokerOrder(
        order_id=str(order.get("id") or ""),
        symbol=str(order.get("symbol") or ""),
        side=OrderSide.BUY if side_raw == "buy" else OrderSide.SELL,
        qty=float(order.get("quantity") or order.get("cumulative_quantity") or 0),
        status=OrderStatus.from_raw(state),
    )


def map_robinhood_order_result(order: dict, *, symbol: str, qty: float, side: OrderSide) -> BrokerOrderResult:
    state = str(order.get("state") or order.get("status") or "filled")
    return BrokerOrderResult(
        order_id=str(order.get("id") or ""),
        symbol=symbol,
        side=side,
        qty=qty,
        status=OrderStatus.from_raw(state),
    )


def map_robinhood_portfolio_history(history: Any) -> PortfolioHistory:
    if not history:
        return PortfolioHistory()
    if isinstance(history, dict):
        points = (
            history.get("equity_historicals")
            or history.get("equity_history")
            or history.get("data")
            or []
        )
        if isinstance(points, dict):
            points = [points]
        timestamps: List[int] = []
        equities: List[float] = []
        for point in points:
            if not isinstance(point, dict):
                continue
            ts = point.get("timestamp") or point.get("begins_at")
            if ts is None:
                continue
            if isinstance(ts, str):
                from datetime import datetime

                try:
                    ts_val = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    continue
            else:
                ts_val = int(ts)
            equity = point.get("equity") or point.get("close_equity") or point.get("adjusted_equity")
            if equity is None:
                continue
            timestamps.append(ts_val)
            equities.append(float(equity))
        return PortfolioHistory(
            timestamps=timestamps,
            equity=equities,
            base_value=equities[0] if equities else 0.0,
            timeframe=str(history.get("timeframe") or ""),
        )
    return map_alpaca_portfolio_history(history)


def broker_account_to_snapshot_fields(account: BrokerAccount) -> BrokerAccount:
    return account


def positions_from_broker(positions: List[BrokerPosition]) -> List[BrokerPosition]:
    return [p for p in positions if p.qty > 0]
