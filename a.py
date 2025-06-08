import pandas as pd
from mftool import Mftool
import re
import difflib

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
    
    return matches_df

# Initialize MF tool
mf = Mftool()

# Convert scheme codes to DataFrame
codes = mf.get_scheme_codes()
schemes_df = pd.DataFrame.from_dict(codes, orient='index', columns=['scheme_name'])
schemes_df.index.name = 'scheme_code'
schemes_df.reset_index(inplace=True)

# Read fund names from a.csv
funds_df = pd.read_csv('a.csv')
print(f"Total funds in a.csv: {len(funds_df)}")

# Create a list to store fund information
fund_info_list = []

# Process each fund name from a.csv
for fund_name in funds_df['name'].unique():
    # Search for matching schemes using improved matching logic
    matching_schemes = find_matching_schemes(fund_name, schemes_df)
    
    if not matching_schemes.empty:
        print(f"\nMatches found for {fund_name}:")
        print(matching_schemes[['original_name', 'scheme_name', 'match_score']].to_string())
        
        for _, scheme in matching_schemes.iterrows():
            try:
                # Get scheme information
                info = mf.get_scheme_quote(scheme['scheme_code'])
                if info:
                    info['original_name'] = scheme['original_name']  # Use the original name from matches
                    fund_info_list.append(info)
                    print(f"Found info for: {scheme['original_name']}")
                    
                    # Get historical NAV
                    hist = mf.get_scheme_historical_nav(scheme['scheme_code'], as_dataframe=True)
                    if not hist.empty:
                        print(f"Latest NAV data:\n{hist.tail(1)}")
                    
            except Exception as e:
                print(f"Error processing {fund_name}: {str(e)}")
    
    else:
        print(f"No matching scheme found for: {fund_name}")

# Convert results to DataFrame
if fund_info_list:
    results_df = pd.DataFrame(fund_info_list)
    print("\nSummary of found funds:")
    print(results_df[['original_name', 'scheme_name', 'nav', 'last_updated']].to_string())
    
    # Save results to CSV
    results_df.to_csv('fund_info_results.csv', index=False)
    print("\nResults saved to fund_info_results.csv")


