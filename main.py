import sys
import os
import asyncio
import threading
import time
from datetime import datetime
from config.config import Config
from src.api.deriv_connector import DerivConnector
from src.api.data_fetcher import DataFetcher
from src.strategy.strategy_executor import StrategyExecutor
from src.execution.order_executor import OrderExecutor
from src.risk.risk_manager import RiskManager
from src.monitor.logger import Logger
from src.monitor.performance import PerformanceTracker
from src.utils.console import cyan_status, green_success, red_error, magenta_warning, white_wait, blue_status, yellow_signal

def check_virtual_env():
    """Check if running in the correct virtual environment"""
    venv_path = os.environ.get('VIRTUAL_ENV', '')
    required_venv = 'TradingENV_virtualenv'

    if not venv_path or required_venv not in venv_path:
        print("Error: Please run the bot from within the TradingENV_virtualenv virtual environment.")
        print("Use 'setup_env.bat' to set up and activate the environment.")
        return False
    return True

async def main():
    api_connector = None
    logger = None

    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Initialize logger first for error tracking
        logger = Logger(log_file='trading_bot.log')
        cyan_status('🚀 Initializing trading bot...')
        logger.log('Initializing trading bot...', level='info')

        # Load configuration
        cyan_status('📄 Loading configuration...')
        try:
            config = Config()
            api_token = config.get_api_token()
            app_id = int(config.get_app_id())  # Ensure app_id is converted to int
            risk_params = config.get_risk_params()
            trading_params = config.get_trading_params()
            
            blue_status(f"📊 Trading parameters: Symbol={trading_params['default_symbol']}, Windows={trading_params['SHORT_WINDOW']}/{trading_params['MEDIUM_WINDOW']}/{trading_params['LONG_WINDOW']}")

            # Validate API credentials
            if not api_token or not app_id:
                error_msg = "Missing API credentials. Check DERIV_API_TOKEN_DEMO and APP_ID in environment."
                logger.log_error(Exception(error_msg), {'context': 'configuration'})
                red_error(error_msg)
                return

            logger.log('Configuration loaded successfully',
                       level='info',
                       environment=config.environment,
                       trading_params=trading_params)
            green_success('Configuration loaded successfully')
        except Exception as e:
            logger.log_error(e, {'context': 'configuration_loading'})
            red_error('Failed to load configuration. Check logs/trading_bot.log for details.')
            return

        # Initialize components with error handling
        cyan_status('Initializing components...')
        try:
            # Initialize API connector with detailed validation
            api_connector = DerivConnector(api_token, app_id)
            cyan_status('🔌 Connecting to Deriv API...')

            connect_success, error_message = await api_connector.connect()
            if not connect_success:
                logger.log_error(Exception(error_message), {'context': 'api_connection'})
                red_error(f'❌ Failed to connect to Deriv API: {error_message}')
                return

            if not api_connector.authorized:
                error_msg = "API connection succeeded but authorization failed."
                logger.log_error(Exception(error_msg), {'context': 'api_authorization'})
                red_error(f'❌ {error_msg}')
                return

            green_success('✅ Connected to Deriv API successfully')
            blue_status('🔒 API authorization verified')

            # Initialize data fetcher
            cyan_status('📈 Initializing DataFetcher...')
            data_fetcher = DataFetcher(api_connector)
            green_success('✅ DataFetcher initialized')

            # Initialize monitoring and risk management
            cyan_status('🛡️ Initializing RiskManager...')
            trading_start = datetime.strptime(config.trading_start_time, "%H:%M").time()
            trading_end = datetime.strptime(config.trading_end_time, "%H:%M").time()
            blue_status(f"⏰ Trading hours set to {trading_start} - {trading_end}")
            
            risk_manager = RiskManager(
                api_connector=api_connector,  # Pass API connector here
                max_risk=risk_params['max_risk'],
                max_daily_loss=risk_params['max_daily_loss'],
                risk_per_trade=risk_params['risk_per_trade'],
                max_open_trades=risk_params['max_open_trades'],
                trading_hours=(trading_start, trading_end),
                min_volatility=trading_params.get('min_volatility', 0.01),
                max_volatility=trading_params.get('max_volatility', 0.05)
            )

            # Initialize the risk manager with API balance
            logger.log('Initializing RiskManager with API balance...', level='info')
            await risk_manager.initialize()  # Let it fetch balance from API

            # Log initial risk metrics
            initial_metrics = risk_manager.get_risk_metrics()
            logger.log('Initial risk metrics', level='info', metrics=initial_metrics)

            performance_tracker = PerformanceTracker()

            # Initialize order executor with monitoring components
            order_executor = OrderExecutor(
                api_connector,
                performance_tracker=performance_tracker,
                risk_manager=risk_manager
            )

            # Initialize strategy
            strategy_executor = StrategyExecutor(
                data_fetcher=data_fetcher,
                order_executor=order_executor,
                **trading_params
            )

            logger.log('Components initialized successfully', level='info')
            green_success('Components initialized successfully')

        except Exception as e:
            if logger:
                logger.log_error(e, {'context': 'component_initialization'})
            red_error('Failed to initialize components. Check logs/trading_bot.log for details.')
            return

        # Start trading
        try:
            symbol = trading_params['default_symbol']
            cyan_status(f'Starting strategy execution for symbol: {symbol}')
            logger.log(f'Starting strategy execution for symbol: {symbol}', level='info')

            while True:
                try:
                    white_wait('⏳ Waiting for next iteration...')
                    # Verify API connection
                    if not api_connector.connected or not api_connector.authorized:
                        magenta_warning('⚠️ API connection lost, attempting to reconnect...')
                        logger.log('API connection lost, attempting to reconnect...', level='warning')
                        cyan_status('🔌 Reconnecting to Deriv API...')
                        connect_success, error_message = await api_connector.connect()
                        if not connect_success:
                            logger.log_error(Exception(error_message), {'context': 'api_reconnection'})
                            red_error(f'❌ Failed to reconnect: {error_message}')
                            break
                        green_success('✅ API reconnected successfully.')

                    # Get current market price for the symbol
                    blue_status(f"📊 DEBUG: Fetching current price for {symbol}...")
                    logger.log(f"DEBUG: Getting price for {symbol}", level='debug')
                    
                    # Check if we have an active subscription for this symbol
                    if symbol in api_connector.active_subscriptions:
                        logger.log(f"Using existing subscription for {symbol}", level='debug')
                        # Use the last received price or query it without subscribing
                        ticks_request = {
                            "ticks": symbol,
                            "subscribe": 0  # Don't subscribe, just get the current price
                        }
                    else:
                        logger.log(f"Creating new subscription for {symbol}", level='debug')
                        ticks_request = {
                            "ticks": symbol,
                            "subscribe": 1
                        }
                    
                    try:
                        ticks_response = await api_connector.api.ticks(ticks_request)
                        logger.log(f"DEBUG: Received ticks response: {ticks_response}", level='debug')
                        
                        if not ticks_response or 'error' in ticks_response:
                            error_msg = ticks_response.get('error', {}).get('message', 'Unknown error')
                            red_error(f"❌ Error fetching price: {error_msg}")
                            logger.log_error(Exception(f"Ticks request failed: {error_msg}"), {'context': 'price_fetch'})
                            current_price = 0
                        else:
                            current_price = float(ticks_response.get('tick', {}).get('quote', 0))
                            # If this was a subscription, track it
                            if ticks_request.get('subscribe') == 1 and 'subscription' in ticks_response:
                                api_connector.active_subscriptions.add(symbol)
                    except Exception as e:
                        red_error(f"❌ Error fetching price: {str(e)}")
                        logger.log_error(e, {'context': 'price_fetch'})
                        current_price = 0

                    if current_price > 0:
                        blue_status(f"💹 Current price for {symbol}: {current_price}")
                        logger.log(f"Current market price: {current_price}", level='info', symbol=symbol)
                        
                        # Update any open positions
                        active_trades = order_executor.get_active_trades()
                        if active_trades:
                            cyan_status(f"🔍 Checking {len(active_trades)} active positions...")
                            logger.log(f"Processing {len(active_trades)} active trades", level='info')
                            for trade_id, trade in active_trades.items():
                                logger.log(f"DEBUG: Evaluating position {trade_id} at price {current_price}", level='debug', trade=trade)
                                await order_executor.close_position(trade_id, price=current_price)
                        else:
                            blue_status("📭 No active trades to update")
                            logger.log("No active trades to update", level='info')
                    else:
                        magenta_warning(f"⚠️ Invalid price (0) received for {symbol}. Skipping this iteration.")
                        logger.log_error(Exception("Invalid price received"), {'context': 'price_validation', 'symbol': symbol})

                    # Execute strategy iteration with enhanced logging
                    cyan_status(f"🧠 Executing trading strategy for {symbol}...")
                    logger.log(f"DEBUG: Starting strategy execution for {symbol}", level='debug')
                    
                    # Execute strategy with signal tracking
                    signal = await strategy_executor.execute_iteration(symbol)
                    
                    if signal and isinstance(signal, dict) and 'type' in signal:
                        yellow_signal(f"🎯 New signal generated: {signal['type']} for {symbol} at {signal.get('entry_price', 'N/A')}")
                        logger.log_signal(signal)
                        logger.log(f"DEBUG: Signal details - Stop Loss: {signal.get('stop_loss')}, Take Profit: {signal.get('take_profit')}", 
                                  level='debug', signal_id=signal.get('id', 'unknown'))
                    else:
                        blue_status(f"⏳ No new trading signals for {symbol} in this iteration")
                        logger.log(f"No trading signals generated for {symbol}", level='info')

                    # Get and log risk metrics
                    risk_metrics = risk_manager.get_risk_metrics()
                    logger.log('Risk metrics update', level='info', metrics=risk_metrics)
                    blue_status(f"📊 Risk metrics - Open positions: {risk_metrics['open_positions']}, Open risk: {risk_metrics['open_risk_pct']:.2f}%")

                    # Get and log performance metrics
                    blue_status("📈 Analyzing trading performance...")
                    performance_data = performance_tracker.analyze_performance()
                    if performance_data:
                        logger.log_performance(performance_data)
                        
                        # Format performance summary for console
                        win_rate = performance_data['overall'].get('win_rate', 0) * 100
                        total_profit = performance_data['overall'].get('total_profit', 0)
                        total_loss = performance_data['overall'].get('total_loss', 0)
                        net_pl = total_profit - total_loss
                        
                        if net_pl >= 0:
                            green_success(f"💰 Performance: Win rate {win_rate:.1f}%, Net P/L: +{net_pl:.2f}")
                        else:
                            magenta_warning(f"📉 Performance: Win rate {win_rate:.1f}%, Net P/L: {net_pl:.2f}")

                        # Check if we've hit our daily loss limit
                        if performance_data['overall']['total_loss'] >= risk_params['max_daily_loss']:
                            magenta_warning('⚠️ Daily loss limit reached, stopping trading')
                            logger.log('Daily loss limit reached, stopping trading', level='warning')
                            break

                    # Log active trades
                    active_trades = order_executor.get_active_trades()
                    logger.log('Active trades update', level='info',
                             active_trades=len(active_trades))

                    # Sleep for iteration interval
                    blue_status(f"⏱️ Sleeping for 30 seconds (waiting for next iteration)")
                    logger.log("Sleeping between iterations", level='debug', 
                              time=datetime.now().strftime("%H:%M:%S"),
                              active_positions=len(order_executor.get_active_trades()))
                    
                    # Sleep in smaller chunks to allow for more responsive updates
                    for i in range(6):  # 6 intervals of 5 seconds
                        await asyncio.sleep(5)
                        if i % 2 == 0:  # Output status every 10 seconds
                            white_wait(f"⏳ Waiting... {(i+1)*5}/30 seconds elapsed")

                except KeyboardInterrupt:
                    cyan_status('Received shutdown signal')
                    logger.log('Received shutdown signal', level='info')
                    break
                except Exception as e:
                    logger.log_error(e, {'context': 'main_loop'})
                    red_error('Error in main loop. Check logs/trading_bot.log for details.')
                    await asyncio.sleep(60)  # Wait before retrying

        except Exception as e:
            if logger:
                logger.log_error(e, {'context': 'strategy_execution'})
            red_error('Error during strategy execution. Check logs/trading_bot.log for details.')

    except KeyboardInterrupt:
        cyan_status('Shutting down gracefully...')
        if logger:
            logger.log('Shutting down gracefully...', level='info')
    except Exception as e:
        if logger:
            logger.log_error(e, {'context': 'main'})
        red_error('Fatal error occurred. Check logs/trading_bot.log for details.')
    finally:
        # Clean shutdown
        if api_connector:
            try:
                # Forget all active subscriptions before disconnecting
                if api_connector.connected and api_connector.authorized and hasattr(api_connector, 'active_subscriptions'):
                    for symbol in list(api_connector.active_subscriptions):
                        logger.log(f"Unsubscribing from {symbol}", level='debug')
                        try:
                            await api_connector.api.forget_all('ticks')
                            api_connector.active_subscriptions.clear()
                        except Exception as unsub_error:
                            logger.log_error(unsub_error, {'context': 'unsubscribe'})
                
                await api_connector.disconnect()
                if logger:
                    logger.log('Trading bot shut down successfully', level='info')
                green_success('Trading bot shut down successfully')
            except Exception as e:
                if logger:
                    logger.log_error(e, {'context': 'shutdown'})
                red_error('Error during shutdown. Check logs/trading_bot.log for details.')

if __name__ == '__main__':
    asyncio.run(main())