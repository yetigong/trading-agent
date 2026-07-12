import logging
import os
from typing import Optional

from trading_agent.broker.alpaca_client import AlpacaBrokerClient
from trading_agent.broker.base import BrokerClient
from trading_agent.broker.mock_client import MockBrokerClient
from trading_agent.config import AppConfig, get_config
from trading_agent.domain.user.brokerage_config import BrokerageConfig

logger = logging.getLogger(__name__)

__all__ = [
    "BrokerClient",
    "build_broker_client",
    "get_broker_client",
]

_CLIENTS = {
    "alpaca": AlpacaBrokerClient,
    "mock": MockBrokerClient,
}


def _resolve_provider(
    provider: Optional[str],
    config: Optional[AppConfig],
    brokerage_config: Optional[BrokerageConfig],
) -> str:
    if provider:
        return provider.lower()
    if config and config.broker_provider:
        return config.broker_provider.lower()
    if brokerage_config and brokerage_config.provider:
        return brokerage_config.provider.lower()
    return os.getenv("BROKER_PROVIDER", "alpaca").lower()


def get_broker_client(provider: str = "alpaca", **kwargs) -> BrokerClient:
    provider = (provider or "alpaca").lower()
    if provider == "robinhood":
        from trading_agent.broker.robinhood_client import RobinhoodBrokerClient

        return RobinhoodBrokerClient(**kwargs)
    if provider not in _CLIENTS:
        raise ValueError(
            f"Unsupported broker provider: {provider}. "
            f"Supported: {', '.join(list(_CLIENTS) + ['robinhood'])}"
        )
    return _CLIENTS[provider](**kwargs)


def build_broker_client(
    provider: Optional[str] = None,
    config: Optional[AppConfig] = None,
    brokerage_config: Optional[BrokerageConfig] = None,
) -> BrokerClient:
    """Build a broker client from env/config, mirroring build_llm_client()."""
    config = config or get_config()
    resolved = _resolve_provider(provider, config, brokerage_config)

    if resolved == "robinhood":
        logger.warning(
            "Robinhood broker selected. This uses unofficial APIs and real-money accounts only. "
            "See docs/agents/multi-broker.md for risks."
        )
        return get_broker_client(
            "robinhood",
            username=config.robinhood_username,
            password=config.robinhood_password,
            mfa_secret=config.robinhood_mfa_secret,
            session_path=config.robinhood_session_path,
            live_trading_ack=config.robinhood_live_trading_ack,
        )

    if resolved == "alpaca":
        return get_broker_client(
            "alpaca",
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            paper=config.alpaca_paper,
        )

    return get_broker_client(resolved)
