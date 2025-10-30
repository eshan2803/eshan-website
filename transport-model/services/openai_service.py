"""
services/openai_service.py
OpenAI GPT-4 integration for port lookups and other AI services.
Extracted from app.py for better organization.
"""

import json
from openai import OpenAI
from constants import API_KEY_OPENAI


def openai_get_nearest_port(coordinates_str):
    """
    Use OpenAI GPT-4 to find the nearest deep-water port for given coordinates.

    Args:
        coordinates_str: String in format "lat, lng"

    Returns:
        tuple: (port_lat, port_lng, port_name) or (None, None, None) if failed
    """
    try:
        client = OpenAI(api_key=API_KEY_OPENAI)

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides information about ports. Return the nearest deep-water or deep-draft port for the given coordinates as JSON."
                },
                {
                    "role": "user",
                    "content": f'Given coordinates {coordinates_str}, return the nearest deep-water or deep-draft port in JSON format: {{"nearest_port": "PORT_NAME", "latitude": "LATITUDE", "longitude": "LONGITUDE"}}'
                }
            ],
            timeout=15.0
        )

        result = json.loads(response.choices[0].message.content)

        lat_str = result.get("latitude")
        lon_str = result.get("longitude")
        port_name = result.get("nearest_port")

        # Convert to float
        try:
            port_lat = float(str(lat_str).strip().replace(',', '')) if lat_str else None
            port_lon = float(str(lon_str).strip().replace(',', '')) if lon_str else None
        except ValueError:
            print(f"Could not convert port coordinates to float: {lat_str}, {lon_str}")
            return (None, None, None)

        return (port_lat, port_lon, port_name)

    except Exception as e:
        print(f"Error in OpenAI port lookup: {e}")
        return (None, None, None)


def openai_get_hydrogen_production_cost(location):
    """
    Use OpenAI to estimate hydrogen production cost for a location.

    Args:
        location: Location string (city, state/country)

    Returns:
        float: Estimated hydrogen production cost in $/kg or None if failed
    """
    try:
        client = OpenAI(api_key=API_KEY_OPENAI)

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in hydrogen economics. Provide realistic hydrogen production cost estimates based on location, considering electricity costs, renewable energy availability, and industrial infrastructure."
                },
                {
                    "role": "user",
                    "content": f'Estimate the current green hydrogen production cost in {location} in USD per kg. Consider local electricity prices and renewable energy resources. Return JSON: {{"production_cost_usd_per_kg": <number>, "explanation": "<brief explanation>"}}'
                }
            ],
            timeout=15.0
        )

        result = json.loads(response.choices[0].message.content)
        cost = result.get("production_cost_usd_per_kg")

        if cost:
            return float(cost)
        return None

    except Exception as e:
        print(f"Error in OpenAI hydrogen cost lookup: {e}")
        return None


# ===== Additional OpenAI Functions =====

