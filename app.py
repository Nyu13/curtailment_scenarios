"""
Wind Turbine Power Correction Application
"""

import os
import re
import logging
import pandas as pd
from config import DIRECTORIES, PHYSICAL_CONSTANTS, WIND_SPEEDS, PROCESSING_CONFIG, FILE_PATTERNS, LOGGING_CONFIG

# Local imports
import input
import blanket
import roughness
import power_output
import write_data

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format'],
    filename=LOGGING_CONFIG['file']
)
logger = logging.getLogger(__name__)


class WindTurbineProcessor:
    def __init__(self, config=None):
        self.config = config or {}
        self.setup_directories()
        self.setup_constants()
        
    def setup_directories(self):
        """Setup required directories."""
        self.directories = self.config.get('directories', DIRECTORIES)
        
        # Create directories if they don't exist
        for dir_path in self.directories.values():
            os.makedirs(dir_path, exist_ok=True)
            
        self.power_curve_dir = os.path.join(self.directories['supply'], 'curve/')
        os.makedirs(self.power_curve_dir, exist_ok=True)
        
    def setup_constants(self):
        """Setup physical constants and parameters."""
        self.constants = {**PHYSICAL_CONSTANTS, 'wind_speeds': WIND_SPEEDS}
        self.processing_config = PROCESSING_CONFIG
        self.file_patterns = FILE_PATTERNS
        
    def load_turbine_data(self, index=None):
        """Load turbine configuration data."""
        index = index or self.processing_config['default_turbine_index']
        
        try:
            wind_turbines_pattern = input.read_file(
                self.directories['supply'], 
                self.file_patterns['turbine_config_file']
            )
            
            turbine_name = wind_turbines_pattern.loc[index, 'Asset Name']
            station_name = wind_turbines_pattern.loc[index, 'Nearby_Station']
            curva_name = wind_turbines_pattern.loc[index, 'Model']
            
            logger.info(f"Loaded turbine: {turbine_name}")
            logger.info(f"Station: {station_name}")
            logger.info(f"Curve: {curva_name}")
            
            return turbine_name, station_name, curva_name, wind_turbines_pattern
            
        except Exception as e:
            logger.error(f"Failed to load turbine data: {e}")
            raise
            
    def find_input_file(self, station_name, year):
        """Find the input meteorological data file."""
        expected_file = self.file_patterns['input_file_pattern'].format(
            station_name=station_name, year=year
        )
        file_path = os.path.join(self.directories['input'], expected_file)
        
        if os.path.exists(file_path):
            return expected_file
        else:
            # Fallback: search for files containing station name and year
            file_list = [f for f in os.listdir(self.directories['input']) 
                        if os.path.isfile(os.path.join(self.directories['input'], f))]
            
            for file in file_list:
                if station_name in file and year in file:
                    return file
                    
            raise FileNotFoundError(f"No input file found for station {station_name} and year {year}")
            
    def find_real_data_file(self, turbine_name, year):
        """Find the real power data file."""
        file_list = [f for f in os.listdir(self.directories['real']) 
                    if os.path.isfile(os.path.join(self.directories['real'], f))]
        
        filtered_files = [f for f in file_list if year in f and turbine_name in f]
        
        if not filtered_files:
            raise FileNotFoundError(f"No real data file found for turbine {turbine_name} and year {year}")
            
        return filtered_files[0]
        
    def process_meteorological_data(self, metdata):
        """Process and prepare meteorological data."""
        # Convert wind speed from km/h to m/s
        metdata['Wind Spd (m/s)'] = metdata['Wind Spd (km/h)'] * self.processing_config['wind_speed_conversion']
        
        # Convert datetime
        metdata['Date/Time (LST)'] = pd.to_datetime(metdata['Date/Time (LST)'])
        
        return metdata
        
    def process_turbine(self, turbine_name, station_name, curva_name, year, wind_turbines_pattern):
        """Process a single turbine."""
        try:
            # Find input files
            file_to_work = self.find_input_file(station_name, year)
            file_real = self.find_real_data_file(turbine_name, year)
            
            logger.info(f"Processing file: {file_to_work}")
            logger.info(f"Real data file: {file_real}")
            

            # Read input data
            hub_height, number_of_turbines, capacity, power_curve, metdata = input.read_data(
                wind_turbines_pattern, self.power_curve_dir, curva_name, turbine_name, 
                year, self.directories['input'], file_to_work
            )
            
            # Read sun times
            sunrise_sunset_file = os.path.join(self.directories['supply'], self.file_patterns['sunrise_sunset_file'])
            sun_times = input.read_sun_time(sunrise_sunset_file, year, turbine_name)
            
            # Process meteorological data
            metdata = self.process_meteorological_data(metdata)
            
            # Calculate roughness
            metdata['Roughness'] = metdata.apply(
                roughness.get_roughness, 
                axis=1, 
                wind_turbines_pattern=wind_turbines_pattern, 
                turbine_name=turbine_name
            )
            
            # Calculate power output
            wind_speed = metdata['Wind Spd (m/s)']
            temperature = metdata['Temp (°C)']
            roughness_values = metdata['Roughness']
            
            df_power_out = power_output.get_power_output(
                temperature, wind_speed, hub_height, roughness_values,
                self.constants['ref_height'], power_curve, self.constants['losses'], metdata
            )
            
            # Apply blanket corrections
            start_date = self.processing_config['blanket_start_date']
            end_date = self.processing_config['blanket_end_date']
            df_blanket = blanket.blanket_extract(sun_times, start_date, end_date, year)
            df_power_out, df_blanket = blanket.stop_work_time(df_power_out, df_blanket)
            
            # Initialize blanket and smart columns
            for speed in self.constants['wind_speeds']:
                df_power_out[f'blanket_{speed}'] = df_power_out['power_out']
                df_power_out[f'smart_{speed}'] = df_power_out['power_out']
            
            # Calculate speed results
            speed_results = []
            for _, row in df_power_out.iterrows():
                result = blanket.datework_row(
                    row, start_date, end_date, year, 
                    self.constants['wind_speeds'], df_blanket
                )
                speed_results.append(result)
            
            speed_results_df = pd.DataFrame(speed_results)
            
            
            # wind_turbines_action.update_win_corrected(wind_turbines, turbine_data, year)
            write_data.write_speed(speed_results_df, self.directories['input'], turbine_name, year)
            
            logger.info(f"Successfully processed turbine {turbine_name}")
            return False  # Stop processing
            
        except Exception as e:
            logger.error(f"Error processing turbine {turbine_name}: {e}")
            return True  # Continue processing
            
    def run(self, turbine_index=None, year=None):
        """Run the main processing loop."""
        turbine_index = turbine_index or self.processing_config['default_turbine_index']
        year = year or self.processing_config['default_year']
        
        logger.info("Starting wind turbine processing")
        logger.info(f"Turbine index: {turbine_index}, Year: {year}")
        
        try:
            # Load turbine data
            turbine_name, station_name, curva_name, wind_turbines_pattern = self.load_turbine_data(turbine_index)
            
            # Process the turbine
            continue_processing = self.process_turbine(
                turbine_name, station_name, curva_name, year, wind_turbines_pattern
            )
            
            if not continue_processing:
                logger.info("Processing completed successfully")
            else:
                logger.warning("Processing encountered issues but will continue")
                
        except Exception as e:
            logger.error(f"Fatal error in processing: {e}")
            raise


def main():
    """Main entry point for the application."""
    processor = WindTurbineProcessor()
    processor.run()


if __name__ == "__main__":
    main() 