import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from src.strategy.moving_average import MovingAverageStrategy
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_data_fetcher():
    fetcher = AsyncMock()
    
    # Setup historical data
    df = pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [105, 106, 107, 108, 109],
        'low': [95, 96, 97, 98, 99],
        'close': [102, 103, 104, 105, 106],
        'epoch': list(range(1234567890, 1234567890 + 5))
    })
    fetcher.get_historical_data.return_value = df
    
    return fetcher

@pytest.fixture
def strategy(mock_data_fetcher):
    return MovingAverageStrategy(
        data_fetcher=mock_data_fetcher,
        SHORT_WINDOW=2,
        MEDIUM_WINDOW=3,
        LONG_WINDOW=4,
        RSI_PERIOD=2,
        RSI_OVERBOUGHT=70,
        RSI_OVERSOLD=30,
        VOLATILITY_THRESHOLD=0.01,
        RISK_REWARD_RATIO=2.0,
        ATR_MULTIPLIER=2.0
    )

@pytest.mark.asyncio
async def test_analyze_symbol(strategy, mock_data_fetcher):
    symbol = 'R_100'
    signal = await strategy.analyze_symbol(symbol)
    
    # Verify data fetcher was called
    mock_data_fetcher.get_historical_data.assert_called_once()
    assert mock_data_fetcher.get_historical_data.call_args[0][0] == symbol
    
    # Basic signal validation
    assert signal is not None
    assert signal['symbol'] == symbol
    assert 'type' in signal
    assert signal['type'] in ['CALL', 'PUT']
    assert 'entry_price' in signal
    assert 'stop_loss' in signal
    assert 'take_profit' in signal
    assert 'indicators' in signal

def test_validate_signal(strategy):
    # Valid CALL signal
    valid_call = {
        'symbol': 'R_100',
        'type': 'CALL',
        'entry_price': 100.0,
        'stop_loss': 99.0,
        'take_profit': 102.0
    }
    assert strategy.validate_signal(valid_call) is True
    
    # Valid PUT signal
    valid_put = {
        'symbol': 'R_100',
        'type': 'PUT',
        'entry_price': 100.0,
        'stop_loss': 101.0,
        'take_profit': 98.0
    }
    assert strategy.validate_signal(valid_put) is True
    
    # Invalid signal type
    invalid_type = valid_call.copy()
    invalid_type['type'] = 'INVALID'
    assert strategy.validate_signal(invalid_type) is False
    
    # Invalid price levels for CALL
    invalid_call = valid_call.copy()
    invalid_call['stop_loss'] = 101.0  # Stop loss above entry
    assert strategy.validate_signal(invalid_call) is False
    
    # Invalid price levels for PUT
    invalid_put = valid_put.copy()
    invalid_put['take_profit'] = 102.0  # Take profit above entry
    assert strategy.validate_signal(invalid_put) is False
    
    # Missing required fields
    missing_fields = {'symbol': 'R_100', 'type': 'CALL'}
    assert strategy.validate_signal(missing_fields) is False