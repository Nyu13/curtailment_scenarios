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
import backward_calc

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
            curve_name = wind_turbines_pattern.loc[index, 'Model']
            
            logger.info(f"Loaded turbine: {turbine_name}")
            logger.info(f"Station: {station_name}")
            logger.info(f"Curve: {curve_name}")
            
            return turbine_name, station_name, curve_name, wind_turbines_pattern
            
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
        files = [f for f in os.listdir(self.directories["real"]) if year in f and turbine_name in f]
        if not files:
            raise FileNotFoundError(f"No real data file for {turbine_name}, {year}")
        return files[0]
        
    def process_meteorological_data(self, metdata):
        """Process and prepare meteorological data."""
        # Convert wind speed from km/h to m/s
        metdata['Wind Spd (m/s)'] = metdata['Wind Spd (km/h)'] * self.processing_config['wind_speed_conversion']
        
        # Convert datetime
        metdata['Date/Time (LST)'] = pd.to_datetime(metdata['Date/Time (LST)'])
        
        return metdata
        
    def process_turbine(self, turbine_name, station_name, curve_name, year, wind_turbines_pattern):
        """Process a single turbine."""
        try:
            # Find input files
            file_to_work = self.find_input_file(station_name, year)
            file_real = self.find_real_data_file(turbine_name, year)
            
            logger.info(f"Processing file: {file_to_work}")
            logger.info(f"Real data file: {file_real}")
            

            # Read input data
            hub_height, number_of_turbines, capacity, power_curve, metdata = input.read_data(
                wind_turbines_pattern, self.power_curve_dir, curve_name, turbine_name, 
                year, self.directories['input'], file_to_work
            )
            
            real_df = input.read_real_power_data(self.directories["real"], file_real)
            real_df['Volume'] *=1000 # MW → kW
            real_df["time"] = pd.to_datetime(real_df["Date (MST)"])
            real_df = real_df[["time", "Volume"]]

            # ---------- merge met & power on timestamp
            metdata = self.process_meteorological_data(metdata)
            metdata = metdata.merge(
            real_df, left_on="Date/Time (LST)", right_on="time", how="left")

            
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
            surface_pressure = metdata['Stn Press (kPa)']
            roughness_values = metdata['Roughness']
            
            df_power_out = power_output.get_power_output(
                temperature, wind_speed, hub_height, roughness_values,
                self.constants['ref_height'], power_curve, self.constants['losses'], metdata
            )

            # Read sun times
            sunrise_sunset_file = os.path.join(self.directories['supply'], self.file_patterns['sunrise_sunset_file'])
            sun_times = input.read_sun_time(sunrise_sunset_file, year, turbine_name)            

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
            
            # ───────── BACK-CALCULATE HUB-HEIGHT WIND SPEED ─────────
            # Site air density ρ_site  [kg m-3]
            air_density = backward_calc.calculate_air_density(
                metdata["Stn Press (kPa)"],      # kPa → Pa 
                metdata["Temp (°C)"]             # air temperature in °C
            )

            # Per-turbine real power  [kW]
            per_turbine_kw = metdata["Volume"] / number_of_turbines

            # Invert power curve → W_hub_backcalc  [m s-1]
            W_hub_backcalc = backward_calc.calc_wind_speed_from_power(
                per_turbine_kw,
                power_curve,
                air_density,
                losses=0.0                        # we don't use losses
            )

            # Pack into its own DataFrame
            df_backcalc = pd.DataFrame({
                "time":   metdata["Date/Time (LST)"],
                "temp":   metdata["Temp (°C)"],
                "precip": metdata["Precip. Amount (mm)"],
                "W_hub": W_hub_backcalc,
                "power_out": per_turbine_kw

                
            })

            df_backcalc, df_blanket = blanket.stop_work_time(df_backcalc, df_blanket)
            
            # Initialize blanket and smart columns
            for speed in self.constants['wind_speeds']:
                df_backcalc[f'blanket_{speed}'] = df_backcalc['power_out']
                df_backcalc[f'smart_{speed}'] = df_backcalc['power_out']

            # Calculate speed results
            speed_results_b = []
            for _, row in df_backcalc.iterrows():
                result = blanket.datework_row(
                    row, start_date, end_date, year, 
                    self.constants['wind_speeds'], df_blanket
                )
                speed_results_b.append(result)
            
            speed_backcalc_df = pd.DataFrame(speed_results_b)
            # Write the back-calc CSV
            write_data.write_backcalc(
                speed_backcalc_df,
                self.directories["output"],
                turbine_name,
                year
            )
           
            
            write_data.write_power(speed_results_df, self.directories['output'], turbine_name, year)
            
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
            turbine_name, station_name, curve_name, wind_turbines_pattern = self.load_turbine_data(turbine_index)
            
            # Process the turbine
            continue_processing = self.process_turbine(
                turbine_name, station_name, curve_name, year, wind_turbines_pattern
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
