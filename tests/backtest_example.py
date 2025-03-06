import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta, timezone

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.deriv_connector import DerivConnector
from backtesting.engine import BacktestEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def run_backtest():
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

        # Configure backtest
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)  # Test with 1 day of data first

        config = {
            'symbols': ['R_100'],  # Start with one symbol
            'initial_balance': 10000,
            'max_risk': 0.02,  # 2% max risk per trade
            'max_daily_loss': 0.05,  # 5% max daily loss
            'risk_per_trade': 0.01,  # 1% risk per trade
            'max_open_trades': 3,
            'timeframe': '1m',
            'short_window': 5,
            'medium_window': 20,
            'long_window': 50,
            'atr_period': 14
        }

        logger.info("Initializing backtest engine...")
        engine = BacktestEngine(api_connector, config)

        logger.info(f"Running backtest from {start_date} to {end_date}")
        results = await engine.run(start_date, end_date)

        # Log results
        if results:
            logger.info("Backtest completed successfully")
            logger.info(f"Performance metrics: {results['metrics']}")
            logger.info(f"Risk metrics: {results['risk_metrics']}")
            logger.info(f"Total trades executed: {len(results['trades'])}")

            # Log some example trades
            if results['trades']:
                logger.info("Example trades:")
                for trade in results['trades'][:3]:  # Show first 3 trades
                    logger.info(f"Trade: {trade}")
        else:
            logger.error("Backtest failed to produce results")

    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_backtest())