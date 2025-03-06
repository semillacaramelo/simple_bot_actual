"""
Context: Deriv.com Trading Bot Project

You are assisting with a Python trading bot project that uses the Deriv.com API. The bot implements a triple moving average crossover strategy with RSI filtering and proper risk management. The project has the following key characteristics:

PROJECT STRUCTURE:
- Uses python-deriv-api SDK for API connectivity
- Implements WebSocket-based real-time data streaming
- Follows a modular architecture with separate components for:
  * API connectivity (deriv_connector.py)
  * Data handling (data_fetcher.py)
  * Strategy execution (moving_average.py, strategy_executor.py)
  * Risk management (risk_manager.py)
  * Performance monitoring (performance.py)
  * Logging (logger.py)

CORE FUNCTIONALITY:
1. Authentication: Uses OAuth 2.0 with API tokens
2. Market Data: Real-time WebSocket streams for price data
3. Trading Strategy: Triple MA crossover with RSI filter
4. Risk Management: Position sizing and drawdown protection
5. Performance Tracking: Trade analysis and reporting

TECHNICAL CONSTRAINTS:
- Must maintain persistent WebSocket connections
- Follows Deriv API rate limits and best practices
- Handles both demo and real account trading
- Uses proper error handling as per Deriv API docs

IMPORTANT CONSIDERATIONS:
1. Any API modifications must follow Deriv's WebSocket API specifications
2. Risk parameters must be respected (MAX_RISK, MAX_DAILY_LOSS, etc.)
3. All trades must go through the risk manager validation
4. Logging should maintain the established format
5. New features should integrate with the existing monitoring system

For detailed API references, consult docs/references.md which contains links to all relevant Deriv API documentation.
"""
