import unittest
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from backtesting.engine import BacktestEngine
from backtesting.simulator import SimulatedExecutor
from backtesting.utils import (
    calculate_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    generate_trade_report
)

class TestBacktesting(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'symbols': ['R_100'],
            'timeframe': '1m',
            'initial_balance': 10000,
            'max_risk': 0.10,
            'max_daily_loss': 0.05,
            'risk_per_trade': 0.02,
            'max_open_trades': 3
        }
        
        # Mock API connector
        self.api_connector = Mock()
        
        # Create test instance
        self.engine = BacktestEngine(self.api_connector, self.config)
        
    def test_simulator_order_execution(self):
        """Test simulated order execution"""
        simulator = SimulatedExecutor()
        
        # Test order creation
        signal = {
            'symbol': 'R_100',
            'type': 'CALL',
            'entry_price': 100.0,
            'stop_loss': 99.0,
            'take_profit': 102.0,
            'stake_amount': 100.0
        }
        
        async def execute_test():
            order = await simulator.execute_order(signal)
            self.assertIsNotNone(order)
            self.assertEqual(order['symbol'], 'R_100')
            self.assertEqual(order['type'], 'CALL')
            self.assertEqual(order['status'], 'open')
            
            # Test position closing
            success = await simulator.close_position(
                order['order_id'],
                exit_price=101.0
            )
            self.assertTrue(success)
            
            # Verify trade history
            history = simulator.get_trade_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]['status'], 'closed')
            self.assertGreater(history[0]['profit_loss'], 0)
            
        asyncio.run(execute_test())
        
    def test_drawdown_calculation(self):
        """Test drawdown calculation"""
        # Create test equity curve
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        equity = pd.Series(
            [100, 105, 103, 102, 106, 108, 104, 103, 105, 107],
            index=dates[:10]
        )
        
        results = calculate_drawdown(equity)
        self.assertIsNotNone(results['max_drawdown'])
        self.assertLess(results['max_drawdown'], 0)
        
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""
        # Create test returns
        returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
        
        sharpe = calculate_sharpe_ratio(returns)
        self.assertIsInstance(sharpe, float)
        
    def test_sortino_ratio_calculation(self):
        """Test Sortino ratio calculation"""
        # Create test returns
        returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
        
        sortino = calculate_sortino_ratio(returns)
        self.assertIsInstance(sortino, float)
        
    def test_trade_report_generation(self):
        """Test trade report generation"""
        trades = [
            {
                'order_id': '1',
                'symbol': 'R_100',
                'type': 'CALL',
                'entry_price': 100.0,
                'exit_price': 102.0,
                'stake_amount': 100.0,
                'profit_loss': 2.0,
                'entry_time': 1706745600,  # 2024-02-01
                'exit_time': 1706749200    # 2024-02-01 + 1h
            },
            {
                'order_id': '2',
                'symbol': 'R_100',
                'type': 'PUT',
                'entry_price': 102.0,
                'exit_price': 101.0,
                'stake_amount': 100.0,
                'profit_loss': -1.0,
                'entry_time': 1706752800,  # 2024-02-01 + 2h
                'exit_time': 1706756400    # 2024-02-01 + 3h
            }
        ]
        
        report = generate_trade_report(trades)
        self.assertEqual(report['total_trades'], 2)
        self.assertEqual(report['winning_trades'], 1)
        self.assertEqual(report['losing_trades'], 1)
        self.assertEqual(report['win_rate'], 0.5)
        self.assertGreater(report['net_profit'], 0)

if __name__ == '__main__':
    unittest.main()
