#!/usr/bin/env python3
"""
Asset Information Retriever for Deriv API

This script retrieves and displays detailed information about available trading assets from Deriv API.
It organizes the data in a well-formatted table to help users select suitable assets for their trading strategies.

Usage:
    python -m src.utils.open_assets

Output:
    A formatted table displaying key asset information including symbol, name, market, market_display_name,
    pip size, and trading status.
"""

import asyncio
import logging
import pandas as pd
from typing import Dict, List, Optional, Any
from tabulate import tabulate
import sys
import os
from datetime import datetime, timezone
import math
import numpy as np

# Ensure the deriv_api module is installed
try:
    from deriv_api import DerivAPI
except ImportError:
    print("Error: deriv_api package not installed. Please install it using 'pip install deriv-api'.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AssetInformationRetriever:
    """Class to retrieve, process and display asset information from Deriv API."""

    def __init__(self, app_id: int = 1089):
        """
        Initialize the AssetInformationRetriever.

        Args:
            app_id (int): The Deriv API app ID. Defaults to 1089 (commonly used for testing).
        """
        self.app_id = app_id
        self.api = None

    async def connect(self) -> bool:
        """
        Connect to the Deriv API.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            logger.info("Connecting to Deriv API...")
            self.api = DerivAPI(app_id=self.app_id)

            # Simple ping to test connection
            ping_response = await self.api.ping({'ping': 1})
            if ping_response and 'ping' in ping_response:
                logger.info(f"Connected to Deriv API. Ping response: {ping_response['ping']}")
                return True
            else:
                logger.error("Failed to ping Deriv API")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Deriv API: {str(e)}")
            return False

    async def get_assets(self, detail_level: str = "full") -> List[Dict]:
        """
        Retrieve asset information from Deriv API.

        Args:
            detail_level (str): Level of detail for asset information. Options: "brief" or "full".
                                Defaults to "full" for maximum information.

        Returns:
            List[Dict]: List of asset dictionaries, or empty list if retrieval failed.
        """
        try:
            logger.info(f"Retrieving {detail_level} asset information...")

            # Request active symbols with specified detail level
            response = await self.api.active_symbols({"active_symbols": detail_level})

            # Check for errors in the response
            if response and 'error' in response:
                logger.error(f"API Error: {response['error'].get('message', 'Unknown error')}")
                return []

            # Extract the list of symbols from the response
            symbols = response.get("active_symbols", [])
            logger.info(f"Retrieved {len(symbols)} assets")
            return symbols

        except Exception as e:
            logger.error(f"Error getting assets: {str(e)}")
            return []

    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Get additional market data for a specific symbol.

        Args:
            symbol (str): The trading symbol to get data for.

        Returns:
            Optional[Dict]: Market data dictionary or None if retrieval failed.
        """
        try:
            # Get market data from the ticks endpoint
            ticks_response = await self.api.ticks({'ticks': symbol})

            if ticks_response and 'error' not in ticks_response and 'tick' in ticks_response:
                return ticks_response['tick']
            return None
        except Exception as e:
            logger.debug(f"Error getting market data for {symbol}: {str(e)}")
            return None

    def calculate_volatility(self, historical_prices: List[float]) -> tuple[float, float]:
        """
        Calculate price volatility from a list of historical prices.

        Args:
            historical_prices (List[float]): List of historical prices.

        Returns:
            tuple[float, float]: Calculated standard deviation volatility and (a simple approximation of) 1-minute volatility as percentages.
        """
        if not historical_prices or len(historical_prices) < 2:
            return 0.0, 0.0

        import numpy as np
        # Calculate returns
        returns = np.diff(historical_prices) / historical_prices[:-1]
        # Calculate standard deviation volatility (standard deviation of returns)
        std_volatility = np.std(returns) * 100  # Convert to percentage

        #Simple Approximation of 1-minute volatility (assuming evenly spaced data)
        minute_volatility = std_volatility * np.sqrt(1/len(historical_prices))


        return std_volatility, minute_volatility


    async def get_historical_prices(self, symbol: str, count: int = 100) -> List[float]:
        """
        Get historical prices for a symbol.

        Args:
            symbol (str): The trading symbol to get history for.
            count (int): Number of historical data points to retrieve.

        Returns:
            List[float]: List of historical prices.
        """
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())

            # Request historical ticks
            history_response = await self.api.ticks_history({
                'ticks_history': symbol,
                'end': current_time,
                'count': count,
                'style': 'ticks'
            })

            if history_response and 'error' not in history_response and 'history' in history_response:
                # Extract prices from history
                prices = [float(tick['quote']) for tick in history_response['history']['prices']]
                return prices
            return []
        except Exception as e:
            logger.debug(f"Error getting historical prices for {symbol}: {str(e)}")
            return []

    def enrich_asset_data(self, assets: List[Dict], additional_data: Dict[str, Any]) -> List[Dict]:
        """
        Enrich asset data with additional information.

        Args:
            assets (List[Dict]): List of asset dictionaries.
            additional_data (Dict[str, Any]): Additional data keyed by symbol.

        Returns:
            List[Dict]: Enriched asset data.
        """
        enriched_assets = []

        for asset in assets:
            symbol = asset.get('symbol')
            if symbol in additional_data:
                # Add additional data to the asset dictionary
                asset.update(additional_data[symbol])
            enriched_assets.append(asset)

        return enriched_assets

    def format_asset_table(self, assets: List[Dict]) -> pd.DataFrame:
        """
        Format asset information into a pandas DataFrame.

        Args:
            assets (List[Dict]): List of asset dictionaries.

        Returns:
            pd.DataFrame: DataFrame containing formatted asset information.
        """
        # Define columns to extract
        columns = [
            'symbol', 'display_name', 'market', 'market_display_name',
            'pip', 'submarket_display_name', 'exchange_is_open',
            'volatility', 'last_price', 'price_change', 'minute_volatility'
        ]

        # Create a DataFrame from the assets
        df = pd.DataFrame([
            {col: asset.get(col, '') for col in columns}
            for asset in assets
        ])

        # Format boolean columns
        if 'exchange_is_open' in df.columns:
            df['exchange_is_open'] = df['exchange_is_open'].apply(
                lambda x: '✅ Open' if x else '❌ Closed')
            df.rename(columns={'exchange_is_open': 'trading_status'}, inplace=True)

        # Format numeric columns
        if 'volatility' in df.columns:
            df['volatility'] = df['volatility'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")
        if 'minute_volatility' in df.columns:
            df['minute_volatility'] = df['minute_volatility'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")

        if 'price_change' in df.columns:
            df['price_change'] = df['price_change'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")

        # Set better column ordering
        preferred_order = [
            'symbol', 'display_name', 'market_display_name', 
            'submarket_display_name', 'last_price', 'price_change',
            'volatility', 'minute_volatility', 'pip', 'trading_status'
        ]

        # Filter to only include columns that actually exist in the DataFrame
        final_order = [col for col in preferred_order if col in df.columns]

        return df[final_order]

    async def cleanup(self):
        """Disconnect from the API and clean up resources."""
        if self.api:
            try:
                await self.api.disconnect()
                logger.info("Disconnected from Deriv API")
            except Exception as e:
                logger.error(f"Error during API disconnect: {str(e)}")

async def main():
    """Main entry point for the script."""
    try:
        from datetime import datetime
        start_time = datetime.now()
        logger.info(f"Starting asset information retrieval at {start_time}")

        # Create and connect to the asset information retriever
        retriever = AssetInformationRetriever()
        connected = await retriever.connect()

        if not connected:
            logger.error("Failed to connect to API. Exiting.")
            return

        # Get the list of available assets
        assets = await retriever.get_assets()

        if not assets:
            logger.error("No assets retrieved. Exiting.")
            return

        logger.info(f"Retrieved {len(assets)} assets. Starting market data collection...")    
        # Track additional data for enrichment
        additional_data = {}

        # Focus on synthetic indices which are typically better for 1-minute trading
        synthetic_assets = [asset for asset in assets if asset.get('market') == 'synthetic_index']
        other_assets = [asset for asset in assets if asset.get('market') != 'synthetic_index']

        # Process synthetic assets first (they're generally better for 1-min trading)
        processed_count = 0
        max_to_process = 20  # Increased limit for more comprehensive analysis

        assets_to_process = synthetic_assets + other_assets

        for asset in assets_to_process:
            if processed_count >= max_to_process:
                break

            symbol = asset.get('symbol')
            logger.info(f"Processing asset {processed_count+1}/{max_to_process}: {symbol}")

            # Get more historical data points for better volatility calculation
            historical_prices = await retriever.get_historical_prices(symbol, count=300)
            market_data = await retriever.get_market_data(symbol)

            if historical_prices and len(historical_prices) > 10:
                # Calculate both standard and 1-minute volatility
                std_volatility, minute_volatility = retriever.calculate_volatility(historical_prices)

                last_price = market_data.get('quote') if market_data else None
                price_change = market_data.get('change') if market_data else None

                # Add to additional data
                additional_data[symbol] = {
                    'volatility': std_volatility,
                    'minute_volatility': minute_volatility,
                    'last_price': last_price,
                    'price_change': price_change,
                }
                processed_count += 1
            else:
                logger.warning(f"Insufficient historical data for {symbol}: {len(historical_prices) if historical_prices else 0} points")

        logger.info(f"Processed {processed_count} assets. Enriching data...")

        # Enrich asset data
        enriched_assets = retriever.enrich_asset_data(assets, additional_data)

        # Format asset information into a table
        df = retriever.format_asset_table(enriched_assets)

        #Added this section to fix the KeyError
        if 'volatility' in additional_data.get(list(additional_data.keys())[0],{}):
            df['std_volatility'] = df['symbol'].map(lambda x: additional_data.get(x, {}).get('volatility', np.nan))
            df['minute_volatility'] = df['symbol'].map(lambda x: additional_data.get(x, {}).get('minute_volatility', np.nan))
            # Format numeric columns after adding volatility data
            df['std_volatility'] = df['std_volatility'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")
            df['minute_volatility'] = df['minute_volatility'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")


        # Sort by 1-minute volatility (descending) to highlight best assets for 1-min trading
        if 'minute_volatility' in df.columns:
            # Convert percentage strings to numeric for sorting
            df['minute_volatility_numeric'] = df['minute_volatility'].apply(
                lambda x: float(x.strip('%')) if x != 'N/A' else 0)
            df = df.sort_values('minute_volatility_numeric', ascending=False)
            df = df.drop('minute_volatility_numeric', axis=1)
        else:
            # Fall back to sorting by symbol
            df = df.sort_values('symbol')

        # Print the formatted table
        print("\n1-MINUTE TRADING ASSET ANALYSIS\n")
        print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=False))

        # Show a summary of best assets for 1-minute trading
        # (This section is a placeholder and needs refinement based on specific criteria)

        end_time = datetime.now()
        logger.info(f"Asset information retrieval completed in {(end_time - start_time).total_seconds():.2f} seconds")

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

    finally:
        # Ensure we always disconnect
        if 'retriever' in locals() and retriever:
            await retriever.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from deriv_api import DerivAPI

logger = logging.getLogger(__name__)

class AssetInformationRetriever:
    """Class to retrieve, process and display asset information from Deriv API."""

    def __init__(self, app_id: int = 1089):
        """
        Initialize the AssetInformationRetriever.

        Args:
            app_id (int): The Deriv API app ID. Defaults to 1089 (commonly used for testing).
        """
        self.app_id = app_id
        self.api = None

    async def connect(self) -> bool:
        """
        Connect to the Deriv API.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            logger.info("Connecting to Deriv API...")
            self.api = DerivAPI(app_id=self.app_id)

            # Simple ping to test connection
            ping_response = await self.api.ping({'ping': 1})
            if ping_response and 'ping' in ping_response:
                logger.info(f"Connected to Deriv API. Ping response: {ping_response['ping']}")
                return True
            else:
                logger.error("Failed to ping Deriv API")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Deriv API: {str(e)}")
            return False

    async def get_assets(self, detail_level: str = "full") -> List[Dict]:
        """
        Retrieve asset information from Deriv API.

        Args:
            detail_level (str): Level of detail for asset information. Options: "brief" or "full".
                                Defaults to "full" for maximum information.

        Returns:
            List[Dict]: List of asset dictionaries, or empty list if retrieval failed.
        """
        try:
            logger.info(f"Retrieving {detail_level} asset information...")

            # Request active symbols with specified detail level
            response = await self.api.active_symbols({"active_symbols": detail_level})

            # Check for errors in the response
            if response and 'error' in response:
                logger.error(f"API Error: {response['error'].get('message', 'Unknown error')}")
                return []

            # Extract the list of symbols from the response
            symbols = response.get("active_symbols", [])
            logger.info(f"Retrieved {len(symbols)} assets")
            return symbols

        except Exception as e:
            logger.error(f"Error getting assets: {str(e)}")
            return []

    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Get additional market data for a specific symbol.

        Args:
            symbol (str): The trading symbol to get data for.

        Returns:
            Optional[Dict]: Market data dictionary or None if retrieval failed.
        """
        try:
            # Get market data from the ticks endpoint
            ticks_response = await self.api.ticks({'ticks': symbol})

            if ticks_response and 'error' not in ticks_response and 'tick' in ticks_response:
                return ticks_response['tick']
            return None
        except Exception as e:
            logger.debug(f"Error getting market data for {symbol}: {str(e)}")
            return None

    def calculate_volatility(self, historical_prices: List[float]) -> tuple[float, float]:
        """
        Calculate price volatility from a list of historical prices.

        Args:
            historical_prices (List[float]): List of historical prices.

        Returns:
            tuple[float, float]: Calculated standard deviation volatility and (a simple approximation of) 1-minute volatility as percentages.
        """
        if not historical_prices or len(historical_prices) < 2:
            return 0.0, 0.0

        import numpy as np
        # Calculate returns
        returns = np.diff(historical_prices) / historical_prices[:-1]
        # Calculate standard deviation volatility (standard deviation of returns)
        std_volatility = np.std(returns) * 100  # Convert to percentage

        #Simple Approximation of 1-minute volatility (assuming evenly spaced data)
        minute_volatility = std_volatility * np.sqrt(1/len(historical_prices))


        return std_volatility, minute_volatility

    async def get_historical_prices(self, symbol: str, count: int = 100) -> List[float]:
        """
        Get historical prices for a symbol.

        Args:
            symbol (str): The trading symbol to get history for.
            count (int): Number of historical data points to retrieve.

        Returns:
            List[float]: List of historical prices.
        """
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())

            # Request historical ticks
            history_response = await self.api.ticks_history({
                'ticks_history': symbol,
                'end': current_time,
                'count': count,
                'style': 'ticks'
            })

            if history_response and 'error' not in history_response and 'history' in history_response:
                # Extract prices from history
                prices = [float(tick['quote']) for tick in history_response['history']['prices']]
                return prices
            return []
        except Exception as e:
            logger.debug(f"Error getting historical prices for {symbol}: {str(e)}")
            return []

    def enrich_asset_data(self, assets: List[Dict], additional_data: Dict[str, Any]) -> List[Dict]:
        """
        Enrich asset data with additional information.

        Args:
            assets (List[Dict]): List of asset dictionaries.
            additional_data (Dict[str, Any]): Additional data keyed by symbol.

        Returns:
            List[Dict]: Enriched asset data.
        """
        enriched_assets = []

        for asset in assets:
            symbol = asset.get('symbol')
            if symbol in additional_data:
                # Add additional data to the asset dictionary
                asset.update(additional_data[symbol])
            enriched_assets.append(asset)

        return enriched_assets

    def format_asset_table(self, assets: List[Dict]) -> pd.DataFrame:
        """
        Format asset information into a pandas DataFrame.

        Args:
            assets (List[Dict]): List of asset dictionaries.

        Returns:
            pd.DataFrame: DataFrame containing formatted asset information.
        """
        # Define columns to extract
        columns = [
            'symbol', 'display_name', 'market', 'market_display_name',
            'pip', 'submarket_display_name', 'exchange_is_open',
            'volatility', 'last_price', 'price_change', 'minute_volatility'
        ]

        # Create a DataFrame from the assets
        df = pd.DataFrame([
            {col: asset.get(col, '') for col in columns}
            for asset in assets
        ])

        # Format boolean columns
        if 'exchange_is_open' in df.columns:
            df['exchange_is_open'] = df['exchange_is_open'].apply(
                lambda x: '✅ Open' if x else '❌ Closed')
            df.rename(columns={'exchange_is_open': 'trading_status'}, inplace=True)

        # Format numeric columns
        if 'volatility' in df.columns:
            df['volatility'] = df['volatility'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")
        if 'minute_volatility' in df.columns:
            df['minute_volatility'] = df['minute_volatility'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")

        if 'price_change' in df.columns:
            df['price_change'] = df['price_change'].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) and isinstance(x, (int, float)) else "N/A")

        # Set better column ordering
        preferred_order = [
            'symbol', 'display_name', 'market_display_name', 
            'submarket_display_name', 'last_price', 'price_change',
            'volatility', 'minute_volatility', 'pip', 'trading_status'
        ]

        # Filter to only include columns that actually exist in the DataFrame
        final_order = [col for col in preferred_order if col in df.columns]

        return df[final_order]

    async def cleanup(self):
        """Disconnect from the API and clean up resources."""
        if self.api:
            try:
                await self.api.disconnect()
                logger.info("Disconnected from Deriv API")
            except Exception as e:
                logger.error(f"Error during API disconnect: {str(e)}")