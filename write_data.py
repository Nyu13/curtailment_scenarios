"""
Data writing functions for wind turbine power correction application.
"""

import pandas as pd
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def write_speed(speed_res_df: pd.DataFrame, dir_out: str, turbine_name: str, year: str) -> None:
    """
    Write speed results DataFrame to CSV file.
    
    Args:
        speed_res_df: DataFrame containing speed results
        dir_out: Output directory path
        turbine_name: Name of the turbine
        year: Year of data
    """
    try:
        # Ensure output directory exists
        output_dir = Path(dir_out)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{turbine_name}_{year}_power_output_new3.csv"
        file_path = output_dir / filename
        
        # Write DataFrame to CSV
        speed_res_df.to_csv(file_path, index=False)
        
        logger.info(f"Successfully wrote speed results to: {file_path}")
        print(f"Speed results written to: {file_path}")
        
    except Exception as e:
        logger.error(f"Error writing speed results for turbine {turbine_name}: {e}")
        raise




def write_power_output(power_df: pd.DataFrame, dir_out: str, turbine_name: str, year: str) -> None:
    """
    Write power output DataFrame to CSV file.
    
    Args:
        power_df: DataFrame containing power output data
        dir_out: Output directory path
        turbine_name: Name of the turbine
        year: Year of data
    """
    try:
        # Ensure output directory exists
        output_dir = Path(dir_out)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{turbine_name}_{year}_power_output.csv"
        file_path = output_dir / filename
        
        # Write DataFrame to CSV
        power_df.to_csv(file_path, index=False)
        
        logger.info(f"Successfully wrote power output to: {file_path}")
        
    except Exception as e:
        logger.error(f"Error writing power output for turbine {turbine_name}: {e}")
        raise


def write_seasonal_comparison(comparison_df: pd.DataFrame, dir_out: str, 
                            turbine_name: str, year: str) -> None:
    """
    Write seasonal comparison DataFrame to CSV file.
    
    Args:
        comparison_df: DataFrame containing seasonal comparison data
        dir_out: Output directory path
        turbine_name: Name of the turbine
        year: Year of data
    """
    try:
        # Ensure output directory exists
        output_dir = Path(dir_out)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{turbine_name}_{year}_seasonal_comparison.csv"
        file_path = output_dir / filename
        
        # Write DataFrame to CSV
        comparison_df.to_csv(file_path, index=True)
        
        logger.info(f"Successfully wrote seasonal comparison to: {file_path}")
        
    except Exception as e:
        logger.error(f"Error writing seasonal comparison for turbine {turbine_name}: {e}")
        raise


def backup_file(file_path: str, backup_suffix: str = "_backup") -> str:
    """
    Create a backup of an existing file.
    
    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix to add to backup filename
        
    Returns:
        Path to the backup file
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File does not exist, cannot create backup: {file_path}")
            return str(path)
        
        # Create backup filename
        backup_path = path.with_suffix(f"{backup_suffix}{path.suffix}")
        
        # Copy file
        import shutil
        shutil.copy2(path, backup_path)
        
        logger.info(f"Created backup: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Error creating backup of {file_path}: {e}")
        return file_path


def validate_dataframe(df: pd.DataFrame, required_columns: list = None) -> bool:
    """
    Validate DataFrame before writing.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if df is None:
            logger.error("DataFrame is None")
            return False
        
        if df.empty:
            logger.warning("DataFrame is empty")
            return True  # Empty DataFrame is valid
        
        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False
        
        # Check for infinite values
        if df.isin([float('inf'), float('-inf')]).any().any():
            logger.warning("DataFrame contains infinite values")
        
        # Check for NaN values
        nan_count = df.isna().sum().sum()
        if nan_count > 0:
            logger.warning(f"DataFrame contains {nan_count} NaN values")
        
        logger.info("DataFrame validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating DataFrame: {e}")
        return False