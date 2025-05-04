import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from .base import MarketDataProvider
import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass
from dotenv import load_dotenv

class AlpacaMarketDataProvider(MarketDataProvider):
    """Market data provider using Alpaca's API."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials not found in environment variables")
        
        # Initialize client with IEX data feed
        self.client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        # Market indices to track
        self.indices = ['SPY', 'QQQ', 'DIA', 'IWM']  # S&P 500, Nasdaq, Dow Jones, Russell 2000
        
        # Initialize Alpaca clients
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=True
        )
        
        self.logger.info("AlpacaMarketDataProvider initialized")
    
    def get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions using Alpaca data."""
        return {
            "volatility": self.get_market_volatility(),
            "trend": self.get_market_trend(),
            "economic_cycle": self.get_economic_cycle(),
            "market_phase": self.get_market_phase(),
            "timestamp": datetime.now(),
            "indices": self._get_indices_data()
        }
    
    def get_market_volatility(self) -> str:
        """Calculate market volatility using VIX or similar metrics."""
        # Get recent market data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get VIX data (using SPY as proxy for now)
        vix_data = self._get_historical_data('SPY', start_date, end_date)
        
        if vix_data is None or len(vix_data) < 20:
            return "moderate"
        
        # Calculate volatility
        returns = vix_data['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized volatility
        
        # Determine volatility level
        if volatility < 0.15:  # 15% annualized volatility
            return "low"
        elif volatility < 0.25:  # 25% annualized volatility
            return "moderate"
        else:
            return "high"
    
    def get_market_trend(self) -> str:
        """Determine market trend using moving averages."""
        # Get recent market data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)
        
        # Get SPY data
        spy_data = self._get_historical_data('SPY', start_date, end_date)
        
        if spy_data is None or len(spy_data) < 50:
            return "neutral"
        
        # Calculate moving averages
        spy_data['SMA20'] = spy_data['close'].rolling(window=20).mean()
        spy_data['SMA50'] = spy_data['close'].rolling(window=50).mean()
        
        # Determine trend
        current_price = spy_data['close'].iloc[-1]
        sma20 = spy_data['SMA20'].iloc[-1]
        sma50 = spy_data['SMA50'].iloc[-1]
        
        if current_price > sma20 and sma20 > sma50:
            return "bullish"
        elif current_price < sma20 and sma20 < sma50:
            return "bearish"
        else:
            return "neutral"
    
    def get_economic_cycle(self) -> str:
        """Determine economic cycle phase using various indicators."""
        # This is a simplified version - in a real implementation,
        # you would use multiple economic indicators
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Get SPY data for the year
        spy_data = self._get_historical_data('SPY', start_date, end_date)
        
        if spy_data is None or len(spy_data) < 200:
            return "expansion"
        
        # Calculate year-over-year return
        yoy_return = (spy_data['close'].iloc[-1] / spy_data['close'].iloc[0] - 1) * 100
        
        # Determine economic cycle phase
        if yoy_return > 15:  # Strong growth
            return "expansion"
        elif yoy_return > 5:  # Moderate growth
            return "peak"
        elif yoy_return > -5:  # Moderate decline
            return "contraction"
        else:  # Strong decline
            return "trough"
    
    def get_market_phase(self) -> str:
        """Determine market phase using various indicators."""
        # Get recent market data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get SPY data
        spy_data = self._get_historical_data('SPY', start_date, end_date)
        
        if spy_data is None or len(spy_data) < 20:
            return "normal"
        
        # Calculate recent volatility
        returns = spy_data['close'].pct_change().dropna()
        recent_volatility = returns.std() * np.sqrt(252)
        
        # Calculate recent trend
        recent_return = (spy_data['close'].iloc[-1] / spy_data['close'].iloc[0] - 1) * 100
        
        # Determine market phase
        if recent_volatility > 0.3 and recent_return > 10:  # High volatility and strong gains
            return "bubble"
        elif recent_volatility > 0.3 and recent_return < -10:  # High volatility and strong losses
            return "crash"
        elif recent_volatility > 0.2 and recent_return > 0:  # Moderate volatility and gains
            return "recovery"
        else:
            return "normal"
    
    def get_supported_indicators(self) -> Dict[str, str]:
        """Get list of supported market indicators."""
        return {
            "volatility": "Market volatility level (low, moderate, high)",
            "trend": "Market trend (bullish, neutral, bearish)",
            "economic_cycle": "Economic cycle phase (expansion, peak, contraction, trough)",
            "market_phase": "Market phase (normal, bubble, crash, recovery)",
            "indices": "Major market indices (SPY, QQQ, DIA, IWM)"
        }
    
    def _get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Get historical data for a symbol."""
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date,
                feed='iex'  # Use IEX data feed
            )
            
            bars = self.client.get_stock_bars(request_params)
            df = bars.df
            
            if symbol in df.index.levels[0]:
                df = df.loc[symbol]
            
            return df
            
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def _get_indices_data(self) -> Dict[str, Any]:
        """Get current data for major market indices."""
        indices_data = {}
        
        for index in self.indices:
            try:
                # Get recent data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5)
                
                data = self._get_historical_data(index, start_date, end_date)
                
                if data is not None and not data.empty:
                    indices_data[index] = {
                        "current_price": data['close'].iloc[-1],
                        "daily_change": (data['close'].iloc[-1] / data['close'].iloc[-2] - 1) * 100,
                        "volume": data['volume'].iloc[-1]
                    }
            
            except Exception as e:
                print(f"Error fetching data for {index}: {str(e)}")
        
        return indices_data

    def get_market_data(self, symbols=None):
        """
        Get current market data for specified symbols.
        
        Args:
            symbols (list): List of stock symbols to get data for. If None, returns data for all tracked symbols.
            
        Returns:
            dict: Market data including symbols, prices, and timestamp
        """
        try:
            if not symbols:
                # Get all active assets
                search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
                assets = self.trading_client.get_all_assets(search_params)
                symbols = [asset.symbol for asset in assets if asset.tradable]
            
            # Get latest bars for each symbol
            prices = {}
            for symbol in symbols:
                request_params = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Minute,
                    limit=1
                )
                bars = self.client.get_stock_bars(request_params)
                if bars and symbol in bars:
                    prices[symbol] = bars[symbol][-1].close
            
            return {
                'symbols': symbols,
                'prices': prices,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {str(e)}")
            raise

    def get_historical_data(self, symbol, timeframe=TimeFrame.Day, limit=30):
        """
        Get historical market data for a symbol.
        
        Args:
            symbol (str): Stock symbol
            timeframe (TimeFrame): Time frame for the data
            limit (int): Number of bars to return
            
        Returns:
            list: Historical price data
        """
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                limit=limit
            )
            bars = self.client.get_stock_bars(request_params)
            return bars[symbol] if bars and symbol in bars else []
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            raise 