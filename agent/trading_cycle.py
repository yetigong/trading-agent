import logging
from datetime import datetime
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.llm.client import get_llm_client
from alpaca_client import AlpacaTradingClient
import json
from dotenv import load_dotenv
import os

class TradingCycle:
    """Handles the execution of a single trading cycle."""
    
    def __init__(self, market_data_provider=None, llm_client=None, alpaca_client=None):
        """
        Initialize the trading cycle.
        
        Args:
            market_data_provider: Market data provider instance
            llm_client: LLM client instance
            alpaca_client: Alpaca trading client instance
        """
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        
        # Initialize components
        self.market_data_provider = market_data_provider or AlpacaMarketDataProvider()
        self.llm_client = llm_client or get_llm_client("gemini", model="financial")
        self.alpaca_client = alpaca_client or AlpacaTradingClient()
        
        self.logger.info("Trading cycle initialized")

    def run_cycle(self):
        """Execute a complete trading cycle."""
        try:
            # Get market data
            market_data = self.market_data_provider.get_market_data()
            
            if not self.validate_cycle_data(market_data):
                return {
                    'success': False,
                    'error': 'Invalid market data'
                }
            
            # Get LLM analysis
            analysis = self.llm_client.analyze_market(market_data)
            
            # Process recommendations
            recommendations = analysis.get('recommendations', [])
            processed_recommendations = self.process_recommendations(recommendations)
            
            # Execute trades based on recommendations
            trades = []
            for action, symbols in processed_recommendations.items():
                for symbol in symbols:
                    trade = {
                        'symbol': symbol,
                        'action': action,
                        'price': market_data['prices'].get(symbol),
                        'timestamp': datetime.now()
                    }
                    trades.append(trade)
            
            return {
                'success': True,
                'trades': trades,
                'analysis': analysis,
                'market_data': market_data
            }
            
        except Exception as e:
            return self.handle_cycle_error(e)

    def validate_cycle_data(self, data):
        """Validate the cycle data."""
        if not isinstance(data, dict):
            return False
            
        required_fields = ['symbols', 'prices', 'timestamp']
        if not all(field in data for field in required_fields):
            return False
            
        if not isinstance(data['symbols'], list) or not data['symbols']:
            return False
            
        if not isinstance(data['prices'], dict) or not data['prices']:
            return False
            
        if not isinstance(data['timestamp'], datetime):
            return False
            
        return True

    def handle_cycle_error(self, error):
        """Handle cycle execution errors."""
        error_msg = str(error)
        self.logger.error(f"Error in trading cycle: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'timestamp': datetime.now()
        }

    def process_recommendations(self, recommendations):
        """Process trading recommendations."""
        processed = {
            'buy': [],
            'sell': [],
            'hold': []
        }
        
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
                
            symbol = rec.get('symbol')
            action = rec.get('action', '').lower()
            confidence = rec.get('confidence', 0)
            
            if not symbol or not action or confidence < 0.5:
                continue
                
            if action in processed:
                processed[action].append(symbol)
        
        return processed 