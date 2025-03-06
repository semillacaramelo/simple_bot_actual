from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_drawdown(equity_curve: pd.Series) -> Dict:
    """Calculate maximum drawdown and drawdown periods
    
    Args:
        equity_curve: Series of equity values
        
    Returns:
        dict: Drawdown metrics
    """
    try:
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdown
        drawdown = equity_curve / running_max - 1
        
        # Find maximum drawdown
        max_drawdown = drawdown.min()
        max_drawdown_idx = drawdown.idxmin()
        
        # Find start of drawdown period
        drawdown_start = running_max.loc[:max_drawdown_idx].idxmax()
        
        # Find end of drawdown period
        try:
            drawdown_end = equity_curve.loc[max_drawdown_idx:].ge(
                running_max.loc[drawdown_start]
            ).idxmax()
        except ValueError:
            drawdown_end = equity_curve.index[-1]
        
        return {
            'max_drawdown': max_drawdown,
            'drawdown_start': drawdown_start,
            'drawdown_end': drawdown_end,
            'drawdown_length': (drawdown_end - drawdown_start).total_seconds() / 86400
        }
        
    except Exception as e:
        print(f"Error calculating drawdown: {str(e)}")
        return {
            'max_drawdown': 0,
            'drawdown_start': None,
            'drawdown_end': None,
            'drawdown_length': 0
        }

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.01) -> float:
    """Calculate Sharpe ratio
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate
        
    Returns:
        float: Sharpe ratio
    """
    try:
        # Convert annual risk-free rate to match return frequency
        rf_daily = (1 + risk_free_rate) ** (1/252) - 1
        
        excess_returns = returns - rf_daily
        if excess_returns.std() == 0:
            return 0
            
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        
    except Exception as e:
        print(f"Error calculating Sharpe ratio: {str(e)}")
        return 0

def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.01) -> float:
    """Calculate Sortino ratio
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate
        
    Returns:
        float: Sortino ratio
    """
    try:
        # Convert annual risk-free rate to match return frequency
        rf_daily = (1 + risk_free_rate) ** (1/252) - 1
        
        excess_returns = returns - rf_daily
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0
            
        return np.sqrt(252) * excess_returns.mean() / downside_returns.std()
        
    except Exception as e:
        print(f"Error calculating Sortino ratio: {str(e)}")
        return 0

def generate_trade_report(trades: List[Dict]) -> Dict:
    """Generate detailed trade analysis report
    
    Args:
        trades: List of completed trades
        
    Returns:
        dict: Trade analysis metrics
    """
    try:
        if not trades:
            return {}
            
        # Convert to DataFrame for analysis
        df = pd.DataFrame(trades)
        
        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = len(df[df['profit_loss'] > 0])
        losing_trades = len(df[df['profit_loss'] <= 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit metrics
        total_profit = df[df['profit_loss'] > 0]['profit_loss'].sum()
        total_loss = abs(df[df['profit_loss'] <= 0]['profit_loss'].sum())
        net_profit = total_profit - total_loss
        
        # Average trade metrics
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Calculate daily returns
        df['date'] = pd.to_datetime(df['entry_time'], unit='s').dt.date
        daily_pnl = df.groupby('date')['profit_loss'].sum()
        
        # Calculate return metrics
        returns = daily_pnl / df.groupby('date')['stake_amount'].sum().iloc[0]
        sharpe = calculate_sharpe_ratio(returns)
        sortino = calculate_sortino_ratio(returns)
        
        # Calculate drawdown
        equity_curve = (1 + returns).cumprod()
        drawdown_metrics = calculate_drawdown(equity_curve)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': net_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': drawdown_metrics['max_drawdown'],
            'max_drawdown_duration': drawdown_metrics['drawdown_length']
        }
        
    except Exception as e:
        print(f"Error generating trade report: {str(e)}")
        return {}
