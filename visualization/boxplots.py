"""

─────────────────────────────────────────────────────────────────────
Reads *summary_*.csv files produced by the **forward/backward-calculation**
run and creates:
  • three 8-panel box-plot PNGs (production %, energy-loss MWh/MW, CAD-loss/MW)
    with DIFFERENT y-axis limits for Full vs Peak seasons (top vs bottom row)
  • three CSV tables with Blanket-vs-Smart statistics (cleaned of outliers)

Edit BASE_DIR if your project path differs.
"""

# ───────────────────────────────── 0. Imports & cosmetics ─────────
# Import required libraries for data processing, visualization, and file operations
import re, os
from pathlib import Path
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
from matplotlib import pyplot as plt

matplotlib.use("Agg")                       # Use headless backend for server compatibility
sns.set_style("whitegrid")                  # Set seaborn style to white grid
sns.set_palette("colorblind")               # Use colorblind-friendly palette
plt.rcParams.update({                        # Configure matplotlib font sizes for better readability
    "font.size":       19,
    "axes.titlesize":  19,
    "axes.labelsize":  19,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "legend.fontsize": 19,
})
COLORS = ["#0173B2", "#DE8F05"]             # Color scheme: Blue for Blanket, Orange for Smart

# ──────────────────────────────── 1. Paths & constants ────────────
# Define base directory and subdirectories for data processing
BASE_DIR   = Path(r"C:\Users\asobchen\workspace\filling_up")   # ← adjust if needed
RESULT_DIR = BASE_DIR / "result"                                # Results directory
SUPPLY_DIR = BASE_DIR / "supply"                                # Supply data directory

# Define folder structure for different seasons (peak vs full season analysis)
FOLDERS = {
    "peak_season":  RESULT_DIR / "peak_season" / "losess" / "backward",  # Peak season backward calculation results
    "full_season":  RESULT_DIR / "full_season" / "losess" / "backward",  # Full season backward calculation results
}
TITLES = {"peak_season": "Peak Season", "full_season": "Full Season"}    # Display titles for plots
YEARS  = list(range(2020, 2024))                                        # Analysis years: 2020-2023

# Create output directory for summary statistics tables
STATS_OUT = BASE_DIR / "summary_tables"
STATS_OUT.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────── 2. Turbine meta (capacity) ──────
# Load wind turbine metadata including names and total capacity in MW
meta = pd.read_csv(SUPPLY_DIR / "Nearby_base.csv")[
    ["Asset Name", "total_capacity_MW"]
].drop_duplicates()

# ──────────────────────────────── 3. Accumulators ─────────────────
# Initialize data containers to store results for different metrics and seasons
containers = {
    "loss":        {"peak_season": [], "full_season": []},   # Energy losses in MWh/MW
    "cost":        {"peak_season": [], "full_season": []},   # Financial losses in CAD/MW
    "production":  {"peak_season": [], "full_season": []},   # Production percentages
}

# ──────────────────────────────── 4. Ingest loop  ─────────────────
for scen, folder in FOLDERS.items():
    if not folder.exists():
        print(f"⚠️  Folder missing: {folder}")
        continue

    for year in YEARS:
        for _, row in meta.iterrows():
            turb, cap = row["Asset Name"], row["total_capacity_MW"]
            if pd.isna(cap) or cap == 0:
                continue

            # filenames like: summary_<Turbine>_2020_back.csv  (optionally ..._back_1.csv)
            pat = rf"summary_{re.escape(turb)}_{year}_back(?:_\d+)?\.csv"
            for f in os.listdir(folder):
                if not re.fullmatch(pat, f):
                    continue
                try:
                    df = pd.read_csv(folder / f)
                except Exception as e:
                    print(f"Error {f}: {e}")
                    continue

                need = [
                    "Annual Losses blanket (MWh)",
                    "Annual Losses smart (MWh)",
                    "CAD/yr blanket",
                    "CAD/yr smart",
                    "Cut-in (m/s)",
                    "Production blanket %",
                    "Production smart %",
                ]
                if not set(need).issubset(df.columns):
                    continue

                df = df[df["Cut-in (m/s)"].isin([5.5, 8])]
                if df.empty:
                    continue

                # normalise per installed MW for energy & cost
                df_norm = df.copy()
                df_norm.loc[:, [
                    "Annual Losses blanket (MWh)",
                    "Annual Losses smart (MWh)",
                    "CAD/yr blanket",
                    "CAD/yr smart",
                ]] /= cap

                for cut in [5.5, 8]:
                    sub = df_norm[df_norm["Cut-in (m/s)"] == cut].iloc[0]

                     # energy (MWh/MW)
                    containers["loss"][scen].extend([
                        {"Season": TITLES[scen], "Year": year, "Turbine": turb, "Cut": cut,
                         "Type": "Blanket", "Value": sub["Annual Losses blanket (MWh)"]},
                        {"Season": TITLES[scen], "Year": year, "Turbine": turb, "Cut": cut,
                         "Type": "Smart",   "Value": sub["Annual Losses smart (MWh)"]},
                    ])
                    # cost (CAD/MW)
                    containers["cost"][scen].extend([
                        {"Season": TITLES[scen], "Year": year, "Turbine": turb, "Cut": cut,
                         "Type": "Blanket", "Value": sub["CAD/yr blanket"]},
                        {"Season": TITLES[scen], "Year": year, "Turbine": turb, "Cut": cut,
                         "Type": "Smart",   "Value": sub["CAD/yr smart"]},
                    ])
                    # production (%)
                    containers["production"][scen].extend([
                        {"Season": TITLES[scen], "Year": year, "Turbine": turb, "Cut": cut,
                         "Type": "Blanket", "Value": sub["Production blanket %"]},
                        {"Season": TITLES[scen], "Year": year, "Turbine": turb, "Cut": cut,
                         "Type": "Smart",   "Value": sub["Production smart %"]},
                    ])



