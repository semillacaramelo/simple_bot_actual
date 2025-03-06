import logging
import time
from typing import Dict, Optional, List
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import asyncio
from .deriv_connector import DerivConnector

class DataFetcher:
    def __init__(self, api_connector: DerivConnector):
        """Initialize data fetcher

        Args:
            api_connector: Deriv API connector
        """
        self.api = api_connector
        self.logger = logging.getLogger(__name__)
        self._price_cache: Dict[str, Dict] = {}
        self._history_cache: Dict[str, pd.DataFrame] = {}
        self._last_update = {}
        self._update_interval = 60  # Update cache every minute
        self._subscriptions = {}

    async def initialize_symbol(self, symbol: str):
        """Initialize data collection for symbol

        Args:
            symbol (str): Trading symbol
        """
        try:
            self.logger.info(f"DEBUG: Initializing data for symbol: {symbol}")
            # Check if already subscribed to avoid duplicate subscriptions
            if symbol in self._subscriptions:
                self.logger.info(f"DEBUG: Already subscribed to {symbol}, skipping initialization")
                return

            # Get initial price data
            await self._update_price(symbol)

            # Get historical data
            await self._update_history(symbol)

            # Subscribe to price updates using DerivAPI subscription
            source = await self.api.subscribe_to_price(symbol, self._price_update_callback)
            if source:
                self._subscriptions[symbol] = source
                self.logger.info(f"DEBUG: Successfully subscribed to {symbol} price updates")

        except Exception as e:
            self.logger.error(f"ERROR: Error initializing {symbol}: {str(e)}", exc_info=True)

    async def clear_symbol(self, symbol: str):
        """Clear cached data for symbol

        Args:
            symbol (str): Trading symbol
        """
        try:
            self.logger.info(f"DEBUG: Clearing data for symbol: {symbol}")
            # Dispose RxPY subscription if exists
            if symbol in self._subscriptions:
                self._subscriptions[symbol].dispose()
                del self._subscriptions[symbol]

            # Clear caches
            if symbol in self._price_cache:
                del self._price_cache[symbol]
            if symbol in self._history_cache:
                del self._history_cache[symbol]
            if symbol in self._last_update:
                del self._last_update[symbol]

        except Exception as e:
            self.logger.error(f"ERROR: Error clearing {symbol}: {str(e)}", exc_info=True)

    def _price_update_callback(self, price_data: Dict):
        """Handle real-time price updates from subscription

        Args:
            price_data (dict): Price update data
        """
        try:
            self.logger.debug(f"DEBUG: Received price update: {price_data}")
            if 'tick' in price_data:
                tick = price_data['tick']
                symbol = tick['symbol']

                self._price_cache[symbol] = {
                    'symbol': symbol,
                    'price': tick['quote'],
                    'epoch': tick['epoch'],
                    'is_trading': True
                }
                self._last_update[symbol] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"ERROR: Error in price update callback: {str(e)}", exc_info=True)

    async def _update_price(self, symbol: str):
        """Update latest price data

        Args:
            symbol (str): Trading symbol
        """
        try:
            self.logger.info(f"DEBUG: Updating price for symbol: {symbol}")
            # Get current price
            price_data = await self.api.get_price(symbol)
            if not price_data:
                self.logger.warning(f"WARNING: No price data received for {symbol}")
                return

            self._price_cache[symbol] = price_data
            self._last_update[symbol] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"ERROR: Error updating price for {symbol}: {str(e)}", exc_info=True)

    async def _update_history(self, symbol: str, count: int = 100, end: Optional[int] = None):
        """Update historical price data

        Args:
            symbol (str): Trading symbol
            count (int): Number of candles to request
            end (int, optional): End time in epoch seconds
        """
        try:
            self.logger.info(f"DEBUG: Fetching historical data for {symbol} - count: {count}, end: {end}")

            # Get candle data
            start_time = time.time()
            candles = await self.api.get_candles(
                symbol,
                count=count,
                interval=1,  # 1-minute default interval
                interval_unit='m',
                end=end
            )
            elapsed = time.time() - start_time
            self.logger.info(f"DEBUG: API response time for historical data: {elapsed:.2f}s")


            if candles is None:
                self.logger.error(f"ERROR: No candle data received for {symbol}")
                return

            # Convert to DataFrame
            df = pd.DataFrame(candles)

            if df.empty:
                self.logger.error(f"ERROR: Empty DataFrame after conversion for {symbol}")
                return

            # Convert epoch to datetime without timezone first, then localize to UTC
            df['timestamp'] = pd.to_datetime(df['epoch'], unit='s')
            df = df.set_index('timestamp')

            self.logger.info(f"DEBUG: Received {len(df)} candles for {symbol}")
            self.logger.info(f"DEBUG: Data range: {df.index.min()} to {df.index.max()}")

            # Store in cache
            self._history_cache[symbol] = df
            self._last_update[symbol] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"ERROR: Error updating history for {symbol}: {str(e)}", exc_info=True)

    async def get_historical_data(self, symbol: str, count: int = 100, from_dt=None, to_dt=None) -> Optional[pd.DataFrame]:
        """Get historical candle data for technical analysis

        Args:
            symbol (str): Trading symbol
            count (int): Number of candles
            from_dt: Start datetime
            to_dt: End datetime

        Returns:
            DataFrame: Historical price data
        """
        try:
            self.logger.info(f"DEBUG: Fetching {count} candles for {symbol}")

            # Get candles from API with timestamp for tracking
            start_time = time.time()
            candles = await self.api.get_candles(
                symbol=symbol,
                count=count
            )
            elapsed = time.time() - start_time

            # Log the response time for monitoring API performance
            self.logger.info(f"DEBUG: API response time for candles: {elapsed:.2f}s")

            if not candles:
                self.logger.error(f"ERROR: No candle data returned for {symbol}")
                return None

            if len(candles) < 5:
                self.logger.warning(f"WARNING: Insufficient candle data for {symbol}: only {len(candles)} candles received")
                return None

            self.logger.info(f"DEBUG: Received {len(candles)} candles for {symbol}")

            # Convert to DataFrame with detailed logging
            data = []
            for candle in candles:
                try:
                    data.append({
                        'epoch': candle['epoch'],
                        'open': float(candle['open']),
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close'])
                    })
                except (KeyError, ValueError) as e:
                    self.logger.error(f"ERROR: Invalid candle data: {e} - Candle: {candle}", exc_info=True)

            if not data:
                self.logger.error(f"ERROR: Failed to process any candles for {symbol}")
                return None

            df = pd.DataFrame(data)

            # Add datetime column for easier analysis
            df['date'] = pd.to_datetime(df['epoch'], unit='s')
            df.set_index('date', inplace=True)

            # Log data summary statistics
            first_date = df.index[0].strftime('%Y-%m-%d %H:%M:%S')
            last_date = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
            self.logger.info(f"DEBUG: Historical data summary for {symbol}: {len(df)} rows from {first_date} to {last_date}")

            return df

        except Exception as e:
            self.logger.error(f"ERROR: Error getting historical data for {symbol}: {str(e)}", exc_info=True)
            return None

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            float: Latest price if available
        """
        try:
            self.logger.debug(f"DEBUG: Getting latest price for {symbol}")
            price_data = self._price_cache.get(symbol)
            if price_data and 'price' in price_data:
                return float(price_data['price'])
            return None

        except Exception as e:
            self.logger.error(f"ERROR: Error getting price for {symbol}: {str(e)}", exc_info=True)
            return None

    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols

        Returns:
            list: Available symbols
        """
        self.logger.debug(f"DEBUG: Getting available symbols")
        return list(self._price_cache.keys())

    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            bool: True if market is open
        """
        try:
            self.logger.debug(f"DEBUG: Checking market status for {symbol}")
            price_data = self._price_cache.get(symbol)
            if not price_data:
                return False

            return price_data.get('is_trading', False)

        except Exception as e:
            self.logger.error(f"ERROR: Error checking market for {symbol}: {str(e)}", exc_info=True)
            return False

    def get_trading_times(self, symbol: str) -> Dict:
        """Get trading hours for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            dict: Trading times information
        """
        try:
            self.logger.info(f"DEBUG: Getting trading times for {symbol}")
            return self.api.get_trading_times(symbol)

        except Exception as e:
            self.logger.error(
                f"ERROR: Error getting trading times for {symbol}: {str(e)}", exc_info=True
            )
            return {}

    async def get_price(self, symbol: str) -> Optional[Dict]:
        """Get latest price data for symbol"""
        try:
            self.logger.info(f"DEBUG: Getting price for symbol: {symbol}")
            # Check if we already have this symbol in cache
            if symbol in self._price_cache and self._price_cache[symbol].get('is_trading', False):
                # Return cached price if we're already subscribed
                self.logger.debug(f"DEBUG: Returning cached price for {symbol}")
                return self._price_cache[symbol]

            response = await self.api.get_price(symbol)
            if response:
                self._price_cache[symbol] = response
            return response
        except Exception as e:
            self.logger.error(f"ERROR: Price request error in get_price: {str(e)}", exc_info=True)
            return None