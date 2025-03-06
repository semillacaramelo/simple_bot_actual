
#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.api.deriv_connector import DerivConnector
from src.execution.order_executor import OrderExecutor
from config.config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def main():
    logger.info("Starting put_sell_test script")
    config = Config()
    api_token = config.api_config.api_token
    app_id = config.api_config.app_id

    if not api_token or not app_id:
        logger.error("API_TOKEN or APP_ID not set in config.")
        return

    try:
        # 1. Connect to Deriv API
        api_connector = DerivConnector(api_token, app_id)
        connected, error_msg = await api_connector.connect()
        if not connected:
            logger.error(f"Failed to connect to Deriv API: {error_msg}")
            return

        logger.info("Connected to Deriv API")

        # 2. Select fixed symbol: Volatility 100 Index
        symbol = 'R_100'
        logger.info(f"Selected symbol: {symbol}")

        # 3. Create OrderExecutor instance
        order_executor = OrderExecutor(api_connector)

        # 4. Place PUT trade ($1)
        put_signal = {
            'symbol': symbol,
            'type': 'PUT',
            'stake_amount': 1.0,  # Exactly $1
            'duration': 1,
            'duration_unit': 'm'  # 1 minute duration
        }

        logger.info(f"Placing PUT order for {symbol} with stake $1")
        
        # First get a proposal to verify parameters
        proposal_response_put = await api_connector.api.proposal(
            {
                "proposal": 1,
                "contract_type": put_signal['type'],
                "currency": "USD",
                "symbol": put_signal['symbol'],
                "amount": put_signal['stake_amount'],
                "basis": "stake",
                "duration": put_signal['duration'],
                "duration_unit": put_signal['duration_unit']
            }
        )
        
        if 'error' in proposal_response_put:
            logger.error(f"PUT proposal error: {proposal_response_put['error']['message']}")
        else:
            logger.info(f"PUT proposal successful with price: {proposal_response_put['proposal']['ask_price']}")
            
            # Execute the PUT order
            put_order = await order_executor.execute_order(put_signal)
            if put_order:
                logger.info(f"PUT order placed successfully. Order ID: {put_order['order_id']}")
            else:
                logger.error("Failed to place PUT order.")

        # 5. Place CALL trade ($1)
        call_signal = {
            'symbol': symbol,
            'type': 'CALL',
            'stake_amount': 1.0,  # Exactly $1
            'duration': 1,
            'duration_unit': 'm'  # 1 minute duration
        }
        
        logger.info(f"Placing CALL order for {symbol} with stake $1")
        
        # First get a proposal to verify parameters
        proposal_response_call = await api_connector.api.proposal(
            {
                "proposal": 1,
                "contract_type": call_signal['type'],
                "currency": "USD",
                "symbol": call_signal['symbol'],
                "amount": call_signal['stake_amount'],
                "basis": "stake",
                "duration": call_signal['duration'],
                "duration_unit": call_signal['duration_unit']
            }
        )
        
        if 'error' in proposal_response_call:
            logger.error(f"CALL proposal error: {proposal_response_call['error']['message']}")
        else:
            logger.info(f"CALL proposal successful with price: {proposal_response_call['proposal']['ask_price']}")
            
            # Execute the CALL order
            call_order = await order_executor.execute_order(call_signal)
            if call_order:
                logger.info(f"CALL order placed successfully. Order ID: {call_order['order_id']}")
            else:
                logger.error("Failed to place CALL order.")

        logger.info("Test script execution completed.")
    except Exception as e:
        logger.error(f"Error during test script execution: {str(e)}")
    finally:
        if 'api_connector' in locals():
            await api_connector.disconnect()
            logger.info("Disconnected from Deriv API")

if __name__ == "__main__":
    asyncio.run(main())
