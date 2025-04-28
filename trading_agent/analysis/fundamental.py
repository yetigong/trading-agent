import os
from typing import Dict, Any, Optional
from datetime import datetime
from ..llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy

class FundamentalAnalysisStrategy(AnalysisStrategy):
    """Fundamental analysis strategy using LLM."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
    
    def analyze(self, 
                portfolio_data: Dict[str, Any],
                user_preferences: Dict[str, Any],
                analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform fundamental analysis using LLM.
        
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
        - Metrics: {analysis_params.get('metrics', ['PE', 'PB', 'ROE']) if analysis_params else ['PE', 'PB', 'ROE']}
        - Industry Focus: {analysis_params.get('industry', 'all') if analysis_params else 'all'}
        
        Please provide a fundamental analysis in the following format:
        1. Financial Metrics Analysis
        2. Industry Analysis
        3. Competitive Position
        4. Growth Prospects
        5. Investment Recommendations
        """
        
        try:
            response = self.llm_client.generate_response(context)
            
            return {
                "status": "success",
                "analysis": response,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            print(f"Error in fundamental analysis: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_strategy_name(self) -> str:
        return "Fundamental Analysis Strategy"
    
    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon (short-term, medium-term, long-term)",
            "metrics": "Financial metrics to analyze (PE, PB, ROE, etc.)",
            "industry": "Industry focus for analysis",
            "growth_factors": "Growth factors to consider",
            "valuation_methods": "Valuation methods to use"
        } 