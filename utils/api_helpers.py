"""
utils/api_helpers.py
API wrapper functions for Google Maps and other external APIs.
Extracted from app.py for better organization.
"""

import requests
from urllib.parse import urlencode
from constants import API_KEY_GOOGLE, API_KEY_WEATHER


def extract_lat_long(address_or_postalcode, api_cache=None):
    """
    Extract latitude and longitude from address using Google Geocoding API.

    Args:
        address_or_postalcode: Address string or postal code
        api_cache: Optional cache dictionary

    Returns:
        tuple: (lat, lng, state_name)
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"extract_lat_long_{address_or_postalcode}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address_or_postalcode}&key={API_KEY_GOOGLE}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            cached_value = (None, None, None)
            api_cache[cache_key] = cached_value
            return cached_value

        data = response.json()

        if not data.get('results'):
            cached_value = (None, None, None)
            api_cache[cache_key] = cached_value
            return cached_value

        latlng = data['results'][0]['geometry']['location']

        # Extract state
        state_name = None
        for component in data['results'][0].get('address_components', []):
            if 'administrative_area_level_1' in component.get('types', []):
                state_name = component.get('long_name')
                break

        cached_value = (latlng.get("lat"), latlng.get("lng"), state_name)
        api_cache[cache_key] = cached_value
        return cached_value

    except Exception as e:
        print(f"Geocoding error for {address_or_postalcode}: {e}")
        cached_value = (None, None, None)
        api_cache[cache_key] = cached_value
        return cached_value


def extract_route_coor(origin, destination):
    """
    Extract route coordinates using Google Directions API.

    Args:
        origin: (lat, lng) tuple
        destination: (lat, lng) tuple

    Returns:
        list: List of coordinate tuples along route
    """
    try:
        endpoint = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': f"{origin[0]},{origin[1]}",
            'destination': f"{destination[0]},{destination[1]}",
            'key': API_KEY_GOOGLE,
            'mode': 'driving'
        }

        response = requests.get(f'{endpoint}?{urlencode(params)}', timeout=10)

        if response.status_code not in range(200, 299) or not response.json().get('routes'):
            return []

        polyline_str = response.json()['routes'][0]['overview_polyline']['points']

        # Decode polyline
        from utils.helpers import decode_polyline
        return decode_polyline(polyline_str)

    except Exception as e:
        print(f"Route extraction error: {e}")
        return []


def inland_routes_cal(start_coords, end_coords, api_cache=None):
    """
    Calculate inland route distance and duration using Google Distance Matrix API.

    Args:
        start_coords: (lat, lng) tuple
        end_coords: (lat, lng) tuple
        api_cache: Optional cache dictionary

    Returns:
        tuple: (distance_string, duration_string)
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"inland_route_{start_coords[0]}_{start_coords[1]}_{end_coords[0]}_{end_coords[1]}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        origin = f"{start_coords[0]},{start_coords[1]}"
        destination = f"{end_coords[0]},{end_coords[1]}"

        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&key={API_KEY_GOOGLE}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            cached_value = ("0 km", "0 min")
            api_cache[cache_key] = cached_value
            return cached_value

        data = response.json()

        if (data.get('rows') and data['rows'][0].get('elements') and
            data['rows'][0]['elements'][0].get('status') == 'OK'):

            element = data['rows'][0]['elements'][0]
            distance_str = element['distance']['text']
            duration_str = element['duration']['text']

            cached_value = (distance_str, duration_str)
            api_cache[cache_key] = cached_value
            return cached_value

        cached_value = ("0 km", "0 min")
        api_cache[cache_key] = cached_value
        return cached_value

    except Exception as e:
        print(f"Inland route calculation error: {e}")
        cached_value = ("0 km", "0 min")
        api_cache[cache_key] = cached_value
        return cached_value


def local_temperature(lat, lon, api_cache=None):
    """
    Get local temperature using WeatherAPI.

    Args:
        lat: Latitude
        lon: Longitude
        api_cache: Optional cache dictionary

    Returns:
        float: Temperature in Celsius
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"local_temperature_{lat}_{lon}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY_WEATHER}&q={lat},{lon}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            temp = data['current']['temp_c']
            api_cache[cache_key] = temp
            return temp

        # Default fallback
        api_cache[cache_key] = 25.0
        return 25.0

    except Exception as e:
        print(f"Weather API error for ({lat}, {lon}): {e}")
        api_cache[cache_key] = 25.0
        return 25.0


def carbon_intensity(lat, lng, api_cache=None):
    """
    Get carbon intensity using ElectricityMap API.

    Args:
        lat: Latitude
        lng: Longitude
        api_cache: Optional cache dictionary

    Returns:
        float: Carbon intensity in gCO2eq/kWh
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"carbon_intensity_{lat}_{lng}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        from constants import API_KEY_ELECTRICITYMAP

        url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
        headers = {"auth-token": API_KEY_ELECTRICITYMAP}
        params = {"lat": lat, "lon": lng}

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            intensity = data.get('carbonIntensity', 200.0)
            api_cache[cache_key] = intensity
            return intensity

        # Default fallback
        default_intensity = 200.0
        api_cache[cache_key] = default_intensity
        return default_intensity

    except Exception as e:
        print(f"Carbon intensity API error for ({lat}, {lng}): {e}")
        default_intensity = 200.0
        api_cache[cache_key] = default_intensity
        return default_intensity
