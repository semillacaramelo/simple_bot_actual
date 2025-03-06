import logging
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
            # Check if already subscribed to avoid duplicate subscriptions
            if symbol in self._subscriptions:
                self.logger.info(f"Already subscribed to {symbol}, skipping initialization")
                return

            # Get initial price data
            await self._update_price(symbol)

            # Get historical data
            await self._update_history(symbol)

            # Subscribe to price updates using DerivAPI subscription
            source = await self.api.subscribe_to_price(symbol, self._price_update_callback)
            if source:
                self._subscriptions[symbol] = source
                self.logger.info(f"Successfully subscribed to {symbol} price updates")

        except Exception as e:
            self.logger.error(f"Error initializing {symbol}: {str(e)}")

    async def clear_symbol(self, symbol: str):
        """Clear cached data for symbol

        Args:
            symbol (str): Trading symbol
        """
        try:
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
            self.logger.error(f"Error clearing {symbol}: {str(e)}")

    def _price_update_callback(self, price_data: Dict):
        """Handle real-time price updates from subscription

        Args:
            price_data (dict): Price update data
        """
        try:
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
            self.logger.error(f"Error in price update callback: {str(e)}")

    async def _update_price(self, symbol: str):
        """Update latest price data

        Args:
            symbol (str): Trading symbol
        """
        try:
            # Get current price
            price_data = await self.api.get_price(symbol)
            if not price_data:
                return

            self._price_cache[symbol] = price_data
            self._last_update[symbol] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"Error updating price for {symbol}: {str(e)}")

    async def _update_history(self, symbol: str, count: int = 100, end: Optional[int] = None):
        """Update historical price data

        Args:
            symbol (str): Trading symbol
            count (int): Number of candles to request
            end (int, optional): End time in epoch seconds
        """
        try:
            self.logger.info(f"Fetching historical data for {symbol} - count: {count}, end: {end}")

            # Get candle data
            candles = await self.api.get_candles(
                symbol,
                count=count,
                interval=1,  # 1-minute default interval
                interval_unit='m',
                end=end
            )

            if candles is None:
                self.logger.error(f"No candle data received for {symbol}")
                return

            # Convert to DataFrame
            df = pd.DataFrame(candles)

            if df.empty:
                self.logger.error(f"Empty DataFrame after conversion for {symbol}")
                return

            # Convert epoch to datetime without timezone first, then localize to UTC
            df['timestamp'] = pd.to_datetime(df['epoch'], unit='s')
            df = df.set_index('timestamp')

            self.logger.info(f"Received {len(df)} candles for {symbol}")
            self.logger.info(f"Data range: {df.index.min()} to {df.index.max()}")

            # Store in cache
            self._history_cache[symbol] = df
            self._last_update[symbol] = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"Error updating history for {symbol}: {str(e)}")

    async def get_historical_data(self, symbol: str,
                                count: int = None,
                                end: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Get historical price data

        Args:
            symbol (str): Trading symbol
            count (int): Number of candles to return
            end (int, optional): End time in epoch seconds

        Returns:
            DataFrame: Historical price data
        """
        try:
            # Update history if needed or first time
            if symbol not in self._history_cache:
                self.logger.info(f"Initial historical data fetch for {symbol}")
                await self._update_history(symbol, count if count is not None else 100, end)

            df = self._history_cache.get(symbol)
            if df is None:
                self.logger.warning(f"No cached data available for {symbol}")
                return None

            if df.empty:
                self.logger.warning(f"Empty DataFrame in cache for {symbol}")
                return None

            if count is not None:
                result = df.tail(count)
                self.logger.info(f"Returning {len(result)} candles for {symbol}")
                return result

            self.logger.info(f"Returning all {len(df)} candles for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error getting history for {symbol}: {str(e)}")
            return None

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            float: Latest price if available
        """
        try:
            price_data = self._price_cache.get(symbol)
            if price_data and 'price' in price_data:
                return float(price_data['price'])
            return None

        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None

    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols

        Returns:
            list: Available symbols
        """
        return list(self._price_cache.keys())

    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            bool: True if market is open
        """
        try:
            price_data = self._price_cache.get(symbol)
            if not price_data:
                return False

            return price_data.get('is_trading', False)

        except Exception as e:
            self.logger.error(f"Error checking market for {symbol}: {str(e)}")
            return False

    def get_trading_times(self, symbol: str) -> Dict:
        """Get trading hours for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            dict: Trading times information
        """
        try:
            return self.api.get_trading_times(symbol)

        except Exception as e:
            self.logger.error(
                f"Error getting trading times for {symbol}: {str(e)}"
            )
            return {}

    async def get_price(self, symbol: str) -> Optional[Dict]:
        """Get latest price data for symbol"""
        try:
            # Check if we already have this symbol in cache
            if symbol in self._price_cache and self._price_cache[symbol].get('is_trading', False):
                # Return cached price if we're already subscribed
                return self._price_cache[symbol]

            response = await self.api.get_price(symbol)
            if response:
                self._price_cache[symbol] = response
            return response
        except Exception as e:
            self.logger.error(f"Price request error in get_price: {str(e)}")
            return None