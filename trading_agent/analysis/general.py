from datetime import datetime
from typing import Dict, Optional

from trading_agent.domain.cycle.analysis_context import AnalysisContext
from trading_agent.domain.cycle.market_analysis import MarketAnalysisResult
from trading_agent.formatters.analysis_context import format_analysis_context
from trading_agent.llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy


class GeneralAnalysisStrategy(AnalysisStrategy):
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def analyze(self, context: AnalysisContext) -> MarketAnalysisResult:
        prompt = f"""
        {format_analysis_context(context)}

        Please provide a comprehensive market analysis and specific trading recommendations in the following format:

        1. Market Overview
        2. Sector Analysis
        3. Risk Assessment
        4. Opportunities
        5. Trading Recommendations:
           For each recommendation, provide:
           1. Action (BUY/SELL)
           2. Symbol
           3. Quantity (number or ALL)
           4. Reasoning
           5. Risk Level (low/medium/high)
        """

        try:
            if hasattr(self.llm_client, "system"):
                self.llm_client.system = (
                    "You are a trading analyst providing market analysis and specific trading recommendations."
                )

            response = self.llm_client.generate_response(prompt)
            return MarketAnalysisResult(status="success", analysis=response, timestamp=datetime.now())

        except Exception as e:
            return MarketAnalysisResult(status="failed", error=str(e), timestamp=datetime.now())

    def get_strategy_name(self) -> str:
        return "General Analysis Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon (short-term, medium-term, long-term)",
            "focus_areas": "Specific sectors or areas to focus on",
            "regions": "Geographic regions to analyze",
        }
