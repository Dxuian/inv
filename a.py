import pandas as pd
from mftool import Mftool
import re
from datetime import datetime, timedelta
import numpy as np
import difflib
import difflib
import logging  
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)    
def create_name_hash(words, original_text):
    # First detect acronyms from original text using capital letters
    acronyms = re.findall(r'\b[A-Z]{2,}\b', original_text)
    
    # Separate words by type
    long_words = []
    short_words = []
    for w in words:
        # Check if the word is in our acronyms list (case-insensitive)
        if any(w.upper() == acr for acr in acronyms):
            # It's an acronym, treat it specially
            short_words.append(w.upper())
        elif len(w) > 1:
            long_words.append(w)
        else:
            short_words.append(w)
    
    # Get hash from first letters of long words before sorting
    full_word_hash = ''.join(word[0] for word in long_words)
    
    # Now sort the words for consistent comparison
    full_words = sorted(long_words)
    abbrev_words = sorted(short_words)
    # Give extra weight to acronyms by adding them to both hashes
    abbrev_hash = ''.join(abbrev_words)
    
    return (full_word_hash + abbrev_hash, full_words, abbrev_words, acronyms)

def another_method(funds_df, schemes_df, matches):
    """
    Hash-like comparison method that categorizes words and creates comparable hashes
    with special handling for acronyms
    """
    # Process each fund name
    for fund_name in funds_df['name'].unique():
        # Clean but preserve case for acronym detection
        clean_fund = fund_name
        for char in ['+', '_', '-', '(', ')', '/', '&', '.', ',']:
            clean_fund = clean_fund.replace(char, ' ')
        
        # Get words (lowercase for general comparison)
        fund_words = [word.lower() for word in clean_fund.split() if word]
        
        # Get hash for fund name (pass original text for acronym detection)
        fund_hash, fund_full, fund_abbrev, fund_acronyms = create_name_hash(fund_words, clean_fund)
        
        for idx, row in schemes_df.iterrows():
            # Clean scheme name but preserve case
            clean_scheme = row['scheme_name']
            for char in ['+', '_', '-', '(', ')', '/', '&', '.', ',']:
                clean_scheme = clean_scheme.replace(char, ' ')
            
            # Get words (lowercase for general comparison)
            scheme_words = [word.lower() for word in clean_scheme.split() if word]
            
            # Get hash for scheme name
            scheme_hash, scheme_full, scheme_abbrev, scheme_acronyms = create_name_hash(scheme_words, clean_scheme)
            
            # Compare components
            hash_match = fund_hash == scheme_hash
            full_word_match = len(set(fund_full).intersection(scheme_full))
            abbrev_match = len(set(fund_abbrev).intersection(scheme_abbrev))
            acronym_match = len(set(fund_acronyms).intersection(scheme_acronyms))
            
            # Calculate match score with extra weight for acronym matches
            total_words = len(fund_full) + len(fund_abbrev)
            if total_words > 0:
                # Give 1.5x weight to acronym matches
                match_score = ((full_word_match + abbrev_match + (acronym_match * 1.5)) / total_words * 100)
            else:
                match_score = 0
            
            if hash_match or match_score >= 80:
                matches.append({
                    'original_name': fund_name,
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'match_type': 'hash_match' if hash_match else 'component_match',
                    'match_score': 100 if hash_match else round(match_score, 2),
                    'fund_hash': fund_hash,
                    'scheme_hash': scheme_hash,
                    'matched_full': list(set(fund_full).intersection(scheme_full)),
                    'matched_abbrev': list(set(fund_abbrev).intersection(scheme_abbrev)),
                    'matched_acronyms': list(set(fund_acronyms).intersection(scheme_acronyms))
                })
    
    return matches 
def clean_fund_name(name):
    # Remove special characters except & and convert to lowercase
    name = re.sub(r'[^\w\s&]', ' ', name.lower())
    return ' '.join(name.split())

def build_regex_pattern(fund_name):
    # Clean and split the fund name into words
    words = clean_fund_name(fund_name).split()
    
    # Create a pattern that looks for any word as a whole word or part of a word
    # At least one word must match completely
    patterns = []
    for word in words:
        if len(word) > 2:  # Only use words longer than 2 characters
            patterns.append(f"(?=.*\\b{word})")
    
    # Combine all patterns
    return ''.join(patterns) if patterns else None

def find_matching_schemes(fund_name, schemes_df):
    pattern = build_regex_pattern(fund_name)
    matches = []
    start_time = datetime.now() 
    # Method 1: Regex matching with basic cleaning
    if pattern:
        fund_words = set(clean_fund_name(fund_name).split())
        for idx, row in schemes_df.iterrows():
            clean_scheme_name = clean_fund_name(row['scheme_name'])
            if re.search(pattern, clean_scheme_name, re.IGNORECASE):
                matches.append({
                    'original_name': fund_name,
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'match_type': 'regex',
                    'match_score': 1  # Base score for regex match
                })
    
    # Method 2: Word similarity matching with basic cleaning (80% threshold)
    fund_words = set(clean_fund_name(fund_name).split())
    for idx, row in schemes_df.iterrows():
        clean_scheme_name = clean_fund_name(row['scheme_name'])
        scheme_words = set(clean_scheme_name.split())
        
        common_words = len(fund_words.intersection(scheme_words))
        similarity_score = (common_words / len(fund_words)) * 100
        
        if similarity_score >= 80:
            matches.append({
                'original_name': fund_name,
                'scheme_code': row['scheme_code'],
                'scheme_name': row['scheme_name'],
                'match_type': 'basic_similarity',
                'match_score': round(similarity_score, 2)
            })
    
    # Method 3: Remove small words (<=2 chars) then check similarity
    fund_words = set(word for word in clean_fund_name(fund_name).split() if len(word) > 2)
    for idx, row in schemes_df.iterrows():
        clean_scheme_name = clean_fund_name(row['scheme_name'])
        scheme_words = set(word for word in clean_scheme_name.split() if len(word) > 2)
        
        if fund_words:  # Only if we have words left after filtering
            common_words = len(fund_words.intersection(scheme_words))
            similarity_score = (common_words / len(fund_words)) * 100
            
            if similarity_score >= 80:
                matches.append({
                    'original_name': fund_name,
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'match_type': 'no_small_words',
                    'match_score': round(similarity_score, 2)
                })
    
    # Method 4: Remove all whitespace then check similarity
    fund_text = ''.join(clean_fund_name(fund_name).split())
    for idx, row in schemes_df.iterrows():
        scheme_text = ''.join(clean_fund_name(row['scheme_name']).split())
        
        # Use sequence matcher for text without spaces
        similarity_score = difflib.SequenceMatcher(None, fund_text, scheme_text).ratio() * 100
        
        if similarity_score >= 80:
            matches.append({
                'original_name': fund_name,
                'scheme_code': row['scheme_code'],
                'scheme_name': row['scheme_name'],
                'match_type': 'no_spaces',
                'match_score': round(similarity_score, 2)
            })
    
    # Method 5: Remove all symbols and check similarity
    fund_text = re.sub(r'[^a-z0-9]', '', clean_fund_name(fund_name))
    for idx, row in schemes_df.iterrows():
        scheme_text = re.sub(r'[^a-z0-9]', '', clean_fund_name(row['scheme_name']))
        
        # Use sequence matcher for alphanumeric only text
        similarity_score = difflib.SequenceMatcher(None, fund_text, scheme_text).ratio() * 100
        
        if similarity_score >= 80:
            matches.append({
                'original_name': fund_name,
                'scheme_code': row['scheme_code'],
                'scheme_name': row['scheme_name'],
                'match_type': 'alphanumeric',
                'match_score': round(similarity_score, 2)
            })
    
    # Method 6: Direct string comparison with simple cleaning
    # Clean and split fund name
    fund_words = fund_name.lower()
    for char in ['+', '_', '-', '(', ')', '/', '&', '.', ',']:
        fund_words = fund_words.replace(char, ' ')
    fund_words = [word for word in fund_words.split() if word]

    # Method 7: Hash-like comparison
    for idx, row in schemes_df.iterrows():
        # Clean and split scheme name the same way
        scheme_words = row['scheme_name'].lower()
        for char in ['+', '_', '-', '(', ')', '/', '&', '.', ',']:
            scheme_words = scheme_words.replace(char, ' ')
        scheme_words = [word for word in scheme_words.split() if word]
        
        # Count matching words and keep track of which words matched
        matched_count = 0
        matched_words = []
        for fund_word in fund_words:
            if fund_word in scheme_words:
                matched_count += 1
                matched_words.append(fund_word)
        
        # Calculate word match score as percentage
        match_score = (matched_count / len(fund_words)) * 100
        
        if match_score >= 50:  # At least 80% of words should match exactly
            matches.append({
                'original_name': fund_name,
                'scheme_code': row['scheme_code'],
                'scheme_name': row['scheme_name'],
                'match_type': 'exact_word_match',
                'match_score': round(match_score, 2),
                'matched_words': matched_words,  # Add the list of matched words
                'total_words': len(fund_words)   # Add total number of words for reference
            })
    another_method(funds_df, schemes_df, matches)
    # Convert to DataFrame and sort by match score
    matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
    if not matches_df.empty:
        matches_df = matches_df.sort_values('match_score', ascending=False)
    logger.info(f'time taken to find matches: {datetime.now() - start_time}')
    return matches_df

def save_as_csv_after_using_mftool_test_py_file():
    """
    Function to enhance a.csv with additional metrics and save incrementally to ll.csv
    Supports resuming from last processed fund
    """
    try:
        # Initialize mftool
        mf = Mftool()
        
        # Get all available schemes
        schemes = mf.get_scheme_codes()
        schemes_df = pd.DataFrame([(code, name) for code, name in schemes.items()],
                                columns=['scheme_code', 'scheme_name'])
        
        # Read original data
        original_df = pd.read_csv('a.csv')
        total_funds = len(original_df)
        print(f"Total funds to process: {total_funds}")
        
        # Check for existing progress
        try:
            existing_df = pd.read_csv('ll.csv')
            processed_funds = set(existing_df['name'].tolist())
            print(f"Found {len(processed_funds)} already processed funds")
            enhanced_data = existing_df.to_dict('records')
        except FileNotFoundError:
            existing_df = pd.DataFrame()
            processed_funds = set()
            enhanced_data = []
            print("Starting fresh processing")

        # Process each fund
        for idx, row in original_df.iterrows():
            fund_name = row['name']
            
            # Skip if already processed
            if fund_name in processed_funds:
                print(f"Skipping already processed fund: {fund_name}")
                continue

            print(f"\nProcessing {idx + 1}/{total_funds}: {fund_name}")
            matching_schemes = find_matching_schemes_optimized(fund_name, processed_schemes_df)
            
            try:
                if not matching_schemes.empty:
                    best_match = matching_schemes.iloc[0]  # Get the best match
                    scheme_code = best_match['scheme_code']
                    match_score = best_match['match_score']
                    match_type = best_match['match_type']
                    print(f"Matched to scheme code: {scheme_code} (match score: {match_score}, type: {match_type})")
                    
                    try:
                        # Get all available data using mftool
                        details = mf.get_scheme_details(scheme_code)
                        quote = mf.get_scheme_quote(scheme_code)
                        historical_nav = mf.get_scheme_historical_nav(scheme_code, as_Dataframe=True)
                        
                        # Process historical NAV data
                        if isinstance(historical_nav, pd.DataFrame) and not historical_nav.empty:
                            nav_data = historical_nav.copy()
                            nav_data['nav'] = pd.to_numeric(nav_data['nav'], errors='coerce')
                            
                            # Calculate metrics
                            latest_nav = nav_data['nav'].iloc[0]
                            year_ago_nav = nav_data['nav'][nav_data.index >= (datetime.now() - timedelta(days=365)).strftime('%d-%m-%Y')].iloc[-1]
                            three_year_nav = nav_data['nav'][nav_data.index >= (datetime.now() - timedelta(days=3*365)).strftime('%d-%m-%Y')].iloc[-1]
                            
                            # Calculate daily returns
                            nav_data['daily_returns'] = nav_data['nav'].pct_change()
                            
                            # Get benchmark returns (using NIFTY 50 as default benchmark)
                            try:
                                benchmark_details = mf.get_scheme_historical_nav('120716', as_Dataframe=True)  # NIFTY 50 TRI
                                if isinstance(benchmark_details, pd.DataFrame):
                                    benchmark_data = benchmark_details.copy()
                                    benchmark_data['nav'] = pd.to_numeric(benchmark_data['nav'], errors='coerce')
                                    benchmark_data['daily_returns'] = benchmark_data['nav'].pct_change()
                                    
                                    # Align fund and benchmark data
                                    common_dates = nav_data.index.intersection(benchmark_data.index)
                                    if len(common_dates) > 0:
                                        aligned_fund = nav_data.loc[common_dates]
                                        aligned_benchmark = benchmark_data.loc[common_dates]
                                        
                                        # Calculate up and down periods
                                        up_periods = aligned_benchmark['daily_returns'] > 0
                                        down_periods = aligned_benchmark['daily_returns'] < 0
                                        
                                        # Calculate capture ratios
                                        if up_periods.any():
                                            upside_capture = (aligned_fund.loc[up_periods, 'daily_returns'].mean() / 
                                                            aligned_benchmark.loc[up_periods, 'daily_returns'].mean()) * 100
                                        else:
                                            upside_capture = 'N/A'
                                            
                                        if down_periods.any():
                                            downside_capture = (aligned_fund.loc[down_periods, 'daily_returns'].mean() / 
                                                             aligned_benchmark.loc[down_periods, 'daily_returns'].mean()) * 100
                                        else:
                                            downside_capture = 'N/A'
                                else:
                                    upside_capture = downside_capture = 'N/A'
                            except Exception as e:
                                logger.error(f"Error calculating capture ratios: {str(e)}")
                                upside_capture = downside_capture = 'N/A'
                            
                            # Risk metrics
                            risk_free_rate = 0.04  # Assuming 4% risk-free rate
                            volatility = nav_data['daily_returns'].std() * np.sqrt(252) * 100
                            
                            # Create enhanced metrics dictionary
                            fund_metrics = {
                                **row.to_dict(),  # Include original data
                                'scheme_codecomp': scheme_code,
                                'scheme_namecomp': details.get('scheme_name', 'N/A'),
                                'match_score': match_score,
                                'match_type': match_type,
                                'fund_housecomp': details.get('fund_house', 'N/A'),
                                'scheme_typecomp': details.get('scheme_type', 'N/A'),
                                'scheme_categorycomp': details.get('scheme_category', 'N/A'),
                                'start_date': details.get('scheme_start_date', {}).get('date', 'N/A'),
                                'start_nav': details.get('scheme_start_date', {}).get('nav', 'N/A'),
                                'current_nav': quote.get('nav', 'N/A') if quote else 'N/A',
                                'last_updated': quote.get('last_updated', 'N/A') if quote else 'N/A',
                                '1y_return': ((latest_nav / year_ago_nav) - 1) * 100 if year_ago_nav else 'N/A',
                                '3y_return': (((latest_nav / three_year_nav) ** (1/3)) - 1) * 100 if three_year_nav else 'N/A',
                                'volatility': volatility,
                                'sharpe_computes': ((nav_data['daily_returns'].mean() * 252 - risk_free_rate) / 
                                        (volatility / 100)) if volatility > 0 else 'N/A',
                                'max_drawdown': ((nav_data['nav'].cummax() - nav_data['nav']) / nav_data['nav'].cummax()).max() * 100,
                                'skewness': nav_data['daily_returns'].skew(),
                                'kurtosis': nav_data['daily_returns'].kurtosis(),
                                'nav_mean': nav_data['nav'].mean(),
                                'nav_std': nav_data['nav'].std(),
                                'nav_min': nav_data['nav'].min(),
                                'nav_max': nav_data['nav'].max(),
                                'upside_capture': round(upside_capture, 2) if isinstance(upside_capture, (int, float)) else upside_capture,
                                'downside_capture': round(downside_capture, 2) if isinstance(downside_capture, (int, float)) else downside_capture,
                                'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                        else:
                            # Basic metrics if historical data is not available
                            fund_metrics = {
                                **row.to_dict(),  # Include original data
                                'scheme_code': scheme_code,
                                'scheme_name': details.get('scheme_name', 'N/A'),
                                'fund_house': details.get('fund_house', 'N/A'),
                                'scheme_type': details.get('scheme_type', 'N/A'),
                                'scheme_category': details.get('scheme_category', 'N/A'),
                                'current_nav': quote.get('nav', 'N/A') if quote else 'N/A',
                                'last_updated': quote.get('last_updated', 'N/A') if quote else 'N/A',
                                'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                    except Exception as e:
                        logger.error(f"Error getting data for fund {fund_name}: {str(e)}")
                        fund_metrics = {
                            **row.to_dict(),
                            'scheme_code': scheme_code,
                            'error': str(e),
                            'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            **{k: 'N/A' for k in ['scheme_name', 'fund_house', 'scheme_type', 'scheme_category', 
                                                'current_nav', 'last_updated', '1y_return', '3y_return', 'volatility', 
                                                'sharpe', 'max_drawdown', 'skewness', 'kurtosis', 'upside_capture', 'downside_capture']}
                        }
                else:
                    # If no match found, include original data with N/A for new fields
                    fund_metrics = {
                        **row.to_dict(),
                        'scheme_code': 'N/A',
                        'match_found': False,
                        'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        **{k: 'N/A' for k in ['scheme_name', 'fund_house', 'scheme_type', 'scheme_category', 
                                            'current_nav', 'last_updated', '1y_return', '3y_return', 'volatility', 
                                            'sharpe', 'max_drawdown', 'skewness', 'kurtosis']}
                    }
                
                # Add to enhanced data and save progress
                enhanced_data.append(fund_metrics)
                enhanced_df = pd.DataFrame(enhanced_data)
                enhanced_df.to_csv('ll.csv', index=False)
                processed_funds.add(fund_name)
                
                print(f"Progress: {len(processed_funds)}/{total_funds} funds processed")
                
            except Exception as e:
                print(f"Error processing fund {fund_name}: {str(e)}")
                continue  # Continue with next fund on error
            logger.critical(f"Processed fund: {fund_name} with scheme code: {fund_metrics.get('scheme_code', 'N/A')}")
        # print(f"\nProcessing complete! Enhanced data saved to ll.csv with {len(processed_funds)} processed funds")
        
        # Print summary statistics
        success_count = sum(1 for d in enhanced_data if d['scheme_code'] != 'N/A')
        print(f"Successfully matched: {success_count} funds")
        print(f"Failed to match: {len(enhanced_data) - success_count} funds")
        
    except Exception as e:
        print(f"Fatal error in save_as_csv_after_using_mftool_test_py_file: {str(e)}")
        # Save current progress even if fatal error occurs
        if enhanced_data:
            pd.DataFrame(enhanced_data).to_csv('ll.csv', index=False)
            print("Progress saved despite error")
        raise  # Re-raise the exception for proper error handling

def preprocess_schemes(schemes_df):
    """
    Precompute all necessary data for schemes to optimize matching
    """
    # Initialize new columns
    processed_data = []
    logger.info("Starting schemes preprocessing...")
    
    for idx, row in schemes_df.iterrows():
        # Clean scheme name
        clean_scheme = row['scheme_name']
        for char in ['+', '_', '-', '(', ')', '/', '&', '.', ',']:
            clean_scheme = clean_scheme.replace(char, ' ')
        
        # Get words (lowercase for general comparison)
        scheme_words = [word.lower() for word in clean_scheme.split() if word]
        
        # Get hash and other components
        scheme_hash, scheme_full, scheme_abbrev, scheme_acronyms = create_name_hash(scheme_words, clean_scheme)
        
        # Also compute clean name variations for other matching methods
        clean_name = clean_fund_name(row['scheme_name'])
        clean_no_small = set(word for word in clean_name.split() if len(word) > 2)
        clean_no_space = ''.join(clean_name.split())
        clean_alphanumeric = re.sub(r'[^a-z0-9]', '', clean_name)
        
        # Store all preprocessed data
        processed_data.append({
            'scheme_code': row['scheme_code'],
            'scheme_name': row['scheme_name'],
            'clean_name': clean_name,
            'clean_words': set(clean_name.split()),
            'clean_no_small': clean_no_small,
            'clean_no_space': clean_no_space,
            'clean_alphanumeric': clean_alphanumeric,
            'name_hash': scheme_hash,
            'full_words': set(scheme_full),
            'abbrev_words': set(scheme_abbrev),
            'acronyms': set(scheme_acronyms)
        })
    
    # Convert to DataFrame
    processed_df = pd.DataFrame(processed_data)
    logger.info(f"Completed preprocessing {len(processed_df)} schemes")
    return processed_df

