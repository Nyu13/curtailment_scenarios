#!/usr/bin/env python3
"""
Curtailment‑loss study for **all** wind farms listed in Nearby_base.csv.

This script analyzes curtailment losses across multiple wind farms by comparing
"blanket" (uniform) vs "smart" (optimized) curtailment strategies.

Changes vs. single‑turbine version
----------------------------------
* Replaces the hard‑coded `TURBINE` variable with a loop over every
  `Asset Name` found in `Nearby_base.csv` (or a user‑supplied subset).
* All outputs – tables and PNGs – are written per‑farm, per‑year:
    summary_<asset>_<year>.csv
    losses_vs_hours_<asset>_<year>.png
* The rest of the logic (price padding, summary calculations, plotting)
  is unchanged.

Toggle `SAVE_TABLE` / `SAVE_PLOT` below if you want to suppress creating
CSV / PNG artefacts.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable, Sequence

import pandas as pd
import matplotlib
from matplotlib import pyplot as plt

# ── user switches ───────────────────────────────────────────────────────────
# Control flags for output generation - set to False to suppress specific outputs
SAVE_TABLE = True      # Generate summary CSV files: summary_<farm>_<year>.csv
SAVE_PLOT  = True      # Generate visualization PNG files: losses_vs_hours_<farm>_<year>.png

# Use headless matplotlib backend for server compatibility (remove if you have a GUI)
matplotlib.use("Agg")

# ── helpers ─────────────────────────────────────────────────────────────────

def fix_hour_24(date_str: str) -> str:
    """
    Translate '… 24' to '00' of the next day (mm/dd/YYYY HH).
    
    This function handles the special case where hour 24 appears in datetime strings,
    converting it to hour 00 of the following day for proper datetime parsing.
    """
    if " 24" in date_str:
        next_day = pd.to_datetime(date_str.split(" ")[0]) + pd.Timedelta(days=1)
        return next_day.strftime("%m/%d/%Y 00")
    return date_str


def load_pool(year: int, csv_path: str) -> pd.DataFrame:
    """Return a complete hourly price series for *year*; gaps → 0 CAD/MWh."""
    pool = pd.read_csv(csv_path)

    pool["Date (HE)"] = (
        pool["Date (HE)"]
        .apply(fix_hour_24)
        .pipe(pd.to_datetime, format="%m/%d/%Y %H")
    )

    # collapse duplicated HE rows (mean() skips NaNs)
    pool = pool.groupby("Date (HE)", as_index=False)["Price ($)"].mean()

    # pad to full calendar year
    start, end = datetime(year, 1, 1), datetime(year + 1, 1, 1)
    full_index = pd.date_range(start, end - pd.Timedelta(hours=1), freq="h")

    pool = (
        pool.set_index("Date (HE)")
            .reindex(full_index)
            .rename_axis("Date (HE)")
            .reset_index()
    )

    pool["Price ($)"] = pool["Price ($)"].fillna(0)
    return pool


def make_summary(power: pd.DataFrame,
                 cut_in_speeds: Sequence[str],
                 n_turbines: int) -> pd.DataFrame:
    """Build the per–cut‑in table and return it as a DataFrame."""
    tbl = {
        "Cut-in (m/s)": [],
        "Production blanket %": [],
        "Production smart %":   [],
        "Annual Losses blanket (MWh)": [],
        "Annual Losses smart (MWh)":   [],
        "CAD/yr blanket": [],
        "CAD/yr smart":   [],
        "Time Curtailed blanket %": [],
        "Time Curtailed smart %":   [],
        "Time Curtailed blanket hr": [],
        "Time Curtailed smart hr":   [],
    }

    # farm‑level power → MW
    power = power.copy()
    power["power_out"] = power["power_out"] * n_turbines / 1000
    total_power = power["power_out"].sum()
    total_hours = len(power)

    for spd in cut_in_speeds:
        b_col, s_col = f"blanket_{spd}", f"smart_{spd}"
        power[b_col] = power[b_col] * n_turbines / 1000
        power[s_col] = power[s_col] * n_turbines / 1000

        curtailed_b = power[(power[b_col] == 0) & (power["power_out"] != 0)]
        curtailed_s = power[(power[s_col] == 0) & (power["power_out"] != 0)]

        losses_b = total_power - power[b_col].sum()
        losses_s = total_power - power[s_col].sum()

        tbl["Cut-in (m/s)"].append(float(spd))
        tbl["Production blanket %"].append((losses_b / total_power) * 100)
        tbl["Production smart %"].append((losses_s / total_power) * 100)
        tbl["Annual Losses blanket (MWh)"].append(losses_b)
        tbl["Annual Losses smart (MWh)"].append(losses_s)
        tbl["CAD/yr blanket"].append((curtailed_b["pool_price"] * curtailed_b["power_out"]).sum())
        tbl["CAD/yr smart"].append((curtailed_s["pool_price"] * curtailed_s["power_out"]).sum())
        tbl["Time Curtailed blanket %"].append(len(curtailed_b) / total_hours * 100)
        tbl["Time Curtailed smart %"].append(len(curtailed_s) / total_hours * 100)
        tbl["Time Curtailed blanket hr"].append(len(curtailed_b))
        tbl["Time Curtailed smart hr"].append(len(curtailed_s))

    return pd.DataFrame(tbl).round({
        "Cut-in (m/s)": 1,
        "Production blanket %": 2,
        "Production smart %": 2,
        "Annual Losses blanket (MWh)": 2,
        "Annual Losses smart (MWh)": 2,
        "CAD/yr blanket": 0,
        "CAD/yr smart": 0,
        "Time Curtailed blanket %": 2,
        "Time Curtailed smart %": 2,
        "Time Curtailed blanket hr": 2,
        "Time Curtailed smart hr": 2,
    })


def plot_summary(df: pd.DataFrame,
                 asset: str,
                 year: int,
                 cut_in_speeds: Sequence[str],
                 out_path: str | None = None) -> None:
    """Create the dual‑axis production vs. curtailed‑hours figure."""
    x_vals = [float(s) for s in cut_in_speeds]

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(x_vals, df["Production blanket %"], "o-b",
             label="Production Blanket (%)")
    ax1.plot(x_vals, df["Production smart %"],   "o-r",
             label="Production Smart (%)")
    ax1.set_xlabel("Regulated Cut-in Speed (m/s)")
    ax1.set_ylabel("Production (%)", color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")

    ax2 = ax1.twinx()
    ax2.plot(x_vals, df["Time Curtailed blanket hr"], "o--k",
             label="Hours Curtailed Blanket")
    ax2.plot(x_vals, df["Time Curtailed smart hr"],   "o--g",
             label="Hours Curtailed Smart")
    ax2.set_ylabel("Hours Curtailed (hr/yr)", color="black")
    ax2.tick_params(axis="y", labelcolor="black")

    fig.legend(loc="upper left", bbox_to_anchor=(0.05, 0.95))
    fig.tight_layout()

    if out_path is not None:
        fig.savefig(out_path, dpi=150)
        print(f"🖼  figure saved → {out_path}")
    plt.close(fig)


# ── user paths & constants ─────────────────────────────────────────────────
DIR_OUT   = "./result/peak_season/"
DIR_BASE  = "./supply/"
STATIONS  = os.path.join(DIR_BASE, "Nearby_base.csv")
YEARS     = range(2020, 2024)                    # inclusive
CUTS      = ["5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0"]

# ── asset list ─────────────────────────────────────────────────────────────

assets: Iterable[str] = (
    pd.read_csv(STATIONS)["Asset Name"].unique().tolist()
)


print("Assets found:")
for a in assets:
    print(f" • {a}")
print()

# ── main loop ───────────────────────────────────────────────────────────────
for asset in assets:
    n_turbines = (
        pd.read_csv(STATIONS)
          .loc[lambda d: d["Asset Name"].str.contains(asset, case=False),
               "number_of_turbines"]
          .iloc[0]
    )
    print(f"\n================ {asset}  –  {n_turbines} turbines ================")

    for yr in YEARS:
        power_path = os.path.join(DIR_OUT, f"{asset}_{yr}_power_backcalc_3.csv")
        price_path = os.path.join(DIR_BASE, f"pool_price_{yr}.csv")

        if not (os.path.exists(power_path) and os.path.exists(price_path)):
            print(f"⚠️  missing files for {asset} / {yr} – skipped")
            continue

        print(f"\n▶︎ {yr} …")

        power_df = pd.read_csv(power_path, parse_dates=["time"])
        pool_df  = load_pool(yr, price_path)

        print(f"  • power rows: {len(power_df):5d}")
        print(f"  • pool  rows: {len(pool_df):5d}")

        power = (
            power_df.merge(pool_df, left_on="time", right_on="Date (HE)", how="left")
                    .rename(columns={"Price ($)": "pool_price"})
                    .fillna({"pool_price": 0})
                    .drop(columns=["Date (HE)"])
        )

        zero_price_hrs = power.loc[power["pool_price"] == 0, "time"]
        if not zero_price_hrs.empty:
            print("\n⚠️  hours with zero price:")
            print(zero_price_hrs.dt.strftime("%Y-%m-%d %H:%M").head(10).to_list(), "…")
        else:
            print("✓ no zero‑price hours")

        print(f"  • merged rows: {len(power):5d}  (zero prices: {(power['pool_price'] == 0).sum():,})\n")

        summary = make_summary(power, CUTS, n_turbines)
        print(summary, "\n")

        if SAVE_TABLE:
            csv_out = f"summary_{asset}_{yr}_back_3.csv"
            summary.to_csv(csv_out, index=False)
            print(f"📄 table saved → {csv_out}")

        if SAVE_PLOT:
            png_out = f"losses_vs_hours_{asset}_{yr}_back_3.png"
            plot_summary(summary, asset, yr, CUTS, png_out)