def openai_get_electricity_price(coords_str, api_cache=None):
    """
    Get electricity price for given coordinates using OpenAI.

    Args:
        coords_str: Coordinates as "lat,lng" string
        api_cache: Optional cache dictionary

    Returns:
        tuple: (lat, lng, price_per_mj)
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"electricity_price_{coords_str}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        client = OpenAI(api_key=API_KEY_OPENAI)
        default_price_mj = 0.03

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": "Retrieve the latest average electricity price for the given coordinates, preferring commercial rates. Convert kWh to MJ and return in JSON format."},
                {"role": "user", "content": f'Given coordinates {coords_str}, return the electricity pricing information in JSON format: {{"average_price_kwh": PRICE_IN_USD_PER_KWH, "average_price_mj": PRICE_IN_USD_PER_MJ, "country": "COUNTRY_NAME_HERE", "latitude": LATITUDE, "longitude": LONGITUDE}}'},
            ],
            timeout=15.0
        )

        result = json.loads(response.choices[0].message.content)
        price_mj = result.get("average_price_mj")
        lat = result.get("latitude")
        lon = result.get("longitude")

        if price_mj is not None:
            cached_value = (lat, lon, float(price_mj))
        else:
            cached_value = (lat, lon, default_price_mj)

        api_cache[cache_key] = cached_value
        return cached_value

    except Exception as e:
        print(f"OpenAI Electricity Price API error for {coords_str}: {e}")
        coords = [float(c) for c in coords_str.split(',')]
        cached_value = (coords[0], coords[1], 0.03)
        api_cache[cache_key] = cached_value
        return cached_value


def openai_get_hydrogen_cost(coords_str, api_cache=None):
    """
    Get hydrogen production cost for given coordinates using OpenAI.

    Args:
        coords_str: Coordinates as "lat,lng" string
        api_cache: Optional cache dictionary

    Returns:
        tuple: (coords_str, price_usd_per_kg)
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"hydrogen_cost_{coords_str}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        client = OpenAI(api_key=API_KEY_OPENAI)
        default_price_usd_per_kg = 6.5

        prompt = f"""
        You are an expert in hydrogen markets. Provide the latest delivered hydrogen cost in USD per kilogram (USD/kg) for the location specified by the coordinates {coords_str} (latitude, longitude). The cost should include production, compression, storage, and distribution expenses, as relevant for transportation applications (e.g., fuel cell vehicles). Return only the price in USD/kg as a float, without additional text or explanation. If you cannot provide a specific numerical price, return the string "N/A".
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise data retrieval assistant for hydrogen market prices. Return only a float or 'N/A'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3,
            timeout=15.0
        )

        price_str = response.choices[0].message.content.strip()

        try:
            price = float(price_str)
        except ValueError:
            print(f"DEBUG: OpenAI returned non-numeric value for hydrogen cost: '{price_str}'. Using default.")
            price = default_price_usd_per_kg

        cached_value = (coords_str, price)
        api_cache[cache_key] = cached_value
        return cached_value

    except Exception as e:
        print(f"OpenAI Hydrogen Cost API error for {coords_str}: {e}")
        cached_value = (coords_str, 6.5)
        api_cache[cache_key] = cached_value
        return cached_value


def openai_get_marine_fuel_price(fuel_name, port_coords_tuple, port_name_str, api_cache=None):
    """
    Get marine fuel price at specific port using OpenAI.

    Args:
        fuel_name: Name of fuel (VLSFO, LNG, Methanol, Ammonia)
        port_coords_tuple: (lat, lng) tuple
        port_name_str: Port name string
        api_cache: Optional cache dictionary

    Returns:
        tuple: (port_name, price_usd_per_mt)
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"marine_fuel_price_{fuel_name}_{port_coords_tuple[0]}_{port_coords_tuple[1]}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        client = OpenAI(api_key=API_KEY_OPENAI)
        default_prices = {'VLSFO': 650.0, 'LNG': 550.0, 'Methanol': 700.0, 'Ammonia': 800.0}
        default_price_usd_per_mt = default_prices.get(fuel_name, 650.0)

        prompt = f"""
        You are an expert in marine fuel markets. Provide the latest bunker fuel price in USD per metric ton (USD/mt) for {fuel_name} at the port of {port_name_str} (coordinates: {port_coords_tuple[0]}, {port_coords_tuple[1]}). Return only the price in USD/mt as a float, without additional text or explanation. If you cannot provide a specific numerical price, return the string "N/A".
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise data retrieval assistant for marine fuel prices. Return only a float or 'N/A'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3,
            timeout=15.0
        )

        price_str = response.choices[0].message.content.strip()

        try:
            price = float(price_str)
        except ValueError:
            print(f"DEBUG: OpenAI returned non-numeric value for marine fuel price: '{price_str}'. Using default.")
            price = default_price_usd_per_mt

        cached_value = (port_name_str, price)
        api_cache[cache_key] = cached_value
        return cached_value
    except Exception as e:
        print(f"OpenAI Marine Fuel Price API error for {fuel_name} at {port_name_str}: {e}")
        cached_value = (port_name_str, default_prices.get(fuel_name, 650.0))
        api_cache[cache_key] = cached_value
        return cached_value


def openai_get_food_price(food_name, location_name, api_cache=None):
    """
    Get food commodity price at specific location using OpenAI.

    Args:
        food_name: Name of food commodity
        location_name: Location string
        api_cache: Optional cache dictionary

    Returns:
        float: Price in USD/kg or None if failed
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"food_price_{food_name}_{location_name}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        client = OpenAI(api_key=API_KEY_OPENAI)

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in agricultural commodity markets. Provide realistic wholesale prices."
                },
                {
                    "role": "user",
                    "content": f'What is the current wholesale price for {food_name} at {location_name} in USD per kg? Return JSON: {{"price_usd_per_kg": <number>, "explanation": "<brief explanation>"}}'
                }
            ],
            timeout=15.0
        )

        result = json.loads(response.choices[0].message.content)
        price = result.get("price_usd_per_kg")

        if price:
            price_float = float(price)
            api_cache[cache_key] = price_float
            return price_float

        api_cache[cache_key] = None
        return None

    except Exception as e:
        print(f"OpenAI Food Price API error for {food_name} at {location_name}: {e}")
        api_cache[cache_key] = None
        return None


def openai_get_nearest_farm_region(food_name, location_name, api_cache=None):
    """
    Get nearest farming region for specific food using OpenAI.

    Args:
        food_name: Name of food commodity
        location_name: Location string
        api_cache: Optional cache dictionary

    Returns:
        dict: Dictionary with 'farm_region_name', 'latitude', 'longitude' or None if failed
    """
    if api_cache is None:
        api_cache = {}

    cache_key = f"farm_region_{food_name}_{location_name}"
    if cache_key in api_cache:
        return api_cache[cache_key]

    try:
        client = OpenAI(api_key=API_KEY_OPENAI)

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in agricultural logistics and supply chains. Your task is to identify a major commercial producing region for a specific food item that is as close as possible to a target destination city. Return the name of this region and its representative geographic coordinates as a JSON object. If the destination is itself a major producer, use a location within that region. If no significant commercial production exists nearby, return null for all fields."
                },
                {
                    "role": "user",
                    "content": f'For the food item \'{food_name}\', find the nearest major commercial farming region to the destination \'{location_name}\'. Return the result in the following JSON format: {{"farm_region_name": "NAME_OF_REGION", "latitude": LATITUDE_FLOAT, "longitude": LONGITUDE_FLOAT}}'
                }
            ],
            timeout=15.0
        )

        result = json.loads(response.choices[0].message.content)

        # Validate that we have all required fields and correct types
        farm_region_name = result.get("farm_region_name")
        latitude = result.get("latitude")
        longitude = result.get("longitude")

        if farm_region_name and latitude is not None and longitude is not None:
            # Try to convert lat/lon to float if they're strings
            try:
                farm_result = {
                    'farm_region_name': str(farm_region_name),
                    'latitude': float(latitude),
                    'longitude': float(longitude)
                }
                api_cache[cache_key] = farm_result
                return farm_result
            except (ValueError, TypeError) as e:
                print(f"Error converting coordinates to float for {food_name} near {location_name}: {e}")
                api_cache[cache_key] = None
                return None
        else:
            # Missing required fields
            api_cache[cache_key] = None
            return None

    except Exception as e:
        print(f"AI farm region lookup failed for {food_name} near {location_name}: {e}")
        api_cache[cache_key] = None
        return None
