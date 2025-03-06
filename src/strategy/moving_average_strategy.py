import pandas as pd

class SignalGenerator:
    def __init__(self):
        pass

    def generate_signal(self, symbol: str, historical_data: pd.DataFrame) -> dict:
        """Generates a trading signal.

        Args:
            symbol (str): The symbol to generate a signal for.
            historical_data (pd.DataFrame): Historical price data.  Must contain 'close', 'high', and 'low' columns.

        Returns:
            dict: A dictionary containing the generated signal.
                  Returns None if no signal is generated.
        """
        # Placeholder for your technical indicator calculations.  
        # Replace with your actual logic to determine signal_type, current_price, stop_loss, take_profit
        current_price = historical_data['close'].iloc[-1]
        signal_type = self._determine_signal_type(historical_data)  #Example function
        stop_loss = current_price * 0.98
        take_profit = current_price * 1.02
        current_time = pd.Timestamp.now()


        if signal_type is None:
            return None

        # Calculate volatility and ATR
        volatility = self._calculate_volatility(historical_data)
        atr_value = self._calculate_atr(historical_data)

        # Create signal dictionary with all required fields
        signal = {
            'symbol': symbol,
            'type': signal_type,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': current_time,
            'stake_amount': 100.0,  # Default stake amount
            'volatility': volatility,
            'atr_value': atr_value,
            'duration': 1,  # Default duration for 1-minute contracts
            'duration_unit': 'm'  # Default to minutes
        }

        # Ensure all signal values are not None and are valid
        if not all(value is not None for value in signal.values()):
            self.logger.warning(f"Signal is incomplete, some values are None: {signal}")
            return None

        return signal


    def _determine_signal_type(self, data: pd.DataFrame) -> str:
        """Determines the type of signal (e.g., PUT, CALL). Replace with your actual logic."""
        # Example: simple mean reversion strategy
        short_ema = data['close'].ewm(span=10).mean().iloc[-1]
        medium_ema = data['close'].ewm(span=20).mean().iloc[-1]
        rsi = self._calculate_rsi(data)

        if short_ema < medium_ema and rsi < 30:
            return "CALL"  #Example
        elif short_ema > medium_ema and rsi > 70:
            return "PUT"   #Example
        else:
            return None


    def _calculate_rsi(self, data: pd.DataFrame, window: int = 14) -> float:
        """Calculate Relative Strength Index

        Args:
            data (pd.DataFrame): Historical price data
            window (int, optional): RSI period. Defaults to 14.

        Returns:
            float: RSI value
        """
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    def _calculate_volatility(self, data: pd.DataFrame, window: int = 14) -> float:
        """Calculate price volatility

        Args:
            data (pd.DataFrame): Historical price data
            window (int, optional): Window period. Defaults to 14.

        Returns:
            float: Volatility value
        """
        # Calculate daily returns
        returns = data['close'].pct_change().dropna()

        # If we don't have enough data, return a default value
        if len(returns) < window:
            return 0.02  # Default volatility

        # Calculate standard deviation of returns (volatility)
        volatility = returns.rolling(window=window).std().iloc[-1]

        # Return at least 0.01 volatility to avoid division by zero issues
        return max(volatility, 0.01)

    def _calculate_atr(self, data: pd.DataFrame, window: int = 14) -> float:
        """Calculate Average True Range

        Args:
            data (pd.DataFrame): Historical price data
            window (int, optional): ATR period. Defaults to 14.

        Returns:
            float: ATR value
        """
        # If we don't have high/low data, use a default calculation based on close prices
        if 'high' not in data.columns or 'low' not in data.columns:
            # Use close price movement as a proxy for ATR
            close_changes = data['close'].diff().abs()
            atr = close_changes.rolling(window=window).mean().iloc[-1]
            return max(atr, 1.0)  # Ensure minimum ATR value

        # Traditional ATR calculation with high/low data
        high_low = data['high'] - data['low']
        high_close = (data['high'] - data['close'].shift()).abs()
        low_close = (data['low'] - data['close'].shift()).abs()

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        atr = true_range.rolling(window=window).mean().iloc[-1]
        return max(atr, 1.0)  # Ensure minimum ATR value

# Example usage:
data = pd.DataFrame({'close': [10, 12, 15, 14, 16, 18, 20, 19, 22, 25], 'high': [11, 13, 16, 15, 17, 19, 21, 20, 23, 26], 'low': [9, 11, 14, 13, 15, 17, 19, 18, 21, 24]})
generator = SignalGenerator()
signal = generator.generate_signal('R_100', data)
print(signal)
