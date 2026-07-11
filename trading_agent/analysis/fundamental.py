from datetime import datetime
from typing import Dict, Optional

from trading_agent.domain.cycle.analysis_context import AnalysisContext
from trading_agent.domain.cycle.market_analysis import MarketAnalysisResult
from trading_agent.formatters.analysis_context import format_analysis_context
from trading_agent.llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy


class FundamentalAnalysisStrategy(AnalysisStrategy):
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def analyze(self, context: AnalysisContext) -> MarketAnalysisResult:
        prompt = f"""
        {format_analysis_context(context)}

        Please provide a fundamental analysis in the following format:
        1. Financial Metrics Analysis (use PE, ROE, and quarterly earnings data above)
        2. Industry Analysis
        3. Competitive Position
        4. Growth Prospects
        5. Investment Recommendations
        """

        try:
            response = self.llm_client.generate_response(prompt)
            return MarketAnalysisResult(status="success", analysis=response, timestamp=datetime.now())
        except Exception as e:
            return MarketAnalysisResult(status="failed", error=str(e), timestamp=datetime.now())

    def get_strategy_name(self) -> str:
        return "Fundamental Analysis Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon (short-term, medium-term, long-term)",
            "metrics": "Financial metrics to analyze (PE, PB, ROE, etc.)",
        }