# convert to DataFrames
for metric in containers:
    for scen in containers[metric]:
        containers[metric][scen] = pd.DataFrame(containers[metric][scen])

# ──────────────────────────────── 5.  Outlier handling  ───────────
def mark_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tukey (1.5×IQR) rule applied per group:
       Season × Year × Cut × Type
    Returns the same frame with a Boolean column `IsOutlier`.
    """
    def _flag(group):
        q1, q3 = group.quantile([.25, .75])
        iqr     = q3 - q1
        low, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
        return (group < low) | (group > hi)

    df = df.copy()
    df["IsOutlier"] = (
        df.groupby(["Season", "Year", "Cut", "Type"])["Value"]
          .transform(_flag)
    )
    return df


# ──────────────────────────────── 6.  Plot helper (dual y-lims) ───
def make_boxplot(df_peak, df_full, ylabel, fname, ylim_full, ylim_peak):
    """
    Builds an 8-panel figure (4 years × 2 seasons) with different y-axis
    limits for Full Season (top row) and Peak Season (bottom row).
    *Plots always include* the outliers (dots).
    """
    fig, axes = plt.subplots(2, 4, figsize=(20, 10), sharex=True)
    for idx, year in enumerate(YEARS):
        # -------- FULL season (row-0) --------
        ax = axes[0, idx]
        sns.boxplot(data=df_full[df_full["Year"] == year],
                    x="Cut", y="Value", hue="Type",
                    palette=COLORS, ax=ax,
                    linewidth=1.5, fliersize=3,
                    medianprops={"color": "black", "linewidth": 2})
        ax.set_title(f"{TITLES['full_season']} – {year}")
        ax.set_ylabel(ylabel if idx == 0 else "")
        ax.set_ylim(ylim_full)        # full-season y-range
        ax.grid(True, alpha=.35)
        (ax.legend(loc="upper left") if idx == 0 else ax.get_legend().remove())

        # -------- PEAK season (row-1) --------
        ax = axes[1, idx]
        sns.boxplot(data=df_peak[df_peak["Year"] == year],
                    x="Cut", y="Value", hue="Type",
                    palette=COLORS, ax=ax,
                    linewidth=1.5, fliersize=3,
                    medianprops={"color": "black", "linewidth": 2})
        ax.set_title(f"{TITLES['peak_season']} – {year}")
        ax.set_xlabel("Cut-in speed (m/s)")
        ax.set_ylabel(ylabel if idx == 0 else "")
        ax.set_ylim(ylim_peak)        # peak-season y-range
        ax.grid(True, alpha=.35)
        (ax.legend(loc="upper left") if idx == 0 else ax.get_legend().remove())

    plt.tight_layout()
    plt.savefig(fname, dpi=300)
    plt.close()
    print(f"📊  {fname}")

# ──────────────────────────────── 7.  Stats & outlier CSVs  ───────
def compute_detailed_stats(df_dict: dict, csv_base: str) -> pd.DataFrame:
    """
    For each Season × Year × Cut × Type:
      Min, Q1, Mean, Median, Q3, Max, IQR, LB (lower whisker), UB (upper whisker).
    Saves a single CSV with all groups.
    """
    rows = []
    for scen_key, df in df_dict.items():
        if df.empty:
            continue
        df = df.copy()
        df["Season"] = df["Season"].astype(str)

        # Groupby across Season/Year/Cut/Type
        for (season, yr, cut, typ), g in df.groupby(["Season", "Year", "Cut", "Type"], observed=False):
            vals = g["Value"].dropna().to_numpy()
            if vals.size == 0:
                continue
            q1   = np.quantile(vals, 0.25, method="linear")  # matches pandas Type-7
            med  = np.quantile(vals, 0.50, method="linear")
            q3   = np.quantile(vals, 0.75, method="linear")
            iqr  = q3 - q1
            lb   = q1 - 1.5 * iqr
            ub   = q3 + 1.5 * iqr
            rows.append({
                "Season": season, "Year": yr, "Cut": cut, "Type": typ,
                "Min": float(np.min(vals)), "Q1": float(q1), "Mean": float(np.mean(vals)),
                "Median": float(med), "Q3": float(q3), "Max": float(np.max(vals)),
                "IQR": float(iqr), "LB (1.5×IQR)": float(lb), "UB (1.5×IQR)": float(ub),
                "N": int(vals.size),
            })

    out = pd.DataFrame(rows).sort_values(["Season", "Year", "Cut", "Type"])
    out_csv = STATS_OUT / f"{csv_base}_detailed_stats_backward.csv"
    out.to_csv(out_csv, index=False)
    print(f"📄  detailed stats → {out_csv}")
    return out




# ──────────────────────────────── 8.  Per-station Prod Loss tables ─
def export_production_losses_tables(df_full: pd.DataFrame, df_peak: pd.DataFrame):
    """
    Writes two CSVs (Full + Peak) with wide-format production losses:
      Year | Turbine | Blanket_5.5 | Blanket_8 | Smart_5.5 | Smart_8
    Also prints them to console grouped by year.
    """
    def _build_table(df_in: pd.DataFrame, season_label: str):
        if df_in.empty:
            print(f"No data for {season_label}")
            return
        # Only production rows expected here
        pivot = (
            df_in.pivot_table(
                index=["Year", "Turbine"],
                columns=["Type", "Cut"],
                values="Value",
                aggfunc="first",
                observed=False
            )
            .reindex(columns=[("Blanket", 5.5), ("Blanket", 8.0),
                              ("Smart", 5.5),   ("Smart", 8.0)], fill_value=np.nan)
        )
        pivot.columns = [f"{t}_{c}".replace(".0","") for t, c in pivot.columns]
        pivot = pivot.reset_index().sort_values(["Year", "Turbine"])

        # Save CSV per season
        out_csv = STATS_OUT / f"production_losses_wide_{season_label.replace(' ', '_')}_backward.csv"
        pivot.to_csv(out_csv, index=False)
        print(f"📄  production loss table → {out_csv}")

        # Console pretty-print per year
        for yr, tbl in pivot.groupby("Year"):
            print(f"\n===== {season_label} – Year {yr} =====")
            print(tbl.drop(columns=["Year"]).to_string(index=False))

    _build_table(df_full, "Full Season")
    _build_table(df_peak, "Peak Season")




# ──────────────────────────────── 9.  Build plots (dual y-lims) ───
# Choose ranges you prefer for Full vs Peak rows:
make_boxplot(containers["loss"]["peak_season"],
             containers["loss"]["full_season"],
             "Annual losses (MWh / installed MW)",
             BASE_DIR / "annual_losses_comparison_backward_1.png",
             ylim_full=(0, 140),   # Full Season (top row)
             ylim_peak=(0, 60))    # Peak Season (bottom row)

make_boxplot(containers["cost"]["peak_season"],
             containers["cost"]["full_season"],
             "Annual cost (CAD / installed MW)",
             BASE_DIR / "cost_per_turbine_comparison_backward_1.png",
             ylim_full=(0, 25_000),
             ylim_peak=(0, 10_000))

make_boxplot(containers["production"]["peak_season"],
             containers["production"]["full_season"],
             "Production losses (%)",
             BASE_DIR / "production_comparison_backward_1.png",
             ylim_full=(0, 5),
             ylim_peak=(0, 3))

# ──────────────────────────────── 10.  Tables (cleaned)  ───────────

energy_stats = compute_detailed_stats(containers["loss"],   "energy_losses_backward")
cost_stats   = compute_detailed_stats(containers["cost"],   "financial_losses_backward")
prod_stats   = compute_detailed_stats(containers["production"], "production_losses_backward")




# ──────────────────────────────── 11.  Production loss tables  ────
export_production_losses_tables(
    containers["production"]["full_season"],
    containers["production"]["peak_season"]
)

print("\nDone.")
