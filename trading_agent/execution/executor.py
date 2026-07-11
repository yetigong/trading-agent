import logging
from typing import Any, List

from alpaca.trading.enums import OrderSide

from trading_agent.domain.cycle import ExecutedTrade, TradingDecision
from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.models import format_trade_failure

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Submit validated trades to the broker."""

    def __init__(self, broker_client: Any, snapshot_builder=None):
        self.broker_client = broker_client
        self.snapshot_builder = snapshot_builder

    def execute(self, decisions: List[TradingDecision]) -> List[ExecutedTrade]:
        results: List[ExecutedTrade] = []

        for decision in decisions:
            try:
                quantity = decision.quantity
                if quantity == "ALL":
                    positions = self.broker_client.get_positions()
                    position = next(
                        (p for p in positions if p.symbol == decision.symbol),
                        None,
                    )
                    if not position or float(getattr(position, "qty", 0)) <= 0:
                        results.append(
                            ExecutedTrade(
                                symbol=decision.symbol,
                                action=decision.action,
                                quantity=decision.quantity,
                                status="skipped",
                                failure_detail="No position found to sell ALL",
                            )
                        )
                        continue
                    quantity = int(float(position.qty))

                order = self.broker_client.place_market_order(
                    symbol=decision.symbol,
                    qty=quantity,
                    side=OrderSide.BUY if decision.action == "BUY" else OrderSide.SELL,
                )
                results.append(
                    ExecutedTrade(
                        symbol=decision.symbol,
                        action=decision.action,
                        quantity=quantity,
                        status="executed",
                        order_id=str(order.id),
                    )
                )
            except Exception as exc:
                error_str = str(exc)
                results.append(
                    ExecutedTrade(
                        symbol=decision.symbol,
                        action=decision.action,
                        quantity=decision.quantity,
                        status="failed",
                        error=error_str,
                        failure_detail=format_trade_failure(error_str),
                    )
                )

        return results
