#!/usr/bin/env python3
import asyncio
from deriv_api import DerivAPI  # Ensure python-deriv-api is installed

async def main():
    # Set your app_id (for testing, 1089 is often used)
    app_id = 68832
    # Replace with your actual API token
    api_token = "VW2ILcRli7jNOGp"
    
    # Initialize the API connector (this creates the WebSocket connection)
    api = DerivAPI(app_id=app_id)
    
    # Authorize the session using your API token
    auth_response = await api.authorize(api_token)
    if auth_response.get("error"):
        print("Authorization failed:", auth_response["error"].get("message"))
        await api.disconnect()
        return

    # Retrieve account information (balance, login id, etc.)
    account_info = await api.balance()
    
    if account_info.get("error"):
        print("Error fetching account information:", account_info["error"].get("message"))
    else:
        print("Account Information:")
        print("  - Balance:", account_info.get("balance", "N/A"))
        print("  - Login ID:", account_info.get("loginid", "N/A"))
        # Additional fields can be printed as needed

    # Cleanly disconnect from the API
    await api.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
