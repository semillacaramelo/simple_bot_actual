
#!/usr/bin/env python
"""
Debug Trading Script - For testing signal generation and order execution
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from config.config import Config
from src.api.deriv_connector import DerivConnector
from src.api.data_fetcher import DataFetcher
from src.strategy.strategy_executor import StrategyExecutor
from src.execution.order_executor import OrderExecutor
from src.risk.risk_manager import RiskManager
from src.monitor.logger import Logger
from src.monitor.performance import PerformanceTracker
from src.utils.console import cyan_status, green_success, red_error, blue_status, yellow_signal

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_signal_generation(symbol='R_100'):
    """Test the signal generation process"""
    logger = Logger(log_file='debug_trading.log')
    logger.log(f"Starting debug session for {symbol}", level='info')
    
    try:
        # Load configuration
        logger.log("Loading configuration...", level='info')
        config = Config()
        api_token = config.get_api_token()
        app_id = int(config.get_app_id())
        trading_params = config.get_trading_params()
        
        # Initialize API connector
        logger.log("Initializing API connector...", level='info')
        api_connector = DerivConnector(api_token, app_id)
        cyan_status("Connecting to Deriv API...")
        connect_success, error_message = await api_connector.connect()
        
        if not connect_success:
            red_error(f"Failed to connect: {error_message}")
            return
            
        green_success("Connected to Deriv API")
        
        # Initialize components
        logger.log("Initializing components...", level='info')
        data_fetcher = DataFetcher(api_connector)
        risk_manager = RiskManager(
            api_connector=api_connector,
            max_risk=0.02,
            max_daily_loss=0.05,
            risk_per_trade=0.01,
            max_open_trades=3
        )
        await risk_manager.initialize()
        
        performance_tracker = PerformanceTracker()
        order_executor = OrderExecutor(
            api_connector,
            performance_tracker=performance_tracker,
            risk_manager=risk_manager
        )
        
        # Initialize strategy with debug flag
        trading_params['DEBUG_MODE'] = True
        strategy_executor = StrategyExecutor(
            data_fetcher=data_fetcher,
            order_executor=order_executor,
            **trading_params
        )
        
        # Test market data
        cyan_status(f"Testing data fetch for {symbol}...")
        df = await data_fetcher.get_historical_data(symbol, count=100)
        if df is not None and not df.empty:
            green_success(f"Successfully fetched {len(df)} candles for {symbol}")
            blue_status(f"Latest data: {df.iloc[-1].to_dict()}")
        else:
            red_error(f"Failed to fetch market data for {symbol}")
            return
        
        # Test signal generation
        cyan_status("Testing signal generation...")
        for _ in range(5):  # Try multiple times to increase chance of getting a signal
            signal = await strategy_executor.execute_iteration(symbol)
            if signal:
                yellow_signal(f"Signal generated: {signal['type']} for {symbol}")
                logger.log(f"Signal details: {signal}", level='info')
                
                # Test order execution
                cyan_status("Testing order execution...")
                result = await order_executor.execute_order(signal)
                if result:
                    green_success(f"Order executed: {result.get('order_id')}")
                    
                    # Wait a bit and then try to close the position
                    await asyncio.sleep(5)
                    
                    # Get current price
                    price_data = await api_connector.get_price(symbol)
                    if price_data and 'price' in price_data:
                        current_price = price_data['price']
                        
                        # Close position
                        close_result = await order_executor.close_position(
                            result['order_id'], 
                            price=current_price
                        )
                        if close_result:
                            green_success("Position closed successfully")
                        else:
                            red_error("Failed to close position")
                else:
                    red_error("Order execution failed")
                
                # We got a signal and tested execution, so we can exit
                break
            else:
                blue_status(f"No signal generated in iteration {_ + 1}, trying again...")
                await asyncio.sleep(3)
        
        cyan_status("Debug session completed")
        
    except Exception as e:
        logger.log_error(e, {'context': 'debug_session'})
        red_error(f"Error during debug session: {str(e)}")
    finally:
        if 'api_connector' in locals():
            await api_connector.disconnect()

if __name__ == "__main__":
    # Get symbol from command line if provided
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'R_100'
    print(f"Running debug session for {symbol}")
    asyncio.run(test_signal_generation(symbol))
