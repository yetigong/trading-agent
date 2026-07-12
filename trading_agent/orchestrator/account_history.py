import logging
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

from trading_agent.broker.factory import build_broker_client
from trading_agent.account.history_fetcher import AccountHistoryFetcher
from trading_agent.config import config_summary, get_config, validate_broker_config
from trading_agent.domain.account.account_history import AccountHistoryQuery

logger = logging.getLogger(__name__)


class AccountHistoryMode:
    """Read-only mode that fetches account snapshot and portfolio equity history."""

    def __init__(self, query: Optional[AccountHistoryQuery] = None):
        load_dotenv()
        self.config = get_config()
        self.query = query or AccountHistoryQuery()
        self.fetcher = AccountHistoryFetcher()
        self.logger = logging.getLogger(__name__)

    def execute(self) -> dict:
        started_at = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info("Starting account history fetch at %s", started_at)
        self.logger.info("Config: %s", config_summary(self.config))
        self.logger.info(
            "Query: period=%s timeframe=%s group_by=%s date_end=%s extended_hours=%s",
            self.query.period,
            self.query.timeframe,
            self.query.group_by,
            self.query.date_end,
            self.query.extended_hours,
        )
        self.logger.info("=" * 80)

        try:
            validate_broker_config(self.config)
            broker_client = build_broker_client(config=self.config)
            result = self.fetcher.fetch(broker_client, self.query)
            payload = result.to_dict()

            if result.status == "success" and result.snapshot:
                snapshot = result.snapshot
                self.logger.info("Account %s (%s)", snapshot.account_number, snapshot.status)
                self.logger.info("Equity: $%s", f"{snapshot.equity:,.2f}")
                self.logger.info("Cash: $%s", f"{snapshot.cash:,.2f}")
                if snapshot.margin_debt:
                    self.logger.info("Margin debt (negative cash): $%s", f"{snapshot.margin_debt:,.2f}")
                self.logger.info("Daily equity change: $%s", f"{snapshot.daily_equity_change:,.2f}")
                self.logger.info("History points: %d", len(result.history))
                self.logger.info(
                    "Period change: $%s (%.2f%%)",
                    f"{result.period_change:,.2f}",
                    result.period_change_pct * 100,
                )

            return payload
        except Exception as exc:
            self.logger.error("Account history fetch failed: %s", exc)
            return {
                "status": "error",
                "error": str(exc),
                "timestamp": datetime.now().isoformat(),
            }
