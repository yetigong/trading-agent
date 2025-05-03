from typing import Dict, Any, List, Type, Optional
import os
from ..llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy
from .general import GeneralAnalysisStrategy
from .technical import TechnicalAnalysisStrategy
from .fundamental import FundamentalAnalysisStrategy

class AnalysisStrategySelector:
    """Selects the appropriate analysis strategy based on market conditions."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
        self.available_strategies = {
            "general": GeneralAnalysisStrategy,
            "technical": TechnicalAnalysisStrategy,
            "fundamental": FundamentalAnalysisStrategy
        }
    
    def select_strategy(self, 
                       market_conditions: Dict[str, Any],
                       user_preferences: Dict[str, Any],
                       selection_params: Optional[Dict[str, Any]] = None) -> Type[AnalysisStrategy]:
        """
        Select the most appropriate analysis strategy based on market conditions and user preferences.
        
        Args:
            market_conditions: Current market conditions
            user_preferences: User's investment preferences
            selection_params: Additional parameters for strategy selection
            
        Returns:
            The selected analysis strategy class
        """
        # Prepare context for LLM
        context = f"""
        Market Conditions:
        - Market Trend: {market_conditions.get('trend', 'unknown')}
        - Volatility: {market_conditions.get('volatility', 'unknown')}
        - Market Sentiment: {market_conditions.get('sentiment', 'unknown')}
        - Sector Performance: {market_conditions.get('sector_performance', {})}
        
        User Preferences:
        - Risk Tolerance: {user_preferences.get('risk_tolerance', 'moderate')}
        - Investment Goal: {user_preferences.get('investment_goal', 'growth')}
        - Investment Horizon: {user_preferences.get('investment_horizon', 'medium-term')}
        
        Available Strategies:
        1. General Analysis: Balanced approach suitable for most market conditions
        2. Technical Analysis: Best for trending markets with clear patterns
        3. Fundamental Analysis: Best for value investing and long-term positions
        
        Please select the most appropriate strategy based on the current market conditions and user preferences.
        Respond with just the strategy name (general, technical, or fundamental).
        """
        
        try:
            # Set system message for Claude
            if hasattr(self.llm_client, 'system'):
                self.llm_client.system = """You are a trading strategy selector. Your task is to select the most appropriate analysis strategy based on market conditions and user preferences. Respond with just the strategy name (general, technical, or fundamental)."""
            
            response = self.llm_client.generate_response(context)
            strategy_name = response.strip().lower()
            
            if strategy_name in self.available_strategies:
                return self.available_strategies[strategy_name]
            else:
                # Default to general strategy if selection is invalid
                return GeneralAnalysisStrategy
            
        except Exception as e:
            print(f"Error in strategy selection: {str(e)}")
            # Default to general strategy on error
            return GeneralAnalysisStrategy
    
    def get_available_strategies(self) -> List[str]:
        """Return a list of available strategy names."""
        return list(self.available_strategies.keys())
    
    def get_strategy_description(self, strategy_name: str) -> str:
        """Get a description of the specified strategy."""
        strategy_descriptions = {
            "general": "General market analysis providing a balanced view of market conditions and recommendations.",
            "technical": "Technical analysis focusing on price patterns, indicators, and market trends for short-term trading.",
            "fundamental": "Fundamental analysis focusing on company financials, industry analysis, and economic factors for long-term investing."
        }
        return strategy_descriptions.get(strategy_name, "Unknown strategy") 