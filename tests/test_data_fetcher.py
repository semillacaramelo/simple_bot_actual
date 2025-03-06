import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from src.api.data_fetcher import DataFetcher

@pytest.fixture
def mock_api_connector():
    connector = AsyncMock()

    # Mock price data
    connector.get_price.return_value = {
        'symbol': 'R_100',
        'price': 100.0,
        'epoch': 1234567890,
        'is_trading': True
    }

    # Mock candle data with consistent timestamps
    candles = [
        {'epoch': 1234567890, 'open': 100, 'high': 101, 'low': 99, 'close': 100.5},
        {'epoch': 1234567900, 'open': 100.5, 'high': 102, 'low': 100, 'close': 101.5}
    ]
    connector.get_candles.return_value = candles

    subscription = Mock()
    connector.subscribe_to_price.return_value = subscription

    return connector

@pytest.fixture
def data_fetcher(mock_api_connector):
    return DataFetcher(mock_api_connector)

@pytest.mark.asyncio
async def test_initialize_symbol(data_fetcher, mock_api_connector):
    symbol = 'R_100'
    await data_fetcher.initialize_symbol(symbol)

    # Verify initial data fetching
    mock_api_connector.get_price.assert_called_once_with(symbol)
    mock_api_connector.get_candles.assert_called_once()
    mock_api_connector.subscribe_to_price.assert_called_once()

    # Verify data storage
    assert symbol in data_fetcher._price_cache
    assert symbol in data_fetcher._history_cache
    assert symbol in data_fetcher._subscriptions

@pytest.mark.asyncio
async def test_get_historical_data(data_fetcher, mock_api_connector):
    symbol = 'R_100'
    count = 2
    end = int(datetime.now(timezone.utc).timestamp())

    df = await data_fetcher.get_historical_data(symbol, count=count, end=end)

    # Verify API call parameters
    mock_api_connector.get_candles.assert_called_with(
        symbol,
        count=count,
        interval=1,
        interval_unit='m',
        end=end
    )

    # Verify DataFrame structure and content
    assert df is not None
    assert len(df) == count
    assert all(col in df.columns for col in ['open', 'high', 'low', 'close'])
    assert df.index.name == 'timestamp'

    # Verify timestamps are properly converted
    assert isinstance(df.index, pd.DatetimeIndex)
    assert all(isinstance(ts, pd.Timestamp) for ts in df.index)

@pytest.mark.asyncio
async def test_historical_data_caching(data_fetcher, mock_api_connector):
    symbol = 'R_100'

    # First call should fetch from API
    df1 = await data_fetcher.get_historical_data(symbol, count=2)
    assert mock_api_connector.get_candles.call_count == 1

    # Second call should use cache
    df2 = await data_fetcher.get_historical_data(symbol, count=2)
    assert mock_api_connector.get_candles.call_count == 1  # No additional API call
    assert df1.equals(df2)  # Data should be identical

@pytest.mark.asyncio
async def test_clear_symbol(data_fetcher):
    symbol = 'R_100'

    # Setup test data
    mock_subscription = Mock()
    data_fetcher._subscriptions[symbol] = mock_subscription
    data_fetcher._price_cache[symbol] = {'price': 100.0}
    data_fetcher._history_cache[symbol] = pd.DataFrame()

    # Clear symbol
    await data_fetcher.clear_symbol(symbol)

    # Verify cleanup
    mock_subscription.dispose.assert_called_once()
    assert symbol not in data_fetcher._subscriptions
    assert symbol not in data_fetcher._price_cache
    assert symbol not in data_fetcher._history_cache

def test_price_update_callback(data_fetcher):
    symbol = 'R_100'
    price_data = {
        'tick': {
            'symbol': symbol,
            'quote': 100.0,
            'epoch': 1234567890
        }
    }

    data_fetcher._price_update_callback(price_data)

    assert symbol in data_fetcher._price_cache
    cache_entry = data_fetcher._price_cache[symbol]
    assert cache_entry['price'] == 100.0
    assert cache_entry['epoch'] == 1234567890
    assert cache_entry['is_trading'] is True

def test_get_latest_price(data_fetcher):
    symbol = 'R_100'
    test_price = 100.0

    # Setup cache
    data_fetcher._price_cache[symbol] = {
        'symbol': symbol,
        'price': test_price,
        'epoch': 1234567890,
        'is_trading': True
    }

    price = data_fetcher.get_latest_price(symbol)
    assert price == test_price

    # Test non-existent symbol
    assert data_fetcher.get_latest_price('INVALID') is None

def test_is_market_open(data_fetcher):
    symbol = 'R_100'

    # Test trading market
    data_fetcher._price_cache[symbol] = {
        'symbol': symbol,
        'price': 100.0,
        'is_trading': True
    }
    assert data_fetcher.is_market_open(symbol) is True

    # Test closed market
    data_fetcher._price_cache[symbol] = {
        'symbol': symbol,
        'price': 100.0,
        'is_trading': False
    }
    assert data_fetcher.is_market_open(symbol) is False

    # Test non-existent symbol
    assert data_fetcher.is_market_open('INVALID') is False

def test_get_available_symbols(data_fetcher):
    symbols = ['R_100', 'R_50', 'R_25']

    # Setup cache
    for symbol in symbols:
        data_fetcher._price_cache[symbol] = {'price': 100.0}

    available = data_fetcher.get_available_symbols()
    assert set(available) == set(symbols)