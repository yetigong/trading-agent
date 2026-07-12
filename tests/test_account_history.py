import unittest
from datetime import datetime, timezone

from trading_agent.broker.mock_client import MockAlpacaTradingClient
from trading_agent.account.aggregation import aggregate_history
from trading_agent.account.history_fetcher import AccountHistoryFetcher
from trading_agent.account.query_resolver import resolve_history_request
from trading_agent.domain.account.account_history import (
    AccountHistoryPoint,
    AccountHistoryQuery,
    AccountSnapshot,
)


class TestAccountHistoryFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = AccountHistoryFetcher()
        self.client = MockAlpacaTradingClient()

    def test_fetch_returns_snapshot_and_history(self):
        result = self.fetcher.fetch(self.client, AccountHistoryQuery(period="1M"))

        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.snapshot)
        self.assertEqual(result.snapshot.account_number, "MOCK0001")
        self.assertEqual(result.snapshot.equity, 100000.0)
        self.assertEqual(len(result.history), 3)
        self.assertEqual(result.history[-1].equity, 100000.0)
        self.assertEqual(result.timeframe, "1D")

    def test_period_change_is_computed(self):
        result = self.fetcher.fetch(self.client, AccountHistoryQuery(period="1M"))

        self.assertAlmostEqual(result.period_change, 2000.0)
        self.assertAlmostEqual(result.period_change_pct, 2000.0 / 98000.0)

    def test_to_dict_is_serializable(self):
        result = self.fetcher.fetch(self.client)
        payload = result.to_dict()

        self.assertEqual(payload["status"], "success")
        self.assertIn("snapshot", payload)
        self.assertIn("history", payload)
        self.assertEqual(payload["snapshot"]["margin_debt"], 0.0)

    def test_account_snapshot_margin_debt(self):
        snapshot = AccountSnapshot(
            cash=-89030.63,
            equity=150000.0,
            long_market_value=239030.63,
            last_equity=149000.0,
        )

        self.assertAlmostEqual(snapshot.margin_debt, 89030.63)
        self.assertAlmostEqual(snapshot.daily_equity_change, 1000.0)


class TestHistoryQueryResolver(unittest.TestCase):
    def test_year_alias_maps_to_alpaca_period(self):
        resolved = resolve_history_request(AccountHistoryQuery(period="1Y"))
        self.assertEqual(resolved.period, "1A")

    def test_monthly_timeframe_alias_enables_group_by(self):
        resolved = resolve_history_request(
            AccountHistoryQuery(period="1Y", timeframe="1M")
        )
        self.assertEqual(resolved.period, "1A")
        self.assertEqual(resolved.timeframe, "1D")
        self.assertEqual(resolved.group_by, "month")

    def test_invalid_timeframe_raises(self):
        with self.assertRaises(ValueError):
            resolve_history_request(AccountHistoryQuery(timeframe="2D"))


class TestMonthlyAggregation(unittest.TestCase):
    def test_aggregate_to_end_of_month_points(self):
        history = [
            AccountHistoryPoint(datetime(2025, 1, 10, tzinfo=timezone.utc), 100.0),
            AccountHistoryPoint(datetime(2025, 1, 31, tzinfo=timezone.utc), 110.0),
            AccountHistoryPoint(datetime(2025, 2, 15, tzinfo=timezone.utc), 115.0),
            AccountHistoryPoint(datetime(2025, 2, 28, tzinfo=timezone.utc), 120.0),
        ]

        monthly = aggregate_history(history, "month")

        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly[0].equity, 110.0)
        self.assertEqual(monthly[1].equity, 120.0)
        self.assertAlmostEqual(monthly[1].profit_loss, 10.0)


class TestAccountSnapshotFromBroker(unittest.TestCase):
    def test_from_broker_account_maps_fields(self):
        account = type(
            "Account",
            (),
            {
                "id": "abc",
                "account_number": "123",
                "status": "ACTIVE",
                "currency": "USD",
                "cash": "-1000",
                "equity": "5000",
                "portfolio_value": "5000",
                "buying_power": "2000",
                "last_equity": "4800",
                "long_market_value": "6000",
                "short_market_value": "0",
                "initial_margin": "3000",
                "maintenance_margin": "1500",
                "multiplier": "2",
            },
        )()

        snapshot = AccountSnapshot.from_broker_account(
            account,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(snapshot.account_id, "abc")
        self.assertEqual(snapshot.cash, -1000.0)
        self.assertEqual(snapshot.equity, 5000.0)
        self.assertEqual(snapshot.multiplier, 2.0)
        self.assertEqual(snapshot.margin_debt, 1000.0)


if __name__ == "__main__":
    unittest.main()
