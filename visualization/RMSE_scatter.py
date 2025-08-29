# Import required libraries for file operations, data analysis, statistical metrics, and visualization
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
import matplotlib
from matplotlib import pyplot as plt
import seaborn as sns

# Use headless matplotlib backend for server compatibility
matplotlib.use("Agg")

# Define directory paths for data processing
BASE = Path('.')                           # Current working directory
MODEL_DIR = BASE / 'result' / 'full_season'  # Model results directory
BACK_DIR = MODEL_DIR                       # Back-calculation results (same directory)
SUPPLY_DIR = BASE / 'supply'               # Supply data directory

# Analysis parameters and configuration
BIN_EDGES = np.arange(4, 13, 2)  # Wind speed bins: 4-5, 6-7, 8-9, 10-11, 12-13 m/s
YEARS = range(2020, 2024)         # Analysis years: 2020-2023
PERIOD_START, PERIOD_END = (7, 15), (9, 30)  # Analysis period: July 15 - September 30

# Load metadata for distances
meta = pd.read_csv(SUPPLY_DIR / 'Nearby_base.csv')
meta = meta[['Asset Name', 'Distance']].dropna()

# Turbines to process
TURBINES = meta['Asset Name'].unique()

# Store RMSE and distance
results = []

def read_series(path: Path, year: int):
    if not path.exists():
        return None
    df = pd.read_csv(path, usecols=['time', 'W_hub'])
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time', 'W_hub'])

    # Filter by July 15 - Sep 30
    start = pd.Timestamp(year=year, month=PERIOD_START[0], day=PERIOD_START[1])
    end = pd.Timestamp(year=year, month=PERIOD_END[0], day=PERIOD_END[1], hour=23, minute=59, second=59)
    return df[(df['time'] >= start) & (df['time'] <= end)]

# Calculate RMSE
for turb in TURBINES:
    all_mod, all_bck = [], []

    for yr in YEARS:
        mod = read_series(MODEL_DIR / f'{turb}_{yr}_power_output_new.csv', yr)
        bck = read_series(BACK_DIR / f'{turb}_{yr}_power_backcalc.csv', yr)

        if mod is None or bck is None:
            continue

        mod_hist, _ = np.histogram(mod['W_hub'], bins=BIN_EDGES, density=True)
        bck_hist, _ = np.histogram(bck['W_hub'], bins=BIN_EDGES, density=True)

        all_mod.extend(mod_hist)
        all_bck.extend(bck_hist)

    if all_mod and all_bck:
        rmse = np.sqrt(mean_squared_error(all_mod, all_bck))
        distance = meta.loc[meta['Asset Name'] == turb, 'Distance'].iloc[0]
        results.append((turb, distance, rmse))

# Results DataFrame
df_results = pd.DataFrame(results, columns=['Turbine', 'Distance_km', 'RMSE'])

# Scatter Plot
plt.figure(figsize=(6, 4))
sns.scatterplot(data=df_results, x='Distance_km', y='RMSE')
plt.xlabel('Distance between Weather Station and Wind Farm (km)')
plt.ylabel('RMSE (Distribution Similarity)')
# plt.title('RMSE vs. Distance: Wind-speed Distribution Similarity (July 15 - Sep 30)')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Save Plot
output_path = MODEL_DIR / 'freq_plots' / 'rmse_distance_trend.png'
plt.savefig(output_path, dpi=300)
print('✅ Plot saved:', output_path)
