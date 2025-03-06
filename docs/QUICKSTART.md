# Quick Start Guide

This guide will help you get started with implementing and running your first trading strategy using the bot.

## First Steps

1. Get your API credentials from Deriv.com:
   - Log in to your Deriv account
   - Go to Settings -> API Token
   - Create a new token with "Trade" permission
   - Copy the token

2. Configure your environment:
   ```bash
   # Copy and edit the .env file
   copy .env.example .env

   # Edit the file with your credentials
   DERIV_API_TOKEN_DEMO=your_demo_token_here
   ENVIRONMENT=demo
   ```

## Enhanced Moving Average Strategy for 1-Minute Trading

The trading bot now includes an enhanced strategy specifically optimized for 1-minute binary trades. The strategy uses multiple entry conditions to improve trade frequency while maintaining risk management principles.

```python
from config.strategy_config import StrategyConfig, SymbolConfig

# Create strategy configuration for 1-minute binary trades
config = StrategyConfig()

# Configure moving averages for short-term trading
config.update_moving_average_config(
    short_window=3,     # 3-minute trend (more responsive)
    medium_window=10,   # 10-minute trend
    long_window=30,     # 30-minute overall trend
    rsi_period=10,      # Reduced for faster response
    rsi_overbought=75,  # More permissive threshold
    rsi_oversold=25,    # More permissive threshold
    volatility_threshold=0.005  # Lower threshold for 1-min trading
)

# Enable additional strategy options
config.enable_mean_reversion(True)  # Enable mean reversion strategy
config.set_momentum_threshold(0.001)  # Set sensitivity for momentum detection

# Configure symbol-specific settings
config.add_symbol("R_100", SymbolConfig(
    symbol="R_100",
    stake_amount=5.0,    # Smaller stake for faster trading
    duration=1,          # 1-minute contracts
    duration_unit="m"    # Minutes
))

# Set appropriate risk parameters for fast trading
config.update_risk_config(
    max_risk_per_trade=0.01,   # 1% risk per trade
    max_daily_loss=0.05,       # 5% max daily loss
    max_open_trades=3          # Max 3 concurrent trades
)
```

## Understanding the Enhanced Strategy

The enhanced moving average strategy now generates signals based on multiple factors to increase flexibility:

1. **Multiple Entry Conditions**:
   - **MA Crossover**: Traditional MA crossover (Short EMA crosses Medium EMA)
   - **Mean Reversion**: Entry when price deviates from medium-term average
   - **Momentum-Based**: Entry on significant short-term price momentum

2. **Relaxed Parameters**:
   - More permissive RSI thresholds (25-75 instead of 30-70)
   - Lower volatility requirements suitable for 1-minute data
   - EMA (Exponential Moving Average) for more responsive signals

3. **Improved Risk Management**:
   - Smaller ATR multiplier (1.5 instead of 2.0) for tighter stops
   - Reduced risk-reward ratio (1.5 instead of 2.0) for faster profit taking
   - Maximum trade duration of 1-5 minutes

Example signal conditions:
```python
# Bullish MA Crossover:
- Short EMA > Medium EMA
- RSI < 75 (not overbought)
- Volatility > 0.005 (minimum required volatility)

# Bullish Mean Reversion:
- Price < Medium EMA by at least 0.2%
- Price momentum turning positive
- RSI between 30-50 (not extreme)

# Bullish Momentum:
- Price change over last 3 periods > 0.1%
- RSI between 40-70 (reasonable range)
- Some volatility present
```

## Risk Management for 1-Minute Trading

1. Position Sizing (Adjusted for higher frequency):
```python
# Risk-Based Position Size with lower per-trade risk
account_balance = 1000.0
risk_per_trade = 0.01  # 1%
max_open_trades = 3    # More concurrent trades possible
position_size = (account_balance * risk_per_trade) / max_open_trades  # $3.33 risk per trade
```

2. Stop Loss Calculation (Tighter for short-term trades):
```python
# ATR-Based Stop Loss with lower multiplier
atr = 0.00123  # Current ATR value
entry_price = 1.2345
atr_multiplier = 1.5  # Reduced from 2.0

# For long positions
stop_loss = entry_price - (atr * atr_multiplier)

# For short positions
stop_loss = entry_price + (atr * atr_multiplier)
```

## Performance Monitoring

Monitor your strategy's performance through the enhanced logging system:

1. General Trading Log:
```
2024-02-20 10:15:23 [INFO] Strategy signal generated - R_100
2024-02-20 10:15:24 [INFO] Trade executed - ID: trade_123
2024-02-20 10:20:24 [INFO] Trade closed - P/L: +1.23
```

2. Performance Metrics:
```
Win Rate: 55%
Average Win: $2.50
Average Loss: $1.80
Sharpe Ratio: 1.2
Max Drawdown: 4.5%
```

## Recommended Adjustments for Different Market Conditions

1. For Highly Volatile Markets:
```python
# More conservative settings for high volatility
config.update_moving_average_config(
    short_window=5,        # Slightly longer for stability
    volatility_threshold=0.01,  # Higher threshold
    atr_multiplier=2.0     # Wider stops to avoid whipsaws
)

config.enable_mean_reversion(False)  # Disable mean reversion in high volatility
```

2. For Low Volatility Markets:
```python
# More aggressive settings for low volatility
config.update_moving_average_config(
    short_window=2,        # More responsive
    volatility_threshold=0.003,  # Lower threshold
    momentum_threshold=0.0008    # More sensitive to small movements
)

config.enable_mean_reversion(True)  # Mean reversion works well in range-bound markets
```

3. For Optimized 1-Minute Trading:
```python
# Balanced settings for 1-minute binary options
config.update_moving_average_config(
    short_window=3,
    medium_window=10,
    rsi_period=10,
    risk_reward_ratio=1.5,
    atr_multiplier=1.5
)

# Use dynamic time-based settings by hour of day
# More active during high-volatility hours
config.set_active_hours(8, 17)  # Trading from 8 AM to 5 PM
```

## Next Steps

1. Backtest your configuration:
   - Use the enhanced backtest engine with 1-minute data
   - Test different entry condition combinations
   - Analyze performance across various market conditions

2. Paper Trading:
   - Start with small stakes in demo account
   - Monitor win rate and drawdown carefully
   - Adjust parameters based on results

3. Advanced Customization:
   - Create custom entry/exit rules for specific market conditions
   - Implement time-of-day filters
   - Add market sentiment analysis

## Troubleshooting

1. No Signals Generated:
   - Check if volatility thresholds are too high
   - Verify that RSI thresholds aren't too restrictive
   - Confirm that EMA calculation has enough historical data

2. Too Many Signals:
   - Increase the volatility threshold
   - Make RSI conditions more restrictive
   - Add additional filtering conditions

3. Performance Issues:
   - Monitor system resources during high-frequency trading
   - Check API rate limits
   - Consider using a VPS for stable execution

## Best Practices for 1-Minute Trading

1. **Start Small**: Begin with small stakes until the strategy proves itself
2. **Monitor Constantly**: 1-minute trading requires more active monitoring
3. **Avoid Overtrading**: Set daily limits on number of trades and max loss
4. **Maintain Discipline**: Follow your strategy rules even during drawdowns
5. **Regular Review**: Analyze performance daily and make adjustments weekly

Remember: Always test thoroughly in a demo environment before using real funds.