import os
from typing import Dict, Any, Optional
from datetime import datetime
from ..llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy

class TechnicalAnalysisStrategy(AnalysisStrategy):
    """Technical analysis strategy using LLM."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
    
    def analyze(self, 
                portfolio_data: Dict[str, Any],
                user_preferences: Dict[str, Any],
                analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform technical analysis using LLM.
        
        Args:
            portfolio_data: Current portfolio information
            user_preferences: User's investment preferences
            analysis_params: Additional parameters for analysis
            
        Returns:
            Dictionary containing analysis results
        """
        # Prepare context for LLM
        context = f"""
        Current Portfolio:
        - Total Value: ${portfolio_data.get('portfolio_value', 0)}
        - Cash Balance: ${portfolio_data.get('cash', 0)}
        - Current Positions: {portfolio_data.get('positions', [])}
        
        User Preferences:
        - Risk Tolerance: {user_preferences.get('risk_tolerance', 'moderate')}
        - Investment Goal: {user_preferences.get('investment_goal', 'growth')}
        - Investment Horizon: {user_preferences.get('investment_horizon', 'medium-term')}
        
        Analysis Parameters:
        - Time Horizon: {analysis_params.get('time_horizon', 'medium-term') if analysis_params else 'medium-term'}
        - Technical Indicators: {analysis_params.get('indicators', ['MA', 'RSI', 'MACD']) if analysis_params else ['MA', 'RSI', 'MACD']}
        - Chart Patterns: {analysis_params.get('patterns', ['trend', 'support', 'resistance']) if analysis_params else ['trend', 'support', 'resistance']}
        
        Please provide a technical analysis in the following format:
        1. Price Action Analysis
        2. Technical Indicators
        3. Chart Patterns
        4. Support/Resistance Levels
        5. Trading Signals
        """
        
        try:
            response = self.llm_client.generate_response(context)
            
            return {
                "status": "success",
                "analysis": response,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            print(f"Error in technical analysis: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_strategy_name(self) -> str:
        return "Technical Analysis Strategy"
    
    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon (short-term, medium-term, long-term)",
            "indicators": "Technical indicators to use (MA, RSI, MACD, etc.)",
            "patterns": "Chart patterns to look for (trend, support, resistance, etc.)",
            "timeframes": "Chart timeframes to analyze",
            "volume_analysis": "Whether to include volume analysis"
        } 