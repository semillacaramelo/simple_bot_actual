import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

@dataclass
class ApiConfig:
    """API connection configuration"""
    app_id: str
    api_token: str
    api_url: str = "wss://ws.binaryws.com/websockets/v3"

    @classmethod
    def from_env(cls) -> 'ApiConfig':
        """Create config from environment variables"""
        # Load environment
        env = os.getenv('ENVIRONMENT', 'demo').lower()
        token_key = 'DERIV_API_TOKEN_DEMO' if env == 'demo' else 'DERIV_API_TOKEN_REAL'

        return cls(
            app_id=os.getenv('DERIV_APP_ID', '1089'),
            api_token=os.getenv(token_key, ''),
            api_url=os.getenv('DERIV_API_URL', 
                            'wss://ws.binaryws.com/websockets/v3')
        )

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_risk: float = 0.10  # Maximum total risk (10%)
    max_daily_loss: float = 0.05  # Maximum daily loss (5%)
    risk_per_trade: float = 0.02  # Risk per trade (2%)
    max_open_trades: int = 3  # Maximum concurrent open trades

@dataclass
class TradingConfig:
    """Trading parameters configuration"""
    default_symbol: str = 'R_100'  # Default to R_100 synthetic index
    short_window: int = 3          # Reduced from 5 for faster response
    medium_window: int = 10        # Reduced from 20 for faster response
    long_window: int = 30          # Reduced from 50 for faster response
    rsi_period: int = 10           # Reduced from 14 for faster response
    rsi_overbought: int = 75       # Increased from 70 for more flexibility
    rsi_oversold: int = 25         # Reduced from 30 for more flexibility
    volatility_threshold: float = 0.005  # Reduced from 0.02 for 1-min trades
    min_volatility: float = 0.003  # Reduced from 0.01 for 1-min trades
    max_volatility: float = 0.03   # Reduced from 0.05 for 1-min trades
    risk_reward_ratio: float = 1.5 # Reduced from 2.0 for faster trades
    atr_multiplier: float = 1.5    # Reduced from 2.0 for tighter stops
    atr_period: int = 10           # Reduced from 14 for faster response
    price_action_lookback: int = 3 # New parameter for momentum analysis
    momentum_threshold: float = 0.001 # New parameter for momentum triggers
    enable_mean_reversion: bool = True # New parameter for mean reversion strategy

@dataclass
class LogConfig:
    """Logging configuration"""
    level: str = "INFO"
    file_path: str = "logs/trading_bot.log"
    file_level: str = "DEBUG"
    console_level: str = "INFO"

