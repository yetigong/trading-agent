from typing import Dict, Any
from datetime import datetime
from .base import MarketDataProvider

class MockMarketDataProvider(MarketDataProvider):
    """Mock market data provider for testing."""
    
    def __init__(self):
        self.mock_data = {
            "volatility": "moderate",
            "trend": "bullish",
            "economic_cycle": "expansion",
            "market_phase": "normal",
            "timestamp": datetime.now(),
            "indices": {
                "SPY": {
                    "current_price": 450.0,
                    "daily_change": 1.2,
                    "volume": 100000000
                },
                "QQQ": {
                    "current_price": 380.0,
                    "daily_change": 1.5,
                    "volume": 80000000
                },
                "DIA": {
                    "current_price": 350.0,
                    "daily_change": 0.8,
                    "volume": 60000000
                },
                "IWM": {
                    "current_price": 200.0,
                    "daily_change": 1.0,
                    "volume": 40000000
                }
            },
            "sector_performance": {
                "tech": "+2.5%",
                "healthcare": "+1.8%",
                "financials": "+0.5%",
                "energy": "-0.3%",
                "consumer": "+0.7%"
            }
        }
    
    def get_market_conditions(self) -> Dict[str, Any]:
        """Get mock market conditions."""
        return self.mock_data
    
    def get_market_volatility(self) -> str:
        """Get mock market volatility."""
        return self.mock_data["volatility"]
    
    def get_market_trend(self) -> str:
        """Get mock market trend."""
        return self.mock_data["trend"]
    
    def get_economic_cycle(self) -> str:
        """Get mock economic cycle."""
        return self.mock_data["economic_cycle"]
    
    def get_market_phase(self) -> str:
        """Get mock market phase."""
        return self.mock_data["market_phase"]
    
    def get_supported_indicators(self) -> Dict[str, str]:
        """Get list of supported market indicators."""
        return {
            "volatility": "Market volatility level (low, moderate, high)",
            "trend": "Market trend (bullish, neutral, bearish)",
            "economic_cycle": "Economic cycle phase (expansion, peak, contraction, trough)",
            "market_phase": "Market phase (normal, bubble, crash, recovery)",
            "indices": "Major market indices (SPY, QQQ, DIA, IWM)",
            "sector_performance": "Performance by sector"
        } 