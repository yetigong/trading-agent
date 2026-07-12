import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from trading_agent.account.aggregation import aggregate_history
from trading_agent.account.query_resolver import resolve_history_request
from trading_agent.broker.base import BrokerClient
from trading_agent.domain.account.account_history import (
    AccountHistoryPoint,
    AccountHistoryQuery,
    AccountHistoryResult,
    AccountSnapshot,
)
from trading_agent.domain.broker import PortfolioHistory

logger = logging.getLogger(__name__)


class AccountHistoryFetcher:
    """Fetch current account state and portfolio equity history from a broker client."""

    def fetch(
        self,
        broker_client: BrokerClient,
        query: Optional[AccountHistoryQuery] = None,
    ) -> AccountHistoryResult:
        query = query or AccountHistoryQuery()
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            resolved = resolve_history_request(query)
            account = broker_client.get_account()
            snapshot = AccountSnapshot.from_broker_account(account)
            history_payload = broker_client.get_portfolio_history(
                period=resolved.period,
                timeframe=resolved.timeframe,
                date_end=resolved.date_end,
                extended_hours=resolved.extended_hours,
            )
            history, base_value, timeframe = self._parse_history(history_payload)
            if resolved.group_by:
                history = aggregate_history(history, resolved.group_by)
                timeframe = f"{timeframe or '1D'}-{resolved.group_by}"

            period_change, period_change_pct = self._compute_period_change(history, base_value)

            return AccountHistoryResult(
                status="success",
                snapshot=snapshot,
                history=history,
                query=query,
                base_value=base_value,
                timeframe=timeframe,
                group_by=resolved.group_by,
                period_change=period_change,
                period_change_pct=period_change_pct,
                timestamp=timestamp,
            )
        except Exception as exc:
            logger.error("Failed to fetch account history: %s", exc)
            return AccountHistoryResult(
                status="error",
                query=query,
                error=str(exc),
                timestamp=timestamp,
            )

    def _parse_history(
        self, payload: PortfolioHistory
    ) -> tuple[List[AccountHistoryPoint], float, str]:
        if payload is None:
            return [], 0.0, ""

        timestamps = list(payload.timestamps or [])
        equities = list(payload.equity or [])
        profit_losses = list(payload.profit_loss or [])
        profit_loss_pcts = list(payload.profit_loss_pct or [])
        base_value = float(payload.base_value or 0)
        timeframe = str(payload.timeframe or "")

        history: List[AccountHistoryPoint] = []
        for idx, ts in enumerate(timestamps):
            equity = float(equities[idx]) if idx < len(equities) else 0.0
            profit_loss = float(profit_losses[idx]) if idx < len(profit_losses) else 0.0
            profit_loss_pct = float(profit_loss_pcts[idx]) if idx < len(profit_loss_pcts) else 0.0
            history.append(
                AccountHistoryPoint(
                    timestamp=datetime.fromtimestamp(int(ts), tz=timezone.utc),
                    equity=equity,
                    profit_loss=profit_loss,
                    profit_loss_pct=profit_loss_pct,
                )
            )

        return history, base_value, timeframe

    def _compute_period_change(
        self,
        history: List[AccountHistoryPoint],
        base_value: float,
    ) -> tuple[float, float]:
        if not history:
            return 0.0, 0.0

        start_equity = history[0].equity
        end_equity = history[-1].equity
        period_change = end_equity - start_equity
        if base_value:
            period_change_pct = period_change / base_value
        elif start_equity:
            period_change_pct = period_change / start_equity
        else:
            period_change_pct = 0.0
        return period_change, period_change_pct
