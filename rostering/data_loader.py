"""
Data loading and normalization for roster scheduling.
"""
import pandas as pd
import argparse
import os
from config import days


def load_availability_data(availability_file=None):
    """
    Load and normalize staff availability data from Excel file.
    
    Args:
        availability_file: Path to availability Excel file. If None, uses default.
        
    Returns:
        pandas.DataFrame: Normalized availability data
    """
    # Parse command line arguments if no file specified
    if availability_file is None:
        parser = argparse.ArgumentParser()
        default_path = os.path.join(os.path.dirname(__file__), "AvailabilityHJ-3.xlsx")
        parser.add_argument("--availability", default=default_path)
        args = parser.parse_args()
        availability_file = args.availability
    
    # Read Excel file
    df = pd.read_excel(availability_file)
    
    # Normalize day headers (handle alternate spellings)
    alt_day_keys = {'Tue': ['Tues'], 'Thu': ['Thus']}
    rename_map = {}
    for d in days:
        alts = [d] + alt_day_keys.get(d, [])
        for suffix in ('start', 'end'):
            canonical = f"{d}_{suffix}"
            if canonical in df.columns:
                continue
            for alt in alts:
                alt_col = f"{alt}_{suffix}"
                if alt_col in df.columns:
                    rename_map[alt_col] = canonical
                    break
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # Standardize "Manger" to "Manager"
    df['Role'] = df['Role'].replace('Manger', 'Manager')
    
    return df
