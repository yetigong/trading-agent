from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class TradingStrategy(ABC):
    """Base class for trading strategies."""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of the trading strategy."""
        pass
    
    @abstractmethod
    def get_supported_parameters(self) -> Dict[str, str]:
        """Return a dictionary of supported strategy parameters and their descriptions."""
        pass
    
    @abstractmethod
    def validate_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate trading decisions based on risk management rules.
        
        Args:
            decisions: List of trading decisions to validate
            
        Returns:
            List of validated trading decisions
        """
        pass 