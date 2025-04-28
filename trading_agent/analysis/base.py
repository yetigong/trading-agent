from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class AnalysisStrategy(ABC):
    """Base class for market analysis strategies."""
    
    @abstractmethod
    def analyze(self, 
                portfolio_data: Dict[str, Any],
                user_preferences: Dict[str, Any],
                analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze market conditions based on the given parameters.
        
        Args:
            portfolio_data: Current portfolio information
            user_preferences: User's investment preferences
            analysis_params: Additional parameters for specific analysis types
            
        Returns:
            Dictionary containing analysis results
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of the analysis strategy."""
        pass
    
    @abstractmethod
    def get_supported_parameters(self) -> Dict[str, str]:
        """Return a dictionary of supported analysis parameters and their descriptions."""
        pass 