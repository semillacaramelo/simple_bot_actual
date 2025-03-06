import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
import uuid

class SimulatedExecutor:
    def __init__(self):
        """Initialize simulated order executor"""
        self.logger = logging.getLogger(__name__)
        self.active_trades: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []

    async def execute_order(self, signal: Dict) -> Optional[Dict]:
        """Execute trade order"""
        try:
            # Generate unique trade ID or use existing one from signal
            trade_id = signal.get('trade_id', str(uuid.uuid4())[:8])

            # Validate signal
            required_fields = ['symbol', 'type', 'entry_price', 'stop_loss', 
                             'take_profit', 'stake_amount']

            missing_fields = [field for field in required_fields if field not in signal]
            if missing_fields:
                self.logger.error(f"Signal missing required fields: {missing_fields}")
                return None

            # Log additional fields (not required but useful for analysis)
            recommended_fields = ['volatility', 'atr_value', 'duration', 'duration_unit']
            missing_recommended = [field for field in recommended_fields if field not in signal]
            if missing_recommended:
                self.logger.warning(f"Signal missing recommended fields: {missing_recommended}")


            # Create order record
            order = {
                'trade_id': trade_id,
                'symbol': signal['symbol'],
                'type': signal['type'],
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'stake_amount': signal['stake_amount'],
                'volatility': signal.get('volatility'),
                'atr_value': signal.get('atr_value'),
                'status': 'open',
                'entry_time': datetime.now(timezone.utc).timestamp()
            }

            # Add optional fields if present
            if 'duration' in signal:
                order['duration'] = signal['duration']
            if 'duration_unit' in signal:
                order['duration_unit'] = signal['duration_unit']

            # Store in active trades
            self.active_trades[trade_id] = order

            self.logger.info(
                f"Simulated order executed - ID: {trade_id}",
                extra={'order': order}
            )

            return order

        except Exception as e:
            self.logger.error(f"Error executing simulated order: {str(e)}")
            return None

    async def close_position(self, trade_id: str, exit_price: float) -> bool:
        """Close simulated position

        Args:
            trade_id (str): Trade identifier
            exit_price (float): Exit price

        Returns:
            bool: True if successful
        """
        try:
            if trade_id not in self.active_trades:
                self.logger.warning(f"Trade {trade_id} not found in active trades")
                return False

            order = self.active_trades[trade_id]

            # Calculate P&L
            if order['type'] == 'CALL':
                profit_loss = (
                    (exit_price - order['entry_price']) / 
                    order['entry_price']
                ) * order['stake_amount']
            else:  # PUT
                profit_loss = (
                    (order['entry_price'] - exit_price) / 
                    order['entry_price']
                ) * order['stake_amount']

            # Update order record
            order['status'] = 'closed'
            order['exit_time'] = datetime.now(timezone.utc).timestamp()
            order['exit_price'] = exit_price
            order['profit_loss'] = profit_loss

            # Move to history
            self.trade_history.append(order)
            del self.active_trades[trade_id]

            self.logger.info(
                f"Simulated position closed - ID: {trade_id}, P/L: {profit_loss:.2f}",
                extra={'order': order}
            )

            return True

        except Exception as e:
            self.logger.error(f"Error closing simulated position: {str(e)}")
            return False

    def get_active_trades(self) -> Dict[str, Dict]:
        """Get active trading positions

        Returns:
            dict: Active trades
        """
        return self.active_trades

    def get_trade_history(self) -> List[Dict]:
        """Get completed trades history

        Returns:
            list: Trade history
        """
        return self.trade_history