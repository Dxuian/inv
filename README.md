# Mutual Fund Analysis Tool

A Python-based tool for analyzing mutual funds using the mftool library. This project provides functionality for:

- Matching mutual fund names with their corresponding scheme codes
- Calculating various fund metrics (returns, volatility, etc.)
- Analyzing historical NAV data
- Generating comprehensive fund reports

## Features

- Multiple fund name matching methods (regex, similarity, word matching)
- Risk metrics calculation (volatility, Sharpe ratio, max drawdown)
- Statistical analysis (skewness, kurtosis)
- Historical NAV analysis

## Files

- `a.py`: Main script for fund matching and analysis
- `mftool_test.py`: Testing script for mftool functionality
- `a.csv`: Input file with fund names
- `analysis.ipynb`: Jupyter notebook for data analysis

## Usage

1. Place your fund names in `a.csv`
2. Run `python a.py` to process the funds
3. Results will be saved in `fund_info_results.csv`
