import os
import asyncio
from deriv_api import DerivAPI
import websockets
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_balance():
    """Test balance retrieval from Deriv API"""
    try:
        # Initialize connection
        app_id = 1089
        api_token = os.getenv('DERIV_API_TOKEN_DEMO', '')

        if not api_token:
            logger.error("Error: DERIV_API_TOKEN_DEMO not set")
            return

        # Connect to WebSocket
        url = f'wss://ws.binaryws.com/websockets/v3?l=EN&app_id={app_id}'

        logger.info("Connecting to Deriv WebSocket API...")
        async with websockets.connect(url) as websocket:
            # Create API instance
            api = DerivAPI(websocket=websocket)

            # Authorize
            logger.info("Authorizing with API token...")
            auth_response = await api.authorize(api_token)
            logger.info("Authorization Response:")
            logger.info(json.dumps(auth_response, indent=2))

            if 'error' in auth_response:
                logger.error(f"Authorization failed: {auth_response['error']['message']}")
                return

            # Get balance
            logger.info("Fetching account balance...")
            balance_response = await api.balance()

            # Log full response for debugging
            logger.info("Full Balance Response Structure:")
            logger.info(json.dumps(balance_response, indent=2, sort_keys=True))

            if 'error' in balance_response:
                logger.error(f"Error getting balance: {balance_response['error']['message']}")
            else:
                if 'balance' in balance_response:
                    balance = balance_response['balance']
                    logger.info("Balance data structure:")
                    logger.info(json.dumps(balance, indent=2, sort_keys=True))
                    logger.info(f"Current balance: {balance['currency']} {balance['balance']}")
                else:
                    logger.error("Unexpected response structure - missing 'balance' key")
                    logger.error(f"Response keys: {list(balance_response.keys())}")

    except websockets.exceptions.ConnectionClosed:
        logger.error("WebSocket connection closed unexpectedly")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Detailed error information:")
    finally:
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_balance())