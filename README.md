# Simple Trading Bot for Deriv.com

A Python trading bot that uses the Deriv API to implement a triple moving average strategy with proper risk management.

## Features

- Connects to Deriv.com using the official python-deriv-api library
- Supports both demo and real account trading
- Implements a triple moving average crossover strategy with RSI filter
- Real-time price monitoring and automated trade execution
- Risk management with position sizing and drawdown protection
- Performance tracking and trade analysis
- Structured logging with both file and console output

## Installation

1. Clone this repository
2. Set up a Python virtual environment (Python 3.9+ required):
```bash
python -m venv TradingENV
```
3. Activate the environment:
```bash
# Windows
TradingENV\Scripts\activate
# Unix/MacOS
source TradingENV/bin/activate
```
4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`
2. Get your API token from [Deriv.com](https://app.deriv.com/account/api-token)
3. Configure the following in `.env`:
   - DERIV_API_TOKEN_DEMO: Your demo account API token
   - DERIV_API_TOKEN_REAL: Your real account API token (optional)
   - ENVIRONMENT: 'demo' or 'real'
   - Risk parameters (MAX_RISK, MAX_DAILY_LOSS, etc.)
   - Strategy parameters (moving average windows, RSI settings, etc.)

## Usage

Start the bot using:
```bash
python main.py
```

Or use the provided batch script on Windows:
```bash
start.bat
```

## Components

### API Integration
- `deriv_connector.py`: Manages WebSocket connection and API authorization
- `data_fetcher.py`: Handles market data retrieval and caching

### Strategy
- `moving_average.py`: Implements the triple MA crossover strategy
- `strategy_executor.py`: Manages strategy execution and signal generation

### Risk Management
- `risk_manager.py`: Controls position sizing and risk limits
- Configurable per-trade and daily loss limits
- Maximum open positions control

### Monitoring
- `performance.py`: Tracks trade performance and statistics
- `logger.py`: Structured logging with JSON formatting
- Real-time monitoring of active trades
- **Enhanced Console Output**: Real-time status updates with colors and icons for easy monitoring.

#### Console Output Features

The bot now includes enhanced console output for real-time monitoring, using colors and icons to indicate different status levels:

- **Color Scheme:**
    - 🚀 Cyan: Initialization steps
    - 📊 Blue: Data processing activities
    - 💡 Yellow: Trading signals
    - ⚠️ Magenta: Warnings
    - ✅ Green: Success messages
    - ❌ Red: Error messages
    - ⏳ White: Waiting/idle states

- **Icon Legend:**
    - 🚀: Initialization
    - 📊: Data Processing
    - 💡: Signal
    - ⚠️: Warning
    - ✅: Success
    - ❌: Error
    - ⏳: Waiting

**Example Output:**
```
🚀 Initializing bot...
✅ Configuration loaded successfully
📊 Fetching market data...
💡 Potential BUY signal detected!
✅ Trade executed successfully.
⏳ Waiting for next candle...
```

See below for a full list of icons and colors used in the console output.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| ENVIRONMENT | Trading environment (demo/real) | demo |
| DERIV_APP_ID | Application ID | 1089 |
| DERIV_API_TOKEN_DEMO | Demo account API token | - |
| DERIV_API_TOKEN_REAL | Real account API token | - |
| MAX_RISK | Maximum total risk percentage | 0.10 |
| MAX_DAILY_LOSS | Maximum daily loss percentage | 0.05 |
| RISK_PER_TRADE | Risk per trade percentage | 0.02 |
| MAX_OPEN_TRADES | Maximum concurrent trades | 3 |
| DEFAULT_SYMBOL | Default trading symbol | R_100 |
| SHORT_WINDOW | Short MA period | 5 |
| MEDIUM_WINDOW | Medium MA period | 20 |
| LONG_WINDOW | Long MA period | 50 |
| RSI_PERIOD | RSI calculation period | 14 |

## Console Output Icons and Colors

| Icon | Color   | Description             |
|------|---------|-------------------------|
| 🚀    | Cyan    | Initialization          |
| 📊    | Blue    | Data Processing         |
| 💡    | Yellow  | Trading Signals         |
| ⚠️    | Magenta | Warnings                |
| ✅    | Green   | Success Messages        |
| ❌    | Red     | Error Messages          |
| ⏳    | White   | Waiting/Idle States     |

## Strategy Logic

The bot uses a triple moving average crossover strategy with the following rules:

### Entry Conditions
- Long (CALL):
  - Short MA crosses above Medium MA
  - Medium MA is above Long MA
  - RSI below overbought level
  - Sufficient volatility

- Short (PUT):
  - Short MA crosses below Medium MA
  - Medium MA is below Long MA
  - RSI above oversold level
  - Sufficient volatility

### Exit Conditions
- Take profit at defined R:R ratio
- Stop loss using ATR-based calculation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - feel free to use this code as you wish.

## Disclaimer

Trading carries significant financial risk. This bot is for educational purposes only. Use at your own risk.
