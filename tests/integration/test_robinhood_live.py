import os
import unittest

from trading_agent.broker.robinhood_client import RobinhoodBrokerClient
from trading_agent.domain.broker import OrderSide

# TODO: Run live Robinhood E2E verification locally (account history CLI + optional
# order smoke + full cycle with LLM_PROVIDER=mock). Requires real credentials,
# ROBINHOOD_LIVE_TRADING_ACK=true, and pip install -r requirements-optional.txt.
# See docs/agents/multi-broker.md.


@unittest.skipUnless(
    os.getenv("ROBINHOOD_USERNAME")
    and os.getenv("ROBINHOOD_PASSWORD")
    and os.getenv("ROBINHOOD_LIVE_TRADING_ACK", "").lower() in ("1", "true", "yes"),
    "Robinhood live credentials and ROBINHOOD_LIVE_TRADING_ACK not set",
)
class TestRobinhoodLive(unittest.TestCase):
    def test_account_and_positions_smoke(self):
        client = RobinhoodBrokerClient()
        account = client.get_account()
        self.assertGreaterEqual(account.equity, 0.0)
        positions = client.get_positions()
        self.assertIsInstance(positions, list)

    @unittest.skipUnless(
        os.getenv("ROBINHOOD_PLACE_TEST_ORDER", "").lower() in ("1", "true", "yes"),
        "Set ROBINHOOD_PLACE_TEST_ORDER=true to run live order smoke test",
    )
    def test_place_tiny_order_optional(self):
        client = RobinhoodBrokerClient()
        symbol = os.getenv("ROBINHOOD_TEST_SYMBOL", "AAPL")
        result = client.place_market_order(symbol, 1, OrderSide.BUY)
        self.assertTrue(result.order_id)


if __name__ == "__main__":
    unittest.main()
