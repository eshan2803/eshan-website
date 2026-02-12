"""
async_api_client.py
Asynchronous API client for parallel API calls to improve performance.
Uses aiohttp for non-blocking HTTP requests.
"""

import asyncio
import aiohttp
import json
from urllib.parse import urlencode
from constants import (
    API_KEY_GOOGLE,
    API_KEY_OPENAI,
    API_KEY_WEATHER,
    API_KEY_ELECTRICITYMAP
)


async def fetch_geocode(session, address):
    """
    Fetch geocode (lat, lng, state) for an address using Google Maps Geocoding API.

    Args:
        session: aiohttp ClientSession
        address: Address string to geocode

    Returns:
        tuple: (latitude, longitude, state_name) or (None, None, None) if failed
    """
    endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': address, 'key': API_KEY_GOOGLE}
    url = f'{endpoint}?{urlencode(params)}'

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status not in range(200, 299):
                return (None, None, None)

            data = await response.json()
            if not data.get('results'):
                return (None, None, None)

            latlng = data['results'][0]['geometry']['location']
            state_name = next(
                (comp['long_name'] for comp in data['results'][0]['address_components']
                 if 'administrative_area_level_1' in comp['types']),
                None
            )

            return (latlng.get("lat"), latlng.get("lng"), state_name)
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError) as e:
        print(f"Geocoding error for {address}: {e}")
        return (None, None, None)


async def fetch_inland_route(session, start_coords, end_coords):
    """
    Fetch inland route distance and duration using Google Distance Matrix API.

    Args:
        session: aiohttp ClientSession
        start_coords: tuple of (lat, lng)
        end_coords: tuple of (lat, lng)

    Returns:
        tuple: (distance_text, duration_text) or (None, None) if failed
    """
    endpoint = 'https://maps.googleapis.com/maps/api/distancematrix/json'
    params = {
        "origins": f"{start_coords[0]},{start_coords[1]}",
        "destinations": f"{end_coords[0]},{end_coords[1]}",
        "key": API_KEY_GOOGLE
    }
    url = f'{endpoint}?{urlencode(params)}'

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status not in range(200, 299):
                return (None, None)

            data = await response.json()
            if (data.get('rows') and data['rows'][0].get('elements') and
                data['rows'][0]['elements'][0].get('distance')):
                distance_text = data['rows'][0]['elements'][0]['distance']['text']
                duration_text = data['rows'][0]['elements'][0]['duration']['text']
                return (distance_text, duration_text)

            return (None, None)
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError) as e:
        print(f"Inland route error: {e}")
        return (None, None)


async def fetch_nearest_port(session, lat, lng, port_type="start"):
    """
    Fetch nearest port using OpenAI GPT-4.

    Args:
        session: aiohttp ClientSession
        lat: Latitude
        lng: Longitude
        port_type: "start" or "end" for logging

    Returns:
        tuple: (port_lat, port_lng, port_name) or (None, None, None) if failed
    """
    from openai import AsyncOpenAI

    try:
        client = AsyncOpenAI(api_key=API_KEY_OPENAI)
        port_coor_str = f"{lat}, {lng}"

        response = await client.chat.completions.create(
            model="gpt-5.1",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return the nearest deep-water port for the given coordinates as JSON."},
                {"role": "user", "content": f'Given coordinates {port_coor_str}, return the nearest deep-water or deep-draft port in JSON format: {{"nearest_port": "PORT_NAME", "latitude": "LATITUDE", "longitude": "LONGITUDE"}}'}
            ],
            timeout=15.0
        )

        result = json.loads(response.choices[0].message.content)
        lat_str = result.get("latitude")
        lon_str = result.get("longitude")
        port_name = result.get("nearest_port")

        try:
            port_lat = float(str(lat_str).strip().replace(',', '')) if lat_str else None
            port_lon = float(str(lon_str).strip().replace(',', '')) if lon_str else None
        except ValueError:
            print(f"Could not convert port coordinates to float: {lat_str}, {lon_str}")
            return (None, None, None)

        return (port_lat, port_lon, port_name)
    except Exception as e:
        print(f"OpenAI port lookup error for {port_type}: {e}")
        return (None, None, None)