class Config:
    """Trading bot configuration"""

    def __init__(self):
        """Initialize configuration"""
        # Load environment variables
        load_dotenv()

        # Initialize components
        self.environment = os.getenv('ENVIRONMENT', 'demo').lower()
        self.api_config = ApiConfig.from_env()
        self.risk_config = self._load_risk_config()
        self.trading_config = self._load_trading_config()
        self.log_config = LogConfig()

        # Trading schedule
        self.trading_start_time = os.getenv('TRADING_START_TIME', '09:00')
        self.trading_end_time = os.getenv('TRADING_END_TIME', '17:00')
        self.trading_days = [int(d) for d in 
                           os.getenv('TRADING_DAYS', '1,2,3,4,5').split(',')]

    def _load_risk_config(self) -> RiskConfig:
        """Load risk parameters from environment"""
        return RiskConfig(
            max_risk=float(os.getenv('MAX_RISK', '0.10')),
            max_daily_loss=float(os.getenv('MAX_DAILY_LOSS', '0.05')),
            risk_per_trade=float(os.getenv('RISK_PER_TRADE', '0.02')),
            max_open_trades=int(os.getenv('MAX_OPEN_TRADES', '3'))
        )

    def _load_trading_config(self) -> TradingConfig:
        """Load trading parameters from environment"""
        return TradingConfig(
            default_symbol=os.getenv('DEFAULT_SYMBOL', 'R_100'),
            short_window=int(os.getenv('SHORT_WINDOW', '3')),           # Reduced from 5
            medium_window=int(os.getenv('MEDIUM_WINDOW', '10')),        # Reduced from 20
            long_window=int(os.getenv('LONG_WINDOW', '30')),            # Reduced from 50
            rsi_period=int(os.getenv('RSI_PERIOD', '10')),              # Reduced from 14
            rsi_overbought=int(os.getenv('RSI_OVERBOUGHT', '75')),      # Increased from 70
            rsi_oversold=int(os.getenv('RSI_OVERSOLD', '25')),          # Reduced from 30
            volatility_threshold=float(os.getenv('VOLATILITY_THRESHOLD', '0.005')), # Reduced from 0.02
            min_volatility=float(os.getenv('MIN_VOLATILITY', '0.003')),  # Reduced from 0.01
            max_volatility=float(os.getenv('MAX_VOLATILITY', '0.03')),   # Reduced from 0.05
            risk_reward_ratio=float(os.getenv('RISK_REWARD_RATIO', '1.5')), # Reduced from 2.0
            atr_multiplier=float(os.getenv('ATR_MULTIPLIER', '1.5')),     # Reduced from 2.0
            atr_period=int(os.getenv('ATR_PERIOD', '10')),                # Reduced from 14
            price_action_lookback=int(os.getenv('PRICE_ACTION_LOOKBACK', '3')),
            momentum_threshold=float(os.getenv('MOMENTUM_THRESHOLD', '0.001')),
            enable_mean_reversion=os.getenv('ENABLE_MEAN_REVERSION', 'true').lower() == 'true'
        )

    def get_api_token(self) -> str:
        """Get API token based on environment"""
        return self.api_config.api_token

    def get_app_id(self) -> str:
        """Get app ID"""
        return self.api_config.app_id

    def get_risk_params(self) -> Dict:
        """Get risk management parameters"""
        # Allow environment variables to override defaults
        max_risk = float(os.getenv('MAX_RISK', '0.10'))  # Default to 10%
        # Safety check to ensure max_risk is a proper decimal (between 0 and 1)
        if max_risk > 1.0:
            max_risk = 0.10  # Reset to default if value is too high
        max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', '0.05'))  # Default to 5%
        risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.02'))  # Default to 2%
        max_open_trades = int(os.getenv('MAX_OPEN_TRADES', '3'))  # Default to 3 trades
        return {
            'max_risk': max_risk,
            'max_daily_loss': max_daily_loss,
            'risk_per_trade': risk_per_trade,
            'max_open_trades': max_open_trades
        }

    def get_trading_params(self) -> Dict:
        """Get trading parameters"""
        return {
            'default_symbol': self.trading_config.default_symbol,
            'SHORT_WINDOW': self.trading_config.short_window,
            'MEDIUM_WINDOW': self.trading_config.medium_window,
            'LONG_WINDOW': self.trading_config.long_window,
            'RSI_PERIOD': self.trading_config.rsi_period,
            'RSI_OVERBOUGHT': self.trading_config.rsi_overbought,
            'RSI_OVERSOLD': self.trading_config.rsi_oversold,
            'VOLATILITY_THRESHOLD': self.trading_config.volatility_threshold,
            'RISK_REWARD_RATIO': self.trading_config.risk_reward_ratio,
            'ATR_MULTIPLIER': self.trading_config.atr_multiplier,
            'MIN_VOLATILITY': self.trading_config.min_volatility,
            'MAX_VOLATILITY': self.trading_config.max_volatility,
            'ATR_PERIOD': self.trading_config.atr_period,
            'PRICE_ACTION_LOOKBACK': self.trading_config.price_action_lookback,
            'MOMENTUM_THRESHOLD': self.trading_config.momentum_threshold,
            'ENABLE_MEAN_REVERSION': self.trading_config.enable_mean_reversion
        }

    def setup_logging(self):
        """Configure logging settings"""
        try:
            # Create log directory if needed
            log_path = Path(self.log_config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Configure logging
            logging.basicConfig(
                level=getattr(logging, self.log_config.level),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            logging.info("Logging configured successfully")

        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            raise

    def validate(self) -> tuple:
        """Validate configuration settings

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Validate API configuration
            if not self.api_config.app_id:
                return False, "Missing Deriv APP_ID"

            if not self.api_config.api_token:
                return False, "Missing Deriv API token"

            # Validate trading schedule
            try:
                datetime.strptime(self.trading_start_time, "%H:%M")
                datetime.strptime(self.trading_end_time, "%H:%M")
            except ValueError:
                return False, "Invalid trading hours format"

            if not all(1 <= day <= 7 for day in self.trading_days):
                return False, "Invalid trading days"

            return True, "Configuration validated"

        except Exception as e:
            return False, f"Validation error: {str(e)}"