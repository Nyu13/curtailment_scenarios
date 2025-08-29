# Import required libraries for data analysis and visualization
import pandas as pd
import os
import matplotlib
from matplotlib import pyplot as plt

# Use the Agg backend for non-GUI environments (server compatibility)
matplotlib.use('Agg')  # Non-GUI backend

# Define directory paths for data input
dir_data = "./"                           # Current directory containing summary files
dir_base = "./supply/"                     # Base directory for supply data
stations_path = os.path.join(dir_base, 'Nearby_base.csv')  # Path to wind turbine metadata

# Load wind turbine metadata and remove duplicate entries
wind_turbines = pd.read_csv(stations_path).drop_duplicates(subset=['Asset Name'])

# Calculate normalization factor for cost calculations (capacity × number of turbines)
norm = wind_turbines['capacity_MW'].sum() * wind_turbines['number_of_turbines'].sum()
print(f"Normalization Factor (norm): {norm}")

# Define columns that require normalization (financial costs)
columns_to_normalize = [
    "CAD/yr blanket (est.)",    # Annual costs for blanket curtailment strategy
    "CAD/yr smart (est.)"       # Annual costs for smart curtailment strategy
]

# Define columns that should remain unnormalized (production percentages)
columns_no_normalization = [
    "Production blanket, %",     # Production percentage for blanket strategy
    "Production smart, %"        # Production percentage for smart strategy
]

# Scenario names (only Scenario 1 and Scenario 3)
selected_scenarios = {1: "Full Season", 3: "Peak Season"}

# Dictionary to store data
data_dict = {col: [] for col in columns_no_normalization + columns_to_normalize}
cut_in_values = []  # Store 'Cut-in (m/s)' values
scenario_labels = []

# Read and process data only for Scenario 1 and Scenario 3
for i in selected_scenarios.keys():
    file_name = os.path.join(dir_data, f"summary_Alberta_{i}.csv")  # Ensure correct file path
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)  # Read CSV file
        print(f"Successfully loaded: {file_name}")

        # Store Cut-in speed values (Assumes all files have the same Cut-in column)
        if len(cut_in_values) == 0:  # Store only once
            cut_in_values = df['Cut-in (m/s)'].tolist()

        # Store non-normalized data
        for col in columns_no_normalization:
            if col in df.columns:
                data_dict[col].append(df[col])  # Store directly without normalization

        # Normalize specified columns (costs only) and store data
        for col in columns_to_normalize:
            if col in df.columns:
                data_dict[col].append(df[col] / norm)  # Normalize and store
        
        scenario_labels.append(selected_scenarios[i])  # Use selected scenario names
    else:
        print(f"File not found: {file_name}")

# Define colors for the two scenarios
colors = ["blue", "orange"]

# Plot Losses (Smart & Blanket) on one plot (No Normalization)
plt.figure(figsize=(10, 5))
for i in range(2):
    plt.plot(
    cut_in_values,
    data_dict["Production blanket, %"][i],
    '^--',
    label=f"{scenario_labels[i]} - Blanket",
    color=colors[i],
    markersize=8,  # increase marker size
    markeredgewidth=1.2  # optional: make marker edges stand out
)
    plt.plot(
        cut_in_values,
        data_dict["Production smart, %"][i],
        'o--',
        label=f"{scenario_labels[i]} - Smart",
        color=colors[i],
        markersize=8,
        markeredgewidth=1.2
)
plt.xlabel("Cut-in Speed (m/s)")
plt.ylabel("Production Losses, %")
plt.legend()
plt.grid(True)
plt.savefig("Losses_Scenario_1_3.png")

# Plot Costs (Smart & Blanket) on another plot (Normalized)
plt.figure(figsize=(10, 5))
for i in range(2):
    plt.plot(cut_in_values, data_dict["CAD/yr smart (est.)"][i], 'o--', label=f"Smart - {scenario_labels[i]}", color=colors[i])
    plt.plot(cut_in_values, data_dict["CAD/yr blanket (est.)"][i], 's--', label=f"Blanket - {scenario_labels[i]}", color=colors[i])
plt.xlabel("Cut-in Speed (m/s)")
plt.ylabel("Annual Costs (Normalized CAD/yr)")
plt.legend()
plt.grid(True)
plt.savefig("Costs_Scenario_1_3.png")

print("\nComparison plots for Scenario 1 and Scenario 3 saved successfully.")
