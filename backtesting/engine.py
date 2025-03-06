import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .simulator import SimulatedExecutor
from src.api.data_fetcher import DataFetcher
from src.risk.risk_manager import RiskManager
from src.monitor.performance import PerformanceTracker

class BacktestEngine:
    def __init__(self, api_connector, config: Dict):
        """Initialize backtesting engine

        Args:
            api_connector: DerivConnector instance
            config: Backtest configuration
        """
        self.logger = logging.getLogger(__name__)
        self.data_fetcher = DataFetcher(api_connector)
        self.simulator = SimulatedExecutor()
        self.performance = PerformanceTracker()
        self.risk_manager = RiskManager(
            max_risk=config.get('max_risk', 0.10),
            max_daily_loss=config.get('max_daily_loss', 0.05),
            risk_per_trade=config.get('risk_per_trade', 0.02),
            max_open_trades=config.get('max_open_trades', 3)
        )
        self.config = config

    async def run(self, start_date: datetime, end_date: datetime) -> Dict:
        """Run backtest simulation

        Args:
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            dict: Backtest results
        """
        try:
            self.logger.info(f"Starting backtest from {start_date} to {end_date}")

            # Initialize components
            await self.risk_manager.initialize(self.config.get('initial_balance', 10000))

            # Get historical data for symbols
            data = {}
            for symbol in self.config['symbols']:
                historical_data = await self._fetch_historical_data(
                    symbol, start_date, end_date
                )
                if historical_data is not None and not historical_data.empty:
                    data[symbol] = historical_data

            if not data:
                self.logger.error("No historical data available")
                raise ValueError("No historical data available")

            # Run simulation
            results = await self._run_simulation(data)

            # Generate performance report
            performance_metrics = self.performance.analyze_performance()

            return {
                'metrics': performance_metrics,
                'risk_metrics': self.risk_manager.get_risk_metrics(),
                'trades': self.simulator.get_trade_history()
            }

        except Exception as e:
            self.logger.error(f"Backtest failed: {str(e)}")
            raise

    async def _fetch_historical_data(self, symbol: str, 
                                   start_date: datetime,
                                   end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch historical data for symbol

        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame: Historical price data
        """
        try:
            # Calculate required candles based on timeframe
            timeframe = self.config.get('timeframe', '1m')
            td_map = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440}
            minutes = td_map.get(timeframe, 1)

            duration = end_date - start_date
            total_minutes = int(duration.total_seconds() / 60)
            required_candles = total_minutes // minutes

            # Fetch data in chunks to handle API limits
            chunk_size = 5000  # Deriv API limit
            data_chunks = []

            current_end = end_date
            while len(data_chunks) * chunk_size < required_candles:
                candles = await self.data_fetcher.get_historical_data(
                    symbol,
                    count=min(chunk_size, required_candles - len(data_chunks) * chunk_size),
                    end=int(current_end.timestamp())
                )

                if candles is None or candles.empty:
                    break

                data_chunks.append(candles)
                current_end = candles.index[0]

            if not data_chunks:
                self.logger.error(f"No historical data available for {symbol}")
                return None

            # Combine chunks and sort by time
            combined_data = pd.concat(data_chunks)
            combined_data = combined_data.sort_index()

            # Ensure consistent timezone handling
            # First make sure the dataframe index has no timezone
            if combined_data.index.tz is not None:
                combined_data.index = combined_data.index.tz_localize(None)
            
            # Convert start_date and end_date to pandas Timestamp objects without timezone
            pd_start_date = pd.Timestamp(start_date).tz_localize(None)
            pd_end_date = pd.Timestamp(end_date).tz_localize(None)
            
            # Filter to requested date range
            filtered_data = combined_data[(combined_data.index >= pd_start_date) & 
                                         (combined_data.index <= pd_end_date)]

            self.logger.info(f"Fetched {len(filtered_data)} candles for {symbol} from {pd_start_date} to {pd_end_date}")
            return filtered_data

        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None

    async def _run_simulation(self, historical_data: Dict[str, pd.DataFrame]) -> Dict:
        """Run trading simulation on historical data

        Args:
            historical_data: Dictionary of historical price data by symbol

        Returns:
            dict: Simulation results
        """
        try:
            # Align data timestamps across symbols
            timestamps = set()
            for df in historical_data.values():
                timestamps.update(df.index)
            timestamps = sorted(timestamps)

            # Simulate trading
            for timestamp in timestamps:
                # Update prices
                current_prices = {}
                for symbol, df in historical_data.items():
                    if timestamp in df.index:
                        current_prices[symbol] = df.loc[timestamp]

                if not current_prices:
                    continue

                # Generate signals
                for symbol, price_data in current_prices.items():
                    signal = self._generate_signal(symbol, price_data, historical_data[symbol])

                    if signal:
                        # Validate signal with risk manager
                        if await self.risk_manager.validate_signal(signal):
                            # Calculate position size
                            signal = await self.risk_manager.calculate_position_size(signal)

                            # Execute trade
                            trade = await self.simulator.execute_order(signal)
                            if trade:
                                self.risk_manager.add_position(trade)
                                self.performance.record_trade(trade)

                # Update open positions
                await self._update_positions(current_prices)

            return {
                'success': True,
                'message': 'Simulation completed successfully'
            }

        except Exception as e:
            self.logger.error(f"Error in simulation: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def _generate_signal(self, symbol: str, 
                       current_data: pd.Series,
                       historical_data: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal based on strategy

        Args:
            symbol: Trading symbol
            current_data: Current price data
            historical_data: Historical price data

        Returns:
            dict: Trading signal if generated
        """
        try:
            # Calculate volatility and ATR for risk management
            returns = historical_data['close'].pct_change()
            volatility = returns.std()

            high_low = historical_data['high'] - historical_data['low']
            high_close = abs(historical_data['high'] - historical_data['close'].shift())
            low_close = abs(historical_data['low'] - historical_data['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(window=self.config.get('atr_period', 14)).mean().iloc[-1]

            # Example strategy implementation (triple MA crossover)
            short_ma = historical_data['close'].rolling(
                window=self.config.get('short_window', 5)
            ).mean()
            medium_ma = historical_data['close'].rolling(
                window=self.config.get('medium_window', 20)
            ).mean()
            long_ma = historical_data['close'].rolling(
                window=self.config.get('long_window', 50)
            ).mean()

            # Check for crossover conditions
            if (short_ma.iloc[-1] > medium_ma.iloc[-1] and 
                short_ma.iloc[-2] <= medium_ma.iloc[-2] and
                medium_ma.iloc[-1] > long_ma.iloc[-1]):
                return {
                    'symbol': symbol,
                    'type': 'CALL',
                    'entry_price': current_data['close'],
                    'stop_loss': current_data['close'] * 0.99,  # 1% stop loss
                    'take_profit': current_data['close'] * 1.02,  # 2% take profit
                    'stake_amount': 100.0,  # Default stake, will be adjusted by risk manager
                    'volatility': volatility,
                    'atr_value': atr,
                    'duration': 5,
                    'duration_unit': 'm'
                }

            elif (short_ma.iloc[-1] < medium_ma.iloc[-1] and 
                  short_ma.iloc[-2] >= medium_ma.iloc[-2] and
                  medium_ma.iloc[-1] < long_ma.iloc[-1]):
                return {
                    'symbol': symbol,
                    'type': 'PUT',
                    'entry_price': current_data['close'],
                    'stop_loss': current_data['close'] * 1.01,  # 1% stop loss
                    'take_profit': current_data['close'] * 0.98,  # 2% take profit
                    'stake_amount': 100.0,  # Default stake, will be adjusted by risk manager
                    'volatility': volatility,
                    'atr_value': atr,
                    'duration': 5,
                    'duration_unit': 'm'
                }

            return None

        except Exception as e:
            self.logger.error(f"Error generating signal: {str(e)}")
            return None

    async def _update_positions(self, current_prices: Dict[str, pd.Series]):
        """Update open positions based on current prices

        Args:
            current_prices: Current price data by symbol
        """
        try:
            for position in self.simulator.get_active_trades().values():
                symbol = position['symbol']
                if symbol not in current_prices:
                    continue

                current_price = current_prices[symbol]['close']

                # Check stop loss and take profit
                if position['type'] == 'CALL':
                    if (current_price <= position['stop_loss'] or 
                        current_price >= position['take_profit']):
                        await self.simulator.close_position(
                            position['trade_id'],
                            current_price
                        )
                else:  # PUT
                    if (current_price >= position['stop_loss'] or 
                        current_price <= position['take_profit']):
                        await self.simulator.close_position(
                            position['trade_id'],
                            current_price
                        )

        except Exception as e:
            self.logger.error(f"Error updating positions: {str(e)}")