"""
utils/helpers.py
General helper functions for the transport LCA model.
Extracted from app.py for better organization and reusability.
"""

import re
import math
from constants import ROUTE_RISK_ZONES


def decode_polyline(polyline_str):
    """
    Decode Google Maps polyline string to coordinates.

    Args:
        polyline_str: Encoded polyline string from Google Maps API

    Returns:
        list: List of (lat, lng) tuples
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    while index < len(polyline_str):
        shift, result, lat_change, lng_change = 0, 0, 0, 0
        for unit in ['lat', 'lng']:
            shift, result = 0, 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            change = ~(result >> 1) if result & 1 else (result >> 1)
            if unit == 'lat':
                lat_change = change
            else:
                lng_change = change
        lat += lat_change
        lng += lng_change
        coordinates.append((lat / 100000.0, lng / 100000.0))
    return coordinates


def time_to_minutes(time_str):
    """
    Parse time string to minutes.

    Args:
        time_str: Time string like "2 days 5 hours 30 mins"

    Returns:
        int: Total minutes
    """
    time_str = str(time_str)
    days = int(re.search(r'(\d+)\s*day', time_str).group(1)) * 1440 if re.search(r'(\d+)\s*day', time_str) else 0
    hours = int(re.search(r'(\d+)\s*h', time_str).group(1)) * 60 if re.search(r'(\d+)\s*h', time_str) else 0
    minutes = int(re.search(r'(\d+)\s*min', time_str).group(1)) if re.search(r'(\d+)\s*min', time_str) else 0
    return days + hours + minutes


def detect_canal_transit(route):
    """
    Detect if route passes through Suez or Panama canal.

    Args:
        route: SeaRoute object with geometry

    Returns:
        dict: Canal transit information
    """
    suez_bbox = {'lon_min': 32.0, 'lat_min': 29.5, 'lon_max': 33.0, 'lat_max': 31.5}
    panama_bbox = {'lon_min': -80.0, 'lat_min': 8.5, 'lon_max': -79.0, 'lat_max': 9.5}

    suez_transit = False
    panama_transit = False

    if route and route.geometry and 'coordinates' in route.geometry:
        for lon, lat in route.geometry['coordinates']:
            if (suez_bbox['lon_min'] <= lon <= suez_bbox['lon_max'] and
                suez_bbox['lat_min'] <= lat <= suez_bbox['lat_max']):
                suez_transit = True
            if (panama_bbox['lon_min'] <= lon <= panama_bbox['lon_max'] and
                panama_bbox['lat_min'] <= lat <= panama_bbox['lat_max']):
                panama_transit = True

    return {
        'suez': suez_transit,
        'panama': panama_transit
    }


def calculate_route_risk_multiplier(searoute_coords, route_risk_zones=None):
    """
    Calculate insurance risk multiplier based on route.

    Args:
        searoute_coords: List of [lat, lon] coordinates
        route_risk_zones: List of risk zone definitions

    Returns:
        float: Risk multiplier (1.0 = baseline, >1.0 = higher risk)
    """
    if route_risk_zones is None:
        route_risk_zones = ROUTE_RISK_ZONES

    max_multiplier = 1.0

    if not searoute_coords:
        return max_multiplier

    for coord in searoute_coords:
        if not coord or len(coord) < 2:
            continue

        lat, lon = coord[0], coord[1]

        for zone in route_risk_zones:
            bbox = zone['bbox']
            if (bbox['lon_min'] <= lon <= bbox['lon_max'] and
                bbox['lat_min'] <= lat <= bbox['lat_max']):
                if zone['risk_multiplier'] > max_multiplier:
                    max_multiplier = zone['risk_multiplier']

    return max_multiplier


def get_diesel_price(lat, lon, diesel_price_country_dict):
    """
    Get diesel price for a location.

    Args:
        lat: Latitude
        lon: Longitude
        diesel_price_country_dict: Dictionary of country: price mappings

    Returns:
        float: Diesel price in $/gallon
    """
    # Import here to avoid circular dependency
    from services.geocoding import get_country_from_coords

    country_name = get_country_from_coords(lat, lon)
    return diesel_price_country_dict.get(country_name, 4.0)  # Default $4/gallon


def calculate_dynamic_cop(hot_temp, cold_temp, exergy_efficiency=0.4):
    """
    Calculate dynamic coefficient of performance (COP) for refrigeration.

    Uses Carnot efficiency adjusted by exergy efficiency.

    Args:
        hot_temp: Hot side temperature in Celsius
        cold_temp: Cold side temperature in Celsius
        exergy_efficiency: Exergy efficiency factor (0-1)

    Returns:
        float: Coefficient of performance
    """
    hot_temp_K = hot_temp + 273.15
    cold_temp_K = cold_temp + 273.15

    # Carnot COP for refrigeration
    carnot_cop = cold_temp_K / (hot_temp_K - cold_temp_K)

    # Actual COP accounting for exergy efficiency
    actual_cop = carnot_cop * exergy_efficiency

    # Ensure reasonable bounds
    if actual_cop < 0.5:
        actual_cop = 0.5
    elif actual_cop > 10.0:
        actual_cop = 10.0

    return actual_cop


def straight_dis(coor_start_lang, coor_start_lat, coor_end_lang, coor_end_lat):
    """
    Calculate great circle distance between two points.

    Args:
        coor_start_lang: Starting longitude
        coor_start_lat: Starting latitude
        coor_end_lang: Ending longitude
        coor_end_lat: Ending latitude

    Returns:
        float: Distance in kilometers
    """
    R = 6371  # Earth radius in km

    lat1 = math.radians(coor_start_lat)
    lat2 = math.radians(coor_end_lat)
    delta_lat = math.radians(coor_end_lat - coor_start_lat)
    delta_lon = math.radians(coor_end_lang - coor_start_lang)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) *
         math.sin(delta_lon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


# ===== Additional Helper Functions =====

def get_country_from_coords(lat, lon, api_cache=None):
    """
    Get country name from coordinates using Google Geocoding API.

    Args:
        lat: Latitude
        lon: Longitude
        api_cache: Optional cache dictionary

    Returns:
        str: Country name or None
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"country_{lat}_{lon}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        from constants import API_KEY_GOOGLE
        import requests

        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={API_KEY_GOOGLE}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                for component in data['results'][0].get('address_components', []):
                    if 'country' in component.get('types', []):
                        country = component.get('long_name')
                        api_cache[cache_key] = country
                        return country

        api_cache[cache_key] = None
        return None

    except Exception as e:
        print(f"Error getting country from coords ({lat}, {lon}): {e}")
        api_cache[cache_key] = None
        return None


def get_diesel_price(lat, lon, diesel_price_country_dict, api_cache=None):
    """
    Get diesel price for location based on country.

    Args:
        lat: Latitude
        lon: Longitude
        diesel_price_country_dict: Dictionary mapping countries to diesel prices
        api_cache: Optional cache dictionary

    Returns:
        float: Diesel price in USD/L
    """
    country = get_country_from_coords(lat, lon, api_cache)
    diesel_price = diesel_price_country_dict.get(country)
    return 4.0 if diesel_price is None else diesel_price
