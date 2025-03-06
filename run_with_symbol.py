
import sys
import os
import asyncio
from main import main

if __name__ == "__main__":
    # Check if symbol is provided as command-line argument
    if len(sys.argv) < 2:
        print("Usage: python run_with_symbol.py SYMBOL")
        print("Example: python run_with_symbol.py R_75")
        sys.exit(1)
    
    # Set the symbol as an environment variable
    symbol = sys.argv[1]
    os.environ['DEFAULT_SYMBOL'] = symbol
    
    print(f"Starting trading bot with symbol: {symbol}")
    
    # Run the main function
    asyncio.run(main())
