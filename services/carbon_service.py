"""
services/carbon_service.py
Carbon intensity and electricity grid data services.
Extracted from app.py for better organization.
"""

import requests
from constants import API_KEY_ELECTRICITYMAP


def get_carbon_intensity(lat, lng):
    """
    Get current carbon intensity for given coordinates using ElectricityMap API.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        float: Carbon intensity in gCO2eq/kWh or None if failed
    """
    try:
        url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
        headers = {"auth-token": API_KEY_ELECTRICITYMAP}
        params = {"lat": lat, "lon": lng}

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        carbon_intensity = data.get('carbonIntensity')

        return float(carbon_intensity) if carbon_intensity is not None else None

    except Exception as e:
        print(f"Error fetching carbon intensity: {e}")
        return None


def get_grid_emission_factor(lat, lng, default_factor=500.0):
    """
    Get grid emission factor with fallback to default.

    Args:
        lat: Latitude
        lng: Longitude
        default_factor: Default emission factor in gCO2eq/kWh if API fails (default: 500.0)

    Returns:
        float: Emission factor in gCO2eq/kWh
    """
    carbon_intensity = get_carbon_intensity(lat, lng)
    return carbon_intensity if carbon_intensity is not None else default_factor


def calculate_electricity_emissions(energy_kwh, lat, lng, default_factor=500.0):
    """
    Calculate CO2 emissions from electricity consumption.

    Args:
        energy_kwh: Electricity consumption in kWh
        lat: Latitude (for grid carbon intensity lookup)
        lng: Longitude (for grid carbon intensity lookup)
        default_factor: Default emission factor in gCO2eq/kWh if API fails

    Returns:
        float: CO2 emissions in kg CO2eq
    """
    emission_factor = get_grid_emission_factor(lat, lng, default_factor)
    # Convert gCO2eq/kWh to kgCO2eq/kWh
    return energy_kwh * (emission_factor / 1000.0)
