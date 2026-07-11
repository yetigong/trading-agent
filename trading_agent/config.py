import os
from dataclasses import dataclass
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY_ENV = {
    "gemini": "GOOGLE_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "huggingface": "HUGGINGFACE_API_KEY",
    "mock": None,
}


@dataclass(frozen=True)
class AppConfig:
    llm_provider: str
    llm_model: str
    trading_cycle_interval: int
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool
    log_level: str


def get_config() -> AppConfig:
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").lower(),
        llm_model=os.getenv("LLM_MODEL", "financial"),
        trading_cycle_interval=int(os.getenv("TRADING_CYCLE_INTERVAL", "30")),
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        alpaca_paper=os.getenv("ALPACA_PAPER", "true").lower() in ("1", "true", "yes"),
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


def validate_config(config: AppConfig) -> None:
    """Validate required environment variables for a live paper-trading cycle."""
    validate_alpaca_config(config)
    missing: List[str] = []

    if config.llm_provider not in LLM_API_KEY_ENV:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{config.llm_provider}'. "
            f"Supported: {', '.join(k for k in LLM_API_KEY_ENV if k != 'mock')}, mock"
        )

    api_key_env = LLM_API_KEY_ENV[config.llm_provider]
    if api_key_env and not os.getenv(api_key_env):
        missing.append(api_key_env)

    if missing:
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example and fill in your credentials."
        )


def config_summary(config: AppConfig) -> Dict[str, object]:
    return {
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "alpaca_paper": config.alpaca_paper,
        "trading_cycle_interval": config.trading_cycle_interval,
    }


def validate_finnhub_config() -> bool:
    """Return True if FINNHUB_API_KEY is set (optional for trading cycle)."""
    return bool(os.getenv("FINNHUB_API_KEY"))


def validate_fmp_config() -> bool:
    """Return True if FMP_API_KEY is set (optional for trading cycle)."""
    return bool(os.getenv("FMP_API_KEY"))
