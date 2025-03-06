
from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging
import json

from src.utils.console import blue_status, green_success, magenta_warning, white_wait

class PerformanceTracker:
    """Tracks trading performance metrics"""
    
    def __init__(self):
        """Initialize performance tracker"""
        self.logger = logging.getLogger(__name__)
        self.trades = []
        self.trade_history = {}
        self.daily_performance = {}
        self.session_start_time = datetime.now(timezone.utc).timestamp()
        blue_status("Performance tracking initialized")
        
    def record_trade(self, trade: Dict):
        """Record completed trade for performance analysis
        
        Args:
            trade (dict): Completed trade details
        """
        try:
            if 'order_id' not in trade:
                self.logger.warning("Cannot record trade without order_id")
                magenta_warning("Cannot record trade without order_id")
                return
                
            # Store trade in history
            self.trades.append(trade)
            self.trade_history[trade['order_id']] = trade
            
            # Log trade
            profit_loss = trade.get('profit_loss', 0)
            symbol = trade.get('symbol', 'unknown')
            trade_type = trade.get('type', 'unknown')
            
            if profit_loss > 0:
                green_success(f"Trade recorded: {symbol} {trade_type} - Profit: +{profit_loss:.2f}")
            else:
                magenta_warning(f"Trade recorded: {symbol} {trade_type} - Loss: {profit_loss:.2f}")
                
            self.logger.info(
                f"Trade recorded - ID: {trade['order_id']}, P/L: {profit_loss:.2f}",
                extra={'trade': trade}
            )
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {str(e)}")
            
    def analyze_performance(self) -> Optional[Dict]:
        """Analyze trading performance
        
        Returns:
            dict: Performance metrics if available
        """
        try:
            blue_status("Analyzing trading performance...")
            if not self.trades:
                self.logger.info("No trades to analyze")
                return None
                
            # Calculate overall metrics
            winning_trades = [t for t in self.trades if t.get('profit_loss', 0) > 0]
            losing_trades = [t for t in self.trades if t.get('profit_loss', 0) < 0]
            
            total_trades = len(self.trades)
            total_profit = sum(t.get('profit_loss', 0) for t in winning_trades)
            total_loss = abs(sum(t.get('profit_loss', 0) for t in losing_trades))
            
            # Calculate win rate and risk-reward ratio
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            avg_win = total_profit / len(winning_trades) if winning_trades else 0
            avg_loss = total_loss / len(losing_trades) if losing_trades else 0
            risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
            
            # Calculate by symbol
            symbols = {}
            for trade in self.trades:
                symbol = trade.get('symbol', 'unknown')
                if symbol not in symbols:
                    symbols[symbol] = {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'total_profit': 0,
                        'total_loss': 0
                    }
                    
                symbols[symbol]['total_trades'] += 1
                profit_loss = trade.get('profit_loss', 0)
                
                if profit_loss > 0:
                    symbols[symbol]['winning_trades'] += 1
                    symbols[symbol]['total_profit'] += profit_loss
                elif profit_loss < 0:
                    symbols[symbol]['total_loss'] += abs(profit_loss)
            
            # Build performance data
            performance_data = {
                'overall': {
                    'total_trades': total_trades,
                    'winning_trades': len(winning_trades),
                    'losing_trades': len(losing_trades),
                    'win_rate': win_rate,
                    'total_profit': total_profit,
                    'total_loss': total_loss,
                    'net_pnl': total_profit - total_loss,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'risk_reward': risk_reward
                },
                'by_symbol': symbols
            }
            
            self.logger.info("Performance data calculated", extra={'performance': performance_data})
            
            # Log a summary to console
            blue_status(f"Performance summary - Trades: {total_trades}, Win rate: {win_rate*100:.1f}%")
            if total_profit > total_loss:
                green_success(f"Net profit: +{total_profit-total_loss:.2f}")
            else:
                magenta_warning(f"Net loss: {total_profit-total_loss:.2f}")
                
            return performance_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {str(e)}")
            return None
    
    def get_trade_history(self) -> Dict:
        """Get trade history
        
        Returns:
            dict: Trade history
        """
        return self.trade_history
