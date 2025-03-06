#!/usr/bin/env python3
import asyncio
from deriv_api import DerivAPI  # Ensure python-deriv-api is installed

async def main():
    # Replace with your actual app_id (1089 is often used for testing)
    app_id = 1089
    # Create the API connector instance
    api = DerivAPI(app_id=app_id)

    # Request the full list of active symbols (assets)
    # "active_symbols": "full" returns all available symbol details.
    response = await api.active_symbols({"active_symbols": "full"})
    
    # Check for errors in the response
    if response.get("error"):
        print("Error fetching symbols:", response["error"].get("message"))
    else:
        # Extract the list of symbols from the response
        symbols = response.get("active_symbols", [])
        if not symbols:
            print("No symbols available.")
        else:
            print("Available Symbols:")
            for sym in symbols:
                # Each symbol object typically contains keys like 'symbol' and 'display_name'
                symbol_id = sym.get("symbol", "N/A")
                display_name = sym.get("display_name", "No Name")
                print(f"- {symbol_id}: {display_name}")
    
    # Disconnect cleanly from the API
    await api.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
