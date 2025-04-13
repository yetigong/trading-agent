from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

def test_connection():
    load_dotenv()
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    print(f"API Key length: {len(api_key)}")
    print(f"Secret Key length: {len(secret_key)}")
    
    try:
        # Create trading client - paper trading is True by default
        client = TradingClient(api_key, secret_key)
        
        # Get account information
        account = client.get_account()
        print("\nConnection successful!")
        print(f"Account Status: {account.status}")
        print(f"Buying Power: ${account.buying_power}")
        
        # Test getting some assets
        assets = client.get_all_assets()
        print("\nSample Assets:")
        for asset in list(assets)[:5]:  # Show first 5 assets
            print(f"{asset.symbol}: {asset.name}")
            
    except Exception as e:
        print(f"\nError connecting to Alpaca:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")

if __name__ == "__main__":
    test_connection() 