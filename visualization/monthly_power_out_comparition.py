"""
Monthly Power Output Comparison Analysis
=======================================

This script analyzes monthly power output for July-September across all wind turbines,
comparing three data sources: AESO (actual), modelled, and initial estimates.
Calculates percentage differences per month and for the 3-month total period.

Output:
- Plot: result/full_season/monthly_power_output_sum_all_turbines.png
- Console: Tables showing raw TW values and percentage differences

Purpose: Validate model accuracy by comparing predicted vs actual power generation
during peak summer months when wind patterns are most critical.
"""

import os
from pathlib import Path
import pandas as pd
import matplotlib
from matplotlib import pyplot as plt

matplotlib.use("Agg")
# Label size configuration
title_fontsize = 18
label_fontsize = 18
tick_fontsize = 18
legend_fontsize = 18

# ─── paths ───────────────────────────────────────────────────────────
# Define directory paths for different data sources
DIR_OUT   = Path("./result/full_season")    # Current model results directory
DIR_REAL  = Path("./real/no_code")          # Real (AESO) power generation data
DIR_OLD   = Path("./result_before")         # Previous model results for comparison
DIR_BASE  = Path("./supply")                # Base supply data directory

STATIONS_CSV = DIR_BASE / "Nearby_base.csv" # Wind turbine metadata file
YEARS        = range(2020, 2024)            # Analysis years: 2020-2023

MONTHS        = [7, 8, 9]                   # Analysis months: July, August, September
MONTH_LABELS  = ["July", "August", "September"]  # Human-readable month names

# ─── turbine meta ────────────────────────────────────────────────────
meta         = pd.read_csv(STATIONS_CSV)
TURBINES     = meta["Asset Name"].unique()
N_TURB_DICT  = meta.set_index("Asset Name")["number_of_turbines"].to_dict()

# ─── figure boiler-plate ─────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(18, 12), sharey=True)
axes      = axes.flatten()

COLS   = ["navy", "darkgreen", "#DE8F05"]   # AESO, Modelled, Initial
FMT_CF = 1e9                                # kW → TW

for idx, year in enumerate(YEARS):

    # accumulator ➜ {month: {Series: MWh}}
    monthly_tot = {m: {"AESO": 0.0, "Modelled": 0.0, "Initial": 0.0}
                   for m in MONTHS}

    for turb in TURBINES:
        n_turb = N_TURB_DICT.get(turb, 1) or 1

        # modelled ----------------------------------------------------
        f_mod = DIR_OUT / f"{turb}_{year}_power_output_new.csv"
        if f_mod.exists():
            df = (pd.read_csv(f_mod, parse_dates=["time"])
                    .loc[lambda d: d["time"].dt.month.isin(MONTHS)])
            df["power_out"] *= n_turb
            for m, v in df.groupby(df["time"].dt.month)["power_out"].sum().items():
                monthly_tot[m]["Modelled"] += v

        # AESO --------------------------------------------------------
        f_real = DIR_REAL / f"{year}_{turb}.csv"
        if f_real.exists():
            df = (pd.read_csv(f_real, parse_dates=["Date (MST)"])
                    .loc[lambda d: d["Date (MST)"].dt.month.isin(MONTHS)])
            df["real_power"] = df["Volume"] * 1000        # MW → kW
            for m, v in df.groupby(df["Date (MST)"].dt.month)["real_power"].sum().items():
                monthly_tot[m]["AESO"] += v

        # initial -----------------------------------------------------
        f_old = DIR_OLD / f"{turb}_{year}_power_output_new.csv"
        if f_old.exists():
            df = pd.read_csv(f_old)
            tcol = next((c for c in df.columns if "time" in c.lower()
                         or "date" in c.lower()), None)
            if tcol:
                df[tcol] = pd.to_datetime(df[tcol], errors="coerce")
                df = df.loc[df[tcol].dt.month.isin(MONTHS)]
                df["power_out"] *= n_turb
                for m, v in df.groupby(df[tcol].dt.month)["power_out"].sum().items():
                    monthly_tot[m]["Initial"] += v

    # ----- DataFrame for this year ----------------------------------
    df_m = (pd.DataFrame.from_dict(monthly_tot, orient="index")
              .loc[MONTHS]
              .fillna(0.0))

    # add 4-month total (“Total” row)
    df_tot = pd.DataFrame(df_m.sum().rename("Total")).T
    df_all = pd.concat([df_m, df_tot])

    # convert to TW for reporting & plotting
    df_all_TW = df_all / FMT_CF

    # % differences ---------------------------------------------------
    pct = pd.DataFrame(index=df_all_TW.index)
    pct["% Diff Modelled vs AESO"] = (df_all_TW["Modelled"].sub(df_all_TW["AESO"])
                                      .div(df_all_TW["AESO"])*100).round(2)
    pct["% Diff Initial  vs AESO"] = (df_all_TW["Initial"].sub(df_all_TW["AESO"])
                                      .div(df_all_TW["AESO"])*100).round(2)

    print(f"\n=== {year}  July–Oct power totals (TW) ===")
    print(df_all_TW[["AESO", "Modelled", "Initial"]])
    print("\nPercentage differences:")
    print(pct)

    # ----- plotting --------------------------------------------------
    ax = axes[idx]
    df_m_TW = df_m / FMT_CF                 # only months, no total row

    df_m_TW[["AESO", "Modelled", "Initial"]].plot(
        kind="bar", ax=ax, color=COLS, width=0.8)

    ax.set_title(str(year), fontsize=title_fontsize)
    ax.set_xticklabels(MONTH_LABELS, rotation=0, fontsize=tick_fontsize)
    ax.set_ylabel("Power output (TW)", fontsize=label_fontsize)

    ax.set_ylim(0, 0.4)                     # ← fixed y-axis
    ax.tick_params(axis="y", labelsize=tick_fontsize)

    ax.yaxis.grid(True, linestyle="--", alpha=0.7)


    if idx == 0:
        ax.legend(["AESO", "Modelled", "Initial"], loc="upper right", fontsize=legend_fontsize)
    else:
        ax.get_legend().remove()

plt.tight_layout(rect=[0, 0, 1, 0.95])
out_png = DIR_OUT / "monthly_power_output_sum_all_turbines.png"
plt.savefig(out_png, dpi=300)
print("\nPlot saved to", out_png)