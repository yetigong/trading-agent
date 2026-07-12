import logging
from datetime import datetime
from typing import List

from trading_agent.broker.base import BrokerClient
from trading_agent.domain.broker import BrokerOrder, OrderStatus
from trading_agent.domain.portfolio.portfolio_snapshot import (
    AccountSummary,
    OpenOrder,
    PortfolioSnapshot,
    Position,
)

logger = logging.getLogger(__name__)

_OPEN_STATUSES = {
    OrderStatus.OPEN,
    OrderStatus.NEW,
    OrderStatus.ACCEPTED,
    OrderStatus.PENDING_NEW,
    OrderStatus.PARTIALLY_FILLED,
}


class PortfolioSnapshotBuilder:
    """Build a rich portfolio snapshot from a broker client."""

    def build(self, broker_client: BrokerClient) -> PortfolioSnapshot:
        account = broker_client.get_account()
        positions = broker_client.get_positions()
        open_orders = self._get_open_orders(broker_client)

        account_summary = AccountSummary(
            portfolio_value=float(account.portfolio_value),
            cash=float(account.cash),
            buying_power=float(account.buying_power or account.cash),
            equity=float(account.equity or account.portfolio_value),
        )

        position_models: List[Position] = []
        for pos in positions:
            position_models.append(
                Position(
                    symbol=pos.symbol,
                    qty=float(pos.qty),
                    available_qty=float(pos.available_qty or pos.qty),
                    market_value=float(pos.market_value),
                    current_price=float(pos.current_price),
                    avg_entry_price=float(pos.avg_entry_price),
                )
            )

        return PortfolioSnapshot(
            account=account_summary,
            positions=position_models,
            open_orders=open_orders,
            timestamp=datetime.now(),
        )

    def _get_open_orders(self, broker_client: BrokerClient) -> List[OpenOrder]:
        try:
            orders = broker_client.get_orders()
        except Exception as exc:
            logger.warning("Could not fetch open orders: %s", exc)
            return []

        open_orders: List[OpenOrder] = []
        for order in orders or []:
            if not self._is_open_order(order):
                continue
            open_orders.append(
                OpenOrder(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    qty=float(order.qty),
                    status=order.status.value,
                )
            )
        return open_orders

    @staticmethod
    def _is_open_order(order: BrokerOrder) -> bool:
        return order.status in _OPEN_STATUSES
