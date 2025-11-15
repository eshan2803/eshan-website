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


# ===== PORT DETECTION =====

# Major global ports database with coordinates
MAJOR_PORTS = [
    # North America - Pacific
    {'name': 'Los Angeles', 'lat': 33.7405, 'lon': -118.2713, 'country': 'USA'},
    {'name': 'Long Beach', 'lat': 33.7630, 'lon': -118.1926, 'country': 'USA'},
    {'name': 'Oakland', 'lat': 37.7964, 'lon': -122.2803, 'country': 'USA'},
    {'name': 'Seattle', 'lat': 47.6062, 'lon': -122.3321, 'country': 'USA'},
    {'name': 'Vancouver', 'lat': 49.2827, 'lon': -123.1207, 'country': 'Canada'},

    # North America - Gulf/Atlantic
    {'name': 'Houston', 'lat': 29.7604, 'lon': -95.3698, 'country': 'USA'},
    {'name': 'New Orleans', 'lat': 29.9511, 'lon': -90.0715, 'country': 'USA'},
    {'name': 'New York', 'lat': 40.7128, 'lon': -74.0060, 'country': 'USA'},
    {'name': 'Savannah', 'lat': 32.0809, 'lon': -81.0912, 'country': 'USA'},
    {'name': 'Charleston', 'lat': 32.7765, 'lon': -79.9311, 'country': 'USA'},

    # Europe - North
    {'name': 'Rotterdam', 'lat': 51.9225, 'lon': 4.4792, 'country': 'Netherlands'},
    {'name': 'Antwerp', 'lat': 51.2194, 'lon': 4.4025, 'country': 'Belgium'},
    {'name': 'Hamburg', 'lat': 53.5511, 'lon': 9.9937, 'country': 'Germany'},
    {'name': 'Amsterdam', 'lat': 52.3676, 'lon': 4.9041, 'country': 'Netherlands'},
    {'name': 'Bremen', 'lat': 53.0793, 'lon': 8.8017, 'country': 'Germany'},
    {'name': 'Le Havre', 'lat': 49.4944, 'lon': 0.1079, 'country': 'France'},

    # Europe - Mediterranean
    {'name': 'Barcelona', 'lat': 41.3851, 'lon': 2.1734, 'country': 'Spain'},
    {'name': 'Valencia', 'lat': 39.4699, 'lon': -0.3763, 'country': 'Spain'},
    {'name': 'Marseille', 'lat': 43.2965, 'lon': 5.3698, 'country': 'France'},
    {'name': 'Genoa', 'lat': 44.4056, 'lon': 8.9463, 'country': 'Italy'},
    {'name': 'Piraeus', 'lat': 37.9483, 'lon': 23.6292, 'country': 'Greece'},

    # Asia - East
    {'name': 'Shanghai', 'lat': 31.2304, 'lon': 121.4737, 'country': 'China'},
    {'name': 'Ningbo-Zhoushan', 'lat': 29.8683, 'lon': 121.544, 'country': 'China'},
    {'name': 'Shenzhen', 'lat': 22.5431, 'lon': 114.0579, 'country': 'China'},
    {'name': 'Guangzhou', 'lat': 23.1291, 'lon': 113.2644, 'country': 'China'},
    {'name': 'Hong Kong', 'lat': 22.3193, 'lon': 114.1694, 'country': 'Hong Kong'},
    {'name': 'Busan', 'lat': 35.1796, 'lon': 129.0756, 'country': 'South Korea'},
    {'name': 'Tokyo', 'lat': 35.6762, 'lon': 139.6503, 'country': 'Japan'},
    {'name': 'Yokohama', 'lat': 35.4437, 'lon': 139.6380, 'country': 'Japan'},

    # Asia - Southeast
    {'name': 'Singapore', 'lat': 1.3521, 'lon': 103.8198, 'country': 'Singapore'},
    {'name': 'Port Klang', 'lat': 3.0045, 'lon': 101.3932, 'country': 'Malaysia'},
    {'name': 'Tanjung Pelepas', 'lat': 1.3667, 'lon': 103.5500, 'country': 'Malaysia'},
    {'name': 'Bangkok', 'lat': 13.7563, 'lon': 100.5018, 'country': 'Thailand'},
    {'name': 'Ho Chi Minh City', 'lat': 10.8231, 'lon': 106.6297, 'country': 'Vietnam'},
    {'name': 'Manila', 'lat': 14.5995, 'lon': 120.9842, 'country': 'Philippines'},

    # Asia - South
    {'name': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777, 'country': 'India'},
    {'name': 'Chennai', 'lat': 13.0827, 'lon': 80.2707, 'country': 'India'},
    {'name': 'Kolkata', 'lat': 22.5726, 'lon': 88.3639, 'country': 'India'},
    {'name': 'Karachi', 'lat': 24.8607, 'lon': 67.0011, 'country': 'Pakistan'},

    # Middle East
    {'name': 'Dubai', 'lat': 25.2048, 'lon': 55.2708, 'country': 'UAE'},
    {'name': 'Jebel Ali', 'lat': 25.0104, 'lon': 55.0622, 'country': 'UAE'},
    {'name': 'Doha', 'lat': 25.2854, 'lon': 51.5310, 'country': 'Qatar'},

    # South America
    {'name': 'Santos', 'lat': -23.9608, 'lon': -46.3333, 'country': 'Brazil'},
    {'name': 'Buenos Aires', 'lat': -34.6037, 'lon': -58.3816, 'country': 'Argentina'},
    {'name': 'Valparaiso', 'lat': -33.0472, 'lon': -71.6127, 'country': 'Chile'},
    {'name': 'Callao', 'lat': -12.0464, 'lon': -77.1428, 'country': 'Peru'},

    # Africa
    {'name': 'Cape Town', 'lat': -33.9249, 'lon': 18.4241, 'country': 'South Africa'},
    {'name': 'Durban', 'lat': -29.8587, 'lon': 31.0218, 'country': 'South Africa'},
    {'name': 'Lagos', 'lat': 6.5244, 'lon': 3.3792, 'country': 'Nigeria'},
    {'name': 'Mombasa', 'lat': -4.0435, 'lon': 39.6682, 'country': 'Kenya'},

    # Oceania
    {'name': 'Sydney', 'lat': -33.8688, 'lon': 151.2093, 'country': 'Australia'},
    {'name': 'Melbourne', 'lat': -37.8136, 'lon': 144.9631, 'country': 'Australia'},
    {'name': 'Brisbane', 'lat': -27.4698, 'lon': 153.0251, 'country': 'Australia'},
    {'name': 'Auckland', 'lat': -36.8485, 'lon': 174.7633, 'country': 'New Zealand'},
]


def is_location_near_port(lat, lon, max_distance_km=50):
    """
    Check if a location is near a major port.

    Args:
        lat: Latitude of location
        lon: Longitude of location
        max_distance_km: Maximum distance in km to consider as "near" (default 50km)

    Returns:
        dict: {'is_port': bool, 'port_name': str or None, 'distance_km': float or None}
    """
    closest_port = None
    min_distance = float('inf')

    for port in MAJOR_PORTS:
        # Calculate distance using great circle formula
        distance = straight_dis(lon, lat, port['lon'], port['lat'])

        if distance < min_distance:
            min_distance = distance
            closest_port = port

    is_port = min_distance <= max_distance_km

    return {
        'is_port': is_port,
        'port_name': closest_port['name'] if is_port else None,
        'distance_km': min_distance if is_port else None,
        'closest_port_info': closest_port if is_port else None
    }
