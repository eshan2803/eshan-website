"""
utils/conversions.py
Conversion functions for pressure, density, energy, and other physical properties.
Extracted from app.py for better organization and reusability.
"""

import math
from scipy.optimize import fsolve


def PH2_pressure_fnc(density):
    """
    Calculate pressure of hydrogen as a function of density.

    Args:
        density: Hydrogen density in kg/m³

    Returns:
        float: Pressure in bar
    """
    return 0.0269 * density + 1.9656


def PH2_density_fnc_helper(pressure):
    """
    Helper function to calculate hydrogen density from pressure.

    Args:
        pressure: Pressure in bar

    Returns:
        float: Density in kg/m³
    """
    return (pressure - 1.9656) / 0.0269


def PH2_density_fnc(pressure):
    """
    Calculate hydrogen density from pressure with bounds checking.

    Args:
        pressure: Pressure in bar

    Returns:
        float: Density in kg/m³ (clamped to 1-80 kg/m³)
    """
    density = PH2_density_fnc_helper(pressure)
    if density < 1:
        return 1.0
    elif density > 80:
        return 80.0
    return density


def multistage_compress(pressure):
    """
    Calculate multistage compression work for hydrogen.

    Args:
        pressure: Final pressure in bar

    Returns:
        float: Compression work in kWh/kg
    """
    return 1.66 * pressure**0.283


def kinematic_viscosity_PH2(pressure):
    """
    Calculate kinematic viscosity of pressurized hydrogen.

    Args:
        pressure: Pressure in bar

    Returns:
        float: Kinematic viscosity in m²/s
    """
    rho = PH2_density_fnc(pressure)
    mu = 8.76e-6  # Dynamic viscosity (Pa·s)
    return mu / rho


def solve_colebrook(Re, epsilon, D):
    """
    Solve Colebrook equation for friction factor.

    Args:
        Re: Reynolds number
        epsilon: Pipe roughness (m)
        D: Pipe diameter (m)

    Returns:
        float: Darcy friction factor
    """
    def colebrook(f):
        return (1.0 / math.sqrt(f) + 2.0 * math.log10(epsilon / (3.7 * D) + 2.51 / (Re * math.sqrt(f))))

    # Initial guess
    f_initial = 0.02

    try:
        f_solution = fsolve(colebrook, f_initial)
        return f_solution[0]
    except:
        return 0.02  # Return default if solver fails


def PH2_transport_energy(L, D=0.5, P_initial=500, epsilon=0.000045, v=5.0):
    """
    Calculate energy required to transport pressurized hydrogen through pipeline.

    Args:
        L: Pipeline length in km
        D: Pipe diameter in meters (default: 0.5m)
        P_initial: Initial pressure in bar (default: 500 bar)
        epsilon: Pipe roughness in meters (default: 0.000045m)
        v: Flow velocity in m/s (default: 5 m/s)

    Returns:
        float: Transport energy in kWh/kg
    """
    L_m = L * 1000  # Convert km to meters

    # Get fluid properties
    rho = PH2_density_fnc(P_initial)
    nu = kinematic_viscosity_PH2(P_initial)

    # Calculate Reynolds number
    Re = v * D / nu

    # Solve for friction factor
    f = solve_colebrook(Re, epsilon, D)

    # Calculate pressure drop (Darcy-Weisbach equation)
    delta_P = f * (L_m / D) * (rho * v**2) / 2  # Pressure drop in Pa
    delta_P_bar = delta_P / 1e5  # Convert to bar

    # If pressure drop exceeds initial pressure, clamp it
    if delta_P_bar > P_initial * 0.9:
        delta_P_bar = P_initial * 0.9

    # Calculate recompression energy needed
    # Assume we need to restore pressure every time it drops significantly
    num_booster_stations = max(1, int(delta_P_bar / 50))  # Booster every 50 bar drop

    # Energy for recompression
    recompression_energy = num_booster_stations * multistage_compress(50)  # kWh/kg

    return recompression_energy


def convert_km_to_miles(km):
    """
    Convert kilometers to miles.

    Args:
        km: Distance in kilometers

    Returns:
        float: Distance in miles
    """
    return km * 0.621371


def convert_kg_to_tons(kg):
    """
    Convert kilograms to metric tons.

    Args:
        kg: Mass in kilograms

    Returns:
        float: Mass in metric tons
    """
    return kg / 1000.0


def convert_mj_to_kwh(mj):
    """
    Convert megajoules to kilowatt-hours.

    Args:
        mj: Energy in megajoules

    Returns:
        float: Energy in kilowatt-hours
    """
    return mj / 3.6


def convert_celsius_to_kelvin(celsius):
    """
    Convert temperature from Celsius to Kelvin.

    Args:
        celsius: Temperature in Celsius

    Returns:
        float: Temperature in Kelvin
    """
    return celsius + 273.15


def convert_bar_to_psi(bar):
    """
    Convert pressure from bar to PSI.

    Args:
        bar: Pressure in bar

    Returns:
        float: Pressure in PSI
    """
    return bar * 14.5038


# ===== Hydrogen Physics Functions =====

def PH2_pressure_fnc_simple(density):
    """Simple pressure calculation for pressurized H2 (simplified model)"""
    return density * 1.2


def PH2_density_fnc_simple(pressure):
    """Simple density calculation for pressurized H2 (simplified model)"""
    return pressure / 1.2


def PH2_density_fnc_helper_simple(pressure):
    """Helper for density calculation"""
    return 0.25


def PH2_transport_energy_simple(L):
    """
    Simple transport energy calculation for pressurized H2.

    Args:
        L: Distance in km

    Returns:
        float: Energy in MJ
    """
    return L * 0.001


def liquification_data_fitting(H2_plant_capacity):
    """
    Calculate liquefaction energy for hydrogen based on plant capacity.
    Empirical curve fit from industry data.

    Args:
        H2_plant_capacity: Plant capacity in tons per day

    Returns:
        float: Liquefaction energy in kWh/kg
    """
    import numpy as np
    return 8.05 - 0.31 * np.log(H2_plant_capacity)
