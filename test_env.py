from dotenv import load_dotenv
import os

load_dotenv()

print("ALPACA_API_KEY exists:", bool(os.getenv('ALPACA_API_KEY')))
print("ALPACA_SECRET_KEY exists:", bool(os.getenv('ALPACA_SECRET_KEY')))
print("ALPACA_PAPER:", os.getenv('ALPACA_PAPER')) 