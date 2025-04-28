from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class MarketDataProvider(ABC):
    """Base class for market data providers."""
    
    @abstractmethod
    def get_market_conditions(self) -> Dict[str, Any]:
        """
        Get current market conditions.
        
        Returns:
            Dictionary containing market conditions data
        """
        pass
    
    @abstractmethod
    def get_market_volatility(self) -> str:
        """
        Get current market volatility level.
        
        Returns:
            Volatility level (low, moderate, high)
        """
        pass
    
    @abstractmethod
    def get_market_trend(self) -> str:
        """
        Get current market trend.
        
        Returns:
            Market trend (bullish, neutral, bearish)
        """
        pass
    
    @abstractmethod
    def get_economic_cycle(self) -> str:
        """
        Get current economic cycle phase.
        
        Returns:
            Economic cycle phase (expansion, peak, contraction, trough)
        """
        pass
    
    @abstractmethod
    def get_market_phase(self) -> str:
        """
        Get current market phase.
        
        Returns:
            Market phase (normal, bubble, crash, recovery)
        """
        pass
    
    @abstractmethod
    def get_supported_indicators(self) -> Dict[str, str]:
        """
        Get list of supported market indicators.
        
        Returns:
            Dictionary of indicator names and descriptions
        """
        pass 