import logging
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import sys
import os

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record):
        """Format log record as JSON

        Args:
            record: Log record

        Returns:
            str: Formatted JSON log entry
        """
        try:
            # Base log object
            log_obj = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage()
            }

            # Add exception info
            if record.exc_info:
                log_obj['exception'] = self.formatException(record.exc_info)

            # Add structured data if present
            for key, value in record.__dict__.items():
                if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                             'filename', 'funcName', 'levelname', 'levelno', 'lineno',
                             'module', 'msecs', 'msg', 'name', 'pathname', 'process',
                             'processName', 'relativeCreated', 'stack_info', 'thread',
                             'threadName']:
                    try:
                        json.dumps(value)  # Test if serializable
                        log_obj[key] = value
                    except (TypeError, ValueError):
                        log_obj[key] = str(value)

            return json.dumps(log_obj)

        except Exception as e:
            return f"Error formatting log: {str(e)}"

class Logger:
    _instance = None
    _logger_initialized = False  # Track initialization

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_file='trading_bot.log',
                 console_level='INFO', file_level='DEBUG'):
        if Logger._logger_initialized:  # Only initialize once
            return
        Logger._logger_initialized = True

        try:
            # Ensure logs directory exists
            log_dir = Path('logs')
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create full log path
            log_path = log_dir / log_file

            # Use a logger with a unique name to avoid conflicts
            self.logger = logging.getLogger('trading_bot')

            # Important: prevent propagation to root logger to avoid duplication
            self.logger.propagate = False

            # Set level to lowest of the two to capture all relevant logs
            min_level = min(
                getattr(logging, console_level),
                getattr(logging, file_level)
            )
            self.logger.setLevel(min_level)

            # Configure formatters
            json_formatter = JsonFormatter()
            console_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # Clear any existing handlers to avoid duplication
            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            # File handler for JSON logs (detailed)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(json_formatter)
            file_handler.setLevel(getattr(logging, file_level))

            # Console handler for human-readable logs (less detailed)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(getattr(logging, console_level))

            # Add handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

            self.logger.info("Logger initialized successfully")

        except Exception as e:
            print(f"Error initializing logger: {str(e)}")
            raise

    def log(self, message: str, level: str = 'info', **kwargs):
        """Log a message with optional structured data

        Args:
            message (str): Log message
            level (str): Log level
            **kwargs: Additional structured data
        """
        try:
            # Ensure level is lowercase
            level = level.lower()

            # Get the appropriate log method
            log_method = getattr(self.logger, level)

            # Add extra data if provided
            if kwargs:
                log_method(message, extra=kwargs)
            else:
                log_method(message)

        except Exception as e:
            self.logger.error(f"Error logging message: {str(e)}")

    def log_error(self, error: Exception, context: dict = None):
        """Log an error with context

        Args:
            error (Exception): Error to log
            context (dict): Error context
        """
        try:
            # Initialize empty dict if context is None
            if context is None:
                context = {}

            self.logger.error(
                str(error),
                exc_info=error,
                extra={'context': context}
            )
        except Exception as e:
            self.logger.error(f"Error logging error: {str(e)}")

    def log_trade(self, trade: dict):
        """Log trade details

        Args:
            trade (dict): Trade information
        """
        try:
            self.logger.info(
                f"Trade - ID: {trade.get('trade_id')} "
                f"P/L: {trade.get('profit_loss', 0):.2f}",
                extra={'trade': trade}
            )
        except Exception as e:
            self.logger.error(f"Error logging trade: {str(e)}")

    def log_signal(self, signal: dict):
        """Log trading signal

        Args:
            signal (dict): Signal information
        """
        try:
            self.logger.info(
                f"Signal - {signal.get('symbol')} {signal.get('type')}",
                extra={'signal': signal}
            )
        except Exception as e:
            self.logger.error(f"Error logging signal: {str(e)}")

    def log_performance(self, metrics: dict):
        """Log performance metrics

        Args:
            metrics (dict): Performance metrics
        """
        try:
            self.logger.info(
                "Performance update",
                extra={'metrics': metrics}
            )
        except Exception as e:
            self.logger.error(f"Error logging metrics: {str(e)}")