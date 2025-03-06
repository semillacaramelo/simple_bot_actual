import pytest
import asyncio
from src.api.deriv_connector import DerivConnector
from unittest.mock import Mock, patch

@pytest.fixture
def api_connector():
    return DerivConnector(
        api_token="demo_token",
        app_id=1089
    )

@pytest.mark.asyncio
async def test_connect_success(api_connector):
    with patch('deriv_api.DerivAPI') as mock_api:
        mock_api.return_value.authorize.return_value = {
            'authorize': {
                'email': 'test@example.com',
                'balance': 1000.0,
                'currency': 'USD'
            }
        }
        
        result = await api_connector.connect()
        assert result is True
        assert api_connector.connected is True
        assert api_connector.authorized is True

@pytest.mark.asyncio
async def test_connect_failure(api_connector):
    with patch('deriv_api.DerivAPI') as mock_api:
        mock_api.return_value.authorize.return_value = {
            'error': {
                'code': 'InvalidToken',
                'message': 'Invalid token'
            }
        }
        
        with pytest.raises(Exception):
            await api_connector.connect()
        assert api_connector.connected is False
        assert api_connector.authorized is False

@pytest.mark.asyncio
async def test_get_price(api_connector):
    with patch('deriv_api.DerivAPI') as mock_api:
        mock_api.return_value.ticks.return_value = {
            'tick': {
                'symbol': 'R_100',
                'quote': 1234.5,
                'epoch': 1234567890
            }
        }
        
        price_data = await api_connector.get_price('R_100')
        assert price_data is not None
        assert price_data['symbol'] == 'R_100'
        assert price_data['price'] == 1234.5
        assert price_data['is_trading'] is True

@pytest.mark.asyncio
async def test_get_candles(api_connector):
    with patch('deriv_api.DerivAPI') as mock_api:
        mock_api.return_value.ticks_history.return_value = {
            'candles': [
                {'epoch': 1234567890, 'open': 100, 'high': 101, 'low': 99, 'close': 100.5},
                {'epoch': 1234567900, 'open': 100.5, 'high': 102, 'low': 100, 'close': 101.5}
            ]
        }
        
        candles = await api_connector.get_candles('R_100', count=2)
        assert len(candles) == 2
        assert all(k in candles[0] for k in ['epoch', 'open', 'high', 'low', 'close'])

@pytest.mark.asyncio
async def test_subscribe_to_price(api_connector):
    with patch('deriv_api.DerivAPI') as mock_api:
        mock_source = Mock()
        mock_api.return_value.subscribe.return_value = mock_source
        
        callback = Mock()
        source = await api_connector.subscribe_to_price('R_100', callback)
        
        assert source is not None
        mock_source.subscribe.assert_called_once_with(callback)