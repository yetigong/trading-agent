import unittest

from trading_agent.domain.cycle import TradingDecision
from trading_agent.domain.portfolio.portfolio_snapshot import (
    AccountSummary,
    PortfolioSnapshot,
    Position,
)
from trading_agent.execution.consolidator import TradeConsolidator
from trading_agent.execution.validator import TradeValidator


class TestTradeConsolidator(unittest.TestCase):
    def test_merge_duplicate_sells(self):
        consolidator = TradeConsolidator()
        decisions = [
            TradingDecision("SELL", "SMCI", "ALL", source="strategy"),
            TradingDecision("SELL", "SMCI", 80, source="rebalancer"),
        ]
        result = consolidator.consolidate(decisions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].symbol, "SMCI")
        self.assertEqual(result[0].action, "SELL")
        self.assertEqual(result[0].quantity, "ALL")

    def test_net_buy_and_sell(self):
        consolidator = TradeConsolidator()
        decisions = [
            TradingDecision("BUY", "CRM", 10, source="strategy"),
            TradingDecision("SELL", "CRM", 3, source="rebalancer"),
        ]
        result = consolidator.consolidate(decisions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].action, "BUY")
        self.assertEqual(result[0].quantity, 7)


class TestTradeValidator(unittest.TestCase):
    def setUp(self):
        self.portfolio = PortfolioSnapshot(
            account=AccountSummary(
                portfolio_value=100000,
                cash=50000,
                buying_power=50000,
                equity=100000,
            ),
            positions=[
                Position(symbol="CRM", qty=3, available_qty=3, current_price=100, market_value=300),
                Position(symbol="AVGO", qty=5, available_qty=5, current_price=200, market_value=1000),
            ],
        )
        self.validator = TradeValidator()

    def test_clip_sell_to_available(self):
        decisions = [TradingDecision("SELL", "CRM", 150, source="strategy")]
        result = self.validator.validate(decisions, self.portfolio)
        self.assertEqual(len(result.executable), 1)
        self.assertEqual(result.executable[0].quantity, 3)
        self.assertEqual(len(result.adjusted), 1)

    def test_skip_sell_with_no_position(self):
        decisions = [TradingDecision("SELL", "SMCI", "ALL", source="strategy")]
        result = self.validator.validate(decisions, self.portfolio)
        self.assertEqual(len(result.executable), 0)
        self.assertEqual(len(result.skipped), 1)

    def test_clip_buy_to_buying_power(self):
        decisions = [TradingDecision("BUY", "CRM", 1000, source="strategy")]
        result = self.validator.validate(decisions, self.portfolio)
        self.assertEqual(len(result.executable), 1)
        # 97 = min(1000 requested, 500 affordable, 97 max position size headroom for existing CRM)
        self.assertEqual(result.executable[0].quantity, 97)
        self.assertEqual(len(result.adjusted), 1)

    def test_sells_before_buys(self):
        decisions = [
            TradingDecision("BUY", "AAPL", 1, source="strategy"),
            TradingDecision("SELL", "AVGO", 2, source="strategy"),
        ]
        result = self.validator.validate(decisions, self.portfolio)
        self.assertEqual(result.executable[0].action, "SELL")
        self.assertEqual(result.executable[1].action, "BUY")


if __name__ == "__main__":
    unittest.main()
