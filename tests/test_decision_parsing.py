import unittest

from trading_agent.models import parse_trading_decisions


class TestDecisionParsing(unittest.TestCase):
    def test_parse_json_decisions(self):
        response = """
        {
          "decisions": [
            {
              "action": "buy",
              "symbol": "aapl",
              "quantity": 5,
              "reasoning": "Strong momentum",
              "risk_level": "medium"
            }
          ]
        }
        """
        decisions = parse_trading_decisions(response)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["action"], "BUY")
        self.assertEqual(decisions[0]["symbol"], "AAPL")
        self.assertEqual(decisions[0]["quantity"], 5)

    def test_parse_empty_decisions_hold(self):
        response = '{"decisions": []}'
        decisions = parse_trading_decisions(response)
        self.assertEqual(decisions, [])

    def test_parse_json_in_markdown_fence(self):
        response = """Here are my decisions:
```json
{"decisions": [{"action": "SELL", "symbol": "MSFT", "quantity": "ALL", "reasoning": "Take profit", "risk_level": "low"}]}
```"""
        decisions = parse_trading_decisions(response)
        self.assertEqual(decisions[0]["action"], "SELL")
        self.assertEqual(decisions[0]["quantity"], "ALL")


if __name__ == "__main__":
    unittest.main()