async def fetch_weather(session, lat, lng):
    """
    Fetch weather data for given coordinates.

    Args:
        session: aiohttp ClientSession
        lat: Latitude
        lng: Longitude

    Returns:
        dict: Weather data or None if failed
    """
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY_WEATHER}&q={lat},{lng}"

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                return await response.json()
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Weather API error: {e}")
        return None


async def fetch_carbon_intensity(session, lat, lng):
    """
    Fetch carbon intensity data from ElectricityMap.

    Args:
        session: aiohttp ClientSession
        lat: Latitude
        lng: Longitude

    Returns:
        dict: Carbon intensity data or None if failed
    """
    url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
    headers = {"auth-token": API_KEY_ELECTRICITYMAP}
    params = {"lat": lat, "lon": lng}

    try:
        async with session.get(url, headers=headers, params=params,
                             timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                return await response.json()
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"ElectricityMap API error: {e}")
        return None


async def fetch_all_initial_data(start_address, end_address):
    """
    Fetch all initial data in parallel (geocoding, ports, weather, etc.).

    This is the main entry point for parallel API calls.

    Args:
        start_address: Starting location address
        end_address: Ending location address

    Returns:
        dict: Dictionary containing all fetched data with keys:
            - start_geocode: (lat, lng, state)
            - end_geocode: (lat, lng, state)
            - start_port: (lat, lng, name)
            - end_port: (lat, lng, name)
            - inland_route_start: (distance, duration) - computed after geocoding
            - inland_route_end: (distance, duration) - computed after geocoding
            - start_weather: weather dict
            - end_weather: weather dict
            - start_carbon: carbon intensity dict
            - end_carbon: carbon intensity dict
    """
    async with aiohttp.ClientSession() as session:
        # Phase 1: Geocode start and end addresses (must complete first)
        geocode_tasks = [
            fetch_geocode(session, start_address),
            fetch_geocode(session, end_address)
        ]
        start_geocode, end_geocode = await asyncio.gather(*geocode_tasks)

        # Extract coordinates
        start_lat, start_lng, start_state = start_geocode
        end_lat, end_lng, end_state = end_geocode

        # Phase 2: All other API calls that depend on coordinates (parallel)
        tasks = []
        task_names = []

        if start_lat and start_lng:
            tasks.extend([
                fetch_nearest_port(session, start_lat, start_lng, "start"),
                fetch_weather(session, start_lat, start_lng),
                fetch_carbon_intensity(session, start_lat, start_lng)
            ])
            task_names.extend(["start_port", "start_weather", "start_carbon"])

        if end_lat and end_lng:
            tasks.extend([
                fetch_nearest_port(session, end_lat, end_lng, "end"),
                fetch_weather(session, end_lat, end_lng),
                fetch_carbon_intensity(session, end_lat, end_lng)
            ])
            task_names.extend(["end_port", "end_weather", "end_carbon"])

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks) if tasks else []

        # Build result dictionary
        result_dict = {
            "start_geocode": start_geocode,
            "end_geocode": end_geocode
        }

        for name, result in zip(task_names, results):
            result_dict[name] = result

        # Phase 3: Inland routes (need both geocodes and ports)
        # These depend on previous results, so run them after
        if start_lat and start_lng and "start_port" in result_dict:
            start_port = result_dict["start_port"]
            if start_port[0] and start_port[1]:
                result_dict["inland_route_start"] = await fetch_inland_route(
                    session, (start_lat, start_lng), (start_port[0], start_port[1])
                )
            else:
                result_dict["inland_route_start"] = (None, None)

        if end_lat and end_lng and "end_port" in result_dict:
            end_port = result_dict["end_port"]
            if end_port[0] and end_port[1]:
                result_dict["inland_route_end"] = await fetch_inland_route(
                    session, (end_port[0], end_port[1]), (end_lat, end_lng)
                )
            else:
                result_dict["inland_route_end"] = (None, None)

        return result_dict


def run_parallel_api_calls(start_address, end_address):
    """
    Synchronous wrapper to run parallel API calls.

    This function can be called from synchronous Flask code.

    Args:
        start_address: Starting location address
        end_address: Ending location address

    Returns:
        dict: All fetched API data
    """
    return asyncio.run(fetch_all_initial_data(start_address, end_address))
