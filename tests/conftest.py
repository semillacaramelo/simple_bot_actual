import pytest
import pandas as pd
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def sample_ohlc_data():
    """Generate sample OHLC price data"""
    return pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [105, 106, 107, 108, 109],
        'low': [95, 96, 97, 98, 99],
        'close': [102, 103, 104, 105, 106],
        'epoch': list(range(1234567890, 1234567890 + 5))
    })

@pytest.fixture
def sample_trades():
    """Generate sample trade history"""
    return [
        {
            'trade_id': '1',
            'symbol': 'R_100',
            'type': 'CALL',
            'entry_price': 100.0,
            'exit_price': 102.0,
            'profit_loss': 200.0,
            'stake_amount': 100.0,
            'entry_time': 1234567890,
            'exit_time': 1234567900
        },
        {
            'trade_id': '2',
            'symbol': 'R_100',
            'type': 'PUT',
            'entry_price': 105.0,
            'exit_price': 103.0,
            'profit_loss': -200.0,
            'stake_amount': 100.0,
            'entry_time': 1234567910,
            'exit_time': 1234567920
        }
    ]

@pytest.fixture
def mock_api_response():
    """Generate mock API response data"""
    return {
        'authorize': {
            'email': 'test@example.com',
            'balance': 10000.0,
            'currency': 'USD'
        },
        'proposal': {
            'id': 'xyz789',
            'ask_price': 100.0,
            'payout': 200.0
        },
        'buy': {
            'contract_id': 'abc123',
            'buy_price': 100.0,
            'balance_after': 9900.0,
            'transaction_id': 12345
        },
        'sell': {
            'sold_for': 150.0,
            'profit': 50.0,
            'balance_after': 10050.0
        }
    }

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_logger():
    """Create mock logger"""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger

@pytest.fixture
def trading_config():
    """Generate sample trading configuration"""
    return {
        'SHORT_WINDOW': 5,
        'MEDIUM_WINDOW': 20,
        'LONG_WINDOW': 50,
        'RSI_PERIOD': 14,
        'RSI_OVERBOUGHT': 70,
        'RSI_OVERSOLD': 30,
        'VOLATILITY_THRESHOLD': 0.02,
        'RISK_REWARD_RATIO': 2.0,
        'ATR_MULTIPLIER': 2.0
    }

@pytest.fixture
def risk_config():
    """Generate sample risk configuration"""
    return {
        'max_risk': 0.10,
        'max_daily_loss': 0.05,
        'risk_per_trade': 0.02,
        'max_open_trades': 3
    }

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )