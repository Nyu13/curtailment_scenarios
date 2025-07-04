"""
Configuration file for Wind Turbine Power Correction Application
"""

# Directory configuration
DIRECTORIES = {
    'input': './data/',
    'output': './result/',
    'real': './real/',
    'supply': './supply/'
}

# Physical constants
PHYSICAL_CONSTANTS = {
    'rho_std': 1.225,  # Standard air density (kg/m³)
    'R': 287.05,       # Gas constant (J/(kg·K))
    'ref_height': 10,  # Reference height (m)
    'alpha': 0.143,    # Power law exponent
    'losses': 0,       # Power losses
}

# Wind speed thresholds for analysis
WIND_SPEEDS = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]

# Processing parameters
PROCESSING_CONFIG = {
    'default_turbine_index': 0,
    'default_year': '2020',
    # 'blanket_start_date': '08-01',
    # 'blanket_end_date': '09-10',
    'blanket_start_date': '07-15',
    'blanket_end_date': '09-30',
    'wind_speed_conversion': 0.27778  # km/h to m/s conversion factor
}

# File patterns
FILE_PATTERNS = {
    'input_file_pattern': '{station_name}_{year}_filled.csv',
    'sunrise_sunset_file': 'Sun.csv',
    'turbine_config_file': 'Nearby_base.csv'
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': None  # Set to file path if you want to log to file
} 