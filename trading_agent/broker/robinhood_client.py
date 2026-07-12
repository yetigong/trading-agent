import logging
import os
from typing import List, Optional

from dotenv import load_dotenv

from trading_agent.broker.mappers import (
    map_robinhood_account,
    map_robinhood_order,
    map_robinhood_order_result,
    map_robinhood_portfolio_history,
    map_robinhood_position,
)
from trading_agent.domain.broker import (
    BrokerAccount,
    BrokerError,
    BrokerOrder,
    BrokerOrderResult,
    BrokerPosition,
    OrderSide,
    PortfolioHistory,
)

logger = logging.getLogger(__name__)


class RobinhoodBrokerClient:
    """Robinhood broker client via unofficial robin_stocks library."""

    provider_name = "robinhood"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        mfa_secret: Optional[str] = None,
        session_path: Optional[str] = None,
        live_trading_ack: bool = False,
    ):
        load_dotenv()
        self.username = username or os.getenv("ROBINHOOD_USERNAME", "")
        self.password = password or os.getenv("ROBINHOOD_PASSWORD", "")
        self.mfa_secret = mfa_secret or os.getenv("ROBINHOOD_MFA_SECRET", "")
        self.session_path = session_path or os.getenv("ROBINHOOD_SESSION_PATH", "")
        self.live_trading_ack = live_trading_ack or os.getenv(
            "ROBINHOOD_LIVE_TRADING_ACK", ""
        ).lower() in ("1", "true", "yes")

        if not self.live_trading_ack:
            raise ValueError(
                "Robinhood live trading requires ROBINHOOD_LIVE_TRADING_ACK=true. "
                "Robinhood has no paper trading; see docs/agents/multi-broker.md."
            )
        if not self.username or not self.password:
            raise ValueError(
                "ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD are required for Robinhood broker."
            )

        try:
            import robin_stocks.robinhood as rh
        except ImportError as exc:
            raise ImportError(
                "robin_stocks is required for Robinhood support. "
                "Install with: pip install -r requirements-optional.txt"
            ) from exc

        self._rh = rh
        self._login()

    def _login(self) -> None:
        login_kwargs = {
            "store_session": bool(self.session_path),
            "expiresIn": 86400,
        }
        if self.mfa_secret:
            try:
                import pyotp

                login_kwargs["mfa_code"] = pyotp.TOTP(self.mfa_secret).now()
            except ImportError:
                login_kwargs["mfa_code"] = self.mfa_secret

        if self.session_path:
            login_kwargs["path"] = self.session_path

        result = self._rh.login(self.username, self.password, **login_kwargs)
        if result is None:
            raise BrokerError(
                "Robinhood login failed. Check credentials and MFA settings.",
                provider=self.provider_name,
            )
        logger.warning(
            "Connected to Robinhood via unofficial API. Use at your own risk; "
            "Robinhood may restrict third-party API access."
        )

    def get_account(self) -> BrokerAccount:
        try:
            profile = self._rh.profiles.load_account_profile() or {}
            portfolio = self._rh.profiles.load_portfolio_profile() or {}
            return map_robinhood_account(profile, portfolio)
        except Exception as exc:
            raise BrokerError(str(exc), provider=self.provider_name) from exc

    def get_positions(self) -> List[BrokerPosition]:
        try:
            raw_positions = self._rh.account.get_open_stock_positions() or []
            positions: List[BrokerPosition] = []
            for raw in raw_positions:
                instrument_url = raw.get("instrument")
                if instrument_url:
                    instrument = self._rh.helper.request_get(instrument_url)
                    raw = {**raw, "symbol": instrument.get("symbol", "")}
                pos = map_robinhood_position(raw)
                if pos.qty > 0:
                    positions.append(pos)
            return positions
        except Exception as exc:
            raise BrokerError(str(exc), provider=self.provider_name) from exc

    def get_orders(self) -> List[BrokerOrder]:
        try:
            raw_orders = self._rh.orders.get_all_open_stock_orders() or []
            return [map_robinhood_order(o) for o in raw_orders]
        except Exception as exc:
            raise BrokerError(str(exc), provider=self.provider_name) from exc

    def place_market_order(
        self, symbol: str, qty: int, side: OrderSide
    ) -> BrokerOrderResult:
        try:
            if side == OrderSide.BUY:
                order = self._rh.orders.order_buy_market(symbol, qty)
            else:
                order = self._rh.orders.order_sell_market(symbol, qty)
            if not order:
                raise BrokerError(
                    f"Robinhood rejected {side.value} order for {symbol}",
                    provider=self.provider_name,
                )
            return map_robinhood_order_result(order, symbol=symbol, qty=qty, side=side)
        except BrokerError:
            raise
        except Exception as exc:
            raise BrokerError(str(exc), provider=self.provider_name) from exc

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[str] = None,
        extended_hours: bool = False,
    ) -> PortfolioHistory:
        del date_end, extended_hours
        try:
            span = _map_period_to_span(period)
            interval = timeframe or "day"
            history = self._rh.account.get_portfolio_history(span=span, interval=interval)
            return map_robinhood_portfolio_history(history)
        except Exception as exc:
            raise BrokerError(str(exc), provider=self.provider_name) from exc


def _map_period_to_span(period: str) -> str:
    mapping = {
        "1D": "day",
        "1W": "week",
        "1M": "month",
        "3M": "3month",
        "1Y": "year",
        "5Y": "5year",
        "all": "all",
    }
    return mapping.get(period.upper(), "month")
