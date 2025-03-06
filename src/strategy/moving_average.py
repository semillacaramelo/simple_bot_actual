import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timezone

from src.utils.console import blue_status, cyan_status, magenta_warning, yellow_signal

class MovingAverageStrategy:
    def __init__(self, data_fetcher, **params):
        """Initialize moving average strategy

        Args:
            data_fetcher: Market data component
            params: Strategy parameters from config
        """
        self.data_fetcher = data_fetcher
        self.logger = logging.getLogger(__name__)

        # Store strategy parameters
        self.short_window = params.get('SHORT_WINDOW', 5)
        self.medium_window = params.get('MEDIUM_WINDOW', 20)
        self.long_window = params.get('LONG_WINDOW', 50)
        self.rsi_period = params.get('RSI_PERIOD', 14)
        self.rsi_overbought = params.get('RSI_OVERBOUGHT', 75)  # Increased from 70
        self.rsi_oversold = params.get('RSI_OVERSOLD', 25)      # Increased from 30
        self.volatility_threshold = params.get('VOLATILITY_THRESHOLD', 0.005)  # Lowered from 0.02
        self.atr_multiplier = params.get('ATR_MULTIPLIER', 1.5)  # Reduced from 2.0
        self.risk_reward_ratio = params.get('RISK_REWARD_RATIO', 1.5)  # Reduced from 2.0

        # New parameters for 1-minute trading
        self.price_action_lookback = params.get('PRICE_ACTION_LOOKBACK', 3)
        self.momentum_threshold = params.get('MOMENTUM_THRESHOLD', 0.001)
        self.enable_mean_reversion = params.get('ENABLE_MEAN_REVERSION', True)

        self.logger.info(f"MovingAverageStrategy initialized with parameters: {params}")

    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze symbol and generate trading signal

        Args:
            symbol (str): Trading symbol

        Returns:
            dict: Trading signal if generated
        """
        try:
            cyan_status(f"Analyzing {symbol} for trading signals...")
            # Get required periods for calculations
            periods_needed = max(
                self.long_window,
                self.rsi_period
            ) + 10  # Add buffer

            # Get historical data
            df = await self.data_fetcher.get_historical_data(
                symbol, periods_needed
            )
            if df is None or len(df) < periods_needed:
                magenta_warning(f"Insufficient data for {symbol} analysis.")
                return None

            # Calculate indicators
            df = self._calculate_indicators(df.copy()) # Ensure we are working on a copy

            # Generate trading signal
            signal = self._generate_signal(symbol, df)
            if signal:
                self.logger.info(
                    f"Signal generated for {symbol}",
                    extra={'signal': signal}
                )

            return signal

        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {str(e)}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators

        Args:
            df (DataFrame): Price data

        Returns:
            DataFrame: Data with indicators
        """
        try:
            blue_status("Calculating technical indicators...")
            # Calculate moving averages
            df.loc[:, 'sma_short'] = df['close'].rolling(window=self.short_window).mean()
            df.loc[:, 'sma_medium'] = df['close'].rolling(window=self.medium_window).mean()
            df.loc[:, 'sma_long'] = df['close'].rolling(window=self.long_window).mean()

            # Calculate EMA for more responsive signals
            df.loc[:, 'ema_short'] = df['close'].ewm(span=self.short_window, adjust=False).mean()
            df.loc[:, 'ema_medium'] = df['close'].ewm(span=self.medium_window, adjust=False).mean()

            # Calculate RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=self.rsi_period).mean()
            avg_loss = loss.rolling(window=self.rsi_period).mean()

            if avg_loss.fillna(0).replace(0, np.nan).isnull().all():
                rs = pd.Series(np.zeros_like(avg_gain), index=avg_gain.index)
            else:
                rs = avg_gain / avg_loss

            df.loc[:, 'rsi'] = 100 - (100 / (1 + rs))

            # Calculate ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            df.loc[:, 'atr'] = true_range.rolling(window=14).mean()

            # Calculate volatility (standard deviation of returns)
            df.loc[:, 'volatility'] = df['close'].pct_change().rolling(window=20).std()

            # Price action indicators for 1-minute trading
            df.loc[:, 'price_momentum'] = df['close'].diff(self.price_action_lookback)
            df.loc[:, 'price_pct_change'] = df['close'].pct_change(self.price_action_lookback)

            # Mean reversion indicator (distance from medium EMA)
            df.loc[:, 'mean_distance'] = (df['close'] - df['ema_medium']) / df['ema_medium']

            blue_status("Technical indicators calculated.")
            return df

        except Exception as e:
            self.logger.error(f"Error calculating indicators: {str(e)}")
            return df

    def _generate_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal from indicators

        Args:
            symbol (str): Trading symbol
            df (DataFrame): Price data with indicators

        Returns:
            dict: Trading signal if conditions met
        """
        try:
            cyan_status(f"Generating trading signal for {symbol}...")

            if len(df) < 2:
                magenta_warning(f"Insufficient data to generate signal for {symbol}.")
                return None

            # Get latest data points
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Check trading conditions
            signal = None
            signal_details = {}

            self.logger.info(f"DEBUG: Analyzing signal conditions for {symbol}")
            
            # BULLISH CONDITIONS - More flexible for 1-minute trading with more permissive thresholds
            # 1. Traditional MA crossover (less restrictive) OR
            # 2. Mean reversion (when price is far below EMA and starting to correct) OR
            # 3. Momentum-based entry (sudden price movement with RSI confirmation)

            # Condition 1: MA crossover (relaxed)
            ma_crossover_bullish = (
                previous.ema_short <= previous.ema_medium and 
                current.ema_short > current.ema_medium and
                current.rsi < self.rsi_overbought + 5  # More permissive RSI threshold
            )
            
            if ma_crossover_bullish:
                self.logger.info(f"DEBUG: Bullish MA crossover detected for {symbol}")

            # Condition 2: Mean reversion bullish - Relaxed parameters
            mean_reversion_bullish = (
                self.enable_mean_reversion and
                current.mean_distance < -0.001 and  # Only 0.1% below EMA (more sensitive)
                current.price_momentum > 0 and      # Starting to move up
                current.rsi > 25 and current.rsi < 60  # Wider RSI range
            )
            
            if mean_reversion_bullish:
                self.logger.info(f"DEBUG: Bullish mean reversion detected for {symbol}")

            # Condition 3: Momentum entry - Reduced threshold for more signals
            momentum_bullish = (
                current.price_pct_change > self.momentum_threshold * 0.8 and  # 20% lower threshold
                current.rsi > 35 and current.rsi < 75 and  # Wider RSI range
                current.volatility > self.volatility_threshold * 0.3  # Lower volatility requirement
            )
            
            if momentum_bullish:
                self.logger.info(f"DEBUG: Bullish momentum detected for {symbol}")

            if ma_crossover_bullish or mean_reversion_bullish or momentum_bullish:
                # Determine which condition triggered
                if ma_crossover_bullish:
                    trigger = "MA Crossover"
                elif mean_reversion_bullish:
                    trigger = "Mean Reversion"
                else:
                    trigger = "Momentum"

                signal_details = {
                    'Trigger': trigger,
                    'EMA Relation': f'Short EMA: {current.ema_short:.4f}, Medium EMA: {current.ema_medium:.4f}',
                    'RSI Condition': f'RSI ({current.rsi:.2f}) below Overbought ({self.rsi_overbought})',
                    'Volatility Condition': f'Volatility ({current.volatility:.4f}) above Threshold ({self.volatility_threshold})'
                }
                signal = self._create_signal(symbol, 'CALL', current, signal_details)

            # BEARISH CONDITIONS - More flexible for 1-minute trading
            # Similar conditions as bullish but reversed with more permissive parameters

            # Condition 1: MA crossover (relaxed)
            ma_crossover_bearish = (
                previous.ema_short >= previous.ema_medium and
                current.ema_short < current.ema_medium and
                current.rsi > self.rsi_oversold - 5  # More permissive RSI threshold
            )
            
            if ma_crossover_bearish:
                self.logger.info(f"DEBUG: Bearish MA crossover detected for {symbol}")

            # Condition 2: Mean reversion bearish - Relaxed parameters
            mean_reversion_bearish = (
                self.enable_mean_reversion and
                current.mean_distance > 0.001 and   # Only 0.1% above EMA (more sensitive)
                current.price_momentum < 0 and      # Starting to move down
                current.rsi < 75 and current.rsi > 40  # Wider RSI range
            )
            
            if mean_reversion_bearish:
                self.logger.info(f"DEBUG: Bearish mean reversion detected for {symbol}")

            # Condition 3: Momentum entry - Reduced threshold for more signals
            momentum_bearish = (
                current.price_pct_change < -self.momentum_threshold * 0.8 and  # 20% lower threshold
                current.rsi < 65 and current.rsi > 25 and  # Wider RSI range
                current.volatility > self.volatility_threshold * 0.3  # Lower volatility requirement
            )
            
            if momentum_bearish:
                self.logger.info(f"DEBUG: Bearish momentum detected for {symbol}")

            if ma_crossover_bearish or mean_reversion_bearish or momentum_bearish and not signal:
                # Determine which condition triggered
                if ma_crossover_bearish:
                    trigger = "MA Crossover"
                elif mean_reversion_bearish:
                    trigger = "Mean Reversion"
                else:
                    trigger = "Momentum"

                signal_details = {
                    'Trigger': trigger,
                    'EMA Relation': f'Short EMA: {current.ema_short:.4f}, Medium EMA: {current.ema_medium:.4f}',
                    'RSI Condition': f'RSI ({current.rsi:.2f}) above Oversold ({self.rsi_oversold})',
                    'Volatility Condition': f'Volatility ({current.volatility:.4f}) above Threshold ({self.volatility_threshold})'
                }
                signal = self._create_signal(symbol, 'PUT', current, signal_details)

            if signal:
                yellow_signal(f"Trading Signal Generated: {signal['type']} for {symbol} at {signal['entry_price']:.4f}")
                for condition, detail in signal.get('signal_details', {}).items():
                    blue_status(f"  - {condition}: {detail}")
            else:
                blue_status(f"No signal generated for {symbol} based on current conditions.")

            return signal

        except Exception as e:
            self.logger.error(f"Error generating signal: {str(e)}")
            return None

    def _create_signal(self, symbol: str, signal_type: str,
                      data: pd.Series, signal_details: Dict) -> Dict:
        """Create trading signal

        Args:
            symbol (str): Trading symbol
            signal_type (str): Signal type (CALL/PUT)
            data (Series): Current market data

        Returns:
            dict: Trading signal
        """
        try:
            entry_price = data['close']
            atr = data['atr']

            # Calculate stop loss and take profit with improved risk management for 1-minute trades
            # Use smaller multipliers for fast-paced 1-minute trades
            if signal_type == 'CALL':
                stop_loss = entry_price - (atr * self.atr_multiplier)
                take_profit = entry_price + (
                    atr * self.atr_multiplier * 
                    self.risk_reward_ratio
                )
            else:
                stop_loss = entry_price + (atr * self.atr_multiplier)
                take_profit = entry_price - (
                    atr * self.atr_multiplier * 
                    self.risk_reward_ratio
                )

            signal = {
                'symbol': symbol,
                'type': signal_type,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'generated_time': datetime.now(timezone.utc).timestamp(),
                'indicators': {
                    'sma_short': data['sma_short'],
                    'sma_medium': data['sma_medium'],
                    'sma_long': data['sma_long'],
                    'ema_short': data['ema_short'],
                    'ema_medium': data['ema_medium'],
                    'rsi': data['rsi'],
                    'atr': data['atr'],
                    'volatility': data['volatility'],
                    'price_momentum': data['price_momentum'],
                    'mean_distance': data['mean_distance']
                },
                'signal_details': signal_details # Include signal details in output
            }

            return signal

        except Exception as e:
            self.logger.error(f"Error creating signal: {str(e)}")
            # Return empty dict instead of None to match return type
            return {
                'symbol': symbol,
                'type': signal_type,
                'error': str(e),
                'generated_time': datetime.now(timezone.utc).timestamp()
            }

    def validate_signal(self, signal: Dict) -> bool:
        """Validate trading signal

        Args:
            signal (dict): Trading signal

        Returns:
            bool: True if signal is valid
        """
        try:
            if not signal:
                return False

            # Check required fields
            required_fields = [
                'symbol', 'type', 'entry_price',
                'stop_loss', 'take_profit'
            ]
            if not all(field in signal for field in required_fields):
                return False

            # Check signal type
            if signal['type'] not in ['CALL', 'PUT']:
                return False

            # Check price levels
            entry = signal['entry_price']
            stop = signal['stop_loss']
            target = signal['take_profit']

            if entry <= 0 or stop <= 0 or target <= 0:
                return False

            # Validate price relationships (more lenient for 1-minute trades)
            if signal['type'] == 'CALL':
                if stop >= entry or entry >= target:
                    return False
            else:
                if target >= entry or entry >= stop:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating signal: {str(e)}")
            return False