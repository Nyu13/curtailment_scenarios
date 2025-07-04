"""
Blanket correction calculations for wind turbine power output.
"""

from datetime import timedelta, datetime
import pandas as pd
import logging
from config import PROCESSING_CONFIG

logger = logging.getLogger(__name__)


def blanket_extract(df: pd.DataFrame, start_date: str, end_date: str, year_now: int) -> pd.DataFrame:
    """
    Extract blanket correction data for a specific date range and year.
    
    Args:
        df: DataFrame containing sunrise/sunset data
        start_date: Start date in format 'MM-DD'
        end_date: End date in format 'MM-DD'
        year_now: Year to process
        
    Returns:
        DataFrame containing filtered and processed blanket data
    """
    try:
        # Create full dates with year
        start_date_full = f"{year_now}-{start_date}"
        end_date_full = f"{year_now}-{end_date}"
        
        # Convert to datetime objects
        start_datetime = pd.to_datetime(start_date_full, format='%Y-%m-%d')
        end_datetime = pd.to_datetime(end_date_full, format='%Y-%m-%d')
        
        # Filter DataFrame for the date range
        df_intime = df[(df['date'] >= start_datetime) & (df['date'] <= end_datetime)].copy()
        
        if df_intime.empty:
            logger.warning(f"No data found for date range {start_date} to {end_date} in year {year_now}")
            return df_intime
        
        # Process sunrise and sunset times
        df_intime.loc[:, 'rise'] = pd.to_datetime(df_intime['date'].astype(str) + ' ' + df_intime['rise'])
        df_intime.loc[:, 'set'] = pd.to_datetime(df_intime['date'].astype(str) + ' ' + df_intime['set'])
        
        # Calculate work time boundaries (1 hour after rise, 1 hour before set)
        df_intime['1_hour_after_rise'] = df_intime['rise'] + timedelta(hours=1)
        df_intime['1_hour_before_set'] = df_intime['set'] - timedelta(hours=1)
        # df_intime['1_hour_after_rise'] = df_intime['rise']
        # df_intime['1_hour_before_set'] = df_intime['set']
        
        logger.info(f"Extracted blanket data for {len(df_intime)} days from {start_date} to {end_date}")
        return df_intime
        
    except Exception as e:
        logger.error(f"Error extracting blanket data: {e}")
        raise


def stop_work_time(df_results: pd.DataFrame, df_blanket: pd.DataFrame) -> tuple:
    """
    Process work time data and prepare for blanket corrections.
    
    Args:
        df_results: DataFrame containing power output results
        df_blanket: DataFrame containing blanket correction data
        
    Returns:
        Tuple of (processed_results, processed_blanket)
    """
    try:
        # Ensure time column is datetime
        df_results['time'] = pd.to_datetime(df_results['time'])
        
        # Format time column consistently
        df_results['time'] = df_results['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_results['time'] = pd.to_datetime(df_results['time'])
        
        # Ensure blanket datetime columns are properly formatted
        df_blanket['1_hour_after_rise'] = pd.to_datetime(df_blanket['1_hour_after_rise'])
        df_blanket['1_hour_before_set'] = pd.to_datetime(df_blanket['1_hour_before_set'])
        
        # Convert date column to date format for comparison
        df_blanket['date'] = pd.to_datetime(df_blanket['date']).dt.date
        
        logger.info("Successfully processed work time data")
        return df_results, df_blanket
        
    except Exception as e:
        logger.error(f"Error processing work time data: {e}")
        raise


def win_speed_work(row: pd.Series, speed: list) -> pd.Series:
    """
    Apply wind speed-based work restrictions to a data row.
    
    Args:
        row: DataFrame row containing wind and weather data
        speed: List of wind speed thresholds
        
    Returns:
        Modified row with blanket and smart corrections applied
    """
    try:
        for speed_threshold in speed:
            # Apply blanket correction (wind speed only)
            if pd.notna(row['W_hub']) and float(row['W_hub']) <= speed_threshold:
                row[f'blanket_{speed_threshold}'] = 0.0
            
            # Apply smart correction (wind speed + temperature + precipitation)
            if (pd.notna(row['W_hub']) and 
                float(row['W_hub']) <= speed_threshold and 
                row['temp'] > 9.5 and 
                row['precip'] < 1):
                row[f'smart_{speed_threshold}'] = 0.0
        
        return row
        
    except Exception as e:
        logger.error(f"Error applying wind speed work restrictions: {e}")
        return row

def datework_row(row: pd.Series, start_date: str = PROCESSING_CONFIG['blanket_start_date'], end_date: str = PROCESSING_CONFIG['blanket_end_date'], 
                year: int = 2024, speed: list = None, df_blanket: pd.DataFrame = None) -> pd.Series:
    """
    Apply date-based work restrictions to a data row.
    
    Args:
        row: DataFrame row containing time and weather data
        start_date: Start date in format 'MM-DD'
        end_date: End date in format 'MM-DD'
        year: Year to process
        speed: List of wind speed thresholds
        df_blanket: DataFrame containing blanket correction data
        
    Returns:
        Modified row with date-based corrections applied
    """
    try:
        if speed is None:
            speed = []
        if df_blanket is None:
            return row
        
        # Create full dates with year
        start_date_full = f"{year}-{start_date}"
        end_date_full = f"{year}-{end_date}"
        
        # Convert to datetime objects
        start_datetime = pd.to_datetime(start_date_full, format='%Y-%m-%d')
        end_datetime = pd.to_datetime(end_date_full, format='%Y-%m-%d')
        
        # Check if row time is within the date range
        if start_datetime <= row['time'] <= end_datetime:
            # Check if the date exists in blanket data
            if row['time'].date() in df_blanket['date'].values:
                # Get blanket data for this date
                blanket_rows = df_blanket[df_blanket['date'] == row['time'].date()]
                
                if not blanket_rows.empty:
                    rise_time = blanket_rows['1_hour_after_rise'].iloc[0]
                    set_time = blanket_rows['1_hour_before_set'].iloc[0]
                    
                    # Apply corrections based on time of day
                    if row['time'] <= rise_time or row['time'] >= set_time:
                        row = win_speed_work(row, speed)
        
        return row
        
    except Exception as e:
        logger.error(f"Error applying date-based work restrictions: {e}")
        return row