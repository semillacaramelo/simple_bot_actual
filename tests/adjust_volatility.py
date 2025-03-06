
#!/usr/bin/env python
"""
Utility to adjust volatility thresholds for 1-minute trading.
This helps determine the optimal volatility settings for short-term contracts.
"""

import sys
import os
import pandas as pd
import argparse
import asyncio
import logging
from tabulate import tabulate

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.open_assets import AssetInformationRetriever
from src.risk.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def analyze_volatility(threshold=0.005, asset_limit=20):
    """
    Analyze assets for their volatility and suitability for 1-minute trading.
    
    Args:
        threshold (float): Minimum volatility threshold for 1-minute trading
        asset_limit (int): Maximum number of assets to analyze
    """
    try:
        retriever = AssetInformationRetriever()
        connected = await retriever.connect()
        
        if not connected:
            logger.error("Failed to connect to API. Exiting.")
            return
            
        # Get synthetic indices which are typically good for 1-minute trading
        assets = await retriever.get_assets()
        synthetic_assets = [a for a in assets if a.get('market') == 'synthetic_index']
        other_assets = [a for a in assets if a.get('market') != 'synthetic_index']
        
        # Prioritize synthetic assets
        assets_to_process = synthetic_assets + other_assets
        
        # Collect volatility data
        volatility_data = []
        processed = 0
        
        for asset in assets_to_process:
            if processed >= asset_limit:
                break
                
            symbol = asset.get('symbol')
            logger.info(f"Analyzing {symbol}...")
            
            historical_prices = await retriever.get_historical_prices(symbol, count=300)
            
            if historical_prices and len(historical_prices) > 10:
                std_vol, min_vol = retriever.calculate_volatility(historical_prices)
                
                volatility_data.append({
                    'symbol': symbol,
                    'name': asset.get('display_name'),
                    'std_volatility': std_vol * 100,  # Convert to percentage
                    'minute_volatility': min_vol * 100,  # Convert to percentage
                    'suitable_for_1min': min_vol >= threshold,
                    'market': asset.get('market_display_name')
                })
                processed += 1
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(volatility_data)
        
        # Format for display
        df['std_volatility'] = df['std_volatility'].apply(lambda x: f"{x:.3f}%")
        df['minute_volatility'] = df['minute_volatility'].apply(lambda x: f"{x:.3f}%")
        df['suitable_for_1min'] = df['suitable_for_1min'].apply(
            lambda x: '✅ Yes' if x else '❌ No')
        
        # Sort by minute volatility (descending)
        df = df.sort_values('minute_volatility', ascending=False)
        
        # Print results
        print(f"\nASSET VOLATILITY ANALYSIS (threshold: {threshold:.3f}%)\n")
        print(tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=False))
        
        # Summarize findings
        suitable_count = df['suitable_for_1min'].value_counts().get('✅ Yes', 0)
        print(f"\nFound {suitable_count} assets suitable for 1-minute trading.")
        
        if suitable_count > 0:
            print("\nRECOMMENDED SETTINGS FOR CONFIG:")
            print(f"config.update_risk_config(\n    min_volatility={threshold},\n    max_volatility={threshold*4}\n)")
        else:
            print("\nTry lowering the threshold or checking during more active market hours.")
            print(f"Suggested threshold: {df['minute_volatility'].max()/2:.3f}%")
        
    except Exception as e:
        logger.error(f"Error in analyze_volatility: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if 'retriever' in locals() and retriever:
            await retriever.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze volatility for 1-minute trading")
    parser.add_argument("--threshold", type=float, default=0.005, 
                        help="Minimum volatility threshold (as decimal, e.g., 0.005 for 0.5%)")
    parser.add_argument("--limit", type=int, default=20, 
                        help="Maximum number of assets to analyze")
    
    args = parser.parse_args()
    
    print(f"Analyzing assets with threshold {args.threshold:.3f}% and limit {args.limit}")
    asyncio.run(analyze_volatility(args.threshold, args.limit))
