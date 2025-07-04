# backward_calc.py — v1.0
"""
Inverse power‑curve utilities – reconstruct hub‑height wind speed **W_hub**
from real *per‑turbine* power output (**Volume** column).

This module is completely standalone; just place it next to **app.py** and
import the public helper `calc_wind_speed_from_power()`.

Dependencies
------------
* numpy
* pandas
* scipy.interpolate
* a `config.py` file exposing::

    PHYSICAL_CONSTANTS = {
        'R': 287.05,        # J kg⁻¹ K⁻¹
        'rho_std': 1.225    # kg m⁻³ (ISO‑standard density)
    }

"""
from __future__ import annotations

import numpy as np
import pandas as pd
from   scipy.interpolate import interp1d
from   config           import PHYSICAL_CONSTANTS, WIND_SPEEDS
import blanket 
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Physical constants (imported so tests can monkey‑patch easily)
# -----------------------------------------------------------------------------
R        = PHYSICAL_CONSTANTS['R']
rho_std  = PHYSICAL_CONSTANTS['rho_std']

# -----------------------------------------------------------------------------
# Public helpers
# -----------------------------------------------------------------------------

def calculate_air_density(surface_pressure: float | pd.Series,
                           temperature: float | pd.Series) -> float | pd.Series:
    try:
        # Ensure temperature is not below absolute zero
        if temperature <= -273.15:
            logger.warning(f"Temperature {temperature}°C is below absolute zero, using -273.15°C")
            temperature = -273.15
        
        # Convert temperature to Kelvin and calculate density
        temperature_kelvin = temperature + 273.15
        air_density = (surface_pressure * 1000) / (R * temperature_kelvin)
        
        return air_density
        
    except Exception as e:
        logger.error(f"Error calculating air density: {e}")
        return rho_std



def _inverse_power_curve(power_curve: np.ndarray):
    """Return an interpolator mapping *power* [kW] → *wind speed* [m s⁻¹]."""
    wind, power = power_curve[:, 0], power_curve[:, 1]

    # Remove duplicates so interp1d is strictly monotone in x (power)
    uniq_power, idx = np.unique(power, return_index=True)

    return interp1d(
        uniq_power,
        wind[idx],
        bounds_error=False,
        fill_value=np.nan,
        assume_sorted=True,
    )


def calc_wind_speed_from_power(
    P_T_series: pd.Series,
    power_curve: np.ndarray,
    air_density: pd.Series,
    losses: float = 0.0,
) -> pd.Series:
    """Vectorised back‑calculation of hub‑height wind speed **W_hub** [m s⁻¹].

    Parameters
    ----------
    P_T_series        : *pd.Series* – per‑turbine power [kW]
    power_curve       : *np.ndarray* shape (N, 2) – [[wind(m/s), power(kW)]]
    air_density       : *pd.Series* – site density [kg m⁻³]
    losses            : *float* – aggregate loss fraction (default **0.0**)

    Returns
    -------
    pd.Series  of W_hub values (same index as *P_T_series*)
    """
    if not isinstance(P_T_series, pd.Series):
        raise TypeError("P_T_series must be a pandas Series")

    inv_curve = _inverse_power_curve(power_curve)

    # Density correction term (ρ_std / ρ_site) ** 1/3
    # Use standard air density (can be enhanced with pressure data)
    air_density = rho_std
    density_corr = (rho_std / air_density) ** (1 / 3)

    P_corr = P_T_series / (1 - losses) * density_corr

    # interp1d works on ndarray, so use .values and re‑wrap as Series
    return pd.Series(inv_curve(P_corr.values), index=P_T_series.index, name="W_hub_backcalc")

