from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class MovingAverageConfig:
    """Moving average strategy configuration"""
    short_window: int = 5
    medium_window: int = 20
    long_window: int = 50
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    volatility_threshold: float = 0.02
    risk_reward_ratio: float = 2.0
    atr_multiplier: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'MovingAverageConfig':
        """Create config from dictionary"""
        return cls(**config)

@dataclass
class SymbolConfig:
    """Symbol-specific configuration"""
    symbol: str
    stake_amount: float = 100.0
    duration: int = 1
    duration_unit: str = 'm'
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'SymbolConfig':
        """Create config from dictionary"""
        return cls(**config)

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_risk_per_trade: float = 0.02
    max_daily_loss: float = 0.05
    max_open_trades: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'RiskConfig':
        """Create config from dictionary"""
        return cls(**config)

class StrategyConfig:
    """Trading strategy configuration"""
    
    def __init__(self):
        """Initialize strategy configuration"""
        self.moving_average = MovingAverageConfig()
        self.risk = RiskConfig()
        self.symbols: Dict[str, SymbolConfig] = {}
        
    def add_symbol(self, symbol: str, config: SymbolConfig):
        """Add symbol configuration
        
        Args:
            symbol (str): Trading symbol
            config (SymbolConfig): Symbol configuration
        """
        self.symbols[symbol] = config
    
    def remove_symbol(self, symbol: str):
        """Remove symbol configuration
        
        Args:
            symbol (str): Trading symbol
        """
        if symbol in self.symbols:
            del self.symbols[symbol]
    
    def get_symbol_config(self, symbol: str) -> Optional[SymbolConfig]:
        """Get symbol configuration
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            SymbolConfig: Symbol configuration if exists
        """
        return self.symbols.get(symbol)
    
    def get_all_symbols(self) -> Dict[str, SymbolConfig]:
        """Get all symbol configurations
        
        Returns:
            dict: Symbol configurations
        """
        return self.symbols
    
    def update_moving_average_config(self, **kwargs):
        """Update moving average configuration
        
        Args:
            **kwargs: Configuration parameters
        """
        config_dict = self.moving_average.to_dict()
        config_dict.update(kwargs)
        self.moving_average = MovingAverageConfig.from_dict(config_dict)
    
    def update_risk_config(self, **kwargs):
        """Update risk configuration
        
        Args:
            **kwargs: Configuration parameters
        """
        config_dict = self.risk.to_dict()
        config_dict.update(kwargs)
        self.risk = RiskConfig.from_dict(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary
        
        Returns:
            dict: Configuration dictionary
        """
        return {
            'moving_average': self.moving_average.to_dict(),
            'risk': self.risk.to_dict(),
            'symbols': {
                symbol: config.to_dict()
                for symbol, config in self.symbols.items()
            }
        }
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'StrategyConfig':
        """Create configuration from dictionary
        
        Args:
            config (dict): Configuration dictionary
            
        Returns:
            StrategyConfig: Strategy configuration
        """
        strategy_config = cls()
        
        if 'moving_average' in config:
            strategy_config.moving_average = MovingAverageConfig.from_dict(
                config['moving_average']
            )
        
        if 'risk' in config:
            strategy_config.risk = RiskConfig.from_dict(
                config['risk']
            )
        
        if 'symbols' in config:
            for symbol, symbol_config in config['symbols'].items():
                strategy_config.add_symbol(
                    symbol,
                    SymbolConfig.from_dict(symbol_config)
                )
        
        return strategy_config
    
    def validate(self) -> tuple:
        """Validate configuration settings
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Validate moving average parameters
            ma = self.moving_average
            if ma.short_window >= ma.medium_window:
                return False, "Short MA period must be less than medium MA period"
            
            if ma.medium_window >= ma.long_window:
                return False, "Medium MA period must be less than long MA period"
            
            if ma.rsi_oversold >= ma.rsi_overbought:
                return False, "RSI oversold level must be less than overbought"
            
            if ma.volatility_threshold <= 0:
                return False, "Volatility threshold must be positive"
            
            if ma.risk_reward_ratio <= 1:
                return False, "Risk-reward ratio must be greater than 1"
            
            # Validate risk parameters
            risk = self.risk
            if risk.max_risk_per_trade <= 0 or risk.max_risk_per_trade > 1:
                return False, "Invalid risk per trade (must be between 0 and 1)"
            
            if risk.max_daily_loss <= 0 or risk.max_daily_loss > 1:
                return False, "Invalid max daily loss (must be between 0 and 1)"
            
            if risk.max_open_trades <= 0:
                return False, "Maximum open trades must be positive"
            
            # Validate symbol configurations
            for symbol, config in self.symbols.items():
                if config.stake_amount <= 0:
                    return False, f"Invalid stake amount for {symbol}"
                
                if config.duration <= 0:
                    return False, f"Invalid duration for {symbol}"
                
                if config.duration_unit not in ['m', 'h', 'd']:
                    return False, f"Invalid duration unit for {symbol}"
            
            return True, "Configuration validated"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"