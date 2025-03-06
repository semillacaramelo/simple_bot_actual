import os
import sys
import asyncio
import logging
from datetime import datetime, time

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)  # Insert at beginning of path for priority

from src.api.deriv_connector import DerivConnector
from src.risk.risk_manager import RiskManager
from src.utils.console import cyan_status, green_success, red_error, magenta_warning, white_wait

# Configure logging with both file and console handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_risk_manager():
    """Test RiskManager functionality with simulated trades"""
    try:
        # Initialize API connection
        app_id = int(os.getenv('DERIV_APP_ID', '1089'))
        api_token = os.getenv('DERIV_API_TOKEN_DEMO', '')

        if not api_token:
            logger.error("Error: DERIV_API_TOKEN_DEMO not set")
            return

        # Connect to API
        logger.info("Connecting to Deriv API...")
        api_connector = DerivConnector(api_token, app_id)
        connect_success, error_message = await api_connector.connect()

        if not connect_success:
            logger.error(f"Failed to connect: {error_message}")
            return

        # Initialize RiskManager with trading hours
        risk_manager = RiskManager(
            max_risk=0.10,          # 10% max total risk
            max_daily_loss=0.05,    # 5% max daily loss
            risk_per_trade=0.02,    # 2% risk per trade
            max_open_trades=3,      # Maximum 3 open positions
            api_connector=api_connector,
            trading_hours=(time(9, 0), time(17, 0)),
            min_volatility=0.01,
            max_volatility=0.05
        )

        # Initialize with API balance
        logger.info("Initializing RiskManager...")
        await risk_manager.initialize()

        # Log initial metrics
        initial_metrics = risk_manager.get_risk_metrics()
        logger.info("Initial risk metrics:", extra={'metrics': initial_metrics})

        # Test signal generation and position sizing
        test_signals = [
            {
                'trade_id': 'test_1',
                'symbol': 'R_100',
                'type': 'CALL',
                'entry_price': 1000.0,
                'stop_loss': 990.0,     # 10 points risk
                'take_profit': 1020.0,  # 20 points target
                'stake_amount': 15.0,   # Lower stake for risk management
                'atr_value': 12.5,      # Sample ATR value
                'volatility': 0.02      # Medium volatility
            },
            {
                'trade_id': 'test_2',
                'symbol': 'R_100',
                'type': 'PUT',
                'entry_price': 1000.0,
                'stop_loss': 1010.0,    # 10 points risk
                'take_profit': 980.0,   # 20 points target
                'stake_amount': 12.0,   # Lower stake for risk management
                'atr_value': 12.5,      # Sample ATR value
                'volatility': 0.03      # Higher volatility
            }
        ]

        # Test multiple signals
        for test_signal in test_signals:
            logger.info(f"Testing signal validation for {test_signal['trade_id']}...")
            cyan_status(f"Testing signal: {test_signal['trade_id']} ({test_signal['type']})")

            # Calculate and display risk amount
            risk_per_unit = abs(test_signal['entry_price'] - test_signal['stop_loss'])
            potential_loss = risk_per_unit * test_signal['stake_amount']
            logger.info(f"Risk calculation - Units: {risk_per_unit}, Stake: {test_signal['stake_amount']}, "
                       f"Potential loss: {potential_loss:.2f}, Volatility: {test_signal['volatility']:.4f}")

            is_valid = await risk_manager.validate_signal(test_signal)

            if is_valid:
                green_success("Signal validated successfully")
                sized_signal = await risk_manager.calculate_position_size(test_signal)
                logger.info("Position sized:", extra={'signal': sized_signal})
                cyan_status(f"Calculated position size: {sized_signal['stake_amount']:.2f}")

                # Add position
                risk_manager.add_position(sized_signal)
                metrics_after_add = risk_manager.get_risk_metrics()
                logger.info("Metrics after adding position:", extra={'metrics': metrics_after_add})

                # Simulate trade result (alternating profit/loss)
                profit_loss = 50.0 if test_signal['trade_id'] == 'test_1' else -30.0
                trade_result = {
                    'trade_id': test_signal['trade_id'],
                    'symbol': test_signal['symbol'],
                    'profit_loss': profit_loss
                }
                await risk_manager.record_trade_result(trade_result)

                # Log metrics after trade
                final_metrics = risk_manager.get_risk_metrics()
                logger.info("Metrics after trade:", extra={'metrics': final_metrics})
                cyan_status(f"Trade completed - P/L: {profit_loss:.2f}")
            else:
                magenta_warning(f"Signal validation failed for {test_signal['trade_id']}")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.exception("Detailed error information:")
        red_error(f"Test failed: {str(e)}")
    finally:
        if 'api_connector' in locals():
            await api_connector.disconnect()
        logger.info("Test completed")
        green_success("Test completed")

if __name__ == "__main__":
    asyncio.run(test_risk_manager())