"""
services/weather_service.py
Weather API integration for temperature and climate data.
Extracted from app.py for better organization.
"""

import requests
from constants import API_KEY_WEATHER


def get_weather_temperature(lat, lng):
    """
    Get current temperature for given coordinates using WeatherAPI.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        float: Temperature in Celsius or None if failed
    """
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY_WEATHER}&q={lat},{lng}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        temp_c = data.get('current', {}).get('temp_c')

        return float(temp_c) if temp_c is not None else None

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None


def get_weather_data_full(lat, lng):
    """
    Get full weather data for given coordinates.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        dict: Weather data including temperature, humidity, wind, etc. or None if failed
    """
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY_WEATHER}&q={lat},{lng}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        current = data.get('current', {})

        return {
            'temp_c': current.get('temp_c'),
            'temp_f': current.get('temp_f'),
            'humidity': current.get('humidity'),
            'wind_kph': current.get('wind_kph'),
            'condition': current.get('condition', {}).get('text'),
            'feelslike_c': current.get('feelslike_c')
        }

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None


def estimate_ambient_temperature(lat, lng, default_temp=25.0):
    """
    Estimate ambient temperature with fallback to default.

    Args:
        lat: Latitude
        lng: Longitude
        default_temp: Default temperature in Celsius if API fails (default: 25.0)

    Returns:
        float: Temperature in Celsius
    """
    temp = get_weather_temperature(lat, lng)
    return temp if temp is not None else default_temp
