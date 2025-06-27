"""
Power output calculations for wind turbines.
"""

import scipy.interpolate as interp
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Physical constants
RHO_STD = 1.225  # Standard air density (kg/m³)
R = 287.05       # Gas constant (J/(kg·K))


def wind_speed_at_hub_height(wind_speed: float, hub_height: float, 
                           surface_roughness: float, ref_height: float) -> float:
    """
    Calculate wind speed at hub height using logarithmic wind profile.
    
    Args:
        wind_speed: Wind speed at reference height (m/s)
        hub_height: Hub height of the turbine (m)
        surface_roughness: Surface roughness length (m)
        ref_height: Reference height for wind speed measurement (m)
        
    Returns:
        Wind speed at hub height (m/s)
    """
    try:
        if surface_roughness <= 0:
            logger.warning(f"Invalid surface roughness: {surface_roughness}, using default value")
            surface_roughness = 0.1
        
        if hub_height <= surface_roughness:
            logger.warning(f"Hub height ({hub_height}) must be greater than surface roughness ({surface_roughness})")
            return wind_speed
        
        # Logarithmic wind profile formula
        wind_speed_hub = wind_speed * (np.log(hub_height / surface_roughness) / 
                                     np.log(ref_height / surface_roughness))
        
        return wind_speed_hub
        
    except Exception as e:
        logger.error(f"Error calculating wind speed at hub height: {e}")
        return wind_speed


def calculate_air_density(surface_pressure: float, temperature: float) -> float:
    """
    Calculate air density based on surface pressure and temperature.
    
    Args:
        surface_pressure: Surface pressure (Pa)
        temperature: Temperature (°C)
        
    Returns:
        Air density (kg/m³)
    """
    try:
        # Ensure temperature is not below absolute zero
        if temperature <= -273.15:
            logger.warning(f"Temperature {temperature}°C is below absolute zero, using -273.15°C")
            temperature = -273.15
        
        # Convert temperature to Kelvin and calculate density
        temperature_kelvin = temperature + 273.15
        air_density = surface_pressure / (R * temperature_kelvin)
        
        return air_density
        
    except Exception as e:
        logger.error(f"Error calculating air density: {e}")
        return RHO_STD


def power_output(wind_speed_hub: float, air_density: float, 
                power_curve: np.ndarray, losses: float) -> tuple:
    """
    Calculate power output using power curve and air density correction.
    
    Args:
        wind_speed_hub: Wind speed at hub height (m/s)
        air_density: Air density (kg/m³)
        power_curve: Power curve data as numpy array (wind speed, power)
        losses: Power losses as fraction (0-1)
        
    Returns:
        Tuple of (power_output, adjustment_factor)
    """
    try:
        # Air density adjustment factor
        adjustment_factor = (air_density / RHO_STD) ** (1.0 / 3)
        
        # Create interpolation function for power curve
        if power_curve.shape[1] < 2:
            logger.error("Power curve must have at least 2 columns (wind speed, power)")
            return 0.0, adjustment_factor
        
        wind_speeds = power_curve[:, 0]
        powers = power_curve[:, 1]
        
        # Create interpolation function
        power_interp = interp.interp1d(
            wind_speeds, powers, 
            kind='linear', 
            bounds_error=False, 
            fill_value=0
        )
        
        # Calculate power with density adjustment
        adjusted_wind_speed = wind_speed_hub * adjustment_factor
        power = power_interp(adjusted_wind_speed) * (1 - losses)
        
        return float(power), adjustment_factor
        
    except Exception as e:
        logger.error(f"Error calculating power output: {e}")
        return 0.0, 1.0


def get_power_output(temperature: pd.Series, wind_speed: pd.Series, 
                    hub_height: float, surface_roughness: pd.Series,
                    ref_height: float, power_curve: np.ndarray, 
                    losses: float, metdata: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate power output for all time periods.
    
    Args:
        temperature: Temperature series (°C)
        wind_speed: Wind speed series (m/s)
        hub_height: Hub height of the turbine (m)
        surface_roughness: Surface roughness series (m)
        ref_height: Reference height for wind speed (m)
        power_curve: Power curve data
        losses: Power losses as fraction
        metdata: Meteorological data DataFrame
        
    Returns:
        DataFrame containing power output results
    """
    try:
        results = []
        
        for i in range(len(temperature)):
            try:
                # Calculate wind speed at hub height
                wind_speed_hub = wind_speed_at_hub_height(
                    wind_speed.iloc[i], hub_height, 
                    surface_roughness.iloc[i], ref_height
                )
                
                # Use standard air density (can be enhanced with pressure data)
                air_density = RHO_STD
                
                # Calculate power output
                power_out, adj_factor = power_output(
                    wind_speed_hub, air_density, power_curve, losses
                )
                
                # Store results
                result = {
                    'time': metdata['Date/Time (LST)'].iloc[i],
                    'temp': temperature.iloc[i],
                    'precip': metdata['Precip. Amount (mm)'].iloc[i],
                    'WindSp': wind_speed.iloc[i],
                    'W_hub': wind_speed_hub,
                    'power_out': power_out
                }
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Error processing row {i}: {e}")
                # Add row with zero power output
                result = {
                    'time': metdata['Date/Time (LST)'].iloc[i],
                    'temp': temperature.iloc[i],
                    'precip': metdata['Precip. Amount (mm)'].iloc[i],
                    'WindSp': wind_speed.iloc[i],
                    'W_hub': 0.0,
                    'power_out': 0.0
                }
                results.append(result)
        
        # Create DataFrame from results
        result_df = pd.DataFrame(results)
        
        logger.info(f"Successfully calculated power output for {len(result_df)} time periods")
        return result_df
        
    except Exception as e:
        logger.error(f"Error calculating power output: {e}")
        raise


def validate_power_curve(power_curve: np.ndarray) -> bool:
    """
    Validate power curve data.
    
    Args:
        power_curve: Power curve data as numpy array
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if power_curve is None or power_curve.size == 0:
            logger.error("Power curve is empty or None")
            return False
        
        if power_curve.shape[1] < 2:
            logger.error("Power curve must have at least 2 columns (wind speed, power)")
            return False
        
        # Check for negative values
        if np.any(power_curve < 0):
            logger.warning("Power curve contains negative values")
        
        # Check for monotonic wind speeds
        wind_speeds = power_curve[:, 0]
        if not np.all(np.diff(wind_speeds) >= 0):
            logger.warning("Wind speeds in power curve are not monotonically increasing")
        
        logger.info("Power curve validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating power curve: {e}")
        return False

