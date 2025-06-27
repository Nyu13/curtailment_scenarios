"""
Surface roughness calculations for wind turbine power correction.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Define seasonal mappings
SEASON_MAPPING = {
    'Summer Jun-Jul': [6, 7],
    'Pre-harvest Aug': [8],
    'Post-harvest/pre-snow Sep-Nov': [9, 10, 11],
    'Snow covered Dec-Feb': [12, 1, 2],
    'Spring Mar-May': [3, 4, 5]
}


def get_roughness(row: pd.Series, wind_turbines_pattern: pd.DataFrame, turbine_name: str) -> float:
    """
    Calculate surface roughness value for a specific turbine and time period.
    
    Args:
        row: DataFrame row containing datetime information
        wind_turbines: DataFrame containing turbine configuration and roughness values
        turbine_name: Name of the turbine
        
        
    Returns:
        Roughness value for the given time period, or None if not found
    """
    try:
        # Extract month from datetime
        month = row['Date/Time (LST)'].month
        
        # Find turbine data
        if turbine_name not in wind_turbines_pattern['Asset Name'].values:
            logger.warning(f"Turbine '{turbine_name}' not found in wind turbines data")
            return None
        
        # Filter turbine data for the specific year
        turbine_mask = (wind_turbines_pattern['Asset Name'] == turbine_name) 
        
        roughness_row = wind_turbines_pattern[turbine_mask]
        
        if roughness_row.empty:
            logger.warning(f"No roughness data found for turbine '{turbine_name}'")
            return None
        
        if len(roughness_row) > 1:
            logger.warning(f"Multiple roughness records found for turbine '{turbine_name}' , using first")
        
        roughness_row = roughness_row.iloc[0]
        
        # Determine season based on month and return corresponding roughness value
        if month in SEASON_MAPPING['Summer Jun-Jul']:
            return roughness_row['Summer Jun-Jul']
        elif month in SEASON_MAPPING['Pre-harvest Aug']:
            return roughness_row['Pre-harvest Aug']
        elif month in SEASON_MAPPING['Post-harvest/pre-snow Sep-Nov']:
            return roughness_row['Post-harvest/pre-snow Sep-Nov']
        elif month in SEASON_MAPPING['Snow covered Dec-Feb']:
            return roughness_row['Snow covered Dec-Feb']
        elif month in SEASON_MAPPING['Spring Mar-May']:
            return roughness_row['Spring Mar-May']
        else:
            logger.warning(f"Unknown month {month} for roughness calculation")
            return None
            
    except Exception as e:
        logger.error(f"Error calculating roughness for turbine {turbine_name}: {e}")
        return None


def get_season_name(month: int) -> str:
    """
    Get season name for a given month.
    
    Args:
        month: Month number (1-12)
        
    Returns:
        Season name
    """
    for season, months in SEASON_MAPPING.items():
        if month in months:
            return season
    return "Unknown"


def validate_roughness_data(wind_turbines_pattern: pd.DataFrame, turbine_name: str) -> bool:
    """
    Validate that roughness data exists for a turbine.
    
    Args:
        wind_turbines: DataFrame containing turbine configuration
        turbine_name: Name of the turbine to validate
        
    Returns:
        True if valid roughness data exists, False otherwise
    """
    try:
        if turbine_name not in wind_turbines_pattern['Asset Name'].values:
            logger.error(f"Turbine '{turbine_name}' not found in configuration")
            return False
        
        turbine_data = wind_turbines_pattern[wind_turbines_pattern['Asset Name'] == turbine_name].iloc[0]
        
        # Check that all required roughness columns exist
        required_columns = list(SEASON_MAPPING.keys())
        missing_columns = [col for col in required_columns if col not in turbine_data.index]
        
        if missing_columns:
            logger.error(f"Missing roughness columns for turbine '{turbine_name}': {missing_columns}")
            return False
        
        # Check that roughness values are numeric and positive
        for column in required_columns:
            value = turbine_data[column]
            if pd.isna(value) or value <= 0:
                logger.error(f"Invalid roughness value for turbine '{turbine_name}', column '{column}': {value}")
                return False
        
        logger.info(f"Roughness data validation passed for turbine '{turbine_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Error validating roughness data for turbine '{turbine_name}': {e}")
        return False

