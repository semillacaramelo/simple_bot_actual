import logging
import asyncio
from typing import Dict, Any, Optional, Callable, Tuple
from deriv_api import DerivAPI
from datetime import datetime, timezone

logger = logging.getLogger('deriv_connector')
logger.setLevel(logging.INFO)

class DerivConnector:
    def __init__(self, api_token: str, app_id: int):
        """Initialize Deriv API connector using the official library

        Args:
            api_token: API token for authentication
            app_id: Application ID
        """
        self.api_token = api_token
        self.app_id = app_id
        self.api = None
        self.connected = False
        self.authorized = False
        self.active_subscriptions = set()  # Track active symbol subscriptions

    async def connect(self) -> Tuple[bool, Optional[str]]:
        """Establish API connection using DerivAPI and return connection status and error message

        Returns:
            Tuple[bool, Optional[str]]: Connection status and error message if failed
        """
        try:
            # Initialize API with app_id
            self.api = DerivAPI(app_id=self.app_id)

            # Authorize using token
            authorize = await self.api.authorize(self.api_token)
            if authorize and 'error' not in authorize:
                self.authorized = True
                self.connected = True
                logger.info("Connected and authorized with Deriv API")
                return True, None
            else:
                error = authorize.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Authorization failed: {error}")
                return False, f"Authorization failed: {error}"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection error: {error_msg}")
            self.connected = False
            self.authorized = False
            return False, error_msg

    async def disconnect(self):
        """Close API connection"""
        try:
            if self.api:
                # First try to forget all subscriptions
                try:
                    if self.connected and self.authorized:
                        await self.api.forget_all('ticks')
                        logger.info("Unsubscribed from all ticks")
                except Exception as unsub_error:
                    logger.error(f"Error unsubscribing from ticks: {str(unsub_error)}")
                
                # Then clear API connection
                await self.api.clear()
                self.connected = False
                self.authorized = False
                self.active_subscriptions.clear()  # Clear all subscriptions
                logger.info("Disconnected from Deriv API")
        except Exception as e:
            logger.error(f"Disconnection error: {str(e)}")

    async def subscribe_to_price(self, symbol: str, callback: Callable) -> Optional[Any]:
        """Subscribe to price updates for a symbol
        
        Args:
            symbol (str): Symbol to subscribe to
            callback (Callable): Callback function for price updates
            
        Returns:
            Optional[Any]: Subscription source object if successful
        """
        try:
            if not self.connected:
                logger.info("Connection was lost, attempting to reconnect in subscribe_to_price")
                connect_success, error_message = await self.connect()
                if not connect_success:
                    logger.error(f"Reconnection failed in subscribe_to_price: {error_message}")
                    return None
            
            # Check if we already have a subscription for this symbol
            if symbol in self.active_subscriptions:
                logger.info(f"Already subscribed to {symbol}")
                # Return the existing subscription or None to indicate we're already subscribed
                return None
            
            # Subscribe to the symbol
            source = await self.api.subscribe({'ticks': symbol})
            if source:
                subscription = source.subscribe(callback)
                self.active_subscriptions.add(symbol)
                logger.info(f"Successfully subscribed to {symbol}")
                return source
            return None
            
        except Exception as e:
            logger.error(f"Subscribe to price error: {str(e)}")
            return None
            
    async def proposal(self, proposal_params: Dict) -> Optional[Dict]:
        """Send proposal request to API

        Args:
            proposal_params (dict): Proposal parameters

        Returns:
            dict: Proposal response
        """
        try:
            if not self.connected:
                logger.info("Connection was lost, attempting to reconnect in proposal")
                connect_success, error_message = await self.connect()
                if not connect_success:
                    logger.error(f"Reconnection failed in proposal: {error_message}")
                    return None

            response = await self.api.proposal(proposal_params)
            return response

        except Exception as e:
            logger.error(f"Proposal request error: {str(e)}")
            return None

    async def check_connection_health(self) -> bool:
        """Check connection health by sending a time request"""
        try:
            if not self.connected:
                logger.warning("Connection health check failed because not connected.")
                return False

            time_response = await self.api.time()
            if time_response and 'error' not in time_response:
                logger.debug("Connection health check successful.")
                return True
            else:
                logger.warning(f"Connection health check failed: Time API error: {time_response.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error during connection health check: {str(e)}")
            return False

    async def get_price(self, symbol: str) -> Optional[Dict]:
        """Get current price for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            dict: Price information
        """
        try:
            if not self.connected:
                logger.info("Connection was lost, attempting to reconnect in get_price")
                connect_success, error_message = await self.connect()
                if not connect_success:
                    logger.error(f"Reconnection failed in get_price: {error_message}")
                    return None
            
            # If already subscribed, make a simpler request for the current state
            if symbol in self.active_subscriptions:
                # Use a different method to get the current price without subscription
                response = await self.api.proposal({
                    'proposal': 1,
                    'amount': 1,
                    'currency': 'USD',
                    'duration': 1,
                    'duration_unit': 'm',
                    'symbol': symbol,
                    'contract_type': 'CALL'
                })
                
                if response and 'error' not in response and 'proposal' in response:
                    return {
                        'symbol': symbol,
                        'price': response['proposal']['spot'],
                        'epoch': int(datetime.now(timezone.utc).timestamp()),
                        'is_trading': True
                    }
            else:
                # Regular ticks request with subscription
                response = await self.api.ticks({'ticks': symbol})
                if response and 'error' not in response:
                    # Add to active subscriptions
                    self.active_subscriptions.add(symbol)
                    return {
                        'symbol': symbol,
                        'price': response['tick']['quote'],
                        'epoch': response['tick']['epoch'],
                        'is_trading': True
                    }
            return None

        except Exception as e:
            logger.error(f"Price request error in get_price: {str(e)}")
            return None

    async def get_candles(self, symbol: str, count: int = 100,
                         interval: int = 1, interval_unit: str = 'm',
                         end: Optional[int] = None) -> Optional[list]:
        """Get historical candle data

        Args:
            symbol (str): Trading symbol
            count (int): Number of candles
            interval (int): Candle interval
            interval_unit (str): Interval unit (m/h/d)
            end (int, optional): End time in epoch seconds

        Returns:
            list: Candle data
        """
        try:
            if not self.connected:
                logger.info("Connection was lost, attempting to reconnect in get_candles")
                connect_success, error_message = await self.connect()
                if not connect_success:
                    logger.error(f"Reconnection failed in get_candles: {error_message}")
                    return None

            # Convert interval to seconds
            interval_map = {'m': 60, 'h': 3600, 'd': 86400}
            style = interval * interval_map.get(interval_unit, 60)

            # Set end time to current time if not provided
            if end is None:
                end = int(datetime.now(timezone.utc).timestamp())

            response = await self.api.ticks_history({
                'ticks_history': symbol,
                'count': count,
                'style': 'candles',
                'granularity': style,
                'end': end
            })

            if response and 'error' not in response:
                return response['candles']
            return None

        except Exception as e:
            logger.error(f"Candle request error in get_candles: {str(e)}")
            return None

    async def subscribe_to_price(self, symbol: str, callback: Callable):
        """Subscribe to price updates

        Args:
            symbol (str): Trading symbol
            callback: Callback function for updates
        """
        try:
            if not self.connected:
                logger.info("Connection was lost, attempting to reconnect in subscribe_to_price")
                connect_success, error_message = await self.connect()
                if not connect_success:
                    logger.error(f"Reconnection failed in subscribe_to_price: {error_message}")
                    return None

            # Skip if already subscribed to this symbol
            if symbol in self.active_subscriptions:
                logger.info(f"Already subscribed to {symbol}, reusing existing subscription")
                return True

            # Create subscription
            source = await self.api.subscribe({'ticks': symbol})

            # Subscribe with callback
            if source:
                source.subscribe(callback)
                self.active_subscriptions.add(symbol)
                return source
            return None

        except Exception as e:
            logger.error(f"Subscription error in subscribe_to_price: {str(e)}")
            return None

    def get_trading_times(self, symbol: str) -> Dict:
        """Get trading hours for symbol

        Args:
            symbol (str): Trading symbol

        Returns:
            dict: Trading times
        """
        return {
            'open': '00:00:00',
            'close': '23:59:59',
            'settlement': '23:59:59',
            'trading_days': [1, 2, 3, 4, 5]  # Monday to Friday
        }