def find_matching_schemes_optimized(fund_name, processed_schemes_df):
    """
    Optimized version using preprocessed scheme data
    """
    matches = []
    start_time = datetime.now()

    # Clean fund name once
    clean_fund = fund_name
    for char in ['+', '_', '-', '(', ')', '/', '&', '.', ',']:
        clean_fund = clean_fund.replace(char, ' ')
    
    # Get fund components (compute once)
    fund_words = [word.lower() for word in clean_fund.split() if word]
    fund_hash, fund_full, fund_abbrev, fund_acronyms = create_name_hash(fund_words, clean_fund)
    
    # Precompute fund word sets
    fund_full_set = set(fund_full)
    fund_abbrev_set = set(fund_abbrev)
    fund_acronyms_set = set(fund_acronyms)
    
    # Clean fund variations (compute once)
    clean_fund_name_var = clean_fund_name(fund_name)
    clean_fund_words = set(clean_fund_name_var.split())
    clean_fund_no_small = set(word for word in clean_fund_name_var.split() if len(word) > 2)
    clean_fund_no_space = ''.join(clean_fund_name_var.split())
    clean_fund_alphanumeric = re.sub(r'[^a-z0-9]', '', clean_fund_name_var)
    
    for idx, row in processed_schemes_df.iterrows():
        match_found = False
        match_score = 0
        match_type = ''
        
        # Method 1: Hash matching (fastest)
        if fund_hash == row['name_hash']:
            matches.append({
                'original_name': fund_name,
                'scheme_code': row['scheme_code'],
                'scheme_name': row['scheme_name'],
                'match_type': 'hash_match',
                'match_score': 100
            })
        
        # Method 2: Word set matching
        common_words = len(clean_fund_words.intersection(row['clean_words']))
        if len(clean_fund_words) > 0:
            similarity_score = (common_words / len(clean_fund_words)) * 100
            if similarity_score >= 80:
                matches.append({
                    'original_name': fund_name,
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'match_type': 'word_similarity',
                    'match_score': round(similarity_score, 2)
                })
        
        # Method 3: Component matching (if no match found yet)
        full_word_match = len(fund_full_set.intersection(row['full_words']))
        abbrev_match = len(fund_abbrev_set.intersection(row['abbrev_words']))
        acronym_match = len(fund_acronyms_set.intersection(row['acronyms']))
        
        total_words = len(fund_full) + len(fund_abbrev)
        if total_words > 0:
            match_score = ((full_word_match + abbrev_match + (acronym_match * 1.5)) / total_words * 100)
            if match_score >= 80:
                matches.append({
                    'original_name': fund_name,
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'match_type': 'component_match',
                    'match_score': round(match_score, 2)
                })
        
        # Method 4: No small words comparison
        if clean_fund_no_small:
            common_words = len(clean_fund_no_small.intersection(row['clean_no_small']))
            similarity_score = (common_words / len(clean_fund_no_small)) * 100
            if similarity_score >= 80:
                matches.append({
                    'original_name': fund_name,
                    'scheme_code': row['scheme_code'],
                    'scheme_name': row['scheme_name'],
                    'match_type': 'no_small_words',
                    'match_score': round(similarity_score, 2)
                })
        
        # Method 5: No spaces comparison
        similarity_score = difflib.SequenceMatcher(None, clean_fund_no_space, row['clean_no_space']).ratio() * 100
        if similarity_score >= 80:
            matches.append({
                'original_name': fund_name,
                'scheme_code': row['scheme_code'],
                'scheme_name': row['scheme_name'],                    'match_type': 'no_spaces',
                    'match_score': round(similarity_score, 2)
                })
    
    # Convert to DataFrame and sort by match score
    matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
    if not matches_df.empty:
        matches_df = matches_df.sort_values('match_score', ascending=False)
    
    logger.info(f'time taken to find matches: {datetime.now() - start_time}')
    return matches_df

# Initialize MF tool
mf = Mftool()

# Convert scheme codes to DataFrame and preprocess
codes = mf.get_scheme_codes()
schemes_df = pd.DataFrame([(code, name) for code, name in codes.items()],
                         columns=['scheme_code', 'scheme_name'])

# Preprocess all scheme data for faster matching
processed_schemes_df = preprocess_schemes(schemes_df)
logger.info("Scheme data preprocessing complete")

# Read fund names from a.csv
funds_df = pd.read_csv('a.csv')
print(f"Total funds in a.csv: {len(funds_df)}")

# Create a list to store fund information
fund_info_list = []
save_as_csv_after_using_mftool_test_py_file()
if fund_info_list:
    results_df = pd.DataFrame(fund_info_list)
    print("\nSummary of found funds:")
    print(results_df[['original_name', 'scheme_name', 'nav', 'last_updated']].to_string())
    
    # Save results to CSV
    results_df.to_csv('fund_info_results.csv', index=False)
    print("\nResults saved to fund_info_results.csv")


