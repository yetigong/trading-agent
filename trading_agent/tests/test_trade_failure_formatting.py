import unittest

from trading_agent.models import format_trade_failure, trade_result_detail


class TestTradeFailureFormatting(unittest.TestCase):
    def test_format_insufficient_qty(self):
        error = (
            '{"available":"20","code":40310000,"existing_qty":"20",'
            '"message":"insufficient qty available for order (requested: 200, available: 20)",'
            '"symbol":"PFE"}'
        )
        detail = format_trade_failure(error)
        self.assertIn("insufficient qty", detail)
        self.assertIn("owned: 20", detail)
        self.assertIn("available: 20", detail)

    def test_format_insufficient_buying_power(self):
        error = (
            '{"buying_power":"3388.32","code":40310000,"cost_basis":"27032.36",'
            '"message":"insufficient buying power"}'
        )
        detail = format_trade_failure(error)
        self.assertIn("insufficient buying power", detail)
        self.assertIn("buying_power: $3388.32", detail)

    def test_trade_result_detail_failed(self):
        trade = {
            "status": "failed",
            "error": '{"message":"insufficient buying power","buying_power":"100"}',
            "failure_detail": "insufficient buying power (buying_power: $100)",
        }
        self.assertEqual(trade_result_detail(trade), "insufficient buying power (buying_power: $100)")

    def test_trade_result_detail_executed(self):
        trade = {"status": "executed", "order_id": "abc-123"}
        self.assertEqual(trade_result_detail(trade), "order_id=abc-123")


if __name__ == "__main__":
    unittest.main()
