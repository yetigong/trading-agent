import os
from typing import Dict, List, Any, Optional
from ..llm.client import get_llm_client, LLMClient
from .base import TradingStrategy

class GeneralTradingStrategy(TradingStrategy):
    """General trading strategy using LLM."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
    
    def make_decisions(self, 
                      market_analysis: Dict[str, Any],
                      portfolio_data: Dict[str, Any],
                      user_preferences: Dict[str, Any],
                      strategy_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Make trading decisions based on market analysis and user preferences.
        
        Args:
            market_analysis: Results from market analysis
            portfolio_data: Current portfolio information
            user_preferences: User's investment preferences
            strategy_params: Additional parameters for specific strategies
            
        Returns:
            List of trading decisions
        """
        # Prepare context for LLM
        context = f"""
        Market Analysis:
        {market_analysis['analysis']}
        
        Current Portfolio Status:
        - Account Value: ${portfolio_data.get('portfolio_value', 0)}
        - Cash Balance: ${portfolio_data.get('cash', 0)}
        - Current Positions: {portfolio_data.get('positions', [])}
        
        User Preferences:
        - Risk Tolerance: {user_preferences.get('risk_tolerance', 'moderate')}
        - Investment Goal: {user_preferences.get('investment_goal', 'growth')}
        - Max Position Size: {user_preferences.get('max_position_size', 0.1) * 100}% of portfolio
        
        Strategy Parameters:
        - Decision Timeframe: {strategy_params.get('timeframe', 'immediate') if strategy_params else 'immediate'}
        - Risk Management: {strategy_params.get('risk_management', 'standard') if strategy_params else 'standard'}
        - Position Sizing: {strategy_params.get('position_sizing', 'dynamic') if strategy_params else 'dynamic'}
        
        Please provide specific trading decisions in the following format:
        1. Action (BUY/SELL)
        2. Symbol
        3. Quantity
        4. Reasoning
        5. Risk Level
        """
        
        try:
            response = self.llm_client.generate_response(context)
            
            # Parse LLM response into trading decisions
            decisions = self._parse_decisions(response)
            
            # Validate decisions
            validated_decisions = self.validate_decisions(decisions)
            
            return validated_decisions
            
        except Exception as e:
            print(f"Error in making trading decisions: {str(e)}")
            return []
    
    def get_strategy_name(self) -> str:
        return "General Trading Strategy"
    
    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "timeframe": "Decision timeframe (immediate, short-term, long-term)",
            "risk_management": "Risk management approach (conservative, standard, aggressive)",
            "position_sizing": "Position sizing method (fixed, dynamic, percentage-based)",
            "max_positions": "Maximum number of concurrent positions",
            "stop_loss": "Stop loss percentage",
            "take_profit": "Take profit percentage"
        }
    
    def validate_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate trading decisions based on risk management rules.
        """
        validated_decisions = []
        
        for decision in decisions:
            # Basic validation
            if not all(k in decision for k in ['action', 'symbol', 'quantity', 'reasoning', 'risk_level']):
                continue
                
            # Validate action
            if decision['action'] not in ['BUY', 'SELL']:
                continue
                
            # Validate quantity
            if decision['quantity'] != 'ALL':
                try:
                    decision['quantity'] = int(decision['quantity'])
                    if decision['quantity'] <= 0:
                        continue
                except (ValueError, TypeError):
                    continue
                
            # Validate risk level
            if decision['risk_level'] not in ['low', 'medium', 'high']:
                continue
                
            validated_decisions.append(decision)
        
        return validated_decisions
    
    def _parse_decisions(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured trading decisions.
        """
        decisions = []
        lines = llm_response.split('\n')
        
        current_decision = {}
        for line in lines:
            line = line.strip()
            if line.startswith('1. Action'):
                if current_decision:
                    decisions.append(current_decision)
                current_decision = {'action': line.split(':')[1].strip()}
            elif line.startswith('2. Symbol'):
                current_decision['symbol'] = line.split(':')[1].strip()
            elif line.startswith('3. Quantity'):
                quantity = line.split(':')[1].strip()
                if quantity.upper() == 'ALL':
                    current_decision['quantity'] = 'ALL'
                else:
                    try:
                        current_decision['quantity'] = int(quantity)
                    except ValueError:
                        print(f"Warning: Invalid quantity value: {quantity}")
                        continue
            elif line.startswith('4. Reasoning'):
                current_decision['reasoning'] = line.split(':')[1].strip()
            elif line.startswith('5. Risk Level'):
                current_decision['risk_level'] = line.split(':')[1].strip()
        
        if current_decision:
            decisions.append(current_decision)
        
        return decisions 