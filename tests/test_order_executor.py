import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta, timezone

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.deriv_connector import DerivConnector
from src.execution.order_executor import OrderExecutor
from src.risk.risk_manager import RiskManager
from src.monitor.performance import PerformanceTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_order_executor():
    try:
        # Load API credentials
        api_token = os.getenv('DERIV_API_TOKEN_DEMO')
        if not api_token:
            raise ValueError("API token not found in environment variables")

        # Initialize API connector
        api_connector = DerivConnector(api_token=api_token, app_id=1234)
        connection_success, error = await api_connector.connect()

        if not connection_success:
            raise ConnectionError(f"Failed to connect to Deriv API: {error}")

        # Initialize components
        risk_manager = RiskManager(max_risk=0.02, max_daily_loss=0.05, risk_per_trade=0.01)
        await risk_manager.initialize(initial_balance=10000)

        performance_tracker = PerformanceTracker()

        # Initialize order executor
        order_executor = OrderExecutor(
            api_connector, 
            performance_tracker=performance_tracker,
            risk_manager=risk_manager
        )

        # Test signal validation
        signal = {
            'symbol': 'R_100',
            'type': 'CALL',
            'entry_price': 100.0,
            'stop_loss': 99.0,
            'take_profit': 102.0,
            'stake_amount': 10.0,
            'volatility': 0.05,
            'atr_value': 0.2,
            'duration': 5,
            'duration_unit': 'm'
        }

        is_valid = await order_executor.validate_signal(signal)
        logger.info(f"Signal validation result: {is_valid}")

        if is_valid:
            # Test order execution
            result = await order_executor.execute_order(signal)

            if result:
                logger.info(f"Order executed successfully: {result}")

                # Check active trades
                active_trades = order_executor.get_active_trades()
                logger.info(f"Active trades: {active_trades}")

                # Wait for a few seconds
                await asyncio.sleep(10)

                # Close position if any active
                for order_id in list(active_trades.keys()):
                    order = active_trades[order_id]
                    symbol = order['symbol']
                    # Get current price
                    price_data = await api_connector.get_price(symbol)
                    if price_data and 'price' in price_data:
                        current_price = float(price_data['price'])
                        # Close position
                        close_result = await order_executor.close_position(order_id, current_price)
                        logger.info(f"Position closed: {close_result}")
            else:
                logger.error("Order execution failed")
        else:
            logger.error("Signal validation failed")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_order_executor())