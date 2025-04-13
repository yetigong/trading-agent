import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

class AlpacaTradingClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            raise ValueError("API keys not found in environment variables")
        
        # Create trading client - paper trading is True by default
        self.client = TradingClient(self.api_key, self.secret_key)
    
    def get_account(self):
        """Get account information"""
        return self.client.get_account()
    
    def get_positions(self):
        """Get all positions"""
        return self.client.get_all_positions()
    
    def place_market_order(self, symbol: str, qty: int, side: OrderSide):
        """Place a market order"""
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force=TimeInForce.DAY
        )
        return self.client.submit_order(order_data)
    
    def get_assets(self):
        """Get all available assets"""
        return self.client.get_all_assets()

if __name__ == "__main__":
    # Example usage
    try:
        client = AlpacaTradingClient()
        
        # Get account information
        account = client.get_account()
        print(f"Account Status: {account.status}")
        print(f"Buying Power: ${account.buying_power}")
        
        # Get available assets
        assets = client.get_assets()
        print("\nAvailable Assets:")
        for asset in list(assets)[:5]:  # Show first 5 assets
            print(f"{asset.symbol}: {asset.name}")
            
    except Exception as e:
        print(f"Error: {str(e)}") 