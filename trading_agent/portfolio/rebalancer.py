import os
from typing import Dict, List, Any, Optional
from ..llm.client import get_llm_client, LLMClient

class PortfolioRebalancer:
    """Portfolio rebalancing strategy using LLM."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
    
    def rebalance_portfolio(self,
                          portfolio_data: Dict[str, Any],
                          user_preferences: Dict[str, Any],
                          rebalance_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a portfolio rebalancing plan based on current portfolio and user preferences.
        
        Args:
            portfolio_data: Current portfolio information
            user_preferences: User's investment preferences
            rebalance_params: Additional parameters for rebalancing
            
        Returns:
            Rebalancing plan
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
        - Max Position Size: {user_preferences.get('max_position_size', 0.1) * 100}% of portfolio
        
        Rebalancing Parameters:
        - Target Allocation: {rebalance_params.get('target_allocation', 'balanced') if rebalance_params else 'balanced'}
        - Threshold: {rebalance_params.get('threshold', 5) if rebalance_params else 5}%
        - Sector Weights: {rebalance_params.get('sector_weights', 'market_cap') if rebalance_params else 'market_cap'}
        
        Please provide a rebalancing plan in the following format:
        1. Target Allocation
        2. Required Changes
        3. Reasoning
        """
        
        try:
            response = self.llm_client.generate_response(context)
            
            # Parse LLM response into rebalancing plan
            rebalancing_plan = self._parse_rebalancing_plan(response)
            
            return {
                "status": "success",
                "rebalancing_plan": rebalancing_plan
            }
            
        except Exception as e:
            print(f"Error in portfolio rebalancing: {str(e)}")
        return {
                "status": "failed",
                "error": str(e)
        }
    
    def generate_rebalancing_orders(self, 
                                  rebalancing_plan: Dict[str, Any],
                                  portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate specific orders to execute the rebalancing plan.
        
        Args:
            rebalancing_plan: The rebalancing plan from LLM
            portfolio_data: Current portfolio information
            
        Returns:
            List of orders to execute
        """
        # Prepare context for LLM
        context = f"""
        Rebalancing Plan:
        {rebalancing_plan['rebalancing_plan']}
        
        Current Portfolio:
        - Total Value: ${portfolio_data.get('portfolio_value', 0)}
        - Cash Balance: ${portfolio_data.get('cash', 0)}
        - Current Positions: {portfolio_data.get('positions', [])}
        
        Please provide specific orders in the following format:
        1. Action (BUY/SELL)
        2. Symbol
        3. Quantity
        4. Reason
        """
        
        try:
            response = self.llm_client.generate_response(context)
            
            # Parse LLM response into orders
            orders = self._parse_orders(response)
            
            return orders
            
        except Exception as e:
            print(f"Error generating rebalancing orders: {str(e)}")
            return []
    
    def _parse_rebalancing_plan(self, llm_response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured rebalancing plan.
        """
        plan = {}
        lines = llm_response.split('\n')
        
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('1. Target Allocation'):
                if current_section:
                    plan[current_section] = '\n'.join(current_content)
                current_section = 'target_allocation'
                current_content = []
            elif line.startswith('2. Required Changes'):
                if current_section:
                    plan[current_section] = '\n'.join(current_content)
                current_section = 'required_changes'
                current_content = []
            elif line.startswith('3. Reasoning'):
                if current_section:
                    plan[current_section] = '\n'.join(current_content)
                current_section = 'reasoning'
                current_content = []
            elif line and current_section:
                current_content.append(line)
        
        if current_section:
            plan[current_section] = '\n'.join(current_content)
        
        return plan
    
    def _parse_orders(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured rebalancing orders.
        """
        orders = []
        lines = llm_response.split('\n')
        
        current_order = {}
        for line in lines:
            line = line.strip()
            if line.startswith('1. Action'):
                if current_order:
                    orders.append(current_order)
                current_order = {'action': line.split(':')[1].strip()}
            elif line.startswith('2. Symbol'):
                current_order['symbol'] = line.split(':')[1].strip()
            elif line.startswith('3. Quantity'):
                current_order['quantity'] = int(line.split(':')[1].strip())
            elif line.startswith('4. Reason'):
                current_order['reason'] = line.split(':')[1].strip()
        
        if current_order:
            orders.append(current_order)
        
        return orders 