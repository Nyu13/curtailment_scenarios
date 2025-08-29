# Wind Energy Curtailment Analysis Project

## Overview

This project analyzes wind farm curtailment strategies and their impact on energy production and financial losses in Alberta, Canada. It compares "blanket" (uniform) vs "smart" (optimized) curtailment approaches across multiple wind farms and years.

## Project Purpose

- **Curtailment Loss Analysis**: Evaluate energy and financial losses from different curtailment strategies
- **Production Optimization**: Compare production percentages between blanket and smart approaches
- **Wind Speed Modeling**: Analyze wind speed distributions and their impact on power generation
- **Performance Validation**: Compare modeled vs. actual (AESO) power generation using RMSE metrics

## Key Features

- **Multi-Year Analysis**: Covers 2020-2023 data
- **Multi-Farm Support**: Processes all wind farms listed in `Nearby_base.csv`
- **Cut-in Speed Analysis**: Evaluates performance across different wind speed thresholds (5.0-8.0 m/s)
- **Financial Impact**: Calculates annual losses in both MWh and CAD
- **Visualization**: Generates comprehensive charts and statistical summaries

## Project Structure

```
├── supply/                          # Input data directory
│   ├── Nearby_base.csv             # Wind farm metadata and capacities
│   └── pool_price_*.csv            # Electricity price data by year
├── result/                         # Output directory
│   ├── peak_season/                # Peak season analysis results
│   └── full_season/                # Full year analysis results
├── real/                           # Actual (AESO) power generation data
├── result_before/                  # Previous model results for comparison
└── *.py                           # Analysis scripts
```

## Core Scripts

### 1. `losses_calculation.py`

Main analysis engine that processes wind farm data and calculates curtailment losses.

### 2. `boxplots.py`

Creates statistical summaries and box plots comparing blanket vs smart strategies across seasons.

### 3. `annual_loses_alberta.py`

Analyzes annual losses across all Alberta wind farms with detailed breakdowns.

### 4. `RMSE.py`

Calculates Root Mean Square Error and Mean Absolute Percentage Error between modeled and actual generation.

### 5. `wind_speed_plot.py`

Generates wind speed distribution plots for mid-summer periods (July 15 - September 30).

### 6. `monthly_power_out_comparition.py`

Compares monthly power output between different strategies and years.

### 7. `production_losses_all_years.py`

Aggregates production losses across all years and wind farms.

## Data Requirements

- **Wind Farm Data**: Power output files named `{turbine}_{year}_power_output_new.csv`
- **Price Data**: Pool price files named `pool_price_{year}.csv`
- **Metadata**: Wind farm information in `Nearby_base.csv`

## Output Files

- **Summary Tables**: CSV files with detailed statistics for each wind farm and year
- **Visualizations**: PNG charts showing production comparisons, loss distributions, and wind speed patterns
- **Error Metrics**: RMSE and MAPE calculations for model validation

## Usage

1. Ensure all required data files are in the correct directories
2. Run individual analysis scripts as needed
3. Check the `result/` directory for generated outputs
4. Review summary tables and visualizations for insights

## Dependencies

- Python 3.7+
- pandas
- numpy
- matplotlib
- seaborn
- pathlib

## Notes

- Scripts use headless matplotlib backend (`Agg`) for server compatibility
- All calculations are performed at the wind farm level (scaled by number of turbines)
- Results are separated by season (peak vs full) for detailed analysis
- Financial calculations use Alberta electricity pool prices

## Contact

For questions or issues with this analysis, please refer to the project documentation or contact the development team.
