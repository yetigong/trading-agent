import os
import unittest
from unittest.mock import MagicMock, patch

from trading_agent.broker.factory import build_broker_client, get_broker_client
from trading_agent.broker.mappers import map_alpaca_account, map_robinhood_account
from trading_agent.broker.mock_client import MockBrokerClient
from trading_agent.config import AppConfig, get_config, validate_broker_config, validate_robinhood_config


class TestBrokerFactory(unittest.TestCase):
    def test_get_mock_broker(self):
        broker = get_broker_client("mock")
        self.assertEqual(broker.provider_name, "mock")
        account = broker.get_account()
        self.assertEqual(account.account_id, "mock-account-id")

    def test_build_defaults_to_alpaca_provider(self):
        config = get_config()
        self.assertEqual(config.broker_provider, "alpaca")

    @patch.dict(os.environ, {"BROKER_PROVIDER": "mock"}, clear=False)
    def test_build_broker_client_mock(self):
        broker = build_broker_client(provider="mock")
        self.assertIsInstance(broker, MockBrokerClient)

    def test_validate_alpaca_config_missing_keys(self):
        config = AppConfig(
            llm_provider="mock",
            llm_model="financial",
            llm_fallback_provider=None,
            llm_fallback_model="financial",
            llm_max_retries=3,
            trading_cycle_interval=30,
            broker_provider="alpaca",
            alpaca_api_key="",
            alpaca_secret_key="",
            alpaca_paper=True,
            robinhood_username="",
            robinhood_password="",
            robinhood_mfa_secret="",
            robinhood_session_path="",
            robinhood_live_trading_ack=False,
            log_level="INFO",
        )
        with self.assertRaises(ValueError):
            validate_broker_config(config)

    def test_validate_robinhood_requires_ack(self):
        config = AppConfig(
            llm_provider="mock",
            llm_model="financial",
            llm_fallback_provider=None,
            llm_fallback_model="financial",
            llm_max_retries=3,
            trading_cycle_interval=30,
            broker_provider="robinhood",
            alpaca_api_key="k",
            alpaca_secret_key="s",
            alpaca_paper=True,
            robinhood_username="user",
            robinhood_password="pass",
            robinhood_mfa_secret="",
            robinhood_session_path="",
            robinhood_live_trading_ack=False,
            log_level="INFO",
        )
        with self.assertRaises(ValueError):
            validate_robinhood_config(config)


class TestBrokerMappers(unittest.TestCase):
    def test_map_alpaca_account(self):
        raw = MagicMock()
        raw.id = "acct-1"
        raw.account_number = "123"
        raw.status = "ACTIVE"
        raw.currency = "USD"
        raw.cash = 1000.0
        raw.equity = 5000.0
        raw.portfolio_value = 5000.0
        raw.buying_power = 4000.0
        raw.last_equity = 4800.0
        raw.long_market_value = 4000.0
        raw.short_market_value = 0.0
        raw.initial_margin = 0.0
        raw.maintenance_margin = 0.0
        raw.multiplier = 1.0

        account = map_alpaca_account(raw)
        self.assertEqual(account.account_id, "acct-1")
        self.assertEqual(account.equity, 5000.0)

    def test_map_robinhood_account(self):
        profile = {
            "id": "rh-1",
            "equity": "12000.50",
            "cash": "2500.25",
            "buying_power": "3000.00",
        }
        account = map_robinhood_account(profile)
        self.assertEqual(account.account_id, "rh-1")
        self.assertEqual(account.equity, 12000.50)
        self.assertEqual(account.buying_power, 3000.0)


if __name__ == "__main__":
    unittest.main()
