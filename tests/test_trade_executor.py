import unittest
from unittest.mock import MagicMock

from trading_agent.broker.mock_client import MockAlpacaTradingClient
from trading_agent.domain.cycle import TradingDecision
from trading_agent.execution.executor import TradeExecutor


class TestTradeExecutor(unittest.TestCase):
    def test_execute_success(self):
        broker = MockAlpacaTradingClient()
        executor = TradeExecutor(broker)
        decisions = [TradingDecision("BUY", "AAPL", 1, source="strategy")]

        results = executor.execute(decisions)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "executed")
        self.assertEqual(results[0].symbol, "AAPL")
        self.assertEqual(results[0].quantity, 1)
        self.assertIsNotNone(results[0].order_id)

    def test_sell_all_with_position(self):
        broker = MockAlpacaTradingClient()
        executor = TradeExecutor(broker)
        decisions = [TradingDecision("SELL", "AAPL", "ALL", source="strategy")]

        results = executor.execute(decisions)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "executed")
        self.assertEqual(results[0].quantity, 1)
        self.assertEqual(results[0].action, "SELL")

    def test_sell_all_without_position(self):
        broker = MockAlpacaTradingClient()
        executor = TradeExecutor(broker)
        decisions = [TradingDecision("SELL", "SMCI", "ALL", source="strategy")]

        results = executor.execute(decisions)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "skipped")
        self.assertIn("No position", results[0].failure_detail)

    def test_broker_exception_marks_failed(self):
        broker = MagicMock()
        broker.place_market_order.side_effect = Exception(
            '{"code": 40310000, "message": "insufficient buying power"}'
        )
        executor = TradeExecutor(broker)
        decisions = [TradingDecision("BUY", "AAPL", 10, source="strategy")]

        results = executor.execute(decisions)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "failed")
        self.assertIsNotNone(results[0].failure_detail)
        self.assertIn("buying power", results[0].failure_detail.lower())


if __name__ == "__main__":
    unittest.main()
