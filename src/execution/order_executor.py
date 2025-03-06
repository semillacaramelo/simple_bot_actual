import logging
import asyncio
from typing import Dict, Optional
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from src.utils.console import blue_status, cyan_status, green_success, red_error, magenta_warning, yellow_signal, white_wait

class OrderExecutor:
    def __init__(self, api_connector, performance_tracker=None, risk_manager=None):
        """Initialize order executor

        Args:
            api_connector: Deriv API connector
            performance_tracker: Optional performance tracking component
            risk_manager: Optional risk management component
        """
        self.api = api_connector
        self.performance_tracker = performance_tracker
        self.risk_manager = risk_manager
        self.logger = logging.getLogger(__name__)
        self.active_contracts = {}
        self.subscriptions = {}
        cyan_status("OrderExecutor initialized")

    async def execute_order(self, signal: Dict) -> Optional[Dict]:
        """Execute trading signal

        Args:
            signal (dict): Trading signal with trade parameters

        Returns:
            dict: Order details if successful
        """
        signal_id = signal.get('id', str(uuid.uuid4())[:8])
        self.logger.info(f"Executing order for signal ID: {signal_id}", 
                         extra={'signal_type': signal['type'], 'symbol': signal['symbol']})
        yellow_signal(f"💰 Processing {signal['type']} signal for {signal['symbol']} (ID: {signal_id})")
        
        # Log signal details for debugging
        self.logger.info(f"DEBUG: Signal details", extra={
            'signal_id': signal_id,
            'signal_type': signal['type'],
            'symbol': signal['symbol'],
            'entry_price': signal.get('entry_price'),
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('take_profit'),
            'time': datetime.now().strftime('%H:%M:%S')
        })

        try:
            if not await self.validate_signal(signal):
                self.logger.warning("Signal validation failed")
                magenta_warning(f"Signal validation failed for {signal['symbol']}")
                return None

            # Calculate position size if risk manager present
            if self.risk_manager:
                blue_status("Calculating position size with risk manager...")
                signal = await self.risk_manager.calculate_position_size(signal)

            # Get contract details
            contracts_for_request = {
                "contracts_for": signal['symbol'],
                "currency": "USD",
                "landing_company": "svg",
                "product_type": "basic"
            }

            self.logger.info(f"Sending contracts_for request: {contracts_for_request}")
            blue_status(f"Fetching contract details for {signal['symbol']}...")
            contracts_for_response = await self.api.api.contracts_for(contracts_for_request)
            self.logger.info(f"Contracts for response: {contracts_for_response}")

            if not contracts_for_response or 'error' in contracts_for_response:
                error_msg = contracts_for_response.get('error', {}).get('message', 'Failed to fetch contract details')
                self.logger.error(f"Failed to fetch contract details: {error_msg}")
                red_error(f"Failed to fetch contract details: {error_msg}")
                return None

            # Validate contract type
            available_contracts = contracts_for_response.get('contracts_for', {}).get('available', [])
            is_contract_type_valid = any(contract['contract_type'] == signal['type'] for contract in available_contracts)

            if not is_contract_type_valid:
                self.logger.error(f"Invalid contract type: {signal['type']} for symbol: {signal['symbol']}")
                return None

            # Find minimum duration
            min_duration = next(
                (contract.get('min_contract_duration') for contract in available_contracts
                 if contract['contract_type'] == signal['type']),
                '5m'
            )

            duration = int(min_duration[:-1])  # Remove 'm' and convert to int
            duration_unit = min_duration[-1]   # Get 'm' from '5m'

            # Create proposal
            proposal = {
                "proposal": 1,
                "contract_type": signal['type'],
                "currency": "USD",
                "symbol": signal['symbol'],
                "amount": signal['stake_amount'],
                "basis": "stake",
                "duration": signal.get('duration', duration),
                "duration_unit": signal.get('duration_unit', duration_unit)
            }

            # Get proposal
            self.logger.info(f"Sending proposal request: {proposal}")
            blue_status(f"Requesting price proposal for {signal['type']} contract...")
            response = await self.api.api.proposal(proposal)
            self.logger.info(f"Proposal response: {response}")

            if response and 'error' not in response:
                # Buy contract with detailed logging
                buy_request = {
                    "buy": response['proposal']['id'],
                    "price": response['proposal']['ask_price']
                }

                signal_id = signal.get('id', 'unknown')
                self.logger.info(f"DEBUG: Sending buy request for signal {signal_id}", 
                                extra={'buy_request': buy_request, 'proposal_id': response['proposal']['id']})
                yellow_signal(f"💸 Executing {signal['type']} order for {signal['stake_amount']} USD on {signal['symbol']}...")
                
                try:
                    buy_response = await self.api.api.buy(buy_request)
                    self.logger.info(f"DEBUG: Buy response received: {buy_response}")
                    
                    if 'error' in buy_response:
                        error_msg = buy_response['error'].get('message', 'Unknown error')
                        self.logger.error(f"Buy order failed for signal {signal_id}: {error_msg}")
                        red_error(f"❌ Buy order failed: {error_msg}")
                    else:
                        self.logger.info(f"Buy order successful for signal {signal_id}", 
                                        extra={'contract_id': buy_response.get('buy', {}).get('contract_id', 'unknown')})
                except Exception as e:
                    self.logger.error(f"Exception during buy order execution: {str(e)}", exc_info=True)
                    red_error(f"❌ Exception during buy order: {str(e)}")
                    buy_response = None

                if buy_response and 'error' not in buy_response:
                    contract = buy_response['buy']

                    # Create order record
                    order = {
                        'order_id': str(uuid.uuid4()),
                        'contract_id': contract['contract_id'],
                        'symbol': signal['symbol'],
                        'type': signal['type'],
                        'stake_amount': signal['stake_amount'],
                        'entry_price': float(contract['buy_price']),
                        'stop_loss': signal.get('stop_loss'),
                        'take_profit': signal.get('take_profit'),
                        'status': 'open',
                        'entry_time': datetime.now(timezone.utc).timestamp()
                    }

                    # Store and monitor contract
                    self.active_contracts[order['order_id']] = order
                    await self._subscribe_to_contract(order)

                    self.logger.info(
                        f"Order executed - ID: {order['order_id']}",
                        extra={'order': order}
                    )
                    green_success(f"Order executed successfully - ID: {order['order_id']} - Price: {order['entry_price']}")

                    return order
                else:
                    error = buy_response.get('error', {}).get('message', 'Unknown error')
                    self.logger.error(f"Contract buy failed: {error}")
                    red_error(f"Contract buy failed: {error}")
            else:
                error = response.get('error', {}).get('message', 'Unknown error')
                self.logger.error(f"Proposal failed: {error}")
                red_error(f"Price proposal failed: {error}")

            return None

        except Exception as e:
            self.logger.error(f"Error executing order: {str(e)}")
            return None

    async def close_position(self, order_id: str, price: Optional[float] = None) -> bool:
        """Close trading position

        Args:
            order_id (str): Order identifier
            price (float, optional): Current market price for validation

        Returns:
            bool: True if successful
        """
        try:
            blue_status(f"Attempting to close position {order_id}...")
            order = self.active_contracts.get(order_id)
            if not order:
                self.logger.warning(f"Order {order_id} not found in active contracts")
                magenta_warning(f"Order {order_id} not found in active contracts")
                return False

            if price is None:
                self.logger.error("Required parameter missing: price")
                red_error("Cannot close position: current price not provided")
                return False

            # Validate closing conditions
            if order['type'] == 'CALL':
                if order.get('stop_loss') and price <= order['stop_loss']:
                    self.logger.info(f"Stop loss triggered at {price}")
                elif order.get('take_profit') and price >= order['take_profit']:
                    self.logger.info(f"Take profit triggered at {price}")
            else:  # PUT
                if order.get('stop_loss') and price >= order['stop_loss']:
                    self.logger.info(f"Stop loss triggered at {price}")
                elif order.get('take_profit') and price <= order['take_profit']:
                    self.logger.info(f"Take profit triggered at {price}")

            # Sell contract
            response = await self.api.api.sell({
                "sell": order['contract_id']
            })

            if response and 'error' not in response:
                sold = response['sell']

                # Update order record
                order['status'] = 'closed'
                order['exit_time'] = datetime.now(timezone.utc).timestamp()
                order['exit_price'] = float(sold['sold_for'])
                order['profit_loss'] = float(sold['profit'])

                # Notify components
                if self.performance_tracker:
                    self.performance_tracker.record_trade(order)
                if self.risk_manager:
                    await self.risk_manager.record_trade_result(order)

                # Clean up subscription
                if order_id in self.subscriptions:
                    self.subscriptions[order_id].dispose()
                    del self.subscriptions[order_id]

                # Remove from active contracts
                del self.active_contracts[order_id]

                self.logger.info(
                    f"Position closed - ID: {order_id}, P/L: {order['profit_loss']:.2f}",
                    extra={'order': order}
                )
                
                # Use appropriate color based on profit/loss
                if order['profit_loss'] > 0:
                    green_success(f"Position closed with profit! ID: {order_id}, P/L: +{order['profit_loss']:.2f}")
                else:
                    magenta_warning(f"Position closed with loss - ID: {order_id}, P/L: {order['profit_loss']:.2f}")

                return True
            else:
                error = response.get('error', {}).get('message', 'Unknown error')
                self.logger.error(f"Contract sell failed: {error}")
                red_error(f"Failed to close position: {error}")
                return False

        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")
            return False

    async def _subscribe_to_contract(self, order: Dict):
        """Subscribe to contract updates

        Args:
            order (dict): Order details
        """
        try:
            source = await self.api.api.subscribe({
                "proposal_open_contract": 1,
                "contract_id": order['contract_id']
            })

            self.subscriptions[order['order_id']] = source.subscribe(
                lambda update: self._handle_contract_update(order['order_id'], update)
            )

            self.logger.info(f"Subscribed to contract updates - ID: {order['order_id']}")

        except Exception as e:
            self.logger.error(f"Error subscribing to contract: {str(e)}")

    def _handle_contract_update(self, order_id: str, data: Dict):
        """Handle contract update from subscription

        Args:
            order_id (str): Order identifier
            data (dict): Contract update data
        """
        try:
            if 'error' in data:
                return

            contract = data.get('proposal_open_contract')
            if not contract:
                return

            order = self.active_contracts.get(order_id)
            if not order or order['status'] != 'open':
                return

            current_spot = float(contract['current_spot'])

            # Check exit conditions if stop loss or take profit set
            if order.get('stop_loss') or order.get('take_profit'):
                if order['type'] == 'CALL':
                    if ((order.get('stop_loss') and current_spot <= order['stop_loss']) or
                        (order.get('take_profit') and current_spot >= order['take_profit'])):
                        asyncio.create_task(self.close_position(order_id, price=current_spot))
                else:  # PUT
                    if ((order.get('stop_loss') and current_spot >= order['stop_loss']) or
                        (order.get('take_profit') and current_spot <= order['take_profit'])):
                        asyncio.create_task(self.close_position(order_id, price=current_spot))

        except Exception as e:
            self.logger.error(f"Error handling contract update: {str(e)}")

    async def validate_signal(self, signal: Dict) -> bool:
        """Validate trading signal

        Args:
            signal (dict): Trading signal to validate

        Returns:
            bool: True if signal is valid
        """
        try:
            # Basic validation
            required_fields = ['symbol', 'type', 'stake_amount']
            if not all(field in signal for field in required_fields):
                missing = [field for field in required_fields if field not in signal]
                self.logger.error(f"Missing required fields in signal: {missing}")
                return False

            # Check for volatility and ATR (required for risk calculation)
            if 'volatility' not in signal:
                self.logger.warning("Missing volatility in signal - required for risk assessment")
                # Don't fail validation, but log warning

            if 'atr_value' not in signal:
                self.logger.warning("Missing atr_value in signal - required for risk assessment")
                # Don't fail validation, but log warning

            # Optional fields validation
            if signal.get('stop_loss'):
                try:
                    float(signal['stop_loss'])
                except (ValueError, TypeError):
                    self.logger.error("Invalid stop_loss value")
                    return False

            if signal.get('take_profit'):
                try:
                    float(signal['take_profit'])
                except (ValueError, TypeError):
                    self.logger.error("Invalid take_profit value")
                    return False

            # Validate volatility if risk manager is present and volatility is provided
            if self.risk_manager and 'volatility' in signal:
                return await self.risk_manager.validate_signal(signal)

            # If no risk manager or volatility not provided, do basic volatility check
            if 'volatility' in signal:
                try:
                    volatility = float(signal['volatility'])
                    if volatility > 0.1:  # Basic high volatility check
                        self.logger.error(f"Volatility too high: {volatility}")
                        return False
                except (ValueError, TypeError):
                    self.logger.error("Invalid volatility value")
                    return False

            self.logger.info("Signal validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating signal: {str(e)}")
            return False

    def get_active_trades(self) -> Dict:
        """Get active trading positions

        Returns:
            dict: Active trades
        """
        return self.active_contracts

    def can_trade(self) -> bool:
        """Check if trading is allowed

        Returns:
            bool: True if trading is allowed
        """
        if self.risk_manager:
            return self.risk_manager.can_trade()
        return True