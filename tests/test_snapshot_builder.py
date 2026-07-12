import unittest

from trading_agent.broker.base import BrokerClient
from trading_agent.broker.mock_client import MockBrokerClient
from trading_agent.domain.broker import BrokerAccount, BrokerPosition, PortfolioHistory
from trading_agent.execution.snapshot_builder import PortfolioSnapshotBuilder


class _BrokerWithoutOrders:
    """Minimal broker stub without open orders."""

    provider_name = "stub"

    def get_account(self) -> BrokerAccount:
        return BrokerAccount(
            portfolio_value=100000.0,
            cash=50000.0,
            buying_power=50000.0,
            equity=100000.0,
        )

    def get_positions(self):
        return [
            BrokerPosition(
                symbol="AAPL",
                qty=5,
                available_qty=4,
                market_value=1000.0,
                current_price=200.0,
                avg_entry_price=180.0,
            )
        ]

    def get_orders(self):
        return []

    def place_market_order(self, symbol, qty, side):
        raise NotImplementedError

    def get_portfolio_history(self, **kwargs) -> PortfolioHistory:
        return PortfolioHistory()


class TestPortfolioSnapshotBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = PortfolioSnapshotBuilder()

    def test_build_maps_account_and_positions(self):
        broker = MockBrokerClient()
        snapshot = self.builder.build(broker)

        self.assertEqual(snapshot.account.portfolio_value, 100000.0)
        self.assertEqual(snapshot.account.buying_power, 50000.0)
        self.assertEqual(len(snapshot.positions), 1)
        self.assertEqual(snapshot.positions[0].symbol, "AAPL")
        self.assertEqual(snapshot.positions[0].qty, 1)
        self.assertEqual(snapshot.positions[0].available_qty, 1)

    def test_maps_qty_available(self):
        broker = _BrokerWithoutOrders()
        snapshot = self.builder.build(broker)

        self.assertEqual(snapshot.positions[0].available_qty, 4)
        self.assertEqual(snapshot.positions[0].avg_entry_price, 180.0)

    def test_filters_open_orders_by_status(self):
        broker = MockBrokerClient()
        broker.orders = [
            {"id": "1", "symbol": "AAPL", "side": "BUY", "qty": 1, "status": "new"},
            {"id": "2", "symbol": "MSFT", "side": "SELL", "qty": 2, "status": "filled"},
            {"id": "3", "symbol": "GOOG", "side": "BUY", "qty": 3, "status": "accepted"},
        ]
        snapshot = self.builder.build(broker)

        self.assertEqual(len(snapshot.open_orders), 2)
        symbols = {o.symbol for o in snapshot.open_orders}
        self.assertEqual(symbols, {"AAPL", "GOOG"})

    def test_empty_open_orders_when_get_orders_missing(self):
        broker = _BrokerWithoutOrders()
        snapshot = self.builder.build(broker)

        self.assertEqual(snapshot.open_orders, [])


if __name__ == "__main__":
    unittest.main()
