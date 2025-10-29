"""
services/geocoding.py
Geocoding services using Google Maps API and reverse geocoding.
Extracted from app.py for better organization.
"""

import requests
from constants import API_KEY_GOOGLE


def get_country_from_coords(lat, lon):
    """
    Get country name from coordinates using reverse geocoding.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        str: Country name or "Unknown" if not found
    """
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={API_KEY_GOOGLE}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return "Unknown"

        data = response.json()
        if not data.get('results'):
            return "Unknown"

        # Extract country from address components
        for component in data['results'][0].get('address_components', []):
            if 'country' in component.get('types', []):
                return component.get('long_name', 'Unknown')

        return "Unknown"
    except Exception as e:
        print(f"Error in reverse geocoding: {e}")
        return "Unknown"


def geocode_address(address):
    """
    Get coordinates and state from an address using Google Geocoding API.

    Args:
        address: Address string to geocode

    Returns:
        tuple: (latitude, longitude, state_name) or (None, None, None) if failed
    """
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={API_KEY_GOOGLE}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return (None, None, None)

        data = response.json()
        if not data.get('results'):
            return (None, None, None)

        # Extract coordinates
        location = data['results'][0]['geometry']['location']
        lat = location.get('lat')
        lng = location.get('lng')

        # Extract state/province
        state_name = None
        for component in data['results'][0].get('address_components', []):
            if 'administrative_area_level_1' in component.get('types', []):
                state_name = component.get('long_name')
                break

        return (lat, lng, state_name)
    except Exception as e:
        print(f"Error geocoding address '{address}': {e}")
        return (None, None, None)


def get_distance_duration_google(origin_coords, destination_coords):
    """
    Get distance and duration between two coordinates using Google Distance Matrix API.

    Args:
        origin_coords: tuple of (lat, lng) for origin
        destination_coords: tuple of (lat, lng) for destination

    Returns:
        tuple: (distance_text, duration_text) or (None, None) if failed
    """
    try:
        origin = f"{origin_coords[0]},{origin_coords[1]}"
        destination = f"{destination_coords[0]},{destination_coords[1]}"

        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&key={API_KEY_GOOGLE}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return (None, None)

        data = response.json()
        if (data.get('rows') and data['rows'][0].get('elements') and
            data['rows'][0]['elements'][0].get('status') == 'OK'):

            element = data['rows'][0]['elements'][0]
            distance_text = element['distance']['text']
            duration_text = element['duration']['text']

            return (distance_text, duration_text)

        return (None, None)
    except Exception as e:
        print(f"Error getting distance/duration: {e}")
        return (None, None)
