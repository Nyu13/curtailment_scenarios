# Wind Turbine Power Correction Application

A Python application for processing wind turbine data and correcting power output calculations based on meteorological conditions and seasonal factors.

## Overview

This application processes wind turbine data to:

- Calculate power output based on meteorological conditions
- Apply blanket corrections for seasonal factors
- Generate corrected power output files

## Features

- **Modular Design**: Clean, object-oriented architecture with separate modules for different functionalities
- **Error Handling**: Comprehensive error handling and logging
- **Configuration Management**: External configuration file for easy customization
- **Flexible Processing**: Support for different turbines, years, and parameters

## Project Structure

```
correcting/
├── app.py                 # Main application file
├── config.py              # Configuration settings
├── input.py               # Data input and reading functions
├── blanket.py             # Blanket correction calculations
├── roughness.py           # Surface roughness calculations
├── power_output.py        # Power output calculations
├── write_data.py          # Data writing functions
├── README.md              # This file
└── __init__.py            # Package initialization
```

## Installation

1. Ensure you have Python 3.7+ installed
2. Install required dependencies:
   ```bash
   pip install pandas numpy
   ```

## Configuration

The application uses `config.py` for all configuration settings:

### Directories

- `input/`: Meteorological data files
- `output/`: Results and output files
- `real/`: Real power data files
- `supply/`: Configuration and reference files

### Physical Constants

- Air density, gas constant, reference height, etc.

### Processing Parameters

- Default turbine index, year, date ranges
- Wind speed thresholds
- Conversion factors

## Usage

### Basic Usage

```python
from app import WindTurbineProcessor

# Create processor with default configuration
processor = WindTurbineProcessor()

# Run with default parameters (turbine index 28, year 2023)
processor.run()

# Run with custom parameters
processor.run(turbine_index=25, year='2022')
```

### Custom Configuration

```python
from app import WindTurbineProcessor

# Custom configuration
custom_config = {
    'directories': {
        'input': './custom_data/',
        'output': './custom_results/',
        'real': './custom_real/',
        'supply': './custom_supply/'
    }
}

processor = WindTurbineProcessor(custom_config)
processor.run()
```

### Command Line Usage

```bash
python app.py
```

## Data Requirements

### Input Files

1. **Meteorological Data**: CSV files with columns:

   - `Date/Time (LST)`: Timestamp
   - `Wind Spd (km/h)`: Wind speed in km/h
   - `Temp (°C)`: Temperature in Celsius

2. **Turbine Configuration**: `Nearby_base.csv` with columns:

   - `Asset Name`: Turbine identifier
   - `Nearby_Station`: Weather station name
   - `Model`: Power curve model

3. **Sun Data**: `Sun.csv` with sunrise/sunset times

4. **Power Curves**: Files in `supply/curve/` directory

### Real Data Files

CSV files containing actual power output data for comparison and correction.

## Processing Flow

1. **Data Loading**: Load turbine configuration and meteorological data
2. **Data Processing**: Convert units and calculate derived parameters
3. **Power Calculation**: Calculate theoretical power output
4. **Blanket Corrections**: Apply seasonal corrections
5. **Speed Analysis**: Analyze power output at different wind speeds
7. **Results Writing**: Save corrected power output files

## Error Handling

The application includes comprehensive error handling:

- **File Not Found**: Automatic file discovery and fallback mechanisms
- **Data Validation**: Checks for required columns and data types
- **Processing Errors**: Graceful handling of calculation errors
- **Logging**: Detailed logging for debugging and monitoring

## Logging

The application uses Python's logging module with configurable levels:

- **INFO**: General processing information
- **WARNING**: Non-critical issues
- **ERROR**: Processing errors
- **DEBUG**: Detailed debugging information

## Contributing

1. Follow PEP 8 style guidelines
2. Add docstrings to all functions and classes
3. Include error handling for all external operations
4. Update configuration file for new parameters
5. Add tests for new functionality

## Troubleshooting

### Common Issues

1. **Missing Files**: Ensure all required data files are in the correct directories
2. **Permission Errors**: Check file and directory permissions
3. **Memory Issues**: For large datasets, consider processing in chunks
4. **Configuration Errors**: Verify all paths in `config.py` are correct

### Debug Mode

Enable debug logging by modifying `config.py`:

```python
LOGGING_CONFIG = {
    'level': 'DEBUG',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'debug.log'
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please create an issue in the project repository or contact the development team.
