from mftool import Mftool
import pandas as pd
from datetime import datetime, timedelta
import json
import numpy as np

mt = Mftool()

# Get a sample scheme code (Kotak Credit Risk Fund)
scheme_code = '119741'

# Get all available data
details = mt.get_scheme_details(scheme_code)
quote = mt.get_scheme_quote(scheme_code)
historical_nav = mt.get_scheme_historical_nav(scheme_code, as_Dataframe=True)

# Get performance data
try:
    # Get category performance for comparison
    if "Debt Scheme" in details.get('scheme_category', ''):
        category_performance = mt.get_open_ended_debt_scheme_performance()
    elif "Equity" in details.get('scheme_category', ''):
        category_performance = mt.get_open_ended_equity_scheme_performance()
    elif "Hybrid" in details.get('scheme_category', ''):
        category_performance = mt.get_open_ended_hybrid_scheme_performance()
    else:
        category_performance = mt.get_open_ended_other_scheme_performance()
except:
    category_performance = None

# Calculate metrics from historical data
if isinstance(historical_nav, pd.DataFrame) and not historical_nav.empty:
    nav_data = historical_nav.copy()
    nav_data['nav'] = pd.to_numeric(nav_data['nav'], errors='coerce')
    
    # Calculate returns and risk metrics
    latest_nav = nav_data['nav'].iloc[0]
    year_ago_nav = nav_data['nav'][nav_data.index >= (datetime.now() - timedelta(days=365)).strftime('%d-%m-%Y')].iloc[-1]
    three_year_nav = nav_data['nav'][nav_data.index >= (datetime.now() - timedelta(days=3*365)).strftime('%d-%m-%Y')].iloc[-1]
    
    # Daily returns
    nav_data['daily_returns'] = nav_data['nav'].pct_change()
    
    # Risk metrics
    risk_free_rate = 0.04  # Assuming 4% risk-free rate
    
    metrics = {
        # Basic Info
        'scheme_code': scheme_code,
        'scheme_name': details.get('scheme_name', 'N/A'),
        'fund_house': details.get('fund_house', 'N/A'),
        'scheme_type': details.get('scheme_type', 'N/A'),
        'scheme_category': details.get('scheme_category', 'N/A'),
        
        # NAV Info
        'start_date': details.get('scheme_start_date', {}).get('date', 'N/A'),
        'start_nav': details.get('scheme_start_date', {}).get('nav', 'N/A'),
        'current_nav': quote.get('nav', 'N/A') if quote else 'N/A',
        'last_updated': quote.get('last_updated', 'N/A') if quote else 'N/A',
        
        # Returns
        '1y_return': ((latest_nav / year_ago_nav) - 1) * 100 if year_ago_nav else 'N/A',
        '3y_return': (((latest_nav / three_year_nav) ** (1/3)) - 1) * 100 if three_year_nav else 'N/A',
        
        # Risk Metrics
        'volatility': nav_data['daily_returns'].std() * np.sqrt(252) * 100,  # Annualized volatility
        'sharpe': ((nav_data['daily_returns'].mean() * 252 - risk_free_rate) / 
                  (nav_data['daily_returns'].std() * np.sqrt(252))) if nav_data['daily_returns'].std() > 0 else 'N/A',
        'max_drawdown': ((nav_data['nav'].cummax() - nav_data['nav']) / nav_data['nav'].cummax()).max() * 100,
        
        # Additional Stats
        'skewness': nav_data['daily_returns'].skew(),
        'kurtosis': nav_data['daily_returns'].kurtosis(),
        'alpha': 'Calculated from benchmark returns',  # Placeholder
        'beta': 'Calculated from benchmark returns',   # Placeholder
        'r2': 'Calculated from benchmark returns',     # Placeholder
        'information_ratio': 'Calculated from benchmark returns'  # Placeholder
    }
    
    # Add category performance if available
    if category_performance:
        for category in category_performance:
            for fund in category_performance[category]:
                if fund.get('scheme_name') == details.get('scheme_name'):
                    metrics.update({
                        '1y_return_regular': fund.get('1-Year Return(%)- Regular', 'N/A'),
                        '1y_return_direct': fund.get('1-Year Return(%)- Direct', 'N/A'),
                        '3y_return_regular': fund.get('3-Year Return(%)- Regular', 'N/A'),
                        '3y_return_direct': fund.get('3-Year Return(%)- Direct', 'N/A'),
                        '5y_return_regular': fund.get('5-Year Return(%)- Regular', 'N/A'),
                        '5y_return_direct': fund.get('5-Year Return(%)- Direct', 'N/A'),
                        'benchmark': fund.get('benchmark', 'N/A')
                    })
else:
    # Basic metrics if historical data is not available
    metrics = {
        'scheme_code': scheme_code,
        'scheme_name': details.get('scheme_name', 'N/A'),
        'fund_house': details.get('fund_house', 'N/A'),
        'scheme_type': details.get('scheme_type', 'N/A'),
        'scheme_category': details.get('scheme_category', 'N/A'),
        'current_nav': quote.get('nav', 'N/A') if quote else 'N/A',
        'last_updated': quote.get('last_updated', 'N/A') if quote else 'N/A'
    }

# Convert to pandas DataFrame for better display
df = pd.DataFrame([metrics])

# Display all columns
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print("\nComplete Fund Analysis:")
print(df)

# Display historical NAV summary if available
if isinstance(historical_nav, pd.DataFrame) and not historical_nav.empty:
    print("\nHistorical NAV Summary:")
    print(nav_data['nav'].describe())
