import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY_ENV = {
    "gemini": "GOOGLE_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "huggingface": "HUGGINGFACE_API_KEY",
    "mock": None,
}

SUPPORTED_BROKER_PROVIDERS = ("alpaca", "robinhood", "mock")


@dataclass(frozen=True)
class AppConfig:
    llm_provider: str
    llm_model: str
    llm_fallback_provider: Optional[str]
    llm_fallback_model: str
    llm_max_retries: int
    trading_cycle_interval: int
    broker_provider: str
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool
    robinhood_username: str
    robinhood_password: str
    robinhood_mfa_secret: str
    robinhood_session_path: str
    robinhood_live_trading_ack: bool
    log_level: str


def _normalize_fallback(raw: Optional[str]) -> Optional[str]:
    value = (raw or "").strip().lower()
    if not value or value in ("none", "off", "disabled"):
        return None
    return value


def get_config() -> AppConfig:
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "openai").lower(),
        llm_model=os.getenv("LLM_MODEL", "financial"),
        llm_fallback_provider=_normalize_fallback(
            os.getenv("LLM_FALLBACK_PROVIDER", "gemini")
        ),
        llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", "financial"),
        llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
        trading_cycle_interval=int(os.getenv("TRADING_CYCLE_INTERVAL", "30")),
        broker_provider=os.getenv("BROKER_PROVIDER", "alpaca").lower(),
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        alpaca_paper=os.getenv("ALPACA_PAPER", "true").lower() in ("1", "true", "yes"),
        robinhood_username=os.getenv("ROBINHOOD_USERNAME", ""),
        robinhood_password=os.getenv("ROBINHOOD_PASSWORD", ""),
        robinhood_mfa_secret=os.getenv("ROBINHOOD_MFA_SECRET", ""),
        robinhood_session_path=os.getenv("ROBINHOOD_SESSION_PATH", ""),
        robinhood_live_trading_ack=os.getenv("ROBINHOOD_LIVE_TRADING_ACK", "").lower()
        in ("1", "true", "yes"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


def validate_alpaca_config(config: AppConfig) -> None:
    """Validate Alpaca credentials only (no LLM keys required)."""
    missing: List[str] = []

    if not config.alpaca_api_key:
        missing.append("ALPACA_API_KEY")
    if not config.alpaca_secret_key:
        missing.append("ALPACA_SECRET_KEY")

    if missing:
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example and fill in your Alpaca credentials."
        )


def validate_robinhood_config(config: AppConfig) -> None:
    """Validate Robinhood credentials and live-trading acknowledgement."""
    missing: List[str] = []

    if not config.robinhood_username:
        missing.append("ROBINHOOD_USERNAME")
    if not config.robinhood_password:
        missing.append("ROBINHOOD_PASSWORD")
    if not config.robinhood_live_trading_ack:
        missing.append("ROBINHOOD_LIVE_TRADING_ACK=true")

    if missing:
        raise ValueError(
            "Missing required Robinhood configuration: "
            + ", ".join(missing)
            + ". Robinhood has no paper trading; see docs/agents/multi-broker.md."
        )


def validate_broker_config(config: AppConfig) -> None:
    """Validate credentials for the configured broker provider."""
    provider = (config.broker_provider or "alpaca").lower()
    if provider not in SUPPORTED_BROKER_PROVIDERS:
        raise ValueError(
            f"Unsupported BROKER_PROVIDER '{provider}'. "
            f"Supported: {', '.join(SUPPORTED_BROKER_PROVIDERS)}"
        )
    if provider == "alpaca":
        validate_alpaca_config(config)
    elif provider == "robinhood":
        validate_robinhood_config(config)


def _require_provider_key(provider: str, missing: List[str]) -> None:
    if provider not in LLM_API_KEY_ENV:
        raise ValueError(
            f"Unsupported LLM provider '{provider}'. "
            f"Supported: {', '.join(k for k in LLM_API_KEY_ENV if k != 'mock')}, mock"
        )
    api_key_env = LLM_API_KEY_ENV[provider]
    if api_key_env and not os.getenv(api_key_env):
        missing.append(api_key_env)


def validate_config(config: AppConfig) -> None:
    """Validate required environment variables for a live paper-trading cycle."""
    validate_broker_config(config)
    missing: List[str] = []

    _require_provider_key(config.llm_provider, missing)
    if config.llm_fallback_provider:
        _require_provider_key(config.llm_fallback_provider, missing)

    if missing:
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(sorted(set(missing)))
            + ". Copy .env.example and fill in your credentials."
        )


def config_summary(config: AppConfig) -> Dict[str, object]:
    return {
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "llm_fallback_provider": config.llm_fallback_provider,
        "llm_fallback_model": config.llm_fallback_model,
        "llm_max_retries": config.llm_max_retries,
        "broker_provider": config.broker_provider,
        "alpaca_paper": config.alpaca_paper,
        "trading_cycle_interval": config.trading_cycle_interval,
    }


def validate_finnhub_config() -> bool:
    """Return True if FINNHUB_API_KEY is set (optional for trading cycle)."""
    return bool(os.getenv("FINNHUB_API_KEY"))


def validate_fmp_config() -> bool:
    """Return True if FMP_API_KEY is set (optional for trading cycle)."""
    return bool(os.getenv("FMP_API_KEY"))
