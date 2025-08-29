# Import required libraries for data analysis and visualization
import pandas as pd
import os
import matplotlib
from matplotlib import pyplot as plt

# Use the Agg backend for non-GUI environments (server compatibility)
matplotlib.use('Agg')

# Define file paths for data input and output
# dirOut = "./result/peak_season/"  # Alternative: peak season analysis
dirOut = "./result/full_season/"     # Current: full season analysis
dir_base = "./supply/"               # Base directory for supply data
stations_path = os.path.join(dir_base, 'Nearby_base.csv')  # Path to wind turbine metadata

# Load wind turbine metadata and remove duplicate entries
wind_turbines = pd.read_csv(stations_path).drop_duplicates(subset=['Asset Name'])
# print("Unique turbines found in Nearby_base.csv:")
# print(wind_turbines[['Asset Name', 'number_of_turbines']])

# Define regulated cut-in speeds for wind turbine analysis (in m/s)
cut_in_speeds = ['5.0', '5.5', '6.0', '6.5', '7.0', '7.5', '8.0']

# Initialize summary data structure to store analysis results
summary_data = {
    'Cut-in (m/s)': [],                           # Wind speed thresholds
    'Production blanket, %': [],                   # Production percentage for blanket strategy
    'Production smart, %': [],                     # Production percentage for smart strategy
    'Annual Losses blanket (MWh/yr)': [],         # Annual energy losses for blanket strategy
    'Annual Losses smart (MWh/yr)': [],           # Annual energy losses for smart strategy
    'CAD/yr blanket (est.)': [],                   # Annual financial losses for blanket strategy
    'CAD/yr smart (est.)': [],                     # Annual financial losses for smart strategy
    'Time Spend Curtailed blanket %': [],          # Percentage of time curtailed for blanket strategy
    'Time Spend Curtailed smart %': [],            # Percentage of time curtailed for smart strategy
    'Time Spend Curtailed blanket hr/yr': [],      # Hours per year curtailed for blanket strategy
    'Time Spend Curtailed smart hr/yr': []         # Hours per year curtailed for smart strategy
}

# Initialize final DataFrame to store combined data
combined_data = pd.DataFrame()

# Fix hour 24 in the 'Date (HE)' column
def fix_hour_24(date_str):
    if isinstance(date_str, pd.Timestamp):  # If already a Timestamp, skip processing
        return date_str
    if pd.isnull(date_str):  # Handle NaN entries
        return None
    if "24" in date_str:  # Check for hour 24
        fixed_date = pd.to_datetime(date_str.split(" ")[0], errors='coerce') + pd.Timedelta(days=1)
        return fixed_date.strftime("%m/%d/%Y 00")
    return date_str

# Loop through each turbine
for _, turbine_row in wind_turbines.iterrows():
    turbine_name = turbine_row['Asset Name']
    number_of_turbines = turbine_row['number_of_turbines']

    for year in range(2020, 2024):
        # File paths
        file_path = os.path.join(dirOut, f"{turbine_name}_{year}_power_output_new.csv")
        print(file_path)
        pool_price_file = os.path.join(dir_base, f'pool_price_{year}.csv')

        if not os.path.exists(file_path) or not os.path.exists(pool_price_file):
            print(f"Missing files for {turbine_name} in {year}. Skipping...")
            continue

        # Load data
        power = pd.read_csv(file_path)
        pool_price = pd.read_csv(pool_price_file)

        # Format datetime columns
        power['time'] = pd.to_datetime(power['time'])
        pool_price['Date (HE)'] = pool_price['Date (HE)'].astype(str).apply(fix_hour_24)
        pool_price['Date (HE)'] = pd.to_datetime(pool_price['Date (HE)'], format="%m/%d/%Y %H", errors='coerce')

        # Merge pool price with power data
        power = pd.merge(
            power,
            pool_price[['Date (HE)', 'Price ($)']],
            left_on='time',
            right_on='Date (HE)',
            how='left'
        ).rename(columns={'Price ($)': 'pool_price'})

        # Convert power_out, blanket, and smart columns to MWt and multiply by number of turbines
        power['power_out'] = (power['power_out'] * number_of_turbines) / 1000

        for speed in cut_in_speeds:
            power[f'blanket_{speed}'] = (power[f'blanket_{speed}'] * number_of_turbines) / 1000
            power[f'smart_{speed}'] = (power[f'smart_{speed}'] * number_of_turbines) / 1000

        # Append to combined data
        combined_data = pd.concat([combined_data, power], ignore_index=True)
        # print(combined_data)

        # Total power output
        total_power = combined_data['power_out'].sum()
        total_hours = len(combined_data)
        x_values = [float(speed) for speed in cut_in_speeds]
        # print(total_power)
        # Perform combined calculations for all turbines in Alberta


