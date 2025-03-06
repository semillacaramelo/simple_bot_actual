import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, date, time, timezone
from src.utils.console import blue_status, cyan_status, green_success, red_error, magenta_warning

@dataclass
class Position:
    """Trading position details"""
    trade_id: str
    symbol: str
    type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    stake_amount: float
    entry_time: float
    max_loss: float
    atr_value: Optional[float] = None
    volatility_score: Optional[float] = None

from src.utils.console import blue_status, cyan_status, green_success, red_error, magenta_warning, yellow_signal, white_wait

class RiskManager:
    def __init__(self, max_risk=0.10, max_daily_loss=0.05, 
                 risk_per_trade=0.02, max_open_trades=3, api_connector=None,
                 trading_hours=(time(9, 0), time(17, 0)),
                 min_volatility=0.01, max_volatility=0.05):
        """Initialize risk manager with risk parameters

        Args:
            max_risk (float): Maximum total risk as decimal (default: 10%)
            max_daily_loss (float): Maximum daily loss as decimal (default: 5%)
            risk_per_trade (float): Risk per trade as decimal (default: 2%)
            max_open_trades (int): Maximum concurrent open positions (default: 3)
            api_connector: Optional API connector for balance updates
            trading_hours (tuple): Trading hours (start_time, end_time)
            min_volatility (float): Minimum required volatility for trading
            max_volatility (float): Maximum allowed volatility
        """
        self.max_risk = max_risk
        self.max_daily_loss = max_daily_loss
        self.risk_per_trade = risk_per_trade
        self.max_open_trades = max_open_trades
        self.api_connector = api_connector
        self.trading_hours = trading_hours
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility
        self.logger = logging.getLogger(__name__)

        # Initialize tracking variables
        self.open_positions: Dict[str, Position] = {}
        self._daily_stats = {
            'date': date.today(),
            'loss': 0.0,
            'trades': 0
        }
        self._account_balance = 0.0

    def _is_trading_allowed(self) -> bool:
        """Check if trading is allowed based on time restrictions"""
        now = datetime.now().time()
        start_time, end_time = self.trading_hours
        return start_time <= now <= end_time

    def _adjust_position_size(self, base_size: float, volatility: float) -> float:
        """Adjust position size based on volatility

        Args:
            base_size (float): Base position size
            volatility (float): Current volatility measure

        Returns:
            float: Adjusted position size
        """
        if volatility < self.min_volatility:
            return base_size * 0.5  # Reduce size in low volatility
        elif volatility > self.max_volatility:
            return base_size * 0.25  # Significantly reduce size in high volatility
        return base_size

    async def initialize(self, initial_balance: Optional[float] = None):
        """Initialize with starting account balance
        Args:
            initial_balance (float, optional): Starting account balance, if None will fetch from API
        """
        try:
            self.logger.info("Initializing RiskManager...")
            cyan_status("Initializing Risk Management System...")
            if initial_balance is not None:
                self._account_balance = initial_balance
                self.logger.info(f"Using provided initial balance: {initial_balance}")
                blue_status(f"Setting initial balance: {initial_balance}")
            elif self.api_connector:
                # Fetch balance from API with detailed logging
                self.logger.info("Fetching balance from Deriv API...")
                blue_status("Fetching account balance from Deriv API...")

                # Verify API connector state
                if not self.api_connector.connected or not self.api_connector.authorized:
                    self.logger.error("API connector not ready - attempting to reconnect")
                    connect_success, error_message = await self.api_connector.connect()
                    if not connect_success:
                        raise ValueError(f"Failed to connect to API: {error_message}")

                balance_response = await self.api_connector.api.balance()
                self.logger.info(f"Raw balance response: {balance_response}")

                if 'error' in balance_response:
                    error = balance_response.get('error', {}).get('message', 'Unknown error')
                    self.logger.error(f"Failed to get balance: {error}")
                    raise ValueError(f"Failed to get balance: {error}")

                if 'balance' not in balance_response:
                    self.logger.error("Unexpected response structure - missing 'balance' key")
                    self.logger.error(f"Response keys: {list(balance_response.keys())}")
                    raise ValueError("Balance key not found in API response")

                balance = balance_response['balance']
                if not isinstance(balance, dict) or 'balance' not in balance:
                    self.logger.error(f"Invalid balance data structure: {balance}")
                    raise ValueError("Invalid balance data structure in API response")

                self._account_balance = float(balance['balance'])
                self.logger.info(
                    f"Successfully retrieved account balance: {self._account_balance} "
                    f"{balance.get('currency', 'USD')}"
                )
                green_success(f"Account balance: {self._account_balance} {balance.get('currency', 'USD')}")
            else:
                self.logger.warning("No API connector provided and no initial balance set")
                magenta_warning("No API connector provided and no initial balance set")

            self.logger.info(f"RiskManager initialized with balance: {self._account_balance}")
            green_success(f"Risk Management System initialized - Balance: {self._account_balance}")

            # Calculate and log initial risk metrics
            metrics = self.get_risk_metrics()
            self.logger.info("Initial risk metrics:", extra={'metrics': metrics})

        except Exception as e:
            self.logger.error(f"Error initializing risk manager: {str(e)}")
            raise

    def _reset_daily_stats(self):
        """Reset daily tracking statistics"""
        today = date.today()
        if today > self._daily_stats['date']:
            self._daily_stats = {
                'date': today,
                'loss': 0.0,
                'trades': 0
            }
            self.logger.info("Daily risk statistics reset")

    def can_trade(self) -> bool:
        """Check if trading is allowed based on risk limits

        Returns:
            bool: True if trading is allowed
        """
        try:
            self._reset_daily_stats()

            # Check if we have enough balance
            if self._account_balance <= 0:
                self.logger.warning("Insufficient account balance")
                return False

            # Check daily loss limit
            if self._daily_stats['loss'] >= (self._account_balance * self.max_daily_loss):
                self.logger.warning("Daily loss limit reached")
                return False

            # Check maximum open positions
            if len(self.open_positions) >= self.max_open_trades:
                self.logger.warning("Maximum open positions reached")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking trade conditions: {str(e)}")
            return False

    async def validate_signal(self, signal: Dict) -> bool:
        """Validate trading signal against risk parameters"""
        try:
            blue_status(f"Validating {signal['type']} signal for {signal['symbol']}...")
            if not self.can_trade():
                self.logger.warning("Trading not allowed based on current conditions")
                magenta_warning("Trading not allowed based on current risk conditions")
                return False

            if not self._is_trading_allowed():
                self.logger.warning("Outside allowed trading hours")
                magenta_warning(f"Outside allowed trading hours ({self.trading_hours[0]} - {self.trading_hours[1]})")
                return False

            # Basic validation
            required_fields = ['entry_price', 'stop_loss', 'take_profit', 'stake_amount', 
                             'symbol', 'type', 'atr_value', 'volatility']
            if not all(field in signal for field in required_fields):
                self.logger.warning(f"Signal missing required fields: {required_fields}")
                return False

            entry_price = float(signal['entry_price'])
            stop_loss = float(signal['stop_loss'])
            stake_amount = float(signal['stake_amount'])
            volatility = float(signal['volatility'])

            # Validate price levels
            if entry_price <= 0 or stop_loss <= 0:
                self.logger.warning("Invalid price levels in signal")
                return False

            # Validate volatility
            if not self.min_volatility <= volatility <= self.max_volatility:
                self.logger.warning(f"Volatility {volatility:.4f} outside allowed range")
                return False

            # Calculate potential loss
            risk_amount = abs(entry_price - stop_loss)
            if risk_amount == 0:
                self.logger.warning("Zero risk amount - invalid signal")
                return False

            # Calculate total risk for this trade
            adjusted_stake = self._adjust_position_size(stake_amount, volatility)
            potential_loss = risk_amount * adjusted_stake
            max_risk_amount = self._account_balance * self.risk_per_trade

            self.logger.info(
                f"Signal validation - Base stake: {stake_amount:.2f}, "
                f"Adjusted stake: {adjusted_stake:.2f}, "
                f"Potential loss: {potential_loss:.2f}, "
                f"Max risk allowed: {max_risk_amount:.2f}"
            )

            if potential_loss > max_risk_amount:
                self.logger.warning(
                    f"Signal rejected - Risk too high: {potential_loss:.2f} > {max_risk_amount:.2f}"
                )
                return False

            # Additional validation passed
            self.logger.info("Signal validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error validating signal: {str(e)}")
            return False

    async def calculate_position_size(self, signal: Dict) -> Dict:
        """Calculate appropriate position size based on risk parameters"""
        try:
            entry_price = float(signal['entry_price'])
            stop_loss = float(signal['stop_loss'])
            volatility = float(signal.get('volatility', 0.02))
            atr_value = float(signal.get('atr_value', 0))

            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit == 0:
                self.logger.warning("Cannot calculate position size - zero risk per unit")
                return signal

            # Calculate maximum risk amount for this trade
            max_risk_amount = self._account_balance * self.risk_per_trade

            # Calculate base position size
            base_size = max_risk_amount / risk_per_unit

            # Adjust size based on volatility
            adjusted_size = self._adjust_position_size(base_size, volatility)

            # Update signal with calculated values
            updated_signal = signal.copy()
            updated_signal['stake_amount'] = adjusted_size
            updated_signal['max_loss'] = max_risk_amount
            updated_signal['atr_value'] = atr_value
            updated_signal['volatility_score'] = volatility

            self.logger.info(
                f"Position size calculated - Base: {base_size:.2f}, "
                f"Adjusted: {adjusted_size:.2f}, "
                f"Max loss: {max_risk_amount:.2f}"
            )

            return updated_signal

        except Exception as e:
            self.logger.error(f"Error calculating position size: {str(e)}")
            return signal

    async def update_account_balance(self):
        """Update account balance from API"""
        try:
            if self.api_connector:
                # Verify connection before fetching
                if not self.api_connector.connected or not self.api_connector.authorized:
                    self.logger.warning("API connection lost, attempting to reconnect")
                    connect_success, error_message = await self.api_connector.connect()
                    if not connect_success:
                        self.logger.error(f"Failed to reconnect: {error_message}")
                        return

                balance_response = await self.api_connector.api.balance()
                self.logger.debug(f"Balance update response: {balance_response}")

                if 'error' in balance_response:
                    error = balance_response.get('error', {}).get('message', 'Unknown error')
                    self.logger.error(f"Failed to update balance: {error}")
                    return

                if 'balance' in balance_response:
                    balance = balance_response['balance']
                    if isinstance(balance, dict) and 'balance' in balance:
                        self._account_balance = float(balance['balance'])
                        self.logger.info(
                            f"Updated account balance: {self._account_balance} "
                            f"{balance.get('currency', 'USD')}"
                        )
                    else:
                        self.logger.error(f"Invalid balance data structure: {balance}")
                else:
                    self.logger.error("Balance key not found in API response")
        except Exception as e:
            self.logger.error(f"Error updating account balance: {str(e)}")

    async def record_trade_result(self, trade: Dict):
        """Record trade result and update risk tracking

        Args:
            trade (dict): Completed trade details
        """
        try:
            blue_status("Recording trade result and updating risk metrics...")
            # Update account balance from API first
            await self.update_account_balance()

            # Update daily statistics if loss
            profit_loss = trade.get('profit_loss', 0)
            if profit_loss < 0:
                self._daily_stats['loss'] += abs(profit_loss)
                magenta_warning(f"Daily loss updated: {self._daily_stats['loss']:.2f}")
            else:
                green_success(f"Profit recorded: +{profit_loss:.2f}")
            self._daily_stats['trades'] += 1

            # Remove from open positions if present
            trade_id = trade.get('trade_id')
            if trade_id and trade_id in self.open_positions:
                del self.open_positions[trade_id]

            self.logger.info(
                f"Trade result recorded - P/L: {profit_loss:.2f}",
                extra={
                    'trade': trade,
                    'balance': self._account_balance,
                    'daily_loss': self._daily_stats['loss']
                }
            )

        except Exception as e:
            self.logger.error(f"Error recording trade result: {str(e)}")

    def add_position(self, signal: Dict):
        """Add new position to tracking

        Args:
            signal (dict): Trading signal with position details
        """
        try:
            if not signal.get('trade_id'):
                self.logger.error("Cannot add position without trade_id")
                return

            position = Position(
                trade_id=signal['trade_id'],
                symbol=signal['symbol'],
                type=signal['type'],
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                stake_amount=signal['stake_amount'],
                entry_time=datetime.now(timezone.utc).timestamp(),
                max_loss=signal.get('max_loss', 0.0),
                atr_value=signal.get('atr_value'),
                volatility_score=signal.get('volatility_score')
            )

            self.open_positions[signal['trade_id']] = position

            self.logger.info(
                f"Position added - ID: {signal['trade_id']}",
                extra={'position': vars(position)}
            )

        except Exception as e:
            self.logger.error(f"Error adding position: {str(e)}")

    def get_position(self, trade_id: str) -> Optional[Position]:
        """Get position details

        Args:
            trade_id (str): Trade identifier

        Returns:
            Position: Position details if exists
        """
        return self.open_positions.get(trade_id)

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics

        Returns:
            dict: Risk metrics
        """
        try:
            # Calculate open risk
            open_risk = sum(
                abs(pos.entry_price - pos.stop_loss) * pos.stake_amount
                for pos in self.open_positions.values()
            )

            metrics = {
                'account_balance': self._account_balance,
                'daily_loss': self._daily_stats['loss'],
                'daily_trades': self._daily_stats['trades'],
                'open_positions': len(self.open_positions),
                'open_risk': open_risk,
                'open_risk_pct': (open_risk / self._account_balance * 100)
                if self._account_balance > 0 else 0.0,
                'available_risk': (self.max_risk * self._account_balance) - open_risk,
                'max_risk_percentage': self.max_risk * 100,  # Add percentage for clarity
                'max_risk_decimal': self.max_risk  # Add the actual decimal value for clarity
            }
            blue_status(f"Risk metrics: {metrics}")
            return metrics

        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {str(e)}")
            return {}