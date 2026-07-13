import unittest

from trading_agent.domain.cycle import TradingDecision
from trading_agent.strategies.general import GeneralTradingStrategy


class TestStrategyValidation(unittest.TestCase):
    def setUp(self):
        self.strategy = GeneralTradingStrategy(llm_client=object())

    def test_drops_invalid_action(self):
        decisions = [
            TradingDecision("HOLD", "AAPL", 1, source="strategy"),
            TradingDecision("BUY", "MSFT", 2, source="strategy"),
        ]
        result = self.strategy.validate_decisions(decisions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].symbol, "MSFT")

    def test_drops_empty_symbol(self):
        decisions = [
            TradingDecision("BUY", "", 1, source="strategy"),
            TradingDecision("SELL", "AAPL", 1, source="strategy"),
        ]
        result = self.strategy.validate_decisions(decisions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].symbol, "AAPL")

    def test_drops_non_positive_quantity(self):
        decisions = [
            TradingDecision("BUY", "AAPL", 0, source="strategy"),
            TradingDecision("BUY", "MSFT", -5, source="strategy"),
            TradingDecision("SELL", "GOOG", 3, source="strategy"),
        ]
        result = self.strategy.validate_decisions(decisions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].symbol, "GOOG")
        self.assertEqual(result[0].quantity, 3)

    def test_allows_sell_all(self):
        decisions = [TradingDecision("SELL", "AAPL", "ALL", source="strategy")]
        result = self.strategy.validate_decisions(decisions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].quantity, "ALL")

    def test_normalizes_invalid_risk_level(self):
        decisions = [TradingDecision("BUY", "AAPL", 1, risk_level="extreme", source="strategy")]
        result = self.strategy.validate_decisions(decisions)
        self.assertEqual(result[0].risk_level, "medium")


if __name__ == "__main__":
    unittest.main()
