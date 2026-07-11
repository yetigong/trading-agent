import os
import unittest

from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

load_dotenv()


def _has_alpaca_keys() -> bool:
    return bool(os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"))


@unittest.skipUnless(_has_alpaca_keys(), "ALPACA_API_KEY and ALPACA_SECRET_KEY not set")
class TestAlpacaLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TradingClient(
            os.environ["ALPACA_API_KEY"],
            os.environ["ALPACA_SECRET_KEY"],
        )

    def test_account_is_reachable(self):
        account = self.client.get_account()
        self.assertIsNotNone(account.status)
        self.assertGreater(float(account.buying_power), 0)

    def test_assets_are_listed(self):
        assets = list(self.client.get_all_assets())
        self.assertGreater(len(assets), 0)
        self.assertTrue(any(asset.symbol for asset in assets))


if __name__ == "__main__":
    unittest.main()
