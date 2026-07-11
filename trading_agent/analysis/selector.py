from typing import Dict, Optional

from trading_agent.domain.cycle.analysis_context import AnalysisContext
from trading_agent.domain.cycle.market_analysis import MarketAnalysisResult
from trading_agent.domain.signals.market_data import MarketDataPayload
from trading_agent.domain.signals.news import NewsPayload
from trading_agent.formatters.analysis_context import format_analysis_context
from trading_agent.llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy
from .fundamental import FundamentalAnalysisStrategy
from .general import GeneralAnalysisStrategy
from .technical import TechnicalAnalysisStrategy


class AnalysisStrategySelector:
    """Selects the appropriate analysis strategy based on market conditions."""

    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
        self.available_strategies = {
            "general": GeneralAnalysisStrategy,
            "technical": TechnicalAnalysisStrategy,
            "fundamental": FundamentalAnalysisStrategy,
        }

    def _legacy_market_summary(self, context: AnalysisContext) -> Dict:
        signals = context.market_signals
        conditions = signals.to_legacy_market_conditions()
        news = signals.get_source("news")
        if news and isinstance(news.payload, NewsPayload) and news.payload.sentiment:
            conditions["sentiment"] = news.payload.sentiment.overall
        market_data = signals.get_source("market_data")
        if market_data and isinstance(market_data.payload, MarketDataPayload):
            conditions["sector_performance"] = {
                s.symbol: s.daily_change for s in market_data.payload.sector_etfs
            }
        return conditions

    def select_strategy(
        self,
        context: AnalysisContext,
        market_conditions: Optional[Dict] = None,
        user_preferences: Optional[Dict] = None,
        selection_params: Optional[Dict] = None,
    ):
        conditions = market_conditions or self._legacy_market_summary(context)
        prefs = user_preferences or context.user_preferences.to_legacy_dict()

        prompt = f"""
        Market Conditions:
        - Market Trend: {conditions.get('trend', 'unknown')}
        - Volatility: {conditions.get('volatility', 'unknown')}
        - Market Sentiment: {conditions.get('sentiment', 'unknown')}
        - Sector Performance: {conditions.get('sector_performance', {})}

        User Preferences:
        - Risk Tolerance: {prefs.get('risk_tolerance', 'moderate')}
        - Investment Goal: {prefs.get('investment_goal', 'growth')}
        - Investment Horizon: {prefs.get('investment_horizon', 'medium-term')}

        Available Strategies:
        1. General Analysis: Balanced approach suitable for most market conditions
        2. Technical Analysis: Best for trending markets with clear patterns
        3. Fundamental Analysis: Best for value investing and long-term positions

        Please select the most appropriate strategy based on the current market conditions and user preferences.
        Respond with just the strategy name (general, technical, or fundamental).
        """

        try:
            if hasattr(self.llm_client, "system"):
                self.llm_client.system = (
                    "You are a trading strategy selector. Respond with just the strategy name "
                    "(general, technical, or fundamental)."
                )

            response = self.llm_client.generate_response(prompt)
            strategy_name = response.strip().lower()

            if strategy_name in self.available_strategies:
                return self.available_strategies[strategy_name]
            return GeneralAnalysisStrategy

        except Exception as e:
            print(f"Error in strategy selection: {str(e)}")
            return GeneralAnalysisStrategy

    def get_available_strategies(self):
        return list(self.available_strategies.keys())

    def get_strategy_description(self, strategy_name: str) -> str:
        strategy_descriptions = {
            "general": "General market analysis providing a balanced view of market conditions and recommendations.",
            "technical": "Technical analysis focusing on price patterns, indicators, and market trends for short-term trading.",
            "fundamental": "Fundamental analysis focusing on company financials, industry analysis, and economic factors for long-term investing.",
        }
        return strategy_descriptions.get(strategy_name, "Unknown strategy")
