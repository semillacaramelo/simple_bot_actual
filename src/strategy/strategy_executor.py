import logging
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timezone
from .moving_average import MovingAverageStrategy
import pandas as pd
from src.utils.console import yellow_signal, blue_status, cyan_status, green_success, red_error, magenta_warning, white_wait

class StrategyExecutor:
    def __init__(self, data_fetcher, order_executor, **trading_params):
        """Initialize strategy executor

        Args:
            data_fetcher: Market data component
            order_executor: Order execution component
            trading_params: Trading parameters
        """
        self.data_fetcher = data_fetcher
        self.order_executor = order_executor
        self.logger = logging.getLogger(__name__)
        self.trading_params = trading_params

        # Initialize strategy
        self.moving_average = MovingAverageStrategy(
            data_fetcher,
            **trading_params
        )

        self.active_symbols = set()
        blue_status("StrategyExecutor initialized with parameters:")
        # Log key strategy parameters for visibility
        for param, value in {
            'Short Window': trading_params.get('SHORT_WINDOW', 5),
            'Medium Window': trading_params.get('MEDIUM_WINDOW', 20),
            'RSI Period': trading_params.get('RSI_PERIOD', 14),
            'Volatility Threshold': trading_params.get('VOLATILITY_THRESHOLD', 0.02)
        }.items():
            blue_status(f"  - {param}: {value}")

    async def execute_iteration(self, symbol: str):
        """Execute one iteration of the strategy

        Args:
            symbol (str): Trading symbol
        """
        try:
            cyan_status(f"Starting iteration for {symbol}")
            # Initialize symbol if needed
            if symbol not in self.active_symbols:
                await self.initialize_symbol(symbol)

            # Check if market is open
            if not self.data_fetcher.is_market_open(symbol):
                self.logger.info(f"Market closed for {symbol}")
                return

            # Get market data for calculations
            cyan_status(f"Fetching historical data for {symbol}")
            # Ensure we have more data for the 1-minute strategy
            historical_data = await self.data_fetcher.get_historical_data(
                symbol, 
                count=max(
                    self.trading_params.get('atr_period', 14),
                    self.trading_params.get('LONG_WINDOW', 50)
                ) + 50  # Increased buffer for better analysis
            )

            if historical_data is None or historical_data.empty:
                magenta_warning(f"No historical data available for {symbol}")
                return

            cyan_status(f"Calculating volatility and ATR for {symbol}")
            # Calculate volatility and ATR
            returns = historical_data['close'].pct_change().dropna()
            volatility = returns.std()

            high_low = historical_data['high'] - historical_data['low']
            high_close = abs(historical_data['high'] - historical_data['close'].shift())
            low_close = abs(historical_data['low'] - historical_data['close'].shift())

            # Create a DataFrame with the three series
            tr_df = pd.DataFrame({
                'hl': high_low,
                'hc': high_close,
                'lc': low_close
            })

            # Get the maximum value for each row
            true_range = tr_df.max(axis=1)
            atr = true_range.rolling(window=self.trading_params.get('atr_period', 14)).mean().iloc[-1]

            # Log market condition metrics
            self.logger.info(f"Market metrics - Volatility: {volatility:.6f}, ATR: {atr:.6f}, Last Price: {historical_data['close'].iloc[-1]:.4f}")
            blue_status(f"Current market conditions - Volatility: {volatility:.6f}, ATR: {atr:.6f}")

            # Generate trading signal
            cyan_status(f"Generating trading signal for {symbol}")
            signal = await self.moving_average.analyze_symbol(symbol)

            if signal:
                # Add volatility metrics
                signal['volatility'] = volatility
                signal['atr_value'] = atr
                # For 1-minute binary trades
                signal['duration'] = 1
                signal['duration_unit'] = 'm'

                yellow_signal(f"Generated signal: {signal['type']} at {signal['entry_price']:.4f}")

                if await self.validate_signal(signal):
                    green_success(f"Validated signal for {symbol}, executing order")
                    await self.order_executor.execute_order(signal)
                else:
                    magenta_warning(f"Signal for {symbol} failed validation")
            else:
                self.logger.debug(f"No signal generated for {symbol}")

        except Exception as e:
            red_error(f"Error executing strategy for {symbol}: {str(e)}")
            self.logger.exception(f"Error executing strategy for {symbol}")

    async def initialize_symbol(self, symbol: str):
        """Initialize symbol data and subscriptions

        Args:
            symbol (str): Trading symbol
        """
        try:
            cyan_status(f"Initializing symbol: {symbol}")
            # Initialize market data
            await self.data_fetcher.initialize_symbol(symbol)

            # Add to active symbols
            self.active_symbols.add(symbol)

            green_success(f"Initialized symbol: {symbol}")

        except Exception as e:
            red_error(f"Error initializing symbol {symbol}: {str(e)}")
            self.logger.exception(f"Error initializing symbol {symbol}")

    async def cleanup_symbol(self, symbol: str):
        """Clean up symbol data and subscriptions

        Args:
            symbol (str): Trading symbol
        """
        try:
            cyan_status(f"Cleaning up symbol: {symbol}")
            if symbol in self.active_symbols:
                # Clear market data
                await self.data_fetcher.clear_symbol(symbol)
                self.active_symbols.remove(symbol)

            green_success(f"Cleaned up symbol: {symbol}")

        except Exception as e:
            red_error(f"Error cleaning up symbol {symbol}: {str(e)}")
            self.logger.exception(f"Error cleaning up symbol {symbol}")

    async def validate_signal(self, signal: Dict) -> bool:
        """Validate trading signal

        Args:
            signal (dict): Trading signal

        Returns:
            bool: True if signal is valid
        """
        try:
            cyan_status("Validating signal")
            # Basic validation (relaxed for 1-minute trading)
            required_fields = ['symbol', 'type', 'entry_price', 'stop_loss', 
                              'take_profit', 'stake_amount', 'volatility', 
                              'atr_value', 'duration', 'duration_unit']

            if not all(field in signal for field in required_fields):
                missing = [field for field in required_fields if field not in signal]
                magenta_warning(f"Signal missing required fields: {missing}")
                return False

            # For 1-minute trading, ensure duration is appropriate
            if signal.get('duration', 0) > 5:
                magenta_warning(f"Signal duration too long for short-term strategy: {signal.get('duration')} {signal.get('duration_unit')}")
                # Adjust duration instead of rejecting
                signal['duration'] = 1
                signal['duration_unit'] = 'm'
                yellow_signal("Adjusted signal duration to 1 minute")

            # Validate with risk manager through order executor
            is_valid = await self.order_executor.validate_signal(signal)

            if is_valid:
                blue_status("Signal passed validation checks")
            else:
                magenta_warning("Signal rejected by risk manager validation")

            return is_valid

        except Exception as e:
            red_error(f"Error validating signal: {str(e)}")
            self.logger.exception(f"Error validating signal")
            return False

    def get_active_symbols(self) -> List[str]:
        """Get list of active trading symbols

        Returns:
            list: Active symbols
        """
        return list(self.active_symbols)

    def get_strategy_status(self) -> Dict:
        """Get strategy execution status

        Returns:
            dict: Strategy status
        """
        return {
            'active_symbols': list(self.active_symbols),
            'analyzing': len(self.active_symbols),
            'can_trade': self.order_executor.can_trade(),
            'strategy_parameters': {
                'short_window': self.trading_params.get('SHORT_WINDOW'),
                'medium_window': self.trading_params.get('MEDIUM_WINDOW'),
                'rsi_period': self.trading_params.get('RSI_PERIOD'),
                'volatility_threshold': self.trading_params.get('VOLATILITY_THRESHOLD')
            }
        }