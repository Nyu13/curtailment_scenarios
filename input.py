"""
Data input and reading functions for wind turbine power correction application.
"""

import pandas as pd
import os
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(directory: str, filename: str) -> pd.DataFrame:
    """
    Read a CSV file from the specified directory.
    
    Args:
        directory: Directory path containing the file
        filename: Name of the CSV file
        
    Returns:
        DataFrame containing the file data
    """
    file_path = Path(directory) / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        data = pd.read_csv(file_path)
        logger.info(f"Successfully read file: {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def read_data(wind_turbines: pd.DataFrame, power_curve_dir: str, 
              curva_name: str, turbine_name: str, year: str, 
              dir_input: str, file_to_work: str):
    """
    Read and extract all required data for turbine processing.
    
    Args:
        wind_turbines: DataFrame containing turbine configuration
        power_curve_dir: Directory containing power curve files
        curva_name: Name of the power curve file (without extension)
        turbine_name: Name of the turbine to process
        year: Year of data
        dir_input: Directory containing meteorological data
        file_to_work: Meteorological data filename
        
    Returns:
        Tuple containing (hub_height, number_of_turbines, capacity, power_curve, metdata)
    """
    try:
        # Extract turbine configuration data
        turbine_mask = wind_turbines['Asset Name'].str.contains(turbine_name, case=False, na=False)
        turbine_rows = wind_turbines[turbine_mask]
        
        if turbine_rows.empty:
            raise ValueError(f"Turbine '{turbine_name}' not found in configuration")
        
        turbine_row = turbine_rows.iloc[0]
        
        # Extract required fields
        hub_height = float(turbine_row['hub_height'])
        number_of_turbines = int(turbine_row['number_of_turbines'])
        capacity_MW = float(turbine_row['total_capacity_MW'])
        capacity = capacity_MW * 1000  # Convert to kW
        
        # Load power curve
        power_curve_path = Path(power_curve_dir) / f"{curva_name}.txt"
        if not power_curve_path.exists():
            raise FileNotFoundError(f"Power curve file not found: {power_curve_path}")
        
        power_curve = np.array(pd.read_table(power_curve_path, header=0))
        
        # Load meteorological data
        metdata = read_file(dir_input, file_to_work)
        
        logger.info(f"Successfully loaded data for turbine {turbine_name}")
        return hub_height, number_of_turbines, capacity, power_curve, metdata
        
    except Exception as e:
        logger.error(f"Error reading data for turbine {turbine_name}: {e}")
        raise


def read_sun_time(sunrise_sunset_file: str, year: str, turbine_name: str) -> pd.DataFrame:
    """
    Read and process sunrise/sunset data for a specific turbine and year.
    
    Args:
        sunrise_sunset_file: Path to the sunrise/sunset data file
        year: Year to process
        turbine_name: Name of the turbine
        
    Returns:
        DataFrame containing processed sunrise/sunset data
    """
    try:
        # Load sunrise and sunset data
        sun_times = pd.read_csv(sunrise_sunset_file)
        
        # Convert column names to strings
        sun_times.columns = sun_times.columns.astype(str)
        
        # Process date column
        sun_times['date'] = pd.to_datetime(sun_times['date'], format='%b %d %Y', errors='coerce')
        sun_times['date'] = sun_times['date'].apply(lambda x: x.replace(year=int(year)) if pd.notna(x) else x)
        
        # Filter for specific turbine
        sun_times_turbine = sun_times[sun_times['turbine_name'] == turbine_name]
        
        if sun_times_turbine.empty:
            raise ValueError(f"No sun data found for turbine '{turbine_name}'")
        
        logger.info(f"Successfully loaded sun data for turbine {turbine_name}")
        return sun_times_turbine
        
    except Exception as e:
        logger.error(f"Error reading sun time data for turbine {turbine_name}: {e}")
        raise


