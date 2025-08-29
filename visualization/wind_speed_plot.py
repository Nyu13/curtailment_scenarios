"""
Wind Speed Distribution Analysis for Mid-Summer Period
====================================================

This script generates histogram + KDE overlay plots for wind speeds between 4-11 m/s
during the mid-summer period (July 15 – September 30). Creates one 2×2 panel plot
per wind turbine covering the years 2020-2023.

Output: result/full_season/freq_plots/<Turbine>_speed_mix_Jul15-Sep30.png

Purpose: Analyze wind speed patterns during peak summer months to understand
turbine performance characteristics and optimize curtailment strategies.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

# ─── directories ──────────────────────────────────────────────────
# Define base paths and create output directory structure
BASE       = Path(".")                                    # Current working directory
MODEL_DIR  = BASE / "result" / "full_season"             # Model results directory
BACK_DIR   = MODEL_DIR                                    # Back-calculation results (same directory)
SUPPLY_DIR = BASE / "supply"                             # Supply data directory
OUT_DIR    = MODEL_DIR / "freq_plots"                    # Output directory for frequency plots
OUT_DIR.mkdir(parents=True, exist_ok=True)               # Create output directory if it doesn't exist

YEARS = range(2020, 2024)                                # Analysis years: 2020-2023

# Define wind speed bins for histogram analysis (2 m/s intervals)
BIN_EDGES  = np.arange(4, 13, 2)                        # Bin edges: 4, 6, 8, 10, 12 m/s
BIN_WIDTH  = np.diff(BIN_EDGES)[0]                       # Bin width (2 m/s)
BIN_LABELS = [f"{a}-{b-1}" for a, b in zip(BIN_EDGES[:-1], BIN_EDGES[1:])]  # Labels: "4-5", "6-7", etc.

# colours & style
SRC_ORDER   = ["Back-calc", "Modelled"]
SRC_PALETTE = {"Back-calc": "#0173B2", "Modelled": "#DE8F05"}
sns.set_palette(list(SRC_PALETTE.values()))
plt.rcParams.update({"font.size": 12})

# ─── turbines ─────────────────────────────────────────────────────
meta     = pd.read_csv(SUPPLY_DIR / "Nearby_base.csv")
TURBINES = meta["Asset Name"].unique()

def read_series(path: Path, year: int):
    """Return DF[time,W_hub] filtered to 15 Jul–30 Sep, or None."""
    if not path.exists():
        return None
    df = pd.read_csv(path, usecols=["time", "W_hub"])
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time", "W_hub"])

    # --- keep only 15 Jul – 30 Sep ---
    start = pd.Timestamp(year=year, month=7, day=15)
    end   = pd.Timestamp(year=year, month=9, day=30, hour=23, minute=59, second=59)
    df = df[(df["time"] >= start) & (df["time"] <= end)]

    return df

for turb in TURBINES:
    yearly = {}

    for yr in YEARS:
        mod = read_series(MODEL_DIR / f"{turb}_{yr}_power_output_new.csv", yr)
        bck = read_series(BACK_DIR  / f"{turb}_{yr}_power_backcalc.csv",   yr)

        if mod is None or bck is None or mod.empty or bck.empty:
            continue

        # restrict speed range 4-12 m s⁻¹
        mod = mod.query("4 <= W_hub < 12")
        bck = bck.query("4 <= W_hub < 12")
        if mod.empty or bck.empty:
            continue

        mod["Source"] = "Modelled"
        bck["Source"] = "Back-calc"
        yearly[yr] = pd.concat([mod, bck])

    if not yearly:
        continue

    # ─── figure ---------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    axes = axes.flatten()

    for i, (ax, (yr, df)) in enumerate(zip(axes, sorted(yearly.items()))):


        # KDE overlay
        sns.kdeplot(data=df, x="W_hub",
                    hue="Source", hue_order=SRC_ORDER, palette=SRC_PALETTE,
                    common_norm=False, bw_adjust=0.8, cut=0,
                    fill=False, linewidth=1.4, ax=ax, legend=False)

        ax.set_title(str(yr))
        ax.set_xlim(4, 11)
        ax.set_xlabel("Wind-speed (m/s)")
        ax.set_ylabel("Rel. freq." if i % 2 == 0 else "")
        ax.grid(alpha=.3)

    # remove unused axes if fewer than 4 years present
    for extra in axes[len(yearly):]:
        extra.remove()

    # global legend
    handles = [plt.Line2D([0], [0], color=SRC_PALETTE[s], lw=6) for s in SRC_ORDER]
    fig.legend(handles, SRC_ORDER, loc="upper right", frameon=False)

    plt.tight_layout(rect=[0, 0, 1, 0.93])

    out_png = OUT_DIR / f"{turb}_speed_kde_Jul15-Sep30.png"
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    print("✅ wrote", out_png)
