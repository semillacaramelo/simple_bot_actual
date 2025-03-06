
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta, timezone

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.deriv_connector import DerivConnector
from backtesting.engine import BacktestEngine
from src.utils.console import cyan_status, green_success, red_error, magenta_warning

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def run_backtest():
    api_connector = None
    try:
        # Load API credentials
        api_token = os.getenv('DERIV_API_TOKEN_DEMO')
        if not api_token:
            raise ValueError("API token not found in environment variables")

        # Initialize API connector
        cyan_status("Connecting to Deriv API...")
        api_connector = DerivConnector(api_token=api_token, app_id=1089)
        connection_success, error = await api_connector.connect()

        if not connection_success:
            raise ConnectionError(f"Failed to connect to Deriv API: {error}")
        
        green_success("Connected to Deriv API successfully")

        # Configure backtest with shorter timeframe for debugging
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=3)  # Reduced to 3 hours for faster testing
        
        cyan_status(f"Test period: {start_date} to {end_date}")

        config = {
            'symbols': ['R_100'],  # Start with one symbol
            'initial_balance': 10000,
            'max_risk': 0.02,  # 2% max risk per trade
            'max_daily_loss': 0.05,  # 5% max daily loss
            'risk_per_trade': 0.01,  # 1% risk per trade
            'max_open_trades': 3,
            'timeframe': '1m',
            'short_window': 5,
            'medium_window': 10,  # Reduced for faster testing
            'long_window': 20,    # Reduced for faster testing
            'atr_period': 14
        }

        cyan_status("Initializing backtest engine...")
        engine = BacktestEngine(api_connector, config)

        cyan_status(f"Running backtest from {start_date} to {end_date}")
        results = await engine.run(start_date, end_date)

        # Log results
        if results:
            green_success("Backtest completed successfully")
            
            # Performance metrics
            metrics = results.get('metrics', {})
            logger.info("\nPerformance Metrics:")
            logger.info(f"Total Trades: {metrics.get('total_trades', 0)}")
            logger.info(f"Win Rate: {metrics.get('win_rate', 0):.2f}")
            logger.info(f"Net Profit: ${metrics.get('net_profit', 0):.2f}")
            logger.info(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
            
            # Risk metrics
            risk_metrics = results.get('risk_metrics', {})
            logger.info("\nRisk Metrics:")
            logger.info(f"Final Balance: ${risk_metrics.get('account_balance', 0):.2f}")
            logger.info(f"Open Risk %: {risk_metrics.get('open_risk_pct', 0):.2f}%")
            
            # Log number of trades
            trades = results.get('trades', [])
            logger.info(f"\nTotal trades executed: {len(trades)}")
            
            # Log example trades (first 3)
            if trades:
                logger.info("\nExample trades:")
                for i, trade in enumerate(trades[:3]):
                    logger.info(f"Trade {i+1}: {trade}")
        else:
            magenta_warning("Backtest completed but no results were returned")

    except Exception as e:
        red_error(f"Backtest failed: {str(e)}")
        logger.error(f"Backtest failed: {str(e)}", exc_info=True)
    finally:
        if api_connector:
            try:
                await api_connector.disconnect()
                logger.info("API connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing API connection: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(run_backtest())
    except KeyboardInterrupt:
        logger.info("Backtest interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
