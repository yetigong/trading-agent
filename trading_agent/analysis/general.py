import os
from typing import Dict, Any, Optional
from datetime import datetime
from ..llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy

class GeneralAnalysisStrategy(AnalysisStrategy):
    """General market analysis strategy using LLM."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
    
    def analyze(self, 
                portfolio_data: Dict[str, Any],
                user_preferences: Dict[str, Any],
                analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform general market analysis using LLM.
        
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
        - Focus Areas: {analysis_params.get('focus_areas', 'all') if analysis_params else 'all'}
        - Regions: {analysis_params.get('regions', 'US') if analysis_params else 'US'}
        
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
            # Set system message for Claude
            if hasattr(self.llm_client, 'system'):
                self.llm_client.system = """You are a trading analyst providing market analysis and specific trading recommendations. Your recommendations must follow the exact format specified, with each decision clearly numbered and formatted."""
            
            response = self.llm_client.generate_response(context)
            
            return {
                "status": "success",
                "analysis": response,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            print(f"Error in market analysis: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_strategy_name(self) -> str:
        return "General Analysis Strategy"
    
    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon (short-term, medium-term, long-term)",
            "focus_areas": "Specific sectors or areas to focus on",
            "regions": "Geographic regions to analyze",
            "market_conditions": "Specific market conditions to consider",
            "risk_factors": "Risk factors to analyze"
        } 