# Import required libraries for data analysis, numerical computations, and visualization
import pandas as pd
import os
import numpy as np
import matplotlib
from matplotlib import pyplot as plt

# Use the Agg backend for non-GUI environments (server compatibility)
matplotlib.use('Agg')

# Define input directories for different data sources
dirOut = "./result/full_season/"      # Current model results directory
dirreal = "./real/no_code/"           # Real (AESO) power generation data directory
dir_base = "./supply/"                # Base supply data directory
dirOld = "./result_before/"           # Previous model results for comparison

# Define path to wind turbine metadata file
stations_path = os.path.join(dir_base, 'Nearby_base.csv')
years = range(2020, 2024)  # Analysis period: 2020-2023

# Load wind turbine metadata and create lookup dictionaries for efficient processing
wind_turbines = pd.read_csv(stations_path)
turbine_info = wind_turbines.set_index('Asset Name')['number_of_turbines'].to_dict()  # Convert to dictionary for fast lookup
turbine_names = wind_turbines['Asset Name'].unique()  # Get unique turbine names

# Set up the figure with 4 subplots (one for each year)
fig, axs = plt.subplots(2, 2, figsize=(16, 12))

# Initialize dictionaries to store error metrics
mape_modeled, rmse_modeled = {}, {}
mape_old, rmse_old = {}, {}

# Process each year
for i, year in enumerate(years):
    annual_comparison = pd.DataFrame(index=turbine_names, columns=['Modeled', 'AESO', 'Initial'])

    for turbine_name in turbine_names:
        try:
            num_turbines = turbine_info.get(turbine_name, 1)  # Default to 1 if missing

            # Load forecasted power data (Modeled)
            power_file = os.path.join(dirOut, f"{turbine_name}_{year}_power_output_new.csv")
            if os.path.exists(power_file):
                power = pd.read_csv(power_file)
                total_forecasted_power = (power['power_out'].sum() / 1000) * num_turbines  # Convert to MW & scale
            else:
                total_forecasted_power = np.nan

            # Load real power data (AESO)
            real_file = os.path.join(dirreal, f"{year}_{turbine_name}.csv")
            if os.path.exists(real_file):
                real_power_data = pd.read_csv(real_file)
                total_real_power = real_power_data['Volume'].sum()  # Already in MW
            else:
                total_real_power = np.nan

            # Load old power data (Initial)
            old_file = os.path.join(dirOld, f"{turbine_name}_{year}_power_output_new.csv")
            if os.path.exists(old_file):
                old_power = pd.read_csv(old_file)
                total_old_power = (old_power['power_out'].sum() / 1000) * num_turbines  # Convert to MW & scale
            else:
                total_old_power = np.nan

            # Store data in DataFrame
            annual_comparison.loc[turbine_name] = [total_forecasted_power, total_real_power, total_old_power]

        except Exception as e:
            print(f"Error processing {turbine_name} for year {year}: {e}")

    # Drop rows where all values are NaN
    annual_comparison.dropna(how="all", inplace=True)

    # Calculate error metrics
    valid_modeled_data = annual_comparison.dropna(subset=['Modeled', 'AESO'])
    valid_old_data = annual_comparison.dropna(subset=['Initial', 'AESO'])

    if not valid_modeled_data.empty:
        modeled = valid_modeled_data['Modeled'].values
        actual = valid_modeled_data['AESO'].values

        # MAPE & RMSE for Modeled vs AESO
        mape_modeled[year] = np.mean(np.abs((modeled - actual) / actual)) * 100
        rmse_modeled[year] = np.sqrt(np.mean((modeled - actual) ** 2))

    if not valid_old_data.empty:
        old = valid_old_data['Initial'].values
        actual = valid_old_data['AESO'].values

        # MAPE & RMSE for Old vs AESO
        mape_old[year] = np.mean(np.abs((old - actual) / actual)) * 100
        rmse_old[year] = np.sqrt(np.mean((old - actual) ** 2))

# Print the results
for year in years:
    print(f"Year {year}:")
    print(f"  - Modeled vs Real (AESO):")
    print(f"      - MAPE: {mape_modeled.get(year, 'N/A'):.2f}%")
    print(f"      - RMSE: {rmse_modeled.get(year, 'N/A'):.2f} MW")
    print(f"  - Old vs Real (AESO):")
    print(f"      - MAPE: {mape_old.get(year, 'N/A'):.2f}%")
    print(f"      - RMSE: {rmse_old.get(year, 'N/A'):.2f} MW")
    print()
