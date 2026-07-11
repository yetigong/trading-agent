import logging
from datetime import datetime
from typing import Any, List, Optional

from trading_agent.domain.portfolio.portfolio_snapshot import (
    AccountSummary,
    OpenOrder,
    PortfolioSnapshot,
    Position,
)

logger = logging.getLogger(__name__)


class PortfolioSnapshotBuilder:
    """Build a rich portfolio snapshot from a broker client."""

    def build(self, broker_client: Any) -> PortfolioSnapshot:
        account = broker_client.get_account()
        positions = broker_client.get_positions()
        open_orders = self._get_open_orders(broker_client)

        account_summary = AccountSummary(
            portfolio_value=float(getattr(account, "portfolio_value", 0)),
            cash=float(getattr(account, "cash", 0)),
            buying_power=float(getattr(account, "buying_power", getattr(account, "cash", 0))),
            equity=float(getattr(account, "equity", getattr(account, "portfolio_value", 0))),
        )

        position_models: List[Position] = []
        for pos in positions:
            qty = float(getattr(pos, "qty", 0))
            available = float(getattr(pos, "qty_available", getattr(pos, "available_qty", qty)))
            position_models.append(
                Position(
                    symbol=str(getattr(pos, "symbol", "")),
                    qty=qty,
                    available_qty=available,
                    market_value=float(getattr(pos, "market_value", 0)),
                    current_price=float(getattr(pos, "current_price", 0)),
                    avg_entry_price=float(getattr(pos, "avg_entry_price", 0)),
                )
            )

        return PortfolioSnapshot(
            account=account_summary,
            positions=position_models,
            open_orders=open_orders,
            timestamp=datetime.now(),
        )

    def _get_open_orders(self, broker_client: Any) -> List[OpenOrder]:
        if not hasattr(broker_client, "get_orders"):
            return []

        try:
            orders = broker_client.get_orders()
        except Exception as exc:
            logger.warning("Could not fetch open orders: %s", exc)
            return []

        open_orders: List[OpenOrder] = []
        for order in orders or []:
            status = str(getattr(order, "status", "")).lower()
            if status not in {"new", "accepted", "pending_new", "partially_filled", "open"}:
                continue
            side = getattr(order, "side", "")
            side_value = getattr(side, "value", str(side)).lower()
            open_orders.append(
                OpenOrder(
                    order_id=str(getattr(order, "id", "")),
                    symbol=str(getattr(order, "symbol", "")),
                    side=side_value,
                    qty=float(getattr(order, "qty", 0)),
                    status=status,
                )
            )
        return open_orders