for speed in cut_in_speeds:
    # Define blanket and smart column names for the current speed
    blanket_col = f'blanket_{speed}'
    smart_col = f'smart_{speed}'

    # Filter curtailed periods
    curtailed_blanket = combined_data[(combined_data[blanket_col] == 0) & (combined_data['power_out'] != 0)]
    curtailed_smart = combined_data[(combined_data[smart_col] == 0) & (combined_data['power_out'] != 0)]
    # print(combined_data[blanket_col].sum())
    # Calculate annual losses and production %
    annual_losses_b = total_power - combined_data[blanket_col].sum()
    production_percent_b = (annual_losses_b / total_power) * 100
    annual_losses_s = total_power - combined_data[smart_col].sum()
    production_percent_s = (annual_losses_s / total_power) * 100

    # Calculate curtailed time
    hours_curtailed_b = curtailed_blanket.shape[0]
    curtailed_percent_b = hours_curtailed_b / total_hours * 100
    hours_curtailed_s = curtailed_smart.shape[0]
    curtailed_percent_s = hours_curtailed_s / total_hours * 100

    # Calculate money lost
    money_lost_b = (curtailed_blanket['pool_price'] * curtailed_blanket['power_out']).sum()
    money_lost_s = (curtailed_smart['pool_price'] * curtailed_smart['power_out']).sum()

    # Append to table
    summary_data['Cut-in (m/s)'].append(float(speed))
    summary_data['Production blanket, %'].append(production_percent_b)
    summary_data['Production smart, %'].append(production_percent_s)
    summary_data['Annual Losses blanket (MWh/yr)'].append(annual_losses_b)
    summary_data['Annual Losses smart (MWh/yr)'].append(annual_losses_s)
    summary_data['CAD/yr blanket (est.)'].append(money_lost_b)
    summary_data['CAD/yr smart (est.)'].append(money_lost_s)
    summary_data['Time Spend Curtailed blanket %'].append(curtailed_percent_b)
    summary_data['Time Spend Curtailed smart %'].append(curtailed_percent_s)
    summary_data['Time Spend Curtailed blanket hr/yr'].append(hours_curtailed_b)
    summary_data['Time Spend Curtailed smart hr/yr'].append(hours_curtailed_s)

# Create DataFrame for the table
results_df = pd.DataFrame(summary_data)

# Round values for better readability
results_df = results_df.round({
    'Cut-in (m/s)': 1,
    'Production blanket, %': 2,
    'Production smart, %': 2,
    'Annual Losses blanket (MWh/yr)': 2,
    'Annual Losses smart (MWh/yr)': 2,
    'CAD/yr blanket (est.)': 0,
    'CAD/yr smart (est.)': 0,
    'Time Spend Curtailed blanket %': 2,
    'Time Spend Curtailed smart %': 2,
    'Time Spend Curtailed blanket hr/yr': 2,
    'Time Spend Curtailed smart hr/yr': 2
})

# Save the table to a CSV file
output_file = './summary_Alberta.csv'
results_df.to_csv(output_file, index=False)
print(f"Table saved as {output_file}")

