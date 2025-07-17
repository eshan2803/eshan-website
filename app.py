# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import math
import pandas as pd
import numpy as np
import searoute as sr
from scipy.optimize import minimize
import requests
from urllib.parse import urlencode
import re
import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app, resources={r"/calculate": {"origins": "https://eshansingh.xyz"}})

# --- API KEYS ---
api_key_google = os.environ.get("API_KEY_GOOGLE", "ESHAN_API_KEY_GOOGLE")
api_key_searoutes = os.environ.get("API_KEY_SEAROUTES", "ESHAN_API_KEY_SEAROUTES")
api_key_EIA = os.environ.get("API_KEY_EIA", "ESHAN_API_KEY_EIA")
api_key_weather = os.environ.get("API_KEY_WEATHER", "ESHAN_API_KEY_WEATHER")
api_key_openAI = os.environ.get("API_KEY_OPENAI", "ESHAN_API_KEY_OPENAI")
api_key_electricity_map = os.environ.get("API_KEY_ELECTRICITYMAP", "ESHAN_API_KEY_ELECTRICITYMAP")
HHV_diesel = 45.6
diesel_density = 3.22
CO2e_diesel = 10.21
VOYAGE_OVERHEADS_DATA = {
    'small':    {'daily_operating_cost_usd': 8500, 'daily_capital_cost_usd': 10000, 'port_fee_usd': 30000, 'suez_toll_per_gt_usd': 9.00, 'panama_toll_per_gt_usd': 9.00},
    'midsized': {'daily_operating_cost_usd': 15500, 'daily_capital_cost_usd': 20000, 'port_fee_usd': 50000, 'suez_toll_per_gt_usd': 8.50, 'panama_toll_per_gt_usd': 9.50},
    'standard': {'daily_operating_cost_usd': 22000, 'daily_capital_cost_usd': 35000, 'port_fee_usd': 60000, 'suez_toll_per_gt_usd': 8.00, 'panama_toll_per_gt_usd': 9.00},
    'q-flex':   {'daily_operating_cost_usd': 20000, 'daily_capital_cost_usd': 55000, 'port_fee_usd': 80000, 'suez_toll_per_gt_usd': 7.50, 'panama_toll_per_gt_usd': 8.00},
    'q-max':    {'daily_operating_cost_usd': 25000, 'daily_capital_cost_usd': 75000, 'port_fee_usd': 90000, 'suez_toll_per_gt_usd': 7.00, 'panama_toll_per_gt_usd': 7.50}
}
annual_working_days = 330
truck_capex_params = {
    0: {'cost_usd_per_truck': 1500000, 'useful_life_years': 10, 'annualization_factor': 0.15},
    1: {'cost_usd_per_truck': 800000,  'useful_life_years': 10, 'annualization_factor': 0.15},
    2: {'cost_usd_per_truck': 200000,  'useful_life_years': 10, 'annualization_factor': 0.15}
}
MAINTENANCE_COST_PER_KM_TRUCK = 0.05 # $/km
MAINTENANCE_COST_PER_KM_SHIP = 0.10 # $/km
INSURANCE_PERCENTAGE_OF_CARGO_VALUE = 1.0 # 1% (This seems to be a general default, not the nuanced one)
CARBON_TAX_PER_TON_CO2_DICT = {
    "Sweden": 144.62,          # 2025 rate from Tax Foundation
    "Switzerland": 136.04,     # 2025 rate from Tax Foundation
    "Liechtenstein": 136.04,   # 2025 rate from Tax Foundation
    "Poland": 0.10,            # 2025 rate from Tax Foundation
    "Ukraine": 0.73,           # 2025 rate from Tax Foundation
    "Norway": 107.78,          # 2024 rate from World Population Review
    "Finland": 100.02,         # 2024 rate from World Population Review
    "Netherlands": 71.51,      # 2024 rate from World Population Review
    "Portugal": 60.48,         # 2024 rate from World Population Review
    "Ireland": 60.22,          # 2024 rate from World Population Review
    "Luxembourg": 49.92,       # 2024 rate from World Population Review
    "Germany": 48.39,          # 2024 rate from World Population Review
    "Austria": 48.37,          # 2024 rate from World Population Review
    "France": 47.96,           # 2024 rate from World Population Review
    "Iceland": 36.51,          # 2024 rate from World Population Review
    "Denmark": 28.10,          # 2024 rate from World Population Review
    "United Kingdom": 22.62,   # 2024 rate from World Population Review
    "Slovenia": 18.60,         # 2024 rate from World Population Review
    "Spain": 16.13,            # 2024 rate from World Population Review
    "Latvia": 16.13,           # 2024 rate from World Population Review
    "Estonia": 2.18,           # 2024 rate from World Population Review
    "South Africa": 10.69,     # 2024 rate from World Population Review
    "Singapore": 19.55,        # 2024 rate from World Population Review
    "Uruguay": 167.00,         # 2024 rate from Statista
    "Japan": 2.65              # Rate from academic sources, stable since implementation
}

# List of current EU Member Countries (as of July 2025)
EU_MEMBER_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden"
]

# Insurance-related constants from app_food.py
BASE_PER_TRANSIT_INSURANCE_PERCENTAGE = 0.25  # 0.2% - 0.5%
MINIMUM_INSURANCE_PREMIUM_USD = 750           # $500 - $1,000
COMMODITY_RISK_FACTORS = {
    "Liquid Hydrogen": 1.5,
    "Ammonia": 1.2,
    "Methanol": 0.8,
    "Strawberry": 0.6,
    "Hass Avocado": 0.7,
    "Banana": 0.75,
}
ROUTE_RISK_ZONES = [
    {"name": "Gulf of Aden/Somali Basin", "bbox": {"lon_min": 42.5, "lat_min": 10.0, "lon_max": 55.0, "lat_max": 18.0}, "risk_multiplier": 2.5},
    {"name": "West African Coast", "bbox": {"lon_min": 0.0, "lat_min": 0.0, "lon_max": 15.0, "lat_max": 10.0}, "risk_multiplier": 1.8},
    {"name": "South China Sea", "bbox": {"lon_min": 105.0, "lat_min": 0.0, "lon_max": 120.0, "lat_max": 20.0}, "risk_multiplier": 1.3},
    {"name": "Hurricane Alley (Atlantic)", "bbox": {"lon_min": -95.0, "lat_min": 10.0, "lon_max": -40.0, "lat_max": 40.0}, "risk_multiplier": 1.15},
]


# ==============================================================================
# MAIN CALCULATION FUNCTION
# ==============================================================================
def run_lca_model(inputs):
    """
    This single function encapsulates all logic for both Fuel and Food pathways.
    All helper functions, parameters, and process steps are defined and called
    within this function to ensure correct variable scoping.
    """
    # =================================================================
    # <<<                       HELPER FUNCTIONS                    >>>
    # =================================================================
    final_energy_output_gj = 0.0 
    opex_per_kg_for_chart_idx = 0
    capex_per_kg_for_chart_idx = 0
    carbon_tax_per_kg_for_chart_idx = 0
    insurance_per_kg_for_chart_idx = 0
    eco2_per_kg_for_chart_idx = 0
    
    def extract_lat_long(address_or_postalcode):
        endpoint = f'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': address_or_postalcode, 'key': api_key_google}
        url = f'{endpoint}?{urlencode(params)}'
        r = requests.get(url)
        if r.status_code not in range(200, 299): return None, None, None
        data = r.json()
        if not data.get('results'): return None, None, None
        latlng = data['results'][0]['geometry']['location']
        state_name = next((comp['long_name'] for comp in data['results'][0]['address_components'] if 'administrative_area_level_1' in comp['types']), None)
        return latlng.get("lat"), latlng.get("lng"), state_name

    def decode_polyline(polyline_str):
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
                    if not byte >= 0x20: break
                change = ~(result >> 1) if result & 1 else (result >> 1)
                if unit == 'lat': lat_change = change
                else: lng_change = change
            lat += lat_change
            lng += lng_change
            coordinates.append((lat / 100000.0, lng / 100000.0))
        return coordinates

    def extract_route_coor(origin, destination):
        endpoint = "https://maps.googleapis.com/maps/api/directions/json"
        params = {'origin': f"{origin[0]},{origin[1]}", 'destination': f"{destination[0]},{destination[1]}", 'key': api_key_google, 'mode': 'driving'}
        response = requests.get(f'{endpoint}?{urlencode(params)}')
        if response.status_code not in range(200, 299) or not response.json().get('routes'):
            return []
        points = response.json()['routes'][0]['overview_polyline']['points']
        return decode_polyline(points)

    def openai_get_nearest_port(port_coor_str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        response = client.chat.completions.create(
            model="gpt-4o", response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return the nearest deep-water port for the given coordinates as JSON."},
                {"role": "user", "content": f'Given coordinates {port_coor_str}, return the nearest deep-water or deep-draft port in JSON format: {{"nearest_port": "PORT_NAME", "latitude": "LATITUDE", "longitude": "LONGITUDE"}}'}
            ]
        )
        result = json.loads(response.choices[0].message.content)
        lat_str = result.get("latitude")
        lon_str = result.get("longitude")
        port_name = result.get("nearest_port")

        lat = None
        lon = None

        try:
            if lat_str is not None:
                lat = float(str(lat_str).strip().replace(',', ''))
            if lon_str is not None:
                lon = float(str(lon_str).strip().replace(',', ''))
        except ValueError:
            print(f"DEBUG: Could not convert latitude '{lat_str}' or longitude '{lon_str}' to float.")
            return None, None, None
        return lat, lon, port_name

    def inland_routes_cal(start_coords, end_coords):
        endpoint = f'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {"origins": f"{start_coords[0]},{start_coords[1]}", "destinations": f"{end_coords[0]},{end_coords[1]}", "key": api_key_google}
        output = requests.get(f'{endpoint}?{urlencode(params)}').json()
        if output.get('rows') and output['rows'][0].get('elements') and output['rows'][0]['elements'][0].get('distance'):
            return output['rows'][0]['elements'][0]['distance']['text'], output['rows'][0]['elements'][0]['duration']['text']
        return "0 km", "0 min"

    def time_to_minutes(time_str):
        time_str = str(time_str)
        days = int(re.search(r'(\d+)\s*day', time_str).group(1)) * 1440 if re.search(r'(\d+)\s*day', time_str) else 0
        hours = int(re.search(r'(\d+)\s*h', time_str).group(1)) * 60 if re.search(r'(\d+)\s*h', time_str) else 0
        minutes = int(re.search(r'(\d+)\s*min', time_str).group(1)) if re.search(r'(\d+)\s*min', time_str) else 0
        return days + hours + minutes

    def local_temperature(lat, lon):
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key_weather}&q={lat},{lon}"
        response = requests.get(url)
        if response.status_code == 200: return response.json()['current']['temp_c']
        return 25.0

    def carbon_intensity(lat, lng):
        url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
        headers = {"auth-token": api_key_electricity_map}
        response = requests.get(url, headers=headers, params={"lat": lat, "lon": lng})
        if response.status_code == 200: return float(response.json()['carbonIntensity'])
        return 200.0

    def get_country_from_coords(lat, lon):
        url = (
            f"https://maps.googleapis.com/maps/api/geocode/json?"
            f"latlng={lat},{lon}&key={api_key_google}"
        )
        response = requests.get(url)
        if response.status_code != 200: raise Exception("Google Maps API error")
        data = response.json()
        if data['status'] != 'OK': raise Exception(f"Geocoding error: {data['status']}")
        for component in data['results'][0]['address_components']:
            if 'country' in component['types']: return component['long_name']
        return None

    def get_diesel_price(lat, lon, diesel_price_country_dict):
        country = get_country_from_coords(lat, lon)
        diesel_price = diesel_price_country_dict.get(country)
        return 4.0 if diesel_price is None else diesel_price

    def openai_get_electricity_price(coords_str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        default_price_mj = 0.03
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": "Retrieve the latest average electricity price for the given coordinates, preferring commercial rates. Convert kWh to MJ and return in JSON format."},
                    {"role": "user", "content": f"""Given coordinates {coords_str}, return the electricity pricing information in JSON format: {{"average_price_kwh": PRICE_IN_USD_PER_KWH, "average_price_mj": PRICE_IN_USD_PER_MJ, "country": "COUNTRY_NAME_HERE", "latitude": LATITUDE, "longitude": LONGITUDE}}"""},
                ]
            )
            result = json.loads(response.choices[0].message.content)
            price_mj = result.get("average_price_mj")
            if price_mj is not None:
                return result.get("latitude"), result.get("longitude"), float(price_mj)
            return result.get("latitude"), result.get("longitude"), default_price_mj
        except Exception:
            coords = coords_str.split(',')
            return float(coords[0]), float(coords[1]), default_price_mj

    def openai_get_hydrogen_cost(coords_str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        default_price_usd_per_kg = 6.5

        try:
            prompt = f"""
            You are an expert in hydrogen markets with access to real-time data as of June 27, 2025. Provide the latest delivered hydrogen cost in USD per kilogram (USD/kg) for the location specified by the coordinates {coords_str} (latitude, longitude). The cost should include production, compression, storage, and distribution expenses, as relevant for transportation applications (e.g., fuel cell vehicles). Use reliable sources such as S&P Global, IEA, Hydrogen Council, or Argus Media for current prices. If specific data for the location or delivered cost is unavailable, estimate the price based on regional or global averages for the most relevant hydrogen type (grey, blue, or green) and indicate the estimation basis. Return only the price in USD/kg as a float, without additional text or explanation.
            """

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise data retrieval assistant for hydrogen market prices."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )

            price = float(response.choices[0].message.content.strip())
            return coords_str, price
        except Exception:
            return coords_str, default_price_usd_per_kg

    def openai_get_marine_fuel_price(fuel_name, port_coords_tuple, port_name_str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        default_prices = {'VLSFO': 650.0, 'LNG': 550.0, 'Methanol': 700.0, 'Ammonia': 800.0}
        default_price_usd_per_mt = default_prices.get(fuel_name, 650.0)

        try:
            prompt = f"""
            You are an expert in marine fuel markets with access to real-time data as of June 27, 2025. Provide the latest bunker fuel price in USD per metric ton (USD/mt) for {fuel_name} at the port of {port_name_str} (coordinates: {port_coords_tuple[0]}, {port_coords_tuple[1]}). Use reliable sources such as Ship & Bunker, Argus Media, or S&P Global for current prices. If specific data for {port_name_str} or {fuel_name} is unavailable, estimate the price based on global averages or trends for similar ports and fuel types, and indicate the estimation basis. Return only the price in USD/mt as a float, without additional text or explanation.
            """
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise data retrieval assistant for marine fuel prices."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )

            price = float(response.choices[0].message.content.strip())
            return port_name_str, price
        except Exception:
            return port_name_str, default_price_usd_per_mt

    def calculate_ship_power_kw(ship_volume_m3):
        power_scaling_data = [(20000, 7000), (90000, 15000), (174000, 19900), (210000, 25000), (266000, 43540)]
        volumes_m3 = [p[0] for p in power_scaling_data]
        powers_kw = [p[1] for p in power_scaling_data]
        return np.interp(ship_volume_m3, volumes_m3, powers_kw)
    
    def calculate_route_risk_multiplier(searoute_coords, route_risk_zones):
        """
        Calculates a risk multiplier based on whether the marine route passes through high-risk zones.
        Args:
            searoute_coords (list of lists): List of [lat, lon] coordinates for the sea route.
            route_risk_zones (list of dicts): Global data structure defining risk zones.
        Returns:
            float: A multiplier >= 1.0.
        """
        max_risk_multiplier = 1.0

        for zone in route_risk_zones:
            bbox = zone["bbox"]
            for lat, lon in searoute_coords:
                if (bbox["lon_min"] <= lon <= bbox["lon_max"] and
                    bbox["lat_min"] <= lat <= bbox["lat_max"]):
                    max_risk_multiplier = max(max_risk_multiplier, zone["risk_multiplier"])
                    break
        return max_risk_multiplier    

    def calculate_total_insurance_cost(initial_cargo_value_usd, commodity_type_str, searoute_coords_list, port_to_port_duration_hrs):
        """
        Calculates the total insurance cost for a shipment, considering commodity risk, route risk,
        a base per-transit rate, and a minimum premium.
        Args:
            initial_cargo_value_usd (float): Total value of the cargo in USD.
            commodity_type_str (str): The name of the commodity (e.g., 'Liquid Hydrogen', 'Strawberry').
            searoute_coords_list (list of lists): List of [lat, lon] coordinates for the sea route.
                                                Pass [] if no marine transport.
            port_to_port_duration_hrs (float): Duration of the marine transport in hours.
                                                Pass 0 if no marine transport.
        Returns:
            float: Total insurance cost in USD.
        """
        # 1. Base Rate (per transit)
        base_rate_per_transit = BASE_PER_TRANSIT_INSURANCE_PERCENTAGE / 100.0 # Convert % to decimal

        # 2. Commodity Risk Adjustment
        # Use 1.0 as default if commodity type not found to avoid errors
        commodity_risk_factor = COMMODITY_RISK_FACTORS.get(commodity_type_str, 1.0)

        # 3. Route Risk Adjustment (applies only if there is a marine leg)
        route_risk_factor = 1.0
        if searoute_coords_list and port_to_port_duration_hrs > 0:
            route_risk_factor = calculate_route_risk_multiplier(searoute_coords_list, ROUTE_RISK_ZONES)

        # Combine factors for the adjusted effective per-transit rate
        # Note: Duration adjustment (prorating annual rate) is removed as per feedback.
        # The `base_rate_per_transit` is already designed for a single transit.
        adjusted_effective_rate = base_rate_per_transit * commodity_risk_factor * route_risk_factor

        # Calculate the insurance cost based on the adjusted rate and cargo value
        calculated_cost = initial_cargo_value_usd * adjusted_effective_rate

        # 4. Incorporate Minimum Premiums
        insurance_cost = max(calculated_cost, MINIMUM_INSURANCE_PREMIUM_USD)

        return insurance_cost

    def create_breakdown_chart(data, opex_col_idx, capex_col_idx, carbon_tax_col_idx, insurance_col_idx, title, x_label, overlay_text=None, is_emission_chart=False):
        try:
            if not data:
                print("Chart creation skipped: No data provided.")
                return ""
            labels = [row[0] for row in data]
            # Initialize lists for all component values
            opex_values = []
            capex_values = []
            carbon_tax_values = []
            insurance_values = []

            for row in data:
                try:
                    if is_emission_chart:
                        opex_values.append(float(row[opex_col_idx]))
                        capex_values.append(0.0)
                        carbon_tax_values.append(0.0)
                        insurance_values.append(0.0)
                    else:
                        opex_values.append(float(row[opex_col_idx]))
                        capex_values.append(float(row[capex_col_idx]))
                        carbon_tax_values.append(float(row[carbon_tax_col_idx]))
                        insurance_values.append(float(row[insurance_col_idx]))
                except (ValueError, TypeError, IndexError) as e:
                    print(f"DEBUG: Error processing row for chart '{title}': {row}. Error: {e}")
                    opex_values.append(0.0)
                    capex_values.append(0.0)
                    carbon_tax_values.append(0.0)
                    insurance_values.append(0.0)
                    print(f"Warning: Could not convert value to a number for chart '{title}'. Defaulting to 0.")

            plt.style.use('seaborn-v0_8-whitegrid')
            
            # Estimate text height to adjust figure size BEFORE creating the subplot
            extra_bottom_margin = 0.0 # Default no extra margin
            if overlay_text:
                num_lines = len(overlay_text.split('\n'))
                # A good rule of thumb for text height: 0.03-0.04 per line in figure coordinates
                extra_bottom_margin = 0.035 * num_lines + 0.05 # Add some padding

            # Adjust figure height based on labels count and potential overlay text
            fig_height_base = len(labels) * 0.5 # Base height for bars
            total_figure_height_inches = fig_height_base + (extra_bottom_margin * 10) # Convert normalized margin to inches for fig size
            # Ensure a minimum height if there are very few bars
            if total_figure_height_inches < 4:
                total_figure_height_inches = 4
            
            fig, ax = plt.subplots(figsize=(10, total_figure_height_inches))

            # Adjust subplot parameters to create space for the text at the bottom
            # This sets the margin within the figure for the main plot
            fig.subplots_adjust(bottom=extra_bottom_margin + 0.05) # Add a bit more margin to existing plot margin

            y_pos = np.arange(len(labels))

            if is_emission_chart:
                ax.barh(y_pos, opex_values, align='center', color='#4CAF50', edgecolor='black', label='Emissions')
            else:
                ax.barh(y_pos, insurance_values, align='center', color='#800080', edgecolor='black', label='Insurance')
                ax.barh(y_pos, opex_values, left=insurance_values, align='center', color='#8BC34A', edgecolor='black', label='OPEX')
                ax.barh(y_pos, capex_values, left=np.array(insurance_values) + np.array(opex_values), align='center', color='#4CAF50', edgecolor='black', label='CAPEX')
                ax.barh(y_pos, carbon_tax_values, left=np.array(insurance_values) + np.array(opex_values) + np.array(capex_values), align='center', color='#FFC107', edgecolor='black', label='Carbon Tax')

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=12)
            ax.invert_yaxis()
            ax.set_xlabel(x_label, fontsize=14, weight='bold')
            ax.set_title(title, fontsize=16, weight='bold', pad=20)

            for i in range(len(labels)):
                total_value = 0
                if is_emission_chart:
                    total_value = opex_values[i]
                else:
                    total_value = opex_values[i] + capex_values[i] + carbon_tax_values[i] + insurance_values[i]
                ax.text(total_value, i, f' {total_value:,.2f}', color='black', va='center', fontweight='bold')

            ax.legend(loc='lower right', fontsize=10)

            if overlay_text:
                # Place text using fig.text, relative to the figure's bottom margin
                # x=0.05 (5% from left), y=0.01 (1% from bottom, within the extended margin)
                fig.text(0.05, 0.01, overlay_text, # Coordinates are (x, y) relative to the figure
                         ha='left', va='bottom', size=10,
                         bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.6))
            
            # Use tight_layout, but apply it to the subplot area that fig.subplots_adjust defined.
            # No need for the `rect` parameter with fig.subplots_adjust handling margins.
            plt.tight_layout() # Just call it without rect

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

            return img_base64    
    
        except Exception as e:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"CRITICAL ERROR generating chart '{title}': {e}")
            import traceback
            traceback.print_exc()
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return ""
    # =================================================================
    # <<<                   FUEL PROCESS FUNCTIONS                  >>>
    # =================================================================

    def PH2_pressure_fnc(density): return density * 1.2
    def multistage_compress(pressure): return pressure * 0.05
    def kinematic_viscosity_PH2(pressure): return 1e-5 / (pressure/10)
    def solve_colebrook(Re, epsilon, D): return 0.02
    def PH2_transport_energy(L): return L * 0.001
    def PH2_density_fnc(pressure): return pressure / 1.2
    def straight_dis(coor_start_lang,coor_start_lat,coor_end_lang,coor_end_lat): return 1000
    def PH2_density_fnc_helper(pressure): return 0.25
    #actual process functions
    def liquification_data_fitting(H2_plant_capacity):
        x = H2_plant_capacity*(1000/24)
        y0, x0, A1, A2, A3, t1, t2, t3 = 37.76586, -11.05773, 6248.66187, 80.56526, 25.95391, 2.71336, 32.3875, 685.33284
        return y0 + A1*np.exp(-(x-x0)/t1) + A2*np.exp(-(x-x0)/t2) + A3*np.exp(-(x-x0)/t3)

    # UPDATED site_A_chem_production
    def site_A_chem_production(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (GWP_chem_list_arg, hydrogen_production_cost_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg, 
         selected_fuel_name_arg, searoute_coor_arg, port_to_port_duration_arg) = process_args_tuple # Added new args

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0
        insurance_cost = 0 # Initialize insurance_cost here

        cargo_value = A * hydrogen_production_cost_arg
        insurance_cost = calculate_total_insurance_cost(
            initial_cargo_value_usd=cargo_value,
            commodity_type_str=selected_fuel_name_arg,
            searoute_coords_list=searoute_coor_arg,
            port_to_port_duration_hrs=port_to_port_duration_arg
        )
        # We return insurance_cost separately, NOT adding to opex_money here.
        # This allows total_chem_base to create a distinct 'Insurance' line item.

        G_emission = 0 # No emissions in this production step for this model
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax 

        convert_energy_consumed = 0
        BOG_loss = 0

        # Return insurance_cost as a new, 8th element in the tuple
        return opex_money, capex_money, carbon_tax_money, convert_energy_consumed, G_emission, A, BOG_loss, insurance_cost
    
    def site_A_chem_liquification(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_specific_args_tuple):
        (LH2_plant_capacity_arg, EIM_liquefication_arg, specific_heat_chem_arg, 
        start_local_temperature_arg, boiling_point_chem_arg, latent_H_chem_arg, 
        COP_liq_arg, start_electricity_price_tuple_arg, CO2e_start_arg, 
        GWP_chem_list_arg, calculate_liquefaction_capex_helper_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_specific_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        if B_fuel_type == 0:  # LH2
            liquify_energy_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
        elif B_fuel_type == 1:  # Ammonia
            liquify_heat_required = specific_heat_chem_arg[B_fuel_type] * (start_local_temperature_arg + 273 - boiling_point_chem_arg[B_fuel_type]) + latent_H_chem_arg[B_fuel_type]
            liquify_energy_required = liquify_heat_required / COP_liq_arg[B_fuel_type]
        else:  # Methanol
            liquify_energy_required = 0

        liquify_ener_consumed = liquify_energy_required * A
        opex_money += liquify_ener_consumed * start_electricity_price_tuple_arg[2]
        
        # CAPEX
        capex_per_kg = calculate_liquefaction_capex_helper_arg(B_fuel_type, LH2_plant_capacity_arg) # Order matters here
        capex_money += capex_per_kg * A

        G_emission_from_energy = liquify_ener_consumed * 0.2778 * CO2e_start_arg * 0.001
        BOG_loss = 0.016 * A
        A_after_loss = A - BOG_loss
        G_emission_from_bog = BOG_loss * GWP_chem_list_arg[B_fuel_type]
        G_emission = G_emission_from_energy + G_emission_from_bog

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax
        return opex_money, capex_money, carbon_tax_money, liquify_ener_consumed, G_emission, A_after_loss, BOG_loss, 0 # Added 0 for insurance
    
    def fuel_pump_transfer(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (V_flowrate_arg, number_of_cryo_pump_load_arg, dBOR_dT_arg, 
        BOR_transfer_arg, liquid_chem_density_arg, head_pump_arg, 
        pump_power_factor_arg, EIM_cryo_pump_arg, ss_therm_cond_arg, 
        pipe_length_arg, pipe_inner_D_arg, pipe_thick_arg, COP_refrig_arg, 
        EIM_refrig_eff_arg, electricity_price_tuple_arg, CO2e_arg, 
        GWP_chem_list_arg, local_temperature_arg, calculate_loading_unloading_capex_helper_arg, 
        country_of_transfer_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_arg
        local_BOR_transfer = dBOR_dT_arg[B_fuel_type] * (local_temperature_arg - 25) + BOR_transfer_arg[B_fuel_type]
        BOG_loss = local_BOR_transfer * (1 / 24) * duration * A

        pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * \
                        head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100)
        ener_consumed_pumping = pumping_power * duration * 3600 * 1 / 1000000

        log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
        q_pipe = 0
        if log_arg > 0:
            q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * \
                    (local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))

        ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600

        ener_consumed = ener_consumed_pumping + ener_consumed_refrig
        A_after_loss = A - BOG_loss

        opex_money += ener_consumed * electricity_price_tuple_arg[2]
        
        # CAPEX
        capex_per_kg = calculate_loading_unloading_capex_helper_arg(B_fuel_type)
        capex_money += capex_per_kg * A

        G_emission = ener_consumed * 0.2778 * CO2e_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_transfer_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_after_loss, BOG_loss, 0 # Added 0 for insurance

    def fuel_road_transport(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (road_delivery_ener_arg, HHV_chem_arg, chem_in_truck_weight_arg, truck_economy_arg, 
        distance_arg, HHV_diesel_arg, diesel_density_arg, diesel_price_arg, 
        truck_tank_radius_arg, truck_tank_length_arg, truck_tank_metal_thickness_arg, 
        metal_thermal_conduct_arg, truck_tank_insulator_thickness_arg, insulator_thermal_conduct_arg, 
        OHTC_ship_arg, local_temperature_arg, COP_refrig_arg, EIM_refrig_eff_arg, 
        duration_arg, dBOR_dT_arg, BOR_truck_trans_arg, diesel_engine_eff_arg, 
        EIM_truck_eff_arg, CO2e_diesel_arg, GWP_chem_arg, 
        BOG_recirculation_truck_percentage_arg, LH2_plant_capacity_arg, EIM_liquefication_arg, 
        fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg, 
        driver_daily_salary_arg, annual_working_days_arg, maintenance_cost_per_km_truck_arg, 
        truck_capex_params_arg, country_of_road_transport_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable
        total_energy = 0

        number_of_trucks = math.ceil(A / chem_in_truck_weight_arg[B_fuel_type])
        
        trans_energy_required = number_of_trucks * distance_arg * HHV_diesel_arg * diesel_density_arg / truck_economy_arg[B_fuel_type]
        diesel_money = trans_energy_required / HHV_diesel_arg / diesel_density_arg * diesel_price_arg
        opex_money += diesel_money

        storage_area_truck = 2 * np.pi * truck_tank_radius_arg * truck_tank_length_arg
        if B_fuel_type == 0:
            thermal_resist = truck_tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                            truck_tank_insulator_thickness_arg / insulator_thermal_conduct_arg
            OHTC = 1 / thermal_resist if thermal_resist > 0 else float('inf')
        else:
            OHTC = OHTC_ship_arg[B_fuel_type]

        heat_required = OHTC * storage_area_truck * (local_temperature_arg + 273 - 20)
        refrig_ener_consumed = (heat_required / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * 60 * duration_arg * number_of_trucks

        local_BOR_truck_trans = dBOR_dT_arg[B_fuel_type] * (local_temperature_arg - 25) + BOR_truck_trans_arg[B_fuel_type]
        current_BOG_loss = A * local_BOR_truck_trans / (24 * 60) * duration_arg

        refrig_money = (refrig_ener_consumed / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / diesel_density_arg * diesel_price_arg
        opex_money += refrig_money
        total_energy = trans_energy_required + refrig_ener_consumed

        A_after_loss = A - current_BOG_loss
        G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
        G_emission = G_emission_energy + current_BOG_loss * GWP_chem_arg[B_fuel_type]
        net_BOG_loss = current_BOG_loss

        if C_recirculation_BOG == 2:
            if D_truck_apply == 1:
                usable_BOG = current_BOG_loss * BOG_recirculation_truck_percentage_arg * 0.01
                reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                reliq_ener_consumed = reliq_ener_required * usable_BOG

                total_energy += reliq_ener_consumed
                reliq_money = (reliq_ener_consumed / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / diesel_density_arg * diesel_price_arg
                opex_money += reliq_money

                A_after_loss += usable_BOG
                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
                G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
                G_emission = G_emission_energy + net_BOG_loss * GWP_chem_arg[B_fuel_type]

            elif D_truck_apply == 2:
                usable_BOG = current_BOG_loss * BOG_recirculation_truck_percentage_arg * 0.01
                usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]

                energy_saved_from_refrig = min(usable_ener, refrig_ener_consumed)
                money_saved_from_refrig = (energy_saved_from_refrig / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / diesel_density_arg * diesel_price_arg

                total_energy = trans_energy_required + (refrig_ener_consumed - energy_saved_from_refrig)
                opex_money = diesel_money + (refrig_money - money_saved_from_refrig)

                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
                G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
                G_emission = G_emission_energy + net_BOG_loss * GWP_chem_arg[B_fuel_type]

        # Driver salary cost
        trip_days = max(1, math.ceil(duration_arg / 1440))
        driver_cost_per_truck = (driver_daily_salary_arg / annual_working_days_arg) * trip_days
        total_driver_cost = driver_cost_per_truck * number_of_trucks
        opex_money += total_driver_cost

        # Maintenance and Repair Cost
        maintenance_cost = maintenance_cost_per_km_truck_arg * distance_arg * number_of_trucks
        opex_money += maintenance_cost

        # Truck CAPEX
        annual_truck_cost_usd = truck_capex_params_arg[B_fuel_type]['cost_usd_per_truck'] * truck_capex_params_arg[B_fuel_type]['annualization_factor']
        capex_per_truck_trip_usd = annual_truck_cost_usd / 330 # Assuming 330 annual trips
        capex_money += capex_per_truck_trip_usd * number_of_trucks

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_road_transport_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, total_energy, G_emission, A_after_loss, net_BOG_loss, 0 # Added 0 for insurance

    def fuel_storage(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (liquid_chem_density_arg, storage_volume_arg, dBOR_dT_arg, local_temperature_arg, 
        BOR_land_storage_arg, storage_time_arg, storage_radius_arg, tank_metal_thickness_arg, 
        metal_thermal_conduct_arg, tank_insulator_thickness_arg, insulator_thermal_conduct_arg, 
        COP_refrig_arg, EIM_refrig_eff_arg, electricity_price_tuple_arg, CO2e_arg, 
        GWP_chem_list_arg, BOG_recirculation_storage_percentage_arg, 
        LH2_plant_capacity_arg, EIM_liquefication_arg, 
        fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg, calculate_storage_capex_helper_arg,
        country_of_storage_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable
        total_energy_consumed = 0

        number_of_storage = math.ceil(A / liquid_chem_density_arg[B_fuel_type] / storage_volume_arg[B_fuel_type])
        local_BOR_storage = dBOR_dT_arg[B_fuel_type] * (local_temperature_arg - 25) + BOR_land_storage_arg[B_fuel_type]
        current_BOG_loss = A * local_BOR_storage * storage_time_arg

        A_after_loss = A - current_BOG_loss

        storage_area_val = 4 * np.pi * (storage_radius_arg[B_fuel_type]**2) * number_of_storage

        thermal_resist_val = tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                            tank_insulator_thickness_arg / insulator_thermal_conduct_arg
        OHTC_val = 1 / thermal_resist_val if thermal_resist_val > 0 else float('inf')

        heat_required_val = OHTC_val * storage_area_val * (local_temperature_arg + 273 - 20)
        ener_consumed_refrig = (heat_required_val / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * 86400 * storage_time_arg

        opex_money += ener_consumed_refrig * electricity_price_tuple_arg[2]
        total_energy_consumed = ener_consumed_refrig
        
        # CAPEX
        capex_per_kg = calculate_storage_capex_helper_arg(B_fuel_type, LH2_plant_capacity_arg, A, storage_time_arg)
        capex_money += capex_per_kg * A

        G_emission = total_energy_consumed * 0.2778 * CO2e_arg * 0.001 + current_BOG_loss * GWP_chem_list_arg[B_fuel_type]
        net_BOG_loss = current_BOG_loss

        if C_recirculation_BOG == 2:
            if E_storage_apply == 1:
                usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                reliq_ener_consumed = reliq_ener_required * usable_BOG

                total_energy_consumed += reliq_ener_consumed
                opex_money = total_energy_consumed * electricity_price_tuple_arg[2]

                A_after_loss += usable_BOG
                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)

                G_emission = total_energy_consumed * 0.2778 * CO2e_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]

            elif E_storage_apply == 2:
                usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]

                ener_consumed_refrig_original = ener_consumed_refrig
                ener_consumed_refrig -= usable_ener
                if ener_consumed_refrig < 0:
                    ener_consumed_refrig = 0

                total_energy_consumed = ener_consumed_refrig
                opex_money = total_energy_consumed * electricity_price_tuple_arg[2]

                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)

                G_emission = total_energy_consumed * 0.2778 * CO2e_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_storage_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss, 0 # Added 0 for insurance

    def chem_loading_to_ship(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (V_flowrate_arg, number_of_cryo_pump_load_ship_port_A_arg, dBOR_dT_arg,
        start_local_temperature_arg, BOR_loading_arg, liquid_chem_density_arg, head_pump_arg,
        pump_power_factor_arg, EIM_cryo_pump_arg, ss_therm_cond_arg, pipe_length_arg, pipe_inner_D_arg,
        pipe_thick_arg, boiling_point_chem_arg, EIM_refrig_eff_arg, start_electricity_price_tuple_arg,
        CO2e_start_arg, GWP_chem_list_arg, calculated_storage_area_arg, ship_tank_metal_thickness,
        ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density,
        ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat,
        COP_cooldown_arg, COP_refrig_arg, ship_number_of_tanks_arg, pipe_metal_specific_heat_arg,
        calculate_loading_unloading_capex_helper_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_ship_port_A_arg
        local_BOR_loading_val = dBOR_dT_arg[B_fuel_type] * (start_local_temperature_arg - 25) + BOR_loading_arg[B_fuel_type]
        BOG_loss = local_BOR_loading_val * (1 / 24) * duration * A
        pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100)
        ener_consumed_pumping = pumping_power * duration * 3600 / 1000000

        log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
        q_pipe = 0
        if log_arg > 0:
            q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * (start_local_temperature_arg + 273.15 - boiling_point_chem_arg[B_fuel_type]) / (np.log(log_arg))

        ener_consumed_pipe_refrig = 0
        pipe_refrig_cop = COP_refrig_arg[B_fuel_type]
        if pipe_refrig_cop > 0:
            ener_consumed_pipe_refrig = (q_pipe / (pipe_refrig_cop * (EIM_refrig_eff_arg / 100))) / 1000000 * duration * 3600

        ener_consumed_cooldown = 0
        if B_fuel_type in [0, 1]:
            mass_metal = calculated_storage_area_arg * ship_tank_metal_thickness * ship_tank_metal_density * ship_number_of_tanks_arg
            mass_insulation = calculated_storage_area_arg * ship_tank_insulation_thickness[B_fuel_type] * ship_tank_insulation_density * ship_number_of_tanks_arg

            H_tank_metal = ship_tank_metal_specific_heat * mass_metal
            H_tank_insulation = ship_tank_insulation_specific_heat * mass_insulation

            delta_T = (start_local_temperature_arg + 273.15) - boiling_point_chem_arg[B_fuel_type]
            Q_cooling = (H_tank_metal + H_tank_insulation) * delta_T

            cooldown_cop = COP_cooldown_arg[B_fuel_type]
            if cooldown_cop > 0:
                ener_consumed_cooldown = Q_cooling / cooldown_cop

        ener_consumed_cooldown_pipes = 0
        if B_fuel_type in [0, 1]:
            pipe_outer_D = pipe_inner_D_arg + 2 * pipe_thick_arg
            pipe_metal_volume = (np.pi * (pipe_outer_D/2)**2 - np.pi * (pipe_inner_D_arg/2)**2) * pipe_length_arg

            pipe_metal_density = ship_tank_metal_density

            mass_metal_pipes = pipe_metal_volume * pipe_metal_density

            delta_T_pipes = (start_local_temperature_arg + 273.15) - boiling_point_chem_arg[B_fuel_type]

            Q_cooling_pipes = mass_metal_pipes * pipe_metal_specific_heat_arg * delta_T_pipes

            cooldown_cop_pipes = COP_cooldown_arg[B_fuel_type]
            if cooldown_cop_pipes > 0:
                ener_consumed_cooldown_pipes = Q_cooling_pipes / cooldown_cop_pipes

        ener_consumed = ener_consumed_pumping + ener_consumed_pipe_refrig + ener_consumed_cooldown + ener_consumed_cooldown_pipes
        A_after_loss = A - BOG_loss

        opex_money += ener_consumed * start_electricity_price_tuple_arg[2]
        
        # CAPEX
        capex_per_kg = calculate_loading_unloading_capex_helper_arg(B_fuel_type)
        capex_money += capex_per_kg * A

        G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_after_loss, BOG_loss, 0 # Added 0 for insurance

    def port_to_port(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (start_local_temperature_arg, end_local_temperature_arg, OHTC_ship_arg,
        calculated_storage_area_arg, ship_number_of_tanks_arg, COP_refrig_arg, EIM_refrig_eff_arg,
        port_to_port_duration_arg, selected_fuel_params_arg,
        dBOR_dT_arg, BOR_ship_trans_arg, GWP_chem_list_arg,
        BOG_recirculation_maritime_percentage_arg, LH2_plant_capacity_arg, EIM_liquefication_arg,
        fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg,
        avg_ship_power_kw_arg, aux_engine_efficiency_arg, GWP_N2O_arg,
        maintenance_cost_per_km_ship_arg, port_to_port_dis_arg, calculate_voyage_overheads_helper_arg,
        selected_ship_params_arg, canal_transits_arg, port_regions_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg,
        eu_member_countries_arg) = process_args_tuple # Added eu_member_countries_arg

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        propulsion_work_kwh = avg_ship_power_kw_arg * port_to_port_duration_arg

        T_avg = (start_local_temperature_arg + end_local_temperature_arg) / 2
        refrig_work_mj = 0
        if B_fuel_type == 0:
            heat_required_watts = OHTC_ship_arg[B_fuel_type] * calculated_storage_area_arg * (T_avg + 273 - 20) * ship_number_of_tanks_arg
            refrig_work_mj = (heat_required_watts / (COP_refrig_arg[B_fuel_type] * (EIM_refrig_eff_arg / 100))) / 1000000 * 3600 * port_to_port_duration_arg

        local_BOR_transportation = dBOR_dT_arg[B_fuel_type] * (T_avg - 25) + BOR_ship_trans_arg[B_fuel_type]
        current_BOG_loss = local_BOR_transportation * (1 / 24) * port_to_port_duration_arg * A

        net_BOG_loss = current_BOG_loss
        A_after_loss = A - current_BOG_loss
        reliq_work_mj = 0
        energy_saved_from_bog_mj = 0

        if C_recirculation_BOG == 2:
            usable_BOG = current_BOG_loss * (BOG_recirculation_maritime_percentage_arg / 100.0)
            net_BOG_loss -= usable_BOG
            if F_maritime_apply == 1:
                A_after_loss += usable_BOG
                reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                reliq_work_mj = reliq_ener_required * usable_BOG
            elif F_maritime_apply == 2:
                energy_saved_from_bog_mj = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]

        fuel_hhv_mj_per_kg = selected_fuel_params_arg['hhv_mj_per_kg']
        sfoc_g_per_kwh = selected_fuel_params_arg['sfoc_g_per_kwh']

        total_engine_work_mj = (propulsion_work_kwh * 3.6) + refrig_work_mj + reliq_work_mj - energy_saved_from_bog_mj
        if total_engine_work_mj < 0: total_engine_work_mj = 0

        total_engine_work_kwh = total_engine_work_mj / 3.6

        total_fuel_consumed_kg = (total_engine_work_kwh * sfoc_g_per_kwh) / 1000.0

        opex_money += (total_fuel_consumed_kg / 1000) * selected_fuel_params_arg['price_usd_per_ton']

        # Maintenance and Repair Cost
        maintenance_cost = maintenance_cost_per_km_ship_arg * port_to_port_dis_arg
        opex_money += maintenance_cost

        # Voyage CAPEX (from calculate_voyage_overheads)
        voyage_duration_days = port_to_port_duration_arg / 24.0
        voyage_capex_total = calculate_voyage_overheads_helper_arg(voyage_duration_days, selected_ship_params_arg, canal_transits_arg, port_regions_arg)
        capex_money += voyage_capex_total

        co2_factor = selected_fuel_params_arg['co2_emissions_factor_kg_per_kg_fuel']
        methane_factor = selected_fuel_params_arg['methane_slip_gwp100']
        fuel_emissions_co2e = (total_fuel_consumed_kg * co2_factor) + (total_fuel_consumed_kg * methane_factor)

        n2o_emissions_co2e = 0
        if 'n2o_emission_factor_g_per_kwh' in selected_fuel_params_arg:
            n2o_factor_g_kwh = selected_fuel_params_arg['n2o_emission_factor_g_per_kwh']
            n2o_emissions_kg = (total_engine_work_kwh * n2o_factor_g_kwh) / 1000
            n2o_emissions_co2e = n2o_emissions_kg * GWP_N2O_arg

        bog_emissions_co2e = net_BOG_loss * GWP_chem_list_arg[B_fuel_type]

        total_G_emission = fuel_emissions_co2e + bog_emissions_co2e + n2o_emissions_co2e

        # Carbon Tax (General)
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (total_G_emission / 1000)
        carbon_tax_money += carbon_tax

        # EU ETS Carbon Tax (if applicable)
        eu_ets_tax = 0
        if end_country_name_arg in eu_member_countries_arg:
            # As of 2025, 50% of emissions for inbound voyages are covered by EU ETS
            eu_ets_emissions_tons = (total_G_emission / 1000) * 0.50
            eu_ets_tax = eu_ets_emissions_tons * carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0)
            carbon_tax_money += eu_ets_tax # Add to carbon_tax_money

        total_energy_consumed_mj = total_fuel_consumed_kg * fuel_hhv_mj_per_kg
        return opex_money, capex_money, carbon_tax_money, total_energy_consumed_mj, total_G_emission, A_after_loss, net_BOG_loss, 0 # Added 0 for insurance

    def chem_convert_to_H2(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (mass_conversion_to_H2_arg, eff_energy_chem_to_H2_arg, energy_chem_to_H2_arg, 
        CO2e_end_arg, end_electricity_price_tuple_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable
        convert_energy = 0
        G_emission = 0
        BOG_loss = 0

        if B_fuel_type == 0:
            pass
        else:
            convert_to_H2_weight = A * mass_conversion_to_H2_arg[B_fuel_type]
            convert_energy = energy_chem_to_H2_arg[B_fuel_type] * A / eff_energy_chem_to_H2_arg[B_fuel_type]

            G_emission = convert_energy * 0.2778 * CO2e_end_arg * 0.001
            opex_money += convert_energy * end_electricity_price_tuple_arg[2]
            
            # Carbon Tax
            carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (G_emission / 1000)
            carbon_tax_money += carbon_tax

            A = convert_to_H2_weight

        return opex_money, capex_money, carbon_tax_money, convert_energy, G_emission, A, BOG_loss, 0 # Added 0 for insurance

    def PH2_pressurization_at_site_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (PH2_storage_V_arg, numbers_of_PH2_storage_at_start_arg, PH2_pressure_fnc_helper, 
        multistage_compress_helper, multistage_eff_arg, start_electricity_price_tuple_arg, 
        CO2e_start_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_start_arg)
        PH2_pressure = PH2_pressure_fnc_helper(PH2_density)

        compress_energy = multistage_compress_helper(PH2_pressure) * A / (multistage_eff_arg / 100)

        opex_money += start_electricity_price_tuple_arg[2] * compress_energy
        G_emission = compress_energy * 0.2778 * CO2e_start_arg * 0.001

        leak_loss = 0

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, compress_energy, G_emission, A, leak_loss, 0 # Added 0 for insurance

    def PH2_site_A_to_port_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (PH2_storage_V_arg, numbers_of_PH2_storage_at_start_arg, PH2_pressure_fnc_helper, 
        coor_start_lat_arg, coor_start_lng_arg, start_port_lat_arg, start_port_lng_arg, 
        straight_line_dis_helper, kinematic_viscosity_PH2_helper, compressor_velocity_arg, 
        pipeline_diameter_arg, solve_colebrook_helper, epsilon_arg, PH2_transport_energy_helper, 
        gas_chem_density_arg, numbers_of_PH2_storage_arg, start_electricity_price_tuple_arg, 
        CO2e_start_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_start_arg)
        PH2_pressure = PH2_pressure_fnc_helper(PH2_density)

        L_km = straight_line_dis_helper(coor_start_lat_arg, coor_start_lng_arg, start_port_lat_arg, start_port_lng_arg)
        L_meters = L_km * 1000

        kine_vis = kinematic_viscosity_PH2_helper(PH2_pressure)
        Re = compressor_velocity_arg * pipeline_diameter_arg / kine_vis
        f_D = solve_colebrook_helper(Re, epsilon_arg, pipeline_diameter_arg)

        P_drop_Pa = L_meters * f_D * PH2_density * (compressor_velocity_arg**2) / (2 * pipeline_diameter_arg)
        P_drop_bar = P_drop_Pa / 100000

        ener_consumed = PH2_transport_energy_helper(L_km) * A
        final_P_PH2 = PH2_pressure - P_drop_bar

        if final_P_PH2 < 0:
            final_P_PH2 = 0

        final_PH2_density = PH2_density_fnc_helper(final_P_PH2)
        A_final = final_PH2_density * PH2_storage_V_arg * numbers_of_PH2_storage_arg
        A_final = min(A, A_final) if final_P_PH2 > 0 else 0

        trans_loss = A - A_final
        if trans_loss < 0: trans_loss = 0

        opex_money += start_electricity_price_tuple_arg[2] * ener_consumed
        G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_final, trans_loss, 0 # Added 0 for insurance

    def port_A_liquification(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (liquification_data_fitting_helper, LH2_plant_capacity_arg, EIM_liquefication_arg, 
        start_port_electricity_price_tuple_arg, CO2e_start_arg, calculate_liquefaction_capex_helper_arg,
        start_port_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        if B_fuel_type != 0:
            return 0, 0, 0, 0, A, 0, 0, 0 # Added 0 for insurance

        LH2_energy_required = liquification_data_fitting_helper(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
        LH2_ener_consumed = LH2_energy_required * A

        opex_money += LH2_ener_consumed * start_port_electricity_price_tuple_arg[2]
        
        # CAPEX
        capex_per_kg = calculate_liquefaction_capex_helper_arg(B_fuel_type, LH2_plant_capacity_arg) # Order matters here
        capex_money += capex_per_kg * A

        G_emission = LH2_ener_consumed * 0.2778 * CO2e_start_arg * 0.001

        BOG_loss = 0.016 * A

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_port_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, LH2_ener_consumed, G_emission, A, BOG_loss, 0 # Added 0 for insurance

    def H2_pressurization_at_port_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (latent_H_H2_arg, specific_heat_H2_arg, PH2_storage_V_arg, 
        numbers_of_PH2_storage_arg, PH2_pressure_fnc_helper, multistage_compress_helper, 
        multistage_eff_arg, end_port_electricity_price_tuple_arg, CO2e_end_arg,
        end_port_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        if B_fuel_type != 0:
            return 0, 0, 0, 0, A, 0, 0, 0 # Added 0 for insurance

        Q_latent = latent_H_H2_arg * A
        Q_sensible = A * specific_heat_H2_arg * (300 - 20)

        PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_arg)
        PH2_pressure = PH2_pressure_fnc_helper(PH2_density)

        compress_energy = multistage_compress_helper(PH2_pressure) * A / (multistage_eff_arg / 100)

        total_energy_consumed = compress_energy + Q_latent + Q_sensible

        opex_money += end_port_electricity_price_tuple_arg[2] * total_energy_consumed
        G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001

        leak_loss = 0

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_port_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, total_energy_consumed, G_emission, A, leak_loss, 0 # Added 0 for insurance

    def PH2_port_B_to_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (PH2_density_fnc_helper, target_pressure_site_B_arg, PH2_storage_V_arg, 
        numbers_of_PH2_storage_at_port_B_arg, PH2_pressure_fnc_helper, 
        end_port_lat_arg, end_port_lng_arg, coor_end_lat_arg, coor_end_lng_arg, 
        straight_line_dis_helper, kinematic_viscosity_PH2_helper, compressor_velocity_arg, 
        pipeline_diameter_arg, solve_colebrook_helper, epsilon_arg, PH2_transport_energy_helper, 
        end_port_electricity_price_tuple_arg, CO2e_end_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        if B_fuel_type != 0:
            return 0, 0, 0, 0, A, 0, 0, 0 # Added 0 for insurance

        initial_PH2_density_at_port_B = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_port_B_arg)
        initial_PH2_pressure_at_port_B = PH2_pressure_fnc_helper(initial_PH2_density_at_port_B)

        L_km = straight_line_dis_helper(end_port_lat_arg, end_port_lng_arg, coor_end_lat_arg, coor_end_lng_arg)
        L_meters = L_km * 1000

        kine_vis = kinematic_viscosity_PH2_helper(initial_PH2_pressure_at_port_B)
        Re = compressor_velocity_arg * pipeline_diameter_arg / kine_vis
        f_D = solve_colebrook_helper(Re, epsilon_arg, pipeline_diameter_arg)

        P_drop_Pa = L_meters * f_D * initial_PH2_density_at_port_B * (compressor_velocity_arg**2) / (2 * pipeline_diameter_arg)
        P_drop_bar = P_drop_Pa / 100000

        ener_consumed = PH2_transport_energy_helper(L_km) * A

        final_P_PH2_at_site_B = initial_PH2_pressure_at_port_B - P_drop_bar

        if final_P_PH2_at_site_B < 0:
            final_P_PH2_at_site_B = 0

        A_final = A
        if final_P_PH2_at_site_B <= 0:
            A_final = 0

        trans_loss = A - A_final
        if trans_loss < 0: trans_loss = 0

        opex_money += end_port_electricity_price_tuple_arg[2] * ener_consumed
        G_emission = ener_consumed * 0.2778 * CO2e_end_arg * 0.001

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_final, trans_loss, 0 # Added 0 for insurance

    def PH2_storage_at_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        (PH2_storage_V_at_site_B_arg, numbers_of_PH2_storage_at_site_B_arg, PH2_pressure_fnc_helper,
        end_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        if B_fuel_type != 0:
            return 0, 0, 0, 0, A, 0, 0, 0 # Added 0 for insurance

        if PH2_storage_V_at_site_B_arg <= 0 or numbers_of_PH2_storage_at_site_B_arg <= 0:
            PH2_density = 0
            PH2_pressure = 0
        else:
            PH2_density = A / (PH2_storage_V_at_site_B_arg * numbers_of_PH2_storage_at_site_B_arg)
            PH2_pressure = PH2_pressure_fnc_helper(PH2_density)

        ener_consumed = 0
        G_emission = 0
        BOG_loss = 0

        # Carbon Tax (if any emissions from storage, though typically zero for PH2)
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A, BOG_loss, 0 # Added 0 for insurance

    def optimization_chem_weight(A_initial_guess, args_for_optimizer_tuple):
        user_define_params, process_funcs_for_optimization, all_shared_params_tuple = args_for_optimizer_tuple

        (LH2_plant_capacity_opt, EIM_liquefication_opt, specific_heat_chem,
        start_local_temperature_opt, boiling_point_chem, latent_H_chem,
        COP_liq, start_electricity_price_opt, CO2e_start_opt, GWP_chem,
        V_flowrate, number_of_cryo_pump_load_truck_site_A_opt,
        number_of_cryo_pump_load_storage_port_A_opt, number_of_cryo_pump_load_ship_port_A_opt,
        dBOR_dT, BOR_loading, BOR_unloading, head_pump_opt, pump_power_factor_opt,
        EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt,
        pipe_thick_opt, COP_refrig, EIM_refrig_eff_opt, pipe_metal_specific_heat, COP_cooldown,
        road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy,
        truck_tank_radius_opt, truck_tank_length_opt, truck_tank_metal_thickness_opt,
        metal_thermal_conduct_opt, truck_tank_insulator_thickness_opt, insulator_thermal_conduct_opt,
        OHTC_ship, BOR_truck_trans, HHV_diesel_opt, diesel_engine_eff_opt,
        EIM_truck_eff_opt, diesel_density_opt, CO2e_diesel_opt,
        BOG_recirculation_truck_opt, fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem,
        storage_time_A_opt, liquid_chem_density, storage_volume, storage_radius,
        BOR_land_storage, tank_metal_thickness_opt, tank_insulator_thickness_opt,
        BOG_recirculation_storage_opt, distance_A_to_port, duration_A_to_port,
        diesel_price_start_opt, driver_daily_salary_start_opt, annual_working_days_opt,
        calculate_liquefaction_capex_helper_opt, calculate_loading_unloading_capex_helper_opt,
        calculate_storage_capex_helper_opt, truck_capex_params_opt,
        maintenance_cost_per_km_truck_opt, maintenance_cost_per_km_ship_opt,
        hydrogen_production_cost_opt,
        start_country_name_opt, start_port_country_name_opt, carbon_tax_per_ton_co2_dict_opt, # This is carbon_tax_per_ton_co2_dict_opt
        port_regions_opt, selected_fuel_name_opt, searoute_coor_opt, port_to_port_duration_opt # Added new args
        ) = all_shared_params_tuple
        X = A_initial_guess[0]

        for func_entry in process_funcs_for_optimization:
            func_to_call = func_entry
            leg_type = None
            transfer_context = None
            storage_location_type = None

            if isinstance(func_entry, tuple):
                func_to_call, context_type = func_entry
                if func_to_call.__name__ == "fuel_road_transport":
                    leg_type = context_type
                elif func_to_call.__name__ == "fuel_pump_transfer":
                    transfer_context = context_type
                elif func_to_call.__name__ == "fuel_storage":
                    storage_location_type = context_type

            process_args_for_current_func = ()

            # UPDATED site_A_chem_production args for optimizer
            if func_to_call.__name__ == "site_A_chem_production":
                process_args_for_current_func = (
                    GWP_chem, hydrogen_production_cost_opt, start_country_name_opt, 
                    carbon_tax_per_ton_co2_dict_opt, selected_fuel_name_opt, 
                    searoute_coor_opt, port_to_port_duration_opt
                )

            elif func_to_call.__name__ == "site_A_chem_liquification":
                process_args_for_current_func = (
                    LH2_plant_capacity_opt, EIM_liquefication_opt, specific_heat_chem,
                    start_local_temperature_opt, boiling_point_chem, latent_H_chem,
                    COP_liq, start_electricity_price_opt, CO2e_start_opt, GWP_chem,
                    calculate_liquefaction_capex_helper_opt, start_country_name_opt, carbon_tax_per_ton_co2_dict_opt
                )

            elif func_to_call.__name__ == "fuel_pump_transfer":
                country_for_transfer = start_country_name_opt # Default for optimizer's scope
                if transfer_context == 'siteA_to_truck':
                    process_args_for_current_func = (
                        V_flowrate, number_of_cryo_pump_load_truck_site_A_opt,
                        dBOR_dT, BOR_loading,
                        liquid_chem_density, head_pump_opt, pump_power_factor_opt,
                        EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt,
                        pipe_inner_D_opt, pipe_thick_opt, COP_refrig, EIM_refrig_eff_opt,
                        start_electricity_price_opt, CO2e_start_opt, GWP_chem,
                        start_local_temperature_opt, calculate_loading_unloading_capex_helper_opt,
                        country_for_transfer, carbon_tax_per_ton_co2_dict_opt
                    )
                elif transfer_context == 'portA_to_storage':
                    country_for_transfer = start_port_country_name_opt
                    process_args_for_current_func = (
                        V_flowrate, number_of_cryo_pump_load_storage_port_A_opt,
                        dBOR_dT, BOR_unloading,
                        liquid_chem_density, head_pump_opt, pump_power_factor_opt,
                        EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt,
                        pipe_inner_D_opt, pipe_thick_opt, COP_refrig, EIM_refrig_eff_opt,
                        start_electricity_price_opt, CO2e_start_opt, GWP_chem,
                        start_local_temperature_opt, calculate_loading_unloading_capex_helper_opt,
                        country_for_transfer, carbon_tax_per_ton_co2_dict_opt
                    )
            elif func_to_call.__name__ == "fuel_road_transport":
                country_for_road = start_country_name_opt # Default for optimizer's scope
                process_args_for_current_func = (
                    road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy,
                    distance_A_to_port, HHV_diesel_opt, diesel_density_opt,
                    diesel_price_start_opt, truck_tank_radius_opt, truck_tank_length_opt,
                    truck_tank_metal_thickness_opt, metal_thermal_conduct_opt,
                    truck_tank_insulator_thickness_opt, insulator_thermal_conduct_opt,
                    OHTC_ship, start_local_temperature_opt, COP_refrig,
                    EIM_refrig_eff_opt, duration_A_to_port, dBOR_dT,
                    BOR_truck_trans, diesel_engine_eff_opt, EIM_truck_eff_opt,
                    CO2e_diesel_opt, GWP_chem,
                    BOG_recirculation_truck_opt,
                    LH2_plant_capacity_opt, EIM_liquefication_opt,
                    fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem,
                    driver_daily_salary_start_opt, annual_working_days_opt,
                    maintenance_cost_per_km_truck_opt, truck_capex_params_opt,
                    country_for_road, carbon_tax_per_ton_co2_dict_opt
                )

            elif func_to_call.__name__ == "fuel_storage":
                country_for_storage = start_port_country_name_opt # Default for optimizer's scope
                process_args_for_current_func = (
                    liquid_chem_density, storage_volume, dBOR_dT,
                    start_local_temperature_opt,
                    BOR_land_storage, storage_time_A_opt, storage_radius, tank_metal_thickness_opt,
                    metal_thermal_conduct_opt, tank_insulator_thickness_opt, insulator_thermal_conduct_opt,
                    COP_refrig, EIM_refrig_eff_opt, start_electricity_price_opt,
                    CO2e_start_opt, GWP_chem,
                    BOG_recirculation_storage_opt,
                    LH2_plant_capacity_opt, EIM_liquefication_opt,
                    fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem,
                    calculate_storage_capex_helper_opt, country_for_storage, carbon_tax_per_ton_co2_dict_opt
                )

            elif func_to_call.__name__ == "chem_loading_to_ship":
                process_args_for_current_func = (
                    V_flowrate, number_of_cryo_pump_load_ship_port_A_opt, dBOR_dT,
                    start_local_temperature_opt, BOR_loading, liquid_chem_density, head_pump_opt,
                    pump_power_factor_opt, EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt,
                    pipe_thick_opt, boiling_point_chem, EIM_refrig_eff_opt, start_electricity_price_opt,
                    CO2e_start_opt, GWP_chem, storage_area, ship_tank_metal_thickness,
                    ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density,
                    ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat,
                    COP_cooldown, COP_refrig, ship_number_of_tanks, pipe_metal_specific_heat,
                    calculate_loading_unloading_capex_helper_opt, start_country_name_opt, carbon_tax_per_ton_co2_dict_opt
                )
            
            # Call the current process function with its tailored arguments
            # Update the return signature of func_to_call to include carbon_tax_money and insurance_cost
            opex_m, capex_m, carbon_tax_m, Y_energy, Z_emission, X, S_bog_loss, insurance_m = func_to_call(X, # Added insurance_m
                                        user_define_params[1],
                                        user_define_params[2],
                                        user_define_params[3],
                                        user_define_params[4],
                                        user_define_params[5],
                                        process_args_for_current_func)

        return abs(X - target_weight)

    def constraint(A):
        """Ensures the optimized weight is not less than the target weight."""
        return A[0] - target_weight

    def calculate_liquefaction_capex(fuel_type, capacity_tpd): # Corrected order of arguments
        """
        Estimates the amortized capital cost per kg for liquefaction of hydrogen, ammonia, or methanol.
        Source: Based on industry data for hydrogen and ammonia liquefaction costs; methanol assumed zero.
        Parameters:
            fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol
            capacity_tpd: Daily throughput in tons
        Returns:
            Amortized CAPEX per kg in USD
        """
        cost_models = {
            0: {
                "small_scale": {"base_capex_M_usd": 138.6, "base_capacity": 27, "power_law_exp": 0.66},
                "large_scale": {"base_capex_M_usd": 762.67, "base_capacity": 800, "power_law_exp": 0.62}
            },
            1: {
                "default": {"base_capex_M_usd": 36.67, "base_capacity": 100, "power_law_exp": 0.7}
            },
            2: {
                "default": {"base_capex_M_usd": 0, "base_capacity": 1, "power_law_exp": 0}
            }
        }

        if fuel_type not in cost_models:
            return 0

        if fuel_type == 0:
            model = cost_models[0]["large_scale"] if capacity_tpd > 100 else cost_models[0]["small_scale"]
        else:
            model = cost_models[fuel_type]["default"]

        total_capex_usd = (model['base_capex_M_usd'] * 1000000) * (capacity_tpd / model['base_capacity']) ** model['power_law_exp']

        annualized_capex = total_capex_usd * 0.09

        annual_throughput_kg = capacity_tpd * 1000 * 330

        if annual_throughput_kg == 0:
            return 0

        capex_per_kg = annualized_capex / annual_throughput_kg
        return capex_per_kg

    def calculate_storage_capex(fuel_type, capacity_tpd, A, storage_days):
        """
        Estimates the amortized capital cost per kg for large-scale storage of hydrogen, ammonia, or methanol.
        Source: Based on industry data for cryogenic and chemical storage costs.
        Parameters:
            fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol
            capacity_tpd: Daily throughput in tons
            A: Storage capacity in kg
            storage_days: Average storage duration in days
        Returns:
            Amortized CAPEX per kg in USD
        """
        cost_models = {
            0: {
                "base_capex_M_usd": 35, "base_capacity": 335000, "power_law_exp": 0.7
            },
            1: {
                "base_capex_M_usd": 15, "base_capacity": 6650000, "power_law_exp": 0.7
            },
            2: {
                "default": {"base_capex_M_usd": 0, "base_capacity": 1, "power_law_exp": 0}
            }
        }

        if fuel_type not in cost_models:
            return 0

        model = cost_models[fuel_type]

        total_capex_usd = (model['base_capex_M_usd'] * 1000000) * (A / model['base_capacity']) ** model['power_law_exp']

        annualized_capex = total_capex_usd * 0.09

        if fuel_type in [0, 1]:
            if storage_days == 0:
                return 0
            cycles_per_year = 330 / storage_days
            annual_throughput_kg = A * cycles_per_year
        else:
            annual_throughput_kg = capacity_tpd * 1000 * 330

        if annual_throughput_kg == 0:
            return 0

        capex_per_kg = annualized_capex / annual_throughput_kg
        return capex_per_kg

    def calculate_loading_unloading_capex(fuel_type):
            """
            Estimates the amortized capital cost per kg for loading/unloading infrastructure (arms, jetties).
            Prorated based on assumed annual throughput of a typical terminal.
            Parameters:
                fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol
            Returns:
                Amortized CAPEX per kg of throughput (USD/kg).
            """
            capex_model = loading_unloading_capex_params.get(fuel_type)
            ref_throughput_tons_per_year = reference_annual_throughput_tons.get(fuel_type)

            if not capex_model or ref_throughput_tons_per_year == 0:
                return 0

            total_facility_capex_usd = capex_model['total_capex_M_usd'] * 1_000_000
            annualized_capex = total_facility_capex_usd * capex_model['annualization_factor']

            annual_throughput_kg = ref_throughput_tons_per_year * 1000

            capex_per_kg_throughput = annualized_capex / annual_throughput_kg if annual_throughput_kg > 0 else 0

            return capex_per_kg_throughput

    def calculate_voyage_overheads(voyage_duration_days, ship_params, canal_transits, port_regions):
        ship_gt = ship_params['gross_tonnage']
        overheads = VOYAGE_OVERHEADS_DATA.get(ship_params.get('key', 'standard'), VOYAGE_OVERHEADS_DATA['standard'])
        # 1. Daily Operating Cost (OPEX)
        opex_cost = overheads['daily_operating_cost_usd'] * voyage_duration_days
        # 2. Daily Capital Cost (CAPEX)
        capex_cost = overheads['daily_capital_cost_usd'] * voyage_duration_days
        # 3. Port Fees (assumed for 2 ports: origin and destination)
        port_fees_cost = overheads['port_fee_usd'] * 2
        # 4. Canal Transit Fees
        canal_fees_cost = 0
        if canal_transits.get("suez"):
            canal_fees_cost = ship_gt * overheads['suez_toll_per_gt_usd']
        elif canal_transits.get("panama"):
            canal_fees_cost = ship_gt * overheads['panama_toll_per_gt_usd']

        # 5. Total Overhead Calculation
        total_overheads = opex_cost + capex_cost + port_fees_cost + canal_fees_cost
        return total_overheads

    def total_chem_base(A_optimized_chem_weight, B_fuel_type_tc, C_recirculation_BOG_tc,
                        D_truck_apply_tc, E_storage_apply_tc, F_maritime_apply_tc, carbon_tax_per_ton_co2_dict_tc,
                        selected_fuel_name_tc, searoute_coor_tc, port_to_port_duration_tc): # Added new args

        funcs_sequence = [
            site_A_chem_production, site_A_chem_liquification,
            (fuel_pump_transfer, 'siteA_to_truck'),
            (fuel_road_transport, 'start_leg'),
            (fuel_pump_transfer, 'portA_to_storage'),
            (fuel_storage, 'port_A'),
            chem_loading_to_ship,
            port_to_port,
            (fuel_pump_transfer, 'ship_to_portB'),
            (fuel_storage, 'port_B'),
            (fuel_pump_transfer, 'portB_to_truck'),
            (fuel_road_transport, 'end_leg'),
            (fuel_pump_transfer, 'truck_to_siteB'),
            (fuel_storage, 'site_B'),
            (fuel_pump_transfer, 'siteB_to_use')
        ]

        R_current_chem = A_optimized_chem_weight
        data_results_list = []
        total_opex_money_tc = 0.0
        total_capex_money_tc = 0.0
        total_carbon_tax_money_tc = 0.0
        total_ener_consumed_tc = 0.0
        total_G_emission_tc = 0.0
        total_S_bog_loss_tc = 0.0
        total_insurance_money_tc = 0.0 # New total for insurance

        for func_entry in funcs_sequence:
            func_to_call = func_entry
            leg_type = None
            transfer_context = None
            storage_location_type = None

            if isinstance(func_entry, tuple):
                func_to_call, context_type = func_entry
                if func_to_call.__name__ == "fuel_road_transport":
                    leg_type = context_type
                elif func_to_call.__name__ == "fuel_pump_transfer":
                    transfer_context = context_type
                elif func_to_call.__name__ == "fuel_storage":
                    storage_location_type = context_type

            process_args_for_this_call_tc = ()
            # UPDATED process_args_for_this_call_tc for site_A_chem_production
            if func_to_call.__name__ == "site_A_chem_production":
                process_args_for_this_call_tc = (
                    GWP_chem, hydrogen_production_cost, start_country_name, carbon_tax_per_ton_co2_dict_tc,
                    selected_fuel_name_tc, searoute_coor_tc, port_to_port_duration_tc # Passed through total_chem_base
                )
            elif func_to_call.__name__ == "site_A_chem_liquification":
                process_args_for_this_call_tc = (LH2_plant_capacity, EIM_liquefication, specific_heat_chem, start_local_temperature, boiling_point_chem, latent_H_chem, COP_liq, start_electricity_price, CO2e_start, GWP_chem, calculate_liquefaction_capex, start_country_name, carbon_tax_per_ton_co2_dict_tc)
            elif func_to_call.__name__ == "fuel_pump_transfer":
                country_for_transfer = ""
                if transfer_context == 'siteA_to_truck':
                    country_for_transfer = start_country_name
                    process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_truck_site_A, dBOR_dT, BOR_loading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, start_local_temperature, calculate_loading_unloading_capex, country_for_transfer, carbon_tax_per_ton_co2_dict_tc)
                elif transfer_context == 'portA_to_storage':
                    country_for_transfer = start_port_country_name
                    process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_port_A, dBOR_dT, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, start_local_temperature, calculate_loading_unloading_capex, country_for_transfer, carbon_tax_per_ton_co2_dict_tc)
                elif transfer_context == 'ship_to_portB':
                    country_for_transfer = end_port_country_name
                    process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_port_B, dBOR_dT, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem, end_local_temperature, calculate_loading_unloading_capex, country_for_transfer, carbon_tax_per_ton_co2_dict_tc)
                elif transfer_context == 'portB_to_truck':
                    country_for_transfer = end_port_country_name
                    process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_truck_port_B, dBOR_dT, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem, end_local_temperature, calculate_loading_unloading_capex, country_for_transfer, carbon_tax_per_ton_co2_dict_tc)
                elif transfer_context == 'truck_to_siteB':
                    country_for_transfer = end_country_name
                    process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_site_B, dBOR_dT, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem, end_local_temperature, calculate_loading_unloading_capex, country_for_transfer, carbon_tax_per_ton_co2_dict_tc)
                elif transfer_context == 'siteB_to_use':
                    country_for_transfer = end_country_name
                    process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_site_B, dBOR_dT, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem, end_local_temperature, calculate_loading_unloading_capex, country_for_transfer, carbon_tax_per_ton_co2_dict_tc)

            elif func_to_call.__name__ == "fuel_road_transport":
                country_for_road = ""
                if leg_type == 'start_leg':
                    country_for_road = start_country_name
                    process_args_for_this_call_tc = (road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance_A_to_port, HHV_diesel, diesel_density, diesel_price_start, truck_tank_radius, truck_tank_length, truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness, insulator_thermal_conduct, OHTC_ship, start_local_temperature, COP_refrig, EIM_refrig_eff, duration_A_to_port, dBOR_dT, BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel, GWP_chem, BOG_recirculation_truck, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem, driver_daily_salary_start, annual_working_days, MAINTENANCE_COST_PER_KM_TRUCK, truck_capex_params, country_for_road, carbon_tax_per_ton_co2_dict_tc)
                elif leg_type == 'end_leg':
                    country_for_road = end_country_name
                    process_args_for_this_call_tc = (road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance_port_to_B, HHV_diesel, diesel_density, diesel_price_end, truck_tank_radius, truck_tank_length, truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness, insulator_thermal_conduct, OHTC_ship, end_local_temperature, COP_refrig, EIM_refrig_eff, duration_port_to_B, dBOR_dT, BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel, GWP_chem, BOG_recirculation_truck, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem, driver_daily_salary_end, annual_working_days, MAINTENANCE_COST_PER_KM_TRUCK, truck_capex_params, country_for_road, carbon_tax_per_ton_co2_dict_tc)

            elif func_to_call.__name__ == "fuel_storage":
                country_for_storage = ""
                if storage_location_type == 'port_A':
                    country_for_storage = start_port_country_name
                    process_args_for_this_call_tc = (
                        liquid_chem_density, storage_volume, dBOR_dT,
                        start_local_temperature,
                        BOR_land_storage, storage_time_A, storage_radius, tank_metal_thickness,
                        metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct,
                        COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start,
                        GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication,
                        fuel_cell_eff, EIM_fuel_cell, LHV_chem, calculate_storage_capex, country_for_storage, carbon_tax_per_ton_co2_dict_tc
                    )
                elif storage_location_type == 'port_B':
                    country_for_storage = end_port_country_name
                    process_args_for_this_call_tc = (
                        liquid_chem_density, storage_volume, dBOR_dT,
                        end_local_temperature,
                        BOR_land_storage, storage_time_B, storage_radius, tank_metal_thickness,
                        metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct,
                        COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end,
                        GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication,
                        fuel_cell_eff, EIM_fuel_cell, LHV_chem, calculate_storage_capex, country_for_storage, carbon_tax_per_ton_co2_dict_tc
                    )
                elif storage_location_type == 'site_B':
                    country_for_storage = end_country_name
                    process_args_for_this_call_tc = (
                        liquid_chem_density, storage_volume, dBOR_dT,
                        end_local_temperature,
                        BOR_land_storage, storage_time_C, storage_radius, tank_metal_thickness,
                        metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct,
                        COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end,
                        GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication,
                        fuel_cell_eff, EIM_fuel_cell, LHV_chem, calculate_storage_capex, country_for_storage, carbon_tax_per_ton_co2_dict_tc
                    )
            elif func_to_call.__name__ == "chem_loading_to_ship":
                process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_ship_port_A, dBOR_dT, start_local_temperature, BOR_loading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, boiling_point_chem, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, storage_area, ship_tank_metal_thickness, ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density, ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat, COP_cooldown, COP_refrig, ship_number_of_tanks, pipe_metal_specific_heat, calculate_loading_unloading_capex, start_country_name, carbon_tax_per_ton_co2_dict_tc)
            elif func_to_call.__name__ == "port_to_port":
                process_args_for_this_call_tc = (
                    start_local_temperature, end_local_temperature, OHTC_ship,
                    storage_area, ship_number_of_tanks, COP_refrig, EIM_refrig_eff,
                    port_to_port_duration, selected_marine_fuel_params,
                    dBOR_dT, BOR_ship_trans, GWP_chem,
                    BOG_recirculation_mati_trans, LH2_plant_capacity, EIM_liquefication,
                    fuel_cell_eff, EIM_fuel_cell, LHV_chem,
                    avg_ship_power_kw,
                    0.45,
                    GWP_N2O,
                    MAINTENANCE_COST_PER_KM_SHIP, port_to_port_dis, calculate_voyage_overheads,
                    selected_ship_params, canal_transits, port_regions, end_country_name, carbon_tax_per_ton_co2_dict_tc,
                    EU_MEMBER_COUNTRIES # Pass the EU member countries list here
                )
            elif func_to_call.__name__ == "chem_convert_to_H2":
                process_args_for_this_call_tc = (mass_conversion_to_H2, eff_energy_chem_to_H2, energy_chem_to_H2, CO2e_end, end_electricity_price, end_country_name, carbon_tax_per_ton_co2_dict_tc)

            # Updated call to function to receive carbon_tax_money AND insurance_money
            opex_money, capex_money, carbon_tax_money_current, Y_energy, Z_emission, R_current_chem, S_bog_loss, insurance_money_current = \
                func_to_call(R_current_chem, B_fuel_type_tc, C_recirculation_BOG_tc, D_truck_apply_tc,
                            E_storage_apply_tc, F_maritime_apply_tc, process_args_for_this_call_tc)
            
            # For the 'site_A_chem_production' step, we split out the insurance
            if func_to_call.__name__ == "site_A_chem_production":
                # Add a separate entry for insurance only
                data_results_list.append([
                    "Insurance", # Label for insurance
                    insurance_money_current, # Put the insurance cost in the OPEX slot for display/charting purposes
                    0.0, # Capex
                    0.0, # Carbon Tax
                    0.0, # Energy
                    0.0, # Emissions
                    R_current_chem, # Associate with current mass
                    0.0 # BOG Loss
                ])
                total_insurance_money_tc += insurance_money_current # Accumulate total insurance
                # Ensure the production step itself reports 0 for insurance in its row
                insurance_money_current = 0 # Reset for this specific row if it was production

            # Store the individual cost components in data_results_list (for this current step)
            data_results_list.append([
                func_to_call.__name__ + (f'_{leg_type}' if leg_type else '') + (f'_{transfer_context}' if transfer_context else '') + (f'_{storage_location_type}' if storage_location_type else ''),
                opex_money,
                capex_money,
                carbon_tax_money_current, # New column for carbon tax
                Y_energy,
                Z_emission,
                R_current_chem,
                S_bog_loss
            ])
            
            total_opex_money_tc += opex_money
            total_capex_money_tc += capex_money
            total_carbon_tax_money_tc += carbon_tax_money_current
            total_ener_consumed_tc += Y_energy
            total_G_emission_tc += Z_emission
            total_S_bog_loss_tc += S_bog_loss
        
        # Calculate final total money including all components
        final_total_money = total_opex_money_tc + total_capex_money_tc + total_carbon_tax_money_tc + total_insurance_money_tc
        final_total_result_tc = [final_total_money, total_ener_consumed_tc, total_G_emission_tc, R_current_chem]
        
        # Add the final TOTAL row, ensuring insurance is part of the overall sum
        data_results_list.append(["TOTAL", total_opex_money_tc, total_capex_money_tc, total_carbon_tax_money_tc, total_ener_consumed_tc, total_G_emission_tc, R_current_chem, total_S_bog_loss_tc])

        return final_total_result_tc, data_results_list

    # =================================================================
    # <<<                  FOOD PROCESSING FUNCTIONS                >>>
    # =================================================================

    # UPDATED food_harvest_and_prep
    def food_harvest_and_prep(A, args):
        (price_start_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg,
         food_name_arg, searoute_coor_arg, port_to_port_duration_arg) = args # Added new args
        
        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0
        energy = 0
        emissions = 0
        loss = 0
        insurance_cost = 0 # Initialize insurance_cost here

        cargo_value = A * price_start_arg
        insurance_cost = calculate_total_insurance_cost(
            initial_cargo_value_usd=cargo_value,
            commodity_type_str=food_name_arg,
            searoute_coords_list=searoute_coor_arg,
            port_to_port_duration_hrs=port_to_port_duration_arg
        )
        # We return insurance_cost separately, NOT adding to opex_money here.

        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (emissions / 1000)
        carbon_tax_money += carbon_tax

        # Return insurance_cost as a new, 8th element in the tuple
        return opex_money, capex_money, carbon_tax_money, energy, emissions, A - loss, loss, insurance_cost
    
    def food_freezing_process(A, args):
        params, start_temp, elec_price, co2_factor, facility_capacity_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg = args
        
        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        energy_sensible_heat1 = A * params['specific_heat_fresh_mj_kgK'] * (start_temp - 0)
        energy_latent_heat = A * params['latent_heat_fusion_mj_kg']
        energy_sensible_heat2 = A * params['specific_heat_frozen_mj_kgK'] * (0 - params['target_temp_celsius'])
        total_heat_to_remove = energy_sensible_heat1 + energy_latent_heat + energy_sensible_heat2
        energy = total_heat_to_remove / params['cop_freezing_system']
        
        opex_money += energy * elec_price[2]
        
        # CAPEX
        capex_per_kg = calculate_food_infra_capex("freezing", facility_capacity_arg, A, 0)
        capex_money += A * capex_per_kg
        
        emissions = energy * 0.2778 * co2_factor * 0.001
        loss = 0.005 * A
        
        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (emissions / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, energy, emissions, A - loss, loss, 0 # Added 0 for insurance

    def food_road_transport(A, args):
        params, distance, duration_mins, diesel_price, hh_diesel, dens_diesel, co2_diesel, ambient_temp, driver_daily_salary_arg, annual_working_days_arg, maintenance_cost_per_km_truck_arg, truck_capex_params_arg, country_of_road_transport_arg, carbon_tax_per_ton_co2_dict_arg = args
        
        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        base_spoilage_rate = params['general_params']['spoilage_rate_per_day']

        temp_sensitivity_factor = 1 + (0.20 * ((ambient_temp - params['general_params']['target_temp_celsius']) / 5))
        if temp_sensitivity_factor < 1:
            temp_sensitivity_factor = 1
        dynamic_spoilage_rate = base_spoilage_rate * temp_sensitivity_factor
        LITERS_PER_GALLON = 3.78541
        num_trucks = math.ceil(A / params['general_params']['cargo_per_truck_kg'])
        truck_economy_km_per_L = 4.0
        diesel_for_propulsion_L = (distance / truck_economy_km_per_L) * num_trucks
        duration_hr = duration_mins / 60.0
        diesel_for_reefer_L = params['general_params']['reefer_truck_fuel_consumption_L_hr'] * duration_hr * num_trucks
        total_diesel_L = diesel_for_propulsion_L + diesel_for_reefer_L
        total_diesel_gal = total_diesel_L / LITERS_PER_GALLON
        
        opex_money += total_diesel_gal * diesel_price
        energy = total_diesel_gal * dens_diesel * hh_diesel
        emissions = total_diesel_gal * co2_diesel
        duration_days = duration_hr / 24.0
        loss = A * dynamic_spoilage_rate * duration_days

        # Driver salary cost
        trip_days = max(1, math.ceil(duration_mins / 1440))
        driver_cost_per_truck = (driver_daily_salary_arg / annual_working_days_arg) * trip_days
        total_driver_cost = driver_cost_per_truck * num_trucks
        opex_money += total_driver_cost

        # Maintenance and Repair Cost
        maintenance_cost = maintenance_cost_per_km_truck_arg * distance * num_trucks
        opex_money += maintenance_cost

        # Truck CAPEX (using fuel_type 0 for general truck params as a proxy for food trucks)
        annual_truck_cost_usd = truck_capex_params_arg[0]['cost_usd_per_truck'] * truck_capex_params_arg[0]['annualization_factor']
        capex_per_truck_trip_usd = annual_truck_cost_usd / 330 # Assuming 330 annual trips
        capex_money += capex_per_truck_trip_usd * num_trucks

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_road_transport_arg, 0) * (emissions / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, energy, emissions, A - loss, loss, 0 # Added 0 for insurance

    def food_precooling_process(A, args):
        precool_params, elec_price, co2_factor, facility_capacity_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg = args

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        delta_T = (precool_params['initial_field_heat_celsius'] -
                precool_params['target_precool_temperature_celsius'])

        if delta_T <= 0:
            return 0, 0, 0, 0, A, 0, 0, 0 # Added 0 for insurance

        heat_to_remove_mj = A * precool_params['specific_heat_fresh_mj_kgK'] * delta_T
        energy_mj = heat_to_remove_mj / precool_params['cop_precooling_system']

        opex_money += energy_mj * elec_price[2]
        
        # CAPEX
        capex_per_kg = calculate_food_infra_capex("precool", facility_capacity_arg, A, 0)
        capex_money += A * capex_per_kg
        
        emissions = energy_mj * 0.2778 * co2_factor * 0.001
        loss = A * precool_params['moisture_loss_percent']

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (emissions / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, energy_mj, emissions, A - loss, loss, 0 # Added 0 for insurance

    def calculate_ca_energy_kwh(A, food_params, duration_hrs):
        if not food_params.get('process_flags', {}).get('needs_controlled_atmosphere', False):
            return 0

        ca_p = food_params['ca_params']
        gen_p = food_params['general_params']

        num_containers = math.ceil(A / gen_p['cargo_per_truck_kg'])
        container_volume_m3 = 76

        leaked_air_m3 = num_containers * container_volume_m3 * ca_p['container_leakage_rate_ach'] * duration_hrs
        energy_n2_kwh = leaked_air_m3 * ca_p['n2_generator_efficiency_kwh_per_m3']

        co2_density_kg_per_m3 = 1.98
        total_co2_produced_kg = (A * ca_p['respiration_rate_ml_co2_per_kg_hr'] * duration_hrs) / 1000000 * co2_density_kg_per_m3
        energy_co2_scrub_kwh = total_co2_produced_kg * ca_p['co2_scrubber_efficiency_kwh_per_kg_co2']

        water_to_add_liters = num_containers * 2.0 * (duration_hrs / 24.0)
        energy_humidity_kwh = water_to_add_liters * ca_p['humidifier_efficiency_kwh_per_liter']

        energy_base_kwh = num_containers * ca_p['base_control_power_kw'] * duration_hrs

        total_ca_energy_kwh = energy_n2_kwh + energy_co2_scrub_kwh + energy_humidity_kwh + energy_base_kwh

        return total_ca_energy_kwh

    def food_sea_transport(A, args):
        food_params, duration_hrs, selected_fuel, avg_ship_kw, maintenance_cost_per_km_ship_arg, port_to_port_dis_arg, calculate_voyage_overheads_helper_arg, selected_ship_params_arg, canal_transits_arg, port_regions_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg, eu_member_countries_arg, shipment_size_containers_arg, total_ship_container_capacity_arg = args # ADDED new args: shipment_size_containers_arg, total_ship_container_capacity_arg

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0
        
        # Calculate reefer and CA services per container
        reefer_service_cost_per_container, _, _, reefer_service_energy_per_container, reefer_service_emissions_per_container, _, _, _ = calculate_single_reefer_service_cost(duration_hrs, food_params)

        # Scale reefer and CA services for the entire shipment being transported
        total_reefer_cost_shipment = reefer_service_cost_per_container * shipment_size_containers_arg
        total_reefer_energy_shipment = reefer_service_energy_per_container * shipment_size_containers_arg
        total_reefer_emissions_shipment = reefer_service_emissions_per_container * shipment_size_containers_arg

        # Ship Propulsion Cost (scaled by portion of ship used for this cargo)
        # Assuming avg_ship_kw is total ship power, scale it by cargo volume.
        # A simpler approach might be to calculate total ship propulsion cost,
        # and then apportion it based on the user's shipment size relative to total ship capacity.
        # Let's use the latter for clarity and consistency with previous logic.

        # Total propulsion work for the entire ship for this leg
        total_ship_propulsion_work_kwh = avg_ship_kw * duration_hrs
        total_ship_propulsion_fuel_kg = (total_ship_propulsion_work_kwh * selected_fuel['sfoc_g_per_kwh']) / 1000.0
        total_ship_propulsion_cost = (total_ship_propulsion_fuel_kg / 1000.0) * selected_fuel['price_usd_per_ton']
        total_ship_propulsion_emissions = total_ship_propulsion_fuel_kg * selected_fuel['co2_emissions_factor_kg_per_kg_fuel']
        total_ship_propulsion_energy_mj = total_ship_propulsion_fuel_kg * selected_fuel['hhv_mj_per_kg']

        # Apportion propulsion cost/emissions based on containers used
        propulsion_cost_for_shipment = (total_ship_propulsion_cost / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
        propulsion_emissions_for_shipment = (total_ship_propulsion_emissions / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
        propulsion_energy_for_shipment = (total_ship_propulsion_energy_mj / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0


        opex_money += total_reefer_cost_shipment + propulsion_cost_for_shipment
        total_energy_mj = total_reefer_energy_shipment + propulsion_energy_for_shipment
        total_emissions = total_reefer_emissions_shipment + propulsion_emissions_for_shipment

        # Maintenance and Repair Cost (this should also be apportioned to the shipment if possible)
        # For now, let's assume it's part of the general overheads or fixed per voyage.
        # If it's a fixed cost per km of ship, this needs review.
        # Assuming it's already accounted for in `calculate_voyage_overheads` or is a minor fixed cost.
        maintenance_cost = maintenance_cost_per_km_ship_arg * port_to_port_dis_arg
        # If this maintenance is for the WHOLE SHIP, and `total_ship_container_capacity` is total containers,
        # then it should be apportioned too.
        maintenance_cost_for_shipment = (maintenance_cost / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
        opex_money += maintenance_cost_for_shipment


        # Voyage CAPEX (from calculate_voyage_overheads)
        voyage_duration_days = duration_hrs / 24.0
        total_voyage_capex = calculate_voyage_overheads_helper_arg(voyage_duration_days, selected_ship_params_arg, canal_transits_arg, port_regions_arg)
        # Apportion total voyage capex based on containers for the shipment
        capex_money_for_shipment = (total_voyage_capex / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
        capex_money += capex_money_for_shipment

        duration_days = duration_hrs / 24.0
        spoilage_rate = food_params['general_params']['spoilage_rate_per_day']
        if food_params['process_flags'].get('needs_controlled_atmosphere'):
            spoilage_rate = food_params['general_params']['spoilage_rate_ca_per_day']
        loss = A * spoilage_rate * duration_days

        # Carbon Tax (General)
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (total_emissions / 1000)
        carbon_tax_money += carbon_tax

        # EU ETS Carbon Tax (if applicable)
        eu_ets_tax = 0
        if end_country_name_arg in eu_member_countries_arg:
            eu_ets_emissions_tons = (total_emissions / 1000) * 0.50
            eu_ets_tax = eu_ets_emissions_tons * carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0)
            carbon_tax_money += eu_ets_tax
        
        return opex_money, capex_money, carbon_tax_money, total_energy_mj, total_emissions, A - loss, loss, 0 # Added 0 for insurance
    
    def food_cold_storage(A, args):
        params, storage_days, elec_price, co2_factor, ambient_temp, facility_capacity_arg, country_of_storage_arg, carbon_tax_per_ton_co2_dict_arg = args

        opex_money = 0
        capex_money = 0
        carbon_tax_money = 0 # New variable

        volume_m3 = A / params['general_params']['density_kg_per_m3']

        base_energy_factor_kwh_m3_day = 0.5
        temp_adjustment_factor = 1 + (0.03 * (ambient_temp - 20))
        if temp_adjustment_factor < 0.5:
            temp_adjustment_factor = 0.5

        dynamic_energy_factor = base_energy_factor_kwh_m3_day * temp_adjustment_factor
        energy_kwh_per_day = dynamic_energy_factor * volume_m3
        total_energy_kwh = energy_kwh_per_day * storage_days

        energy_mj = total_energy_kwh * 3.6
        opex_money += energy_mj * elec_price[2]
        
        # CAPEX
        capex_per_kg = calculate_food_infra_capex("cold_storage", facility_capacity_arg, A, storage_days)
        capex_money += A * capex_per_kg
        
        emissions = energy_mj * 0.2778 * co2_factor * 0.001
        spoilage_rate = params['general_params']['spoilage_rate_per_day']
        if params['process_flags'].get('needs_controlled_atmosphere'):
            spoilage_rate = params['general_params']['spoilage_rate_ca_per_day']
        loss = A * spoilage_rate * storage_days

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_storage_arg, 0) * (emissions / 1000)
        carbon_tax_money += carbon_tax

        return opex_money, capex_money, carbon_tax_money, energy_mj, emissions, A - loss, loss, 0 # Added 0 for insurance

    def calculate_food_infra_capex(process_name, capacity_tons_per_day, A, storage_days):
        """
        Estimates the amortized capital cost per kg for food processing facilities.
        Source: Based on general industry capital cost estimates for food processing and cold chain logistics.
        Parameters:
            process_name: Type of facility (e.g., 'cold_storage')
            capacity_tons_per_day: Daily throughput in tons (used for precool/freezing)
            A: Total mass held in kg (used for cold storage)
            storage_days: Average storage duration in days
        Returns:
            Amortized CAPEX per kg in USD.
        """
        cost_models = {
            "precool": {"base_cost_M_usd": 1.5, "power_law_exp": 0.6, "reference_capacity": 50},
            "freezing": {"base_cost_M_usd": 3, "power_law_exp": 0.65, "reference_capacity": 30},
            "cold_storage": {"base_cost_M_usd": 0.82, "power_law_exp": 0.7, "reference_capacity": 5000000}
        }

        model = cost_models.get(process_name)
        if not model:
            return 0

        if process_name == "cold_storage":
            total_capex_usd = (model['base_cost_M_usd'] * 1000000) * (A / model['reference_capacity']) ** model['power_law_exp']
        else:
            total_capex_usd = (model['base_cost_M_usd'] * 1000000) * (capacity_tons_per_day / model['reference_capacity']) ** model['power_law_exp']

        annualized_capex = total_capex_usd * 0.1

        if process_name == "cold_storage":
            if storage_days == 0:
                return 0
            cycles_per_year = 330 / storage_days
            annual_throughput_kg = A * cycles_per_year
        else:
            annual_throughput_kg = capacity_tons_per_day * 1000 * 330

        if annual_throughput_kg == 0:
            return 0

        capex_per_kg = annualized_capex / annual_throughput_kg
        return capex_per_kg

    def total_food_lca(initial_weight, food_params, carbon_tax_per_ton_co2_dict_tl, HHV_diesel_tl, diesel_density_tl, CO2e_diesel_tl,
                       food_name_tl, searoute_coor_tl, port_to_port_duration_tl): # Added new args

        food_funcs_sequence = [
            (food_harvest_and_prep, "Harvesting & Preparation"),
        ]

        flags = food_params['process_flags']
        if flags.get('needs_precooling', False):
            food_funcs_sequence.append((food_precooling_process, f"Pre-cooling in {start}"))

        if flags.get('needs_freezing', False):
            food_funcs_sequence.append((food_freezing_process, f"Freezing in {start}"))

        food_funcs_sequence.extend([
            (food_road_transport, f"Road Transport: {start} to {start_port_name}"),
            (food_cold_storage, f"Cold Storage at {start_port_name}"),
            (food_sea_transport, f"Marine Transport: {start_port_name} to {end_port_name}")
        ])

        food_funcs_sequence.extend([
            (food_cold_storage, f"Cold Storage at {end_port_name}"),
            (food_road_transport, f"Road Transport: {end_port_name} to {end}"),
            (food_cold_storage, f"Cold Storage at {end} (Destination)"),
        ])

        current_weight = initial_weight
        results_list = []
        total_opex_money_tl = 0.0
        total_capex_money_tl = 0.0
        total_carbon_tax_money_tl = 0.0
        total_ener_consumed_tl = 0.0
        total_G_emission_tl = 0.0
        total_S_spoilage_loss_tl = 0.0
        total_insurance_money_tl = 0.0 # New accumulator for insurance

        for func_entry in food_funcs_sequence:
            func_to_call, label = func_entry
            args_for_func = ()
            
            if func_to_call == food_harvest_and_prep:
                args_for_func = (price_start, start_country_name, carbon_tax_per_ton_co2_dict_tl,
                                 food_name_tl, searoute_coor_tl, port_to_port_duration_tl) # Added new args
            elif func_to_call == food_precooling_process:
                precooling_full_params = {**food_params['precooling_params'], **food_params['general_params']}
                args_for_func = (precooling_full_params, start_electricity_price, CO2e_start, facility_capacity, start_country_name, carbon_tax_per_ton_co2_dict_tl)
            elif func_to_call == food_freezing_process:
                freezing_full_params = {**food_params.get('freezing_params', {}), **food_params['general_params']}
                args_for_func = (freezing_full_params, start_local_temperature, start_electricity_price, CO2e_start, facility_capacity, start_country_name, carbon_tax_per_ton_co2_dict_tl)
            elif func_to_call == food_road_transport and start_port_name in label:
                args_for_func = (food_params, distance_A_to_port, duration_A_to_port, diesel_price_start, HHV_diesel_tl, diesel_density_tl, CO2e_diesel_tl, start_local_temperature, driver_daily_salary_start, annual_working_days, MAINTENANCE_COST_PER_KM_TRUCK, truck_capex_params, start_country_name, carbon_tax_per_ton_co2_dict_tl)
            elif func_to_call == food_road_transport and end_port_name in label:
                args_for_func = (food_params, distance_port_to_B, duration_port_to_B, diesel_price_end, HHV_diesel_tl, diesel_density_tl, CO2e_diesel_tl, end_local_temperature, driver_daily_salary_end, annual_working_days, MAINTENANCE_COST_PER_KM_TRUCK, truck_capex_params, end_country_name, carbon_tax_per_ton_co2_dict_tl)
            elif func_to_call == food_sea_transport:
                args_for_func = (food_params, port_to_port_duration, selected_marine_fuel_params, avg_ship_power_kw, MAINTENANCE_COST_PER_KM_SHIP, port_to_port_dis, calculate_voyage_overheads, selected_ship_params, canal_transits, port_regions, end_country_name, carbon_tax_per_ton_co2_dict_tl, EU_MEMBER_COUNTRIES, shipment_size_containers, total_ship_container_capacity) 
            elif func_to_call == food_cold_storage and "at " + start_port_name in label:
                args_for_func = (food_params, storage_time_A, start_port_electricity_price, CO2e_start, start_local_temperature, facility_capacity, start_port_country_name, carbon_tax_per_ton_co2_dict_tl)
            elif func_to_call == food_cold_storage and "at " + end_port_name in label:
                args_for_func = (food_params, storage_time_B, end_port_electricity_price, CO2e_end, end_local_temperature, facility_capacity, end_port_country_name, carbon_tax_per_ton_co2_dict_tl)
            elif func_to_call == food_cold_storage and "Destination" in label:
                args_for_func = (food_params, storage_time_C, end_electricity_price, CO2e_end, end_local_temperature, facility_capacity, end_country_name, carbon_tax_per_ton_co2_dict_tl)
            
            # Updated call to function to receive carbon_tax_money AND insurance_money
            opex_m, capex_m, carbon_tax_m, energy, emissions, current_weight, loss, insurance_m = func_to_call(current_weight, args_for_func) # Added insurance_m

            # For 'Harvesting & Preparation', split out insurance into a separate line
            if func_to_call == food_harvest_and_prep:
                results_list.append([
                    "Insurance", # Label for insurance
                    insurance_m, # Put the insurance cost in the OPEX slot for display/charting purposes
                    0.0, # Capex
                    0.0, # Carbon Tax
                    0.0, # Energy
                    0.0, # Emissions
                    current_weight, # Associate with current mass
                    0.0 # Spoilage Loss
                ])
                total_insurance_money_tl += insurance_m # Accumulate total insurance
                insurance_m = 0 # Reset for this specific row if it was harvesting

            results_list.append([label, opex_m, capex_m, carbon_tax_m, energy, emissions, current_weight, loss])
            
            total_opex_money_tl += opex_m
            total_capex_money_tl += capex_m
            total_carbon_tax_money_tl += carbon_tax_m
            total_ener_consumed_tl += energy
            total_G_emission_tl += emissions
            total_S_spoilage_loss_tl += loss
        
        # Calculate final total money including all components
        final_total_money_tl = total_opex_money_tl + total_capex_money_tl + total_carbon_tax_money_tl + total_insurance_money_tl
        
        # Add the final TOTAL row, ensuring insurance is part of the overall sum
        results_list.append(["TOTAL", total_opex_money_tl, total_capex_money_tl, total_carbon_tax_money_tl, total_ener_consumed_tl, total_G_emission_tl, current_weight, total_S_spoilage_loss_tl])

        return results_list

    def openai_get_food_price(food_name, location_name):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)

        prompt_messages = [
            {
                "role": "system",
                "content": """You are an expert data analyst specializing in global food prices. Your task is to find a recent, representative retail price for a specific food item in a given country or region. Perform all necessary unit (e.g., lb to kg) and currency conversions to return a final price in USD per kg. Your response must be only a JSON object. If you cannot find a reliable price for the specific region, use the national average for that country. If no reliable price can be found, return null."""
            },
            {
                "role": "user",
                "content": f"""Find a representative retail price for {food_name} in the country or region of '{location_name}'. Return the result in the following JSON format: {{"price_usd_per_kg": "PRICE_HERE_AS_FLOAT_OR_NULL", "original_price_found": "ORIGINAL_PRICE_AS_STRING", "source_info": "BRIEF_DESCRIPTION_OF_SOURCE_AND_LOCATION"}}"""
            }
        ]

        try:
            print(f"Requesting AI price analysis for: {food_name} in {location_name}")
            response = client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                temperature=0,
                messages=prompt_messages
            )
            result = json.loads(response.choices[0].message.content)
            price = result.get("price_usd_per_kg")

            if isinstance(price, (int, float)):
                return price
            else:
                return None

        except Exception as e:
            print(f"AI price lookup failed: {e}")
            return None

    def openai_get_nearest_farm_region(food_name, location_name):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)

        prompt_messages = [
            {
                "role": "system",
                "content": """You are an expert in agricultural logistics and supply chains. Your task is to identify a major commercial producing region for a specific food item that is as close as possible to a target destination city. Return the name of this region and its representative geographic coordinates as a JSON object. If the destination is itself a major producer, use a location within that region. If no significant commercial production exists nearby, return null."""
            },
            {
                "role": "user",
                "content": f"""For the food item '{food_name}', find the nearest major commercial farming region to the destination '{location_name}'. Return the result in the following JSON format: {{"farm_region_name": "NAME_OF_REGION", "latitude": "LATITUDE_FLOAT", "longitude": "LONGITUDE_FLOAT"}}"""
            }
        ]

        try:
            print(f"Requesting AI analysis for nearest farm region for: {food_name} near {location_name}")
            response = client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                temperature=0,
                messages=prompt_messages
            )
            result = json.loads(response.choices[0].message.content)

            if all(k in result for k in ['farm_region_name', 'latitude', 'longitude']) and isinstance(result['latitude'], (int, float)):
                return result
            else:
                return None

        except Exception as e:
            print(f"AI farm region lookup failed: {e}")
            return None

    def detect_canal_transit(route_object):
        transits = {
            "suez": False,
            "panama": False
        }

        PANAMA_CANAL_BBOX = (-80.5, 8.5, -78.5, 9.5)
        SUEZ_CANAL_BBOX = (32.0, 29.5, 33.0, 31.5)

        try:
            route_coords = route_object.geometry['coordinates']

            for lon, lat in route_coords:
                if (PANAMA_CANAL_BBOX[0] <= lon <= PANAMA_CANAL_BBOX[2] and
                    PANAMA_CANAL_BBOX[1] <= lat <= PANAMA_CANAL_BBOX[3]):
                    transits["panama"] = True
                    break

                if (SUEZ_CANAL_BBOX[0] <= lon <= SUEZ_CANAL_BBOX[2] and
                    SUEZ_CANAL_BBOX[1] <= lat <= SUEZ_CANAL_BBOX[3]):
                    transits["suez"] = True
                    break

            if transits["panama"] or transits["suez"]:
                return transits

            route_info_string = json.dumps(route_object.properties).lower()
            if "suez" in route_info_string:
                transits["suez"] = True
            if "panama" in route_info_string:
                transits["panama"] = True

        except Exception as e:
            print(f"Could not parse route properties for canal detection: {e}")

        return transits

    def calculate_single_reefer_service_cost(duration_hrs, food_params):
        
        ca_energy_kwh_per_container = calculate_ca_energy_kwh(1, food_params, duration_hrs)
        reefer_energy_kwh_per_container = food_params['general_params']['reefer_container_power_kw'] * duration_hrs        

        total_energy_kwh = ca_energy_kwh_per_container + reefer_energy_kwh_per_container

        aux_sfoc_g_kwh = 200
        fuel_kg = (total_energy_kwh * aux_sfoc_g_kwh) / 1000.0

        opex_money = (fuel_kg / 1000.0) * auxiliary_fuel_params['price_usd_per_ton']
        energy_mj = fuel_kg * auxiliary_fuel_params['hhv_mj_per_kg']
        emissions = fuel_kg * auxiliary_fuel_params['co2_emissions_factor_kg_per_kg_fuel']

        capex_money = 0  # No CAPEX directly attributed to single reefer service in this function
        carbon_tax_money = 0  # Carbon tax is typically handled at the higher 'food_sea_transport' level
        current_weight = 1  # Represents the 'per container' basis of this calculation
        loss = 0  # No direct loss (spoilage) calculated at this micro-level

        return opex_money, capex_money, carbon_tax_money, energy_mj, emissions, current_weight, loss, 0 # Added 0 for insurance
    
    # =================================================================
    # <<< MAIN CONDITIONAL BRANCH STARTS HERE >>>
    # =================================================================

    # --- 1. Unpack user inputs from the frontend ---
    # ... (earlier code, e.g., global parameters and function definitions) ...

    # Define label_map here, accessible to both fuel and food sections
    label_map = {
        # Fuel-specific labels (keep these as they are used dynamically)
        "site_A_chem_production": "Initial Production (Placeholder)",
        "site_A_chem_liquification": "Liquefaction at Site A",
        "fuel_pump_transfer_siteA_to_truck": "Loading to Truck (Site A)",
        "fuel_road_transport_start_leg": "Road Transport: Site A to Port A",
        "fuel_pump_transfer_portA_to_storage": "Unloading at Port A (to Storage)",
        "fuel_storage_port_A": "Storage at Port A",
        "chem_loading_to_ship": "Loading to Ship",
        "port_to_port": "Marine Transport",
        "fuel_pump_transfer_ship_to_portB": "Unloading from Ship (Port B)",
        "fuel_storage_port_B": "Storage at Port B",
        "fuel_pump_transfer_portB_to_truck": "Loading to Truck (Port B)",
        "fuel_road_transport_end_leg": "Road Transport: Port B to Site B",
        "fuel_pump_transfer_truck_to_siteB": "Unloading at Site B (to Storage)",
        "fuel_storage_site_B": "Storage at Site B",
        "fuel_pump_transfer_siteB_to_use": "Unloading for Final Use (Site B)",
        "chem_convert_to_H2": "Cracking/Reforming to H2",
        "PH2_pressurization_at_site_A": "Pressurization at Site A",
        "PH2_site_A_to_port_A": "Pipeline Transport: Site A to Port A",
        "port_A_liquification": "Liquefaction at Port A",
        "H2_pressurization_at_port_B": "Pressurization at Port B",
        "PH2_port_B_to_site_B": "Pipeline Transport: Port B to Site B",
        "PH2_storage_at_site_B": "Storage at Site B",
        "TOTAL": "TOTAL",
        # Add food-specific labels that might be generic or need mapping
        "Harvesting & Preparation": "Harvesting & Preparation",
        "Pre-cooling": "Pre-cooling", # Generic, as total_food_lca adds location
        "Freezing": "Freezing", # Generic, as total_food_lca adds location
        "Road Transport": "Road Transport", # Generic, as total_food_lca adds location
        "Cold Storage": "Cold Storage", # Generic, as total_food_lca adds location
        "Marine Transport (Base Freight)": "Marine Transport (Base Freight)", # Explicitly added
        "Reefer & CA Services": "Reefer & CA Services", # Explicitly added
        "Insurance": "Insurance" # Added new Insurance label
    }

    start = inputs['start']
    end = inputs['end']
    commodity_type = inputs.get('commodity_type', 'fuel')
    marine_fuel_choice = inputs.get('marine_fuel_choice', 'VLSFO')
    storage_time_A = inputs['storage_time_A']
    storage_time_B = inputs['storage_time_B']
    storage_time_C = inputs['storage_time_C']
    facility_capacity = inputs['LH2_plant_capacity']

    coor_start_lat, coor_start_lng, _ = extract_lat_long(start)
    coor_end_lat, coor_end_lng, _ = extract_lat_long(end)
    start_port_lat, start_port_lng, start_port_name = openai_get_nearest_port(f"{coor_start_lat},{coor_start_lng}")
    end_port_lat, end_port_lng, end_port_name = openai_get_nearest_port(f"{coor_end_lat},{coor_end_lng}")
    _, hydrogen_production_cost = openai_get_hydrogen_cost(f"{coor_start_lat},{coor_start_lng}")
    route = sr.searoute((start_port_lng, start_port_lat), (end_port_lng, end_port_lat), units="nm")
    searoute_coor = [[lat, lon] for lon, lat in route.geometry['coordinates']]
    port_to_port_dis = route.properties['length'] * 1.852
    canal_transits = detect_canal_transit(route)
    start_to_port_dist_str, start_to_port_dur_str = inland_routes_cal((coor_start_lat, coor_start_lng), (start_port_lat, start_port_lng))
    port_to_end_dist_str, port_to_end_dur_str = inland_routes_cal((end_port_lat, end_port_lng), (coor_end_lat, coor_end_lng))

    distance_A_to_port = float(re.sub(r'[^\d.]', '', start_to_port_dist_str))
    distance_port_to_B = float(re.sub(r'[^\d.]', '', port_to_end_dist_str))
    duration_A_to_port = time_to_minutes(start_to_port_dur_str)
    duration_port_to_B = time_to_minutes(port_to_end_dur_str)

    start_local_temperature = local_temperature(coor_start_lat, coor_start_lng)
    end_local_temperature = local_temperature(coor_end_lat, coor_end_lng)
    port_to_port_duration = float(port_to_port_dis) / (16 * 1.852)

    CO2e_start = carbon_intensity(coor_start_lat, coor_start_lng)
    CO2e_end = carbon_intensity(coor_end_lat, coor_end_lng)

    start_electricity_price = openai_get_electricity_price(f"{coor_start_lat},{coor_start_lng}")
    end_electricity_price = openai_get_electricity_price(f"{coor_end_lat},{coor_end_lng}")
    start_port_electricity_price = openai_get_electricity_price(f"{start_port_lat},{start_port_lng}")
    end_port_electricity_price = openai_get_electricity_price(f"{end_port_lat},{end_port_lng}")

    road_route_start_coords = extract_route_coor((coor_start_lat, coor_start_lng), (start_port_lat, start_port_lng))
    road_route_end_coords = extract_route_coor((end_port_lat, end_port_lng), (coor_end_lat, end_port_lng))
    diesel_price_country = {
        "Venezuela": 0.016, "Iran": 0.022, "Libya": 0.104, "Algeria": 0.834, "Turkmenistan": 1.082, "Egypt": 1.181, "Angola": 1.238, "Kuwait": 1.419, "Saudi Arabia": 1.675, "Ecuador": 1.798, "Bahrain": 1.807, "Qatar": 2.027, "Bolivia": 2.038, "Kazakhstan": 2.145, "Nigeria": 2.222, "Azerbaijan": 2.227, "Syria": 2.389, "Trinidad and Tobago": 2.46, "Trinidad & Tobago": 2.46, "Malaysia": 2.47, "Sudan": 2.482, "United Arab Emirates": 2.525, "UAE": 2.525, "Oman": 2.54, "Vietnam": 2.553, "Colombia": 2.553, "Bhutan": 2.58, "Lebanon": 2.673, "Tunisia": 2.797, "Myanmar": 2.907, "Burma": 2.907, "Panama": 2.917, "Puerto Rico": 2.949, "Belarus": 3.006, "Guyana": 3.044, "Honduras": 3.059, "Indonesia": 3.07, "Afghanistan": 3.101, "Taiwan": 3.128, "Bangladesh": 3.158, "Laos": 3.185, "Kyrgyzstan": 3.189, "Ethiopia": 3.228, "Paraguay": 3.278, "El Salvador": 3.3, "Cambodia": 3.304, "Curacao": 3.379, "Russia": 3.404, "Pakistan": 3.405, "Maldives": 3.408, "Guatemala": 3.412, "China": 3.442, "United States": 3.452, "USA": 3.452, "Jordan": 3.47, "Philippines": 3.502, "Zambia": 3.54, "Liberia": 3.546, "Uzbekistan": 3.59, "Peru": 3.648, "Fiji": 3.677, "Thailand": 3.703, "Dominican Republic": 3.751, "Dom. Rep.": 3.751, "Gabon": 3.78, "Chile": 3.839, "Congo, Dem. Rep.": 3.882, "DR Congo": 3.882, "Georgia": 3.91, "Canada": 3.934, "Nepal": 3.947, "Aruba": 3.951, "Brazil": 3.977, "Grenada": 3.978, "Australia": 3.988, "India": 3.998, "Cape Verde": 4.032, "Tanzania": 4.036, "Costa Rica": 4.051, "Moldova": 4.071, "Sri Lanka": 4.108, "Japan": 4.143, "Cuba": 4.147, "Lesotho": 4.194, "Botswana": 4.212, "Mongolia": 4.229, "Argentina": 4.24, "Madagascar": 4.246, "Uruguay": 4.268, "New Zealand": 4.271, "South Korea": 4.31, "Suriname": 4.315, "Namibia": 4.357, "Jamaica": 4.389, "Rwanda": 4.404, "Burkina Faso": 4.438, "Nicaragua": 4.444, "Turkey": 4.462, "South Africa": 4.473, "Eswatini": 4.523, "Swaziland": 4.523, "North Macedonia": 4.548, "N. Maced.": 4.548, "Togo": 4.569, "Dominica": 4.58, "Ivory Coast": 4.602, "Côte d'Ivoire": 4.602, "Morocco": 4.633, "Haiti": 4.734, "Benin": 4.734, "Mali": 4.767, "Uganda": 4.788, "Kenya": 4.793, "Ghana": 4.801, "Armenia": 4.832, "Bahamas": 4.869, "Mauritius": 4.912, "Bosnia and Herzegovina": 4.917, "Bosnia-Herzegovina": 4.917, "Ukraine": 4.94, "Senegal": 4.964, "Burundi": 4.989, "Cayman Islands": 5.023, "Mexico": 5.056, "Saint Lucia": 5.084, "Seychelles": 5.094, "Andorra": 5.105, "Mozambique": 5.141, "Malta": 5.208, "Guinea": 5.239, "Sierra Leone": 5.271, "Bulgaria": 5.328, "Cameroon": 5.444, "Montenegro": 5.509, "Belize": 5.606, "Czech Republic": 5.631, "Zimbabwe": 5.754, "Poland": 5.789, "Spain": 5.817, "Luxembourg": 5.871, "Estonia": 5.914, "Malawi": 5.966, "Mayotte": 5.983, "Cyprus": 6.0, "Slovakia": 6.039, "Romania": 6.058, "Lithuania": 6.09, "Croatia": 6.142, "Latvia": 6.159, "Slovenia": 6.168, "Hungary": 6.195, "Sweden": 6.266, "Austria": 6.314, "San Marino": 6.318, "Greece": 6.344, "Barbados": 6.374, "Portugal": 6.512, "Germany": 6.615, "Monaco": 6.624, "France": 6.655, "Belgium": 6.787, "Serbia": 6.866, "Italy": 6.892, "Netherlands": 6.912, "Finland": 7.011, "Norway": 7.026, "United Kingdom": 7.067, "UK": 7.067, "Ireland": 7.114, "Wallis and Futuna": 7.114, "Singapore": 7.195, "Israel": 7.538, "Albania": 7.597, "Denmark": 7.649, "Switzerland": 8.213, "Central African Republic": 8.218, "C. Afr. Rep.": 8.218, "Liechtenstein": 8.36, "Iceland": 9.437, "Hong Kong": 12.666
    }
    diesel_price_start = get_diesel_price(coor_start_lat, coor_start_lng, diesel_price_country)
    diesel_price_end = get_diesel_price(end_port_lat, end_port_lng, diesel_price_country)

    truck_driver_annual_salaries = {
        "Afghanistan": 3535.00, "Albania": 9366.00, "Algeria": 9366.00, "Andorra": 49000.00, "Angola": 9366.00, "Antigua and Barbuda": 14895.00, "Argentina": 7466.00, "Armenia": 8022.00, "Australia": 67568.00, "Austria": 52886.00, "Azerbaijan": 8022.00, "Bahamas": 35452.00, "Bahrain": 27627.00, "Bangladesh": 3535.00, "Barbados": 14895.00, "Belarus": 5040.00, "Belgium": 55097.00, "Belize": 10243.00, "Benin": 9366.00, "Bhutan": 3535.00, "Bolivia": 10243.00, "Bosnia and Herzegovina": 12812.00, "Bosnia-Herzegovina": 12812.00, "Botswana": 9366.00, "Brazil": 10875.00, "Trinidad and Tobago": 12800.00, "Trinidad & Tobago": 12800.00, "Brunei": 40149.00, "Bulgaria": 14901.00, "Burkina Faso": 9366.00, "Burundi": 3535.00, "Cambodia": 4652.00, "Cameroon": 9366.00, "Canada": 46276.00, "Cape Verde": 9366.00, "Central African Republic": 9366.00, "C. Afr. Rep.": 9366.00, "Chad": 9366.00, "Chile": 14675.00, "China": 16881.00, "Colombia": 10494.00, "Comoros": 9366.00, "Congo, Dem. Rep.": 9366.00, "DR Congo": 9366.00, "Congo, Rep.": 9366.00, "Costa Rica": 18581.00, "Croatia": 19858.00, "Cuba": 10243.00, "Cyprus": 27225.00, "Czech Republic": 22545.00, "Denmark": 64323.00, "Djibouti": 9366.00, "Dominica": 14895.00, "Dominican Republic": 6623.00, "Dom. Rep.": 6623.00, "Ecuador": 13737.00, "Egypt": 3363.00, "El Salvador": 10243.00, "Equatorial Guinea": 9366.00, "Eritrea": 9366.00, "Estonia": 20789.00, "Eswatini": 9366.00, "Swaziland": 9366.00, "Ethiopia": 9366.00, "Fiji": 10243.00, "Finland": 52822.00, "France": 39047.00, "Gabon": 9366.00, "Gambia": 9366.00, "Georgia": 8022.00, "Germany": 49000.00, "Ghana": 9366.00, "Greece": 27225.00, "Grenada": 14895.00, "Guatemala": 11533.00, "Guinea": 9366.00, "Guinea-Bissau": 9366.00, "Guyana": 10243.00, "Haiti": 10243.00, "Honduras": 10243.00, "Hong Kong": 40678.00, "Hungary": 17505.00, "Iceland": 66184.00, "India": 7116.00, "Indonesia": 12778.00, "Iran": 14022.00, "Iraq": 14022.00, "Ireland": 51465.00, "Israel": 32004.00, "Italy": 37483.00, "Ivory Coast": 9366.00, "Côte d'Ivoire": 9366.00, "Jamaica": 12018.00, "Japan": 30959.00, "Jordan": 9366.00, "Kazakhstan": 12955.00, "Kenya": 9366.00, "Kiribati": 10243.00, "Kuwait": 27627.00, "Kyrgyzstan": 5040.00, "Laos": 4652.00, "Latvia": 17458.00, "Lebanon": 9366.00, "Lesotho": 9366.00, "Liberia": 9366.00, "Libya": 9366.00, "Liechtenstein": 82171.00, "Lithuania": 21632.00, "Luxembourg": 62117.00, "Madagascar": 9366.00, "Malawi": 9366.00, "Malaysia": 11903.00, "Maldives": 12778.00, "Mali": 9366.00, "Malta": 25803.00, "Marshall Islands": 10243.00, "Mauritania": 9366.00, "Mauritius": 9366.00, "Mexico": 11622.00, "Micronesia": 10243.00, "Moldova": 5040.00, "Monaco": 82171.00, "Mongolia": 5040.00, "Montenegro": 12812.00, "Morocco": 11351.00, "Mozambique": 9366.00, "Myanmar": 3535.00, "Burma": 3535.00, "Namibia": 9366.00, "Nauru": 10243.00, "Nepal": 3535.00, "Netherlands": 49758.00, "New Zealand": 43970.00, "Nicaragua": 10243.00, "Niger": 9366.00, "Nigeria": 9366.00, "North Korea": 5000.00, "North Macedonia": 12812.00, "N. Maced.": 12812.00, "Norway": 48295.00, "Oman": 27627.00, "Pakistan": 3537.00, "Palau": 10243.00, "Panama": 19593.00, "Papua New Guinea": 10243.00, "Paraguay": 10243.00, "Peru": 10149.00, "Philippines": 6312.00, "Poland": 23511.00, "Portugal": 26116.00, "Qatar": 27627.00, "Romania": 21847.00, "Russia": 9382.00, "Rwanda": 9366.00, "Saint Kitts and Nevis": 14895.00, "Saint Lucia": 14895.00, "Saint Vincent and the Grenadines": 14895.00, "Samoa": 10243.00, "San Marino": 37483.00, "Sao Tome and Principe": 9366.00, "Saudi Arabia": 27627.00, "Senegal": 9366.00, "Serbia": 12812.00, "Seychelles": 9366.00, "Sierra Leone": 9366.00, "Singapore": 40104.00, "Slovakia": 22517.00, "Slovenia": 27225.00, "Solomon Islands": 10243.00, "Somalia": 3535.00, "South Africa": 14510.00, "South Korea": 31721.00, "South Sudan": 9366.00, "Spain": 35413.00, "Sri Lanka": 3535.00, "Sudan": 9366.00, "Suriname": 10243.00, "Sweden": 46322.00, "Switzerland": 82171.00, "Syria": 9366.00, "Taiwan": 26178.00, "Tajikistan": 5040.00, "Tanzania": 9366.00, "Thailand": 10455.00, "Timor-Leste": 10243.00, "Togo": 9366.00, "Tonga": 10243.00, "Tunisia": 9366.00, "Turkey": 17788.00, "Turkmenistan": 5040.00, "Tuvalu": 10243.00, "Uganda": 9366.00, "Ukraine": 6539.00, "United Arab Emirates": 35608.00, "UAE": 35608.00, "United Kingdom": 47179.00, "UK": 47179.00, "United States": 72415.00, "USA": 72415.00, "Uruguay": 14959.00, "Uzbekistan": 5040.00, "Vanuatu": 10243.00, "Venezuela": 10243.00, "Vietnam": 4652.00, "Yemen": 9366.00, "Zambia": 9366.00, "Zimbabwe": 9366.00
    }

    start_country_name = get_country_from_coords(coor_start_lat, coor_start_lng)
    end_country_name = get_country_from_coords(coor_end_lat, coor_end_lng)
    start_port_country_name = get_country_from_coords(start_port_lat, start_port_lng)
    end_port_country_name = get_country_from_coords(end_port_lat, end_port_lng)

    driver_daily_salary_start = truck_driver_annual_salaries.get(start_country_name, 30000) / 330
    driver_daily_salary_end = truck_driver_annual_salaries.get(end_country_name, 30000) / 330

    _, dynamic_price = openai_get_marine_fuel_price(marine_fuel_choice, (start_port_lat, start_port_lng), start_port_name)

    ship_archetype_key = inputs.get('ship_archetype', 'standard')
    ship_archetypes = {
        'small':    {'name': 'Small-Scale Carrier', 'volume_m3': 20000,  'num_tanks': 2, 'shape': 2, 'reefer_slots': 400,  'gross_tonnage': 25000},
        'midsized': {'name': 'Midsized Carrier', 'volume_m3': 90000,  'num_tanks': 4, 'shape': 2, 'reefer_slots': 800,  'gross_tonnage': 95000},
        'standard': {'name': 'Standard Modern Carrier', 'volume_m3': 174000, 'num_tanks': 4, 'shape': 1, 'reefer_slots': 1500, 'gross_tonnage': 165000},
        'q-flex':   {'name': 'Q-Flex Carrier', 'volume_m3': 210000, 'num_tanks': 5, 'shape': 1, 'reefer_slots': 1800, 'gross_tonnage': 190000},
        'q-max':    {'name': 'Q-Max Carrier', 'volume_m3': 266000, 'num_tanks': 5, 'shape': 1, 'reefer_slots': 2000, 'gross_tonnage': 215000}
    }
    REGIONAL_PORT_FEE_DATA = {
        'North Europe': 3.50, 'US West Coast': 3.20, 'US East Coast': 3.00, 'East Asia': 2.80, 'Middle East': 2.50, 'Default': 3.00
    }
    # Define port_regions here, using the REGIONAL_PORT_FEE_DATA
    port_regions = REGIONAL_PORT_FEE_DATA

    if ship_archetype_key == 'custom':
        selected_ship_params = {
            'volume_m3': inputs['total_ship_volume'],
            'num_tanks': inputs['ship_number_of_tanks'],
            'shape': inputs['ship_tank_shape'],
            'gross_tonnage': 165000 * (inputs['total_ship_volume'] / 174000)
        }
    else:
        selected_ship_params = ship_archetypes[ship_archetype_key]
        selected_ship_params['key'] = ship_archetype_key
    total_ship_volume = selected_ship_params['volume_m3']
    ship_number_of_tanks = selected_ship_params['num_tanks']
    ship_tank_shape = selected_ship_params['shape']

    avg_ship_power_kw = calculate_ship_power_kw(total_ship_volume)
    marine_fuels_data = {
        'VLSFO': {'price_usd_per_ton': 650.0, 'sfoc_g_per_kwh': 185, 'hhv_mj_per_kg': 41.0, 'co2_emissions_factor_kg_per_kg_fuel': 3.114, 'methane_slip_gwp100': 0},
        'LNG': {'price_usd_per_ton': 550.0, 'sfoc_g_per_kwh': 135, 'hhv_mj_per_kg': 50.0, 'co2_emissions_factor_kg_per_kg_fuel': 2.75, 'methane_slip_gwp100': (0.03 * 28)},
        'Methanol': {'price_usd_per_ton': 700.0, 'sfoc_g_per_kwh': 380, 'hhv_mj_per_kg': 22.7, 'co2_emissions_factor_kg_per_kg_fuel': 1.375, 'methane_slip_gwp100': 0},
        'Ammonia': {'price_usd_per_ton': 800.0, 'sfoc_g_per_kwh': 320, 'hhv_mj_per_kg': 22.5, 'co2_emissions_factor_kg_per_kg_fuel': 0, 'methane_slip_gwp100': 0, 'n2o_emission_factor_g_per_kwh': 0.05, 'nox_emission_factor_g_per_kwh': 2.0}
    }
    selected_marine_fuel_params = marine_fuels_data[marine_fuel_choice]
    selected_marine_fuel_params['price_usd_per_ton'] = dynamic_price
    auxiliary_fuel_params = {
        'name': 'Marine Gas Oil (MGO)',
        'price_usd_per_ton': 750.0,
        'hhv_mj_per_kg': 45.5,
        'co2_emissions_factor_kg_per_kg_fuel': 3.206
    }
    food_params = {
                'strawberry': {
                    'name': 'Strawberry',
                    'process_flags': {
                        'needs_precooling': True,
                        'needs_freezing': True,
                        'needs_controlled_atmosphere': False,
                    },
                    'general_params': {
                        'density_kg_per_m3': 600,
                        'target_temp_celsius': -24.0,
                        'spoilage_rate_per_day': 0.0001,
                        'reefer_container_power_kw': 3.5,
                        'cargo_per_truck_kg': 20000,
                        'specific_heat_fresh_mj_kgK': 0.0039,
                        'reefer_truck_fuel_consumption_L_hr': 1.5,
                        'production_CO2e_kg_per_kg': 0.747,
                    },
                    'precooling_params': {
                        'initial_field_heat_celsius': 28.0,
                        'target_precool_temperature_celsius': 1.0,
                        'cop_precooling_system': 2.0,
                        'moisture_loss_percent': 0.015,
                    },
                    'freezing_params': {
                        'specific_heat_frozen_mj_kgK': 0.0018,
                        'latent_heat_fusion_mj_kg': 0.300,
                        'cop_freezing_system': 2.5
                    }
                },
                'hass_avocado': {
                    'name': 'Hass Avocado',
                    'process_flags': {
                        'needs_precooling': True,
                        'needs_freezing': False,
                        'needs_controlled_atmosphere': True,
                    },
                    'general_params': {
                        'density_kg_per_m3': 600,
                        'target_temp_celsius': 5.0,
                        'spoilage_rate_per_day': 0.0005,
                        'spoilage_rate_ca_per_day': 0.0002,
                        'reefer_container_power_kw': 1.5,
                        'cargo_per_truck_kg': 20000,
                        'specific_heat_fresh_mj_kgK': 0.0035,
                        'reefer_truck_fuel_consumption_L_hr': 1.5,
                        'production_CO2e_kg_per_kg': 1.725,
                    },
                    'precooling_params': {
                        'initial_field_heat_celsius': 25.0,
                        'target_precool_temperature_celsius': 6.0,
                        'cop_precooling_system': 2.0,
                        'moisture_loss_percent': 0.01,
                    },
                    'ca_params': {
                        'o2_target_percent': 5.0,
                        'co2_target_percent': 5.0,
                        'humidity_target_rh_percent': 90.0,
                        'respiration_rate_ml_co2_per_kg_hr': 15.0,
                        'container_leakage_rate_ach': 0.02,
                        'n2_generator_efficiency_kwh_per_m3': 0.4,
                        'co2_scrubber_efficiency_kwh_per_kg_co2': 0.2,
                        'humidifier_efficiency_kwh_per_liter': 0.05,
                        'base_control_power_kw': 0.1
                    }
                },
                'banana': {
                    'name': 'Banana',
                    'process_flags': {
                        'needs_precooling': True,
                        'needs_freezing': False,
                        'needs_controlled_atmosphere': True,
                    },
                    'general_params': {
                        'density_kg_per_m3': 650,
                        'target_temp_celsius': 13.5,
                        'spoilage_rate_per_day': 0.001,
                        'spoilage_rate_ca_per_day': 0.0004,
                        'reefer_container_power_kw': 1.8,
                        'cargo_per_truck_kg': 20000,
                        'specific_heat_fresh_mj_kgK': 0.0033,
                        'reefer_truck_fuel_consumption_L_hr': 1.5,
                        'production_CO2e_kg_per_kg': 0.241,
                    },
                    'precooling_params': {
                        'initial_field_heat_celsius': 30.0,
                        'target_precool_temperature_celsius': 14.0,
                        'cop_precooling_system': 2.0,
                        'moisture_loss_percent': 0.01,
                    },
                    'ca_params': {
                        'o2_target_percent': 2.0,
                        'co2_target_percent': 5.0,
                        'humidity_target_rh_percent': 90.0,
                        'respiration_rate_ml_co2_per_kg_hr': 25.0,
                        'container_leakage_rate_ach': 0.02,
                        'n2_generator_efficiency_kwh_per_m3': 0.4,
                        'co2_scrubber_efficiency_kwh_per_kg_co2': 0.2,
                        'humidifier_efficiency_kwh_per_liter': 0.05,
                        'base_control_power_kw': 0.1
                    }
                }
            }

    data_raw = []
    response_data = {}
    detailed_data_formatted = [] 
    cost_chart_base64 = ""      
    emission_chart_base64 = ""  
    summary1_data = []           
    summary2_data = []           
    assumed_prices_data = []     
    csv_data = []                
    green_premium_data = None    
    local_sourcing_results = None 
    cost_overlay_text = ""       
    emission_overlay_text = ""   
    
    if commodity_type == 'fuel':
        fuel_type = inputs['fuel_type']
        fuel_names = ['Liquid Hydrogen', 'Ammonia', 'Methanol']
        selected_fuel_name = fuel_names[fuel_type] 
        recirculation_BOG = inputs['recirculation_BOG']
        BOG_recirculation_truck = inputs['BOG_recirculation_truck']
        BOG_recirculation_truck_apply = inputs['BOG_recirculation_truck_apply']
        BOG_recirculation_storage = inputs['BOG_recirculation_storage']
        BOG_recirculation_storage_apply = inputs['BOG_recirculation_storage_apply']
        BOG_recirculation_mati_trans = inputs['BOG_recirculation_mati_trans']
        BOG_recirculation_mati_trans_apply = inputs['BOG_recirculation_mati_trans_apply']
        user_define = [0, fuel_type, int(recirculation_BOG), int(BOG_recirculation_truck_apply), int(BOG_recirculation_storage_apply), int(BOG_recirculation_mati_trans_apply)]
        LH2_plant_capacity = facility_capacity
        volume_per_tank = total_ship_volume / ship_number_of_tanks
        if ship_tank_shape == 1:
            ship_tank_radius = np.cbrt(volume_per_tank/( (4/3)*np.pi + 8*np.pi ))
            ship_tank_height = 8 * ship_tank_radius
            storage_area = 2*np.pi*(ship_tank_radius*ship_tank_height) + 4*np.pi*ship_tank_radius**2
        else:
            ship_tank_radius = np.cbrt(volume_per_tank/(4/3*np.pi))
            storage_area = 4*np.pi*ship_tank_radius**2
        HHV_chem = [142, 22.5, 22.7]; LHV_chem = [120, 18.6, 19.9]; boiling_point_chem = [20, 239.66, 337.7];
        latent_H_chem = [449.6/1000, 1.37, 1.1]; specific_heat_chem = [14.3/1000, 4.7/1000, 2.5/1000];
        liquid_chem_density = [71, 682, 805];
        GWP_chem = [33, 0, 0]; GWP_N2O = 273;
        fuel_cell_eff = 0.65; road_delivery_ener = [0.0455/500, 0.022/500, 0.022/500];
        BOR_land_storage = [0.0032, 0.0001, 0.0000032]; BOR_loading = [0.0086, 0.00022, 0.0001667];
        BOR_truck_trans = [0.005, 0.00024, 0.000005]; BOR_ship_trans = [0.00326, 0.00024, 0.000005];
        BOR_unloading = [0.0086, 0.00022, 0.0001667];
        ss_therm_cond = 0.03; pipe_inner_D = 0.508; pipe_thick = 0.13; pipe_length = 1000;
        V_flowrate = [72000, 72000, 72000]; head_pump = 110; pump_power_factor = 0.78;
        tank_metal_thickness = 0.01; tank_insulator_thickness = 0.4; metal_thermal_conduct = 13.8;
        insulator_thermal_conduct = 0.02; chem_in_truck_weight = [4200, 32000, 40000*0.001*liquid_chem_density[2]];
        truck_tank_volume = 50; truck_tank_length = 12; truck_tank_radius = np.sqrt(truck_tank_volume/(np.pi*truck_tank_length));
        truck_tank_metal_thickness = 0.005; truck_tank_insulator_thickness = 0.075;
        number_of_cryo_pump_load_truck_site_A = 10; number_of_cryo_pump_load_ship_port_A = 10;
        number_of_cryo_pump_load_storage_port_A = 10; number_of_cryo_pump_load_storage_port_B = 10;
        number_of_cryo_pump_load_truck_port_B = 10; number_of_cryo_pump_load_storage_site_B = 10;
        storage_volume = [5683, 50000000/liquid_chem_density[1], 50000000/liquid_chem_density[2]];
        storage_radius = [np.cbrt(3 * volume / (4 * np.pi)) for volume in storage_volume];
        OHTC_ship = [0.05, 0.22, 0.02];
        COP_cooldown = [0.131, 1.714, 2]; COP_liq = [0.131, 1.714, 2]; COP_refrig = [0.036, 1.636, 2];
        dBOR_dT = [(0.02538-0.02283)/(45-15)/4, (0.000406-0.0006122)/(45-15)/4, 0];
        EIM_liquefication=100; EIM_cryo_pump=100; EIM_truck_eff=100; EIM_ship_eff=100; EIM_refrig_eff=100; EIM_fuel_cell=100;
        diesel_engine_eff = 0.4; heavy_fuel_density = 3.6; propul_eff = 0.55;
        NH3_ship_cosumption = (18.8*682*4170)/20000
        mass_conversion_to_H2 = [1, 0.176, 0.1875]
        eff_energy_chem_to_H2 = [0, 0.7, 0.75]
        energy_chem_to_H2 = [0, 9.3, 5.3]
        PH2_storage_V = 150.0
        numbers_of_PH2_storage_at_start = 50.0
        multistage_eff = 0.85
        pipeline_diameter = 0.5
        epsilon = 0.000045
        compressor_velocity = 20.0
        gas_chem_density = [0.08, 0.73, 1.42]
        target_pressure_site_B = 300
        latent_H_H2 = 0.4496
        specific_heat_H2 = 14.3
        numbers_of_PH2_storage = 50.0
        ship_engine_eff = 0.6
        PH2_pressure = 800
        truck_economy = [13.84, 10.14, 9.66]

        ship_tank_metal_specific_heat = 0.47 / 1000
        ship_tank_insulation_specific_heat = 1.5 / 1000
        ship_tank_metal_density = 7900
        ship_tank_insulation_density = 100
        pipe_metal_specific_heat = 0.5 / 1000
        ship_tank_metal_thickness = 0.05
        ship_tank_insulation_thickness = [0.66, 0.09, 0]

        COP_cooldown = [0.131, 1.714, 0]
        SMR_EMISSIONS_KG_PER_KG_H2 = 9.3

        loading_unloading_capex_params = {
            0: {'total_capex_M_usd': 500, 'annualization_factor': 0.08},
            1: {'total_capex_M_usd': 200, 'annualization_factor': 0.08},
            2: {'total_capex_M_usd': 80,  'annualization_factor': 0.08}
        }
        reference_annual_throughput_tons = {
            0: 1000000,
            1: 5000000,
            2: 10000000
        }

        target_weight = total_ship_volume * liquid_chem_density[fuel_type] * 0.98

        con = {'type': 'ineq', 'fun': constraint}

        process_funcs_for_optimization = [
            site_A_chem_production, site_A_chem_liquification,
            (fuel_pump_transfer, 'siteA_to_truck'),
            (fuel_road_transport, 'start_leg'),
            (fuel_pump_transfer, 'portA_to_storage'),
            (fuel_storage, 'port_A'),
            chem_loading_to_ship
        ]

        # UPDATED all_shared_params_tuple for optimizer (added selected_fuel_name_opt, searoute_coor_opt, port_to_port_duration_opt)
        all_shared_params_tuple = (
            LH2_plant_capacity, EIM_liquefication, specific_heat_chem,
            start_local_temperature, boiling_point_chem, latent_H_chem,
            COP_liq, start_electricity_price, CO2e_start, GWP_chem,
            V_flowrate,
            number_of_cryo_pump_load_truck_site_A,
            number_of_cryo_pump_load_storage_port_A,
            number_of_cryo_pump_load_ship_port_A,
            dBOR_dT,
            BOR_loading,
            BOR_unloading,
            head_pump, pump_power_factor, EIM_cryo_pump,
            ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick,
            COP_refrig,
            EIM_refrig_eff, pipe_metal_specific_heat, COP_cooldown,
            road_delivery_ener,
            HHV_chem,
            chem_in_truck_weight,
            truck_economy,
            truck_tank_radius, truck_tank_length,
            truck_tank_metal_thickness, metal_thermal_conduct,
            truck_tank_insulator_thickness, insulator_thermal_conduct,
            OHTC_ship,
            BOR_truck_trans,
            HHV_diesel, diesel_engine_eff, EIM_truck_eff,
            diesel_density, CO2e_diesel,
            BOG_recirculation_truck,
            fuel_cell_eff, EIM_fuel_cell, LHV_chem,
            storage_time_A, liquid_chem_density,
            storage_volume,
            storage_radius,
            BOR_land_storage,
            tank_metal_thickness,
            tank_insulator_thickness, BOG_recirculation_storage,
            distance_A_to_port, duration_A_to_port, diesel_price_start, driver_daily_salary_start, annual_working_days,
            calculate_liquefaction_capex, calculate_loading_unloading_capex,
            calculate_storage_capex, truck_capex_params,
            MAINTENANCE_COST_PER_KM_TRUCK, MAINTENANCE_COST_PER_KM_SHIP,
            hydrogen_production_cost, # Note: INSURANCE_PERCENTAGE_OF_CARGO_VALUE is NOT passed here, as it's part of the new func
            start_country_name, start_port_country_name, CARBON_TAX_PER_TON_CO2_DICT,
            port_regions, selected_fuel_name, searoute_coor, port_to_port_duration # Added here
        )
        args_for_optimizer_tuple = (
            user_define,
            process_funcs_for_optimization,
            all_shared_params_tuple
        )

        initial_guess = [target_weight / 0.9]

        result = minimize(optimization_chem_weight,
                        initial_guess,
                        args=(args_for_optimizer_tuple,),
                        method='SLSQP',
                        bounds=[(0, None)],
                        constraints=[con])

        if result.success:
            chem_weight = result.x[0]
        else:
            raise Exception(f"Optimization failed: {result.message}")
        
        # Pass new insurance-related args to total_chem_base
        final_results_raw, data_raw = total_chem_base(
            chem_weight, user_define[1], user_define[2],
            user_define[3], user_define[4], user_define[5], 
            CARBON_TAX_PER_TON_CO2_DICT, selected_fuel_name, searoute_coor, port_to_port_duration
        ) 

        # Retrieve the collected insurance cost from data_raw's first element (from site_A_chem_production)
        total_insurance_money = 0.0
        # Iterate through data_raw to sum up distinct insurance amounts
        for row in data_raw:
            if row[0] == "Insurance":
                total_insurance_money += row[1] # 'Opex' column is used to store the insurance cost for this specific row

        final_chem_kg_denominator = final_results_raw[3] # This is the final quantity of chemical

        # Handle conversion step if fuel type is not LH2
        if user_define[1] != 0: 
            amount_before_conversion = final_results_raw[3] 
            args_for_conversion = (mass_conversion_to_H2, eff_energy_chem_to_H2, energy_chem_to_H2, CO2e_end, end_electricity_price, end_country_name, CARBON_TAX_PER_TON_CO2_DICT)
            
            # The chem_convert_to_H2 function now returns 8 elements
            opex_conv, capex_conv, carbon_tax_conv, energy_conv, emission_conv, amount_after_conversion, bog_conv, _ = \
                chem_convert_to_H2(amount_before_conversion, user_define[1], user_define[2], user_define[3],
                                user_define[4], user_define[5], args_for_conversion)

            # Insert the conversion step into data_raw *before* the final TOTAL row
            # Ensure the row has 8 elements as per standard: [label, opex, capex, carbon_tax, energy, emissions, weight, loss]
            data_raw.insert(-1, ["chem_convert_to_H2", opex_conv, capex_conv, carbon_tax_conv, energy_conv, emission_conv, amount_after_conversion, bog_conv])

            # Update final_results_raw (which comes from total_chem_base) to include conversion costs/emissions
            # NOTE: total_results[0] is the total money (opex + capex + carbon_tax) BEFORE insurance for now,
            # as insurance is added separately.
            final_results_raw[0] += (opex_conv + capex_conv + carbon_tax_conv)
            final_results_raw[1] += energy_conv
            final_results_raw[2] += emission_conv
            final_results_raw[3] = amount_after_conversion 

        # Recalculate totals from data_raw, which now includes the distinct "Insurance" row and potentially "chem_convert_to_H2"
        # Sum all components from data_raw, excluding the final "TOTAL" row itself for these sums
        total_opex_money = sum(row[1] for row in data_raw if row[0] != "TOTAL" and row[0] != "Insurance") # Sum actual OPEX from processes
        total_capex_money = sum(row[2] for row in data_raw if row[0] != "TOTAL")
        total_carbon_tax_money = sum(row[3] for row in data_raw if row[0] != "TOTAL")
        total_energy = sum(row[4] for row in data_raw if row[0] != "TOTAL")
        total_emissions = sum(row[5] for row in data_raw if row[0] != "TOTAL")
        total_spoilage_loss = sum(row[7] for row in data_raw if row[0] != "TOTAL") # Sum all losses

        # Now, calculate total_money by explicitly adding total_insurance_money
        total_money = total_opex_money + total_capex_money + total_carbon_tax_money + total_insurance_money

        # Update the existing "TOTAL" row in data_raw
        total_row_index = -1
        for i, row in enumerate(data_raw):
            if row[0] == "TOTAL":
                total_row_index = i
                break
        
        if total_row_index != -1:
            data_raw[total_row_index] = ["TOTAL", total_opex_money, total_capex_money, total_carbon_tax_money, total_energy, total_emissions, final_chem_kg_denominator, total_spoilage_loss]
        else:
            # Fallback if "TOTAL" row was somehow missing initially. This shouldn't happen with updated total_chem_base.
            data_raw.append(["TOTAL", total_opex_money, total_capex_money, total_carbon_tax_money, total_energy, total_emissions, final_chem_kg_denominator, total_spoilage_loss])


        final_energy_output_mj = final_chem_kg_denominator * HHV_chem[fuel_type] # Corrected variable name
        final_energy_output_gj = final_energy_output_mj / 1000

        # Now, create data_with_all_columns for charting/detailed display
        data_with_all_columns = []
        for row in data_raw:
            process_label_raw = row[0]
            current_opex = float(row[1])
            current_capex = float(row[2])
            current_carbon_tax = float(row[3])
            current_energy = float(row[4])
            current_emission = float(row[5])
            current_chem_kg_at_step = float(row[6])
            current_bog_loss = float(row[7])

            opex_per_kg = 0.0
            insurance_per_kg = 0.0
            
            # This logic correctly separates the "Insurance" entry from regular OPEX
            if process_label_raw == "Insurance":
                insurance_per_kg = current_opex / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0.0
                opex_per_kg = 0.0 # Insurance is not counted as regular OPEX in the stacked bar for this row
            else:
                opex_per_kg = current_opex / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0.0
                insurance_per_kg = 0.0 # For all other rows, insurance component is zero for this calculation

            capex_per_kg = current_capex / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0
            carbon_tax_per_kg = current_carbon_tax / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0

            cost_per_kg_total = opex_per_kg + capex_per_kg + carbon_tax_per_kg + insurance_per_kg # Sum all parts for this specific row's total

            current_total_cost_row = current_opex + current_capex + current_carbon_tax # This reflects the sum of reported totals for the row
            cost_per_gj = current_total_cost_row / final_energy_output_gj if final_energy_output_gj > 0 else 0
            emission_per_kg = current_emission / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0
            emission_per_gj = current_emission / final_energy_output_gj if final_energy_output_gj > 0 else 0
            new_row_with_additions = [
                process_label_raw, current_opex, current_capex, current_carbon_tax, current_energy, current_emission,
                current_chem_kg_at_step, current_bog_loss, opex_per_kg, capex_per_kg, carbon_tax_per_kg, insurance_per_kg,
                cost_per_kg_total, cost_per_gj, emission_per_kg, emission_per_gj
            ]
            data_with_all_columns.append(new_row_with_additions)

        relabeled_data = []
        for row in data_with_all_columns:
            relabel_key = row[0]
            new_label = label_map.get(relabel_key, relabel_key)
            relabeled_data.append([new_label] + row[1:])
        
        # Prepare data for charts: exclude 'TOTAL' and 'Initial Production (Placeholder)'
        data_for_cost_chart_display = [
            row for row in relabeled_data if row[0] not in ["TOTAL", "Initial Production (Placeholder)"]
        ]

        emission_chart_exclusions = ["TOTAL", "Initial Production (Placeholder)", "Insurance"]
        data_for_emission_chart = [row for row in relabeled_data if row[0] not in emission_chart_exclusions]

        # Use the combined total_money for summary
        chem_cost = total_money / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0
        chem_energy = total_energy / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0
        chem_CO2e = total_emissions / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0

        cost_overlay_text = ""
        if hydrogen_production_cost > 0:
            # For the overlay, use the total_money (which includes insurance) for transport cost
            ratio_cost = chem_cost / hydrogen_production_cost
            cost_overlay_text = (
                f"Context:\n"
                f"• Production Cost in {start}: ${hydrogen_production_cost:.2f}/kg*\n"
                f"• Total Transport Cost: ${chem_cost:.2f}/kg\n"
                f"• Transport cost is {ratio_cost:.1f} times the production cost.\n\n"
                f"*These costs are estimates. Take with a pinch of salt.\n"
                f" Working to improve this."
            )

        emission_overlay_text = ""
        if SMR_EMISSIONS_KG_PER_KG_H2 > 0:
            ratio_emission = chem_CO2e / SMR_EMISSIONS_KG_PER_KG_H2
            emission_overlay_text = (
                f"Context:\n"
                f"• Gray Hydrogen (SMR) Emission: {SMR_EMISSIONS_KG_PER_KG_H2:.2f} kg CO2eq/kg\n"
                f"• Total Transport Emission: {chem_CO2e:.2f} kg CO2eq/kg\n"
                f"• Transport emission is {ratio_emission:.1f} times the SMR emission."
            )

        new_detailed_headers = ["Process Step", "Opex ($)", "Capex ($)", "Carbon Tax ($)", "Energy (MJ)", "CO2eq (kg)", "Chem (kg)", "BOG (kg)", "Opex/kg ($/kg)", "Capex/kg ($/kg)", "Carbon Tax/kg ($/kg)", "Insurance/kg ($/kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "CO2eq/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
        opex_per_kg_for_chart_idx = new_detailed_headers.index("Opex/kg ($/kg)")
        capex_per_kg_for_chart_idx = new_detailed_headers.index("Capex/kg ($/kg)")
        carbon_tax_per_kg_for_chart_idx = new_detailed_headers.index("Carbon Tax/kg ($/kg)")
        insurance_per_kg_for_chart_idx = new_detailed_headers.index("Insurance/kg ($/kg)")
        eco2_per_kg_for_chart_idx = new_detailed_headers.index("CO2eq/kg (kg/kg)")
        cost_chart_base64 = create_breakdown_chart(
            data_for_cost_chart_display,
            opex_per_kg_for_chart_idx,
            capex_per_kg_for_chart_idx,
            carbon_tax_per_kg_for_chart_idx,
            insurance_per_kg_for_chart_idx, # Ensure this index is passed
            'Cost Breakdown per kg of Delivered Fuel',
            'Cost ($/kg)',
            overlay_text=cost_overlay_text,
            is_emission_chart=False
        )        

        emission_chart_base64 = create_breakdown_chart(
            data_for_emission_chart,
            eco2_per_kg_for_chart_idx,      # Emissions chart uses this as its primary value
            eco2_per_kg_for_chart_idx,      # Placeholder, will be ignored for emission charts
            eco2_per_kg_for_chart_idx,      # Placeholder, will be ignored for emission charts
            eco2_per_kg_for_chart_idx,      # Placeholder, will be ignored for emission charts
            'CO2eq Breakdown per kg of Delivered Fuel',
            'CO2eq (kg/kg)',
            overlay_text=emission_overlay_text,
            is_emission_chart=True
        )
        summary1_data = [
            ["Cost ($/kg chemical)", f"{chem_cost:.2f}"],
            ["Consumed Energy (MJ/kg chemical)", f"{chem_energy:.2f}"],
            ["Emission (kg CO2eq/kg chemical)", f"{chem_CO2e:.2f}"]
        ]

        summary2_data = [
            ["Cost ($/GJ)", f"{total_money / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Energy consumed (MJ_in/GJ_out)", f"{total_energy / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Emission (kg CO2eq/GJ)", f"{total_emissions / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"]
        ]

        assumed_prices_data = [
            [f"Electricity Price at {start}*", f"{start_electricity_price[2]:.4f} $/MJ"],
            [f"Electricity Price at {end}*", f"{end_electricity_price[2]:.4f} $/MJ"],
            [f"Diesel Price at {start}", f"{diesel_price_start:.2f} $/gal"],
            [f"Diesel Price at {end_port_name}", f"{diesel_price_end:.2f} $/gal"],
            [f"Marine Fuel ({marine_fuel_choice}) Price at {start_port_name}*", f"{dynamic_price:.2f} $/ton"],
            [f"Green H2 Production Price at {start}*", f"{hydrogen_production_cost:.2f} $/kg"],
        ]
        csv_data = [new_detailed_headers] + detailed_data_formatted
        response = {
            "status": "success",
            "map_data": {
                "coor_start": {"lat": coor_start_lat, "lng": coor_start_lng},
                "coor_end": {"lat": coor_end_lat, "lng": coor_end_lng},
                "start_port": {"lat": start_port_lat, "lng": start_port_lng, "name": start_port_name},
                "end_port": {"lat": end_port_lat, "lng": end_port_lng, "name": end_port_name},
                "road_route_start_coords": road_route_start_coords,
                "road_route_end_coords": road_route_end_coords,
                "sea_route_coords": searoute_coor
            },
            "table_data": {
                "detailed_headers": new_detailed_headers,
                "detailed_data": detailed_data_formatted,
                "summary1_headers": ["Metric", "Value"], "summary1_data": summary1_data,
                "summary2_headers": ["Per Energy Output", "Value"], "summary2_data": summary2_data,
                "assumed_prices_headers": ["Assumed Price", "Value"], "assumed_prices_data": assumed_prices_data
            },
            "csv_data": csv_data, # Now csv_data is defined
            "charts": {
                "cost_chart_base64": cost_chart_base64,
                "emission_chart_base64": emission_chart_base64
            }
        }
        return response

    elif commodity_type == 'food':
        food_type = inputs.get('food_type')
        shipment_size_containers = inputs.get('shipment_size_containers', 10)
        current_food_params = food_params[food_type]
        food_name_for_lookup = current_food_params["name"]        
        start_country = get_country_from_coords(coor_start_lat, coor_start_lng) or start
        end_country = get_country_from_coords(coor_end_lat, coor_end_lng) or end
        price_start = openai_get_food_price(food_name_for_lookup, start_country)
        price_end = openai_get_food_price(food_name_for_lookup, end_country)
        price_start_text = f"${price_start:.2f}/kg" if price_start is not None else "Not available"
        price_end_text = f"${price_end:.2f}/kg" if price_end is not None else "Not available"
        
        final_commodity_kg = 0 # Will be updated after LCA run
        total_opex_money = 0
        total_capex_money = 0
        total_energy = 0
        total_emissions = 0
        total_carbon_tax_money = 0 # Ensure this is initialized

        # total_ship_container_capacity and related propulsion_cost/reefer_service_cost_per_container
        # are now used *within* food_sea_transport and calculate_single_reefer_service_cost,
        # so they don't need to overwrite data_raw here.
        # Keeping these variables defined as they might be used for other context or comparisons,
        # but the logic for modifying data_raw directly should be removed.
        total_ship_container_capacity = math.floor(total_ship_volume / 76)
        
        # Calculate initial_weight as before
        initial_weight = shipment_size_containers * current_food_params['general_params']['cargo_per_truck_kg']
        
        # Call total_food_lca; it should correctly populate data_raw including all costs and insurance
        data_raw = total_food_lca(
            initial_weight, current_food_params, CARBON_TAX_PER_TON_CO2_DICT, 
            HHV_diesel, diesel_density, CO2e_diesel,
            food_name_for_lookup, searoute_coor, port_to_port_duration
        )
        
        # Recalculate totals after all steps are processed and potentially re-inserted by total_food_lca
        total_opex_money = sum(row[1] for row in data_raw if row[0] != "TOTAL" and row[0] != "Insurance")
        total_capex_money = sum(row[2] for row in data_raw if row[0] != "TOTAL")
        total_carbon_tax_money = sum(row[3] for row in data_raw if row[0] != "TOTAL")
        total_energy = sum(row[4] for row in data_raw if row[0] != "TOTAL")
        total_emissions = sum(row[5] for row in data_raw if row[0] != "TOTAL")
        total_spoilage_loss = sum(row[7] for row in data_raw if row[0] != "TOTAL")
        total_insurance_money = sum(row[1] for row in data_raw if row[0] == "Insurance") # Sum value stored in 'opex_m' for 'Insurance' row

        final_commodity_kg = data_raw[-1][6] if data_raw and len(data_raw[-1]) > 6 else 0.0 # From the last (TOTAL) row

        # Calculate total_money as the sum of all distinct cost components
        total_money = total_opex_money + total_capex_money + total_carbon_tax_money + total_insurance_money

        # Sum total insurance from the dedicated "Insurance" row in data_raw
        total_insurance_money = sum(row[1] for row in data_raw if row[0] == "Insurance") # Sum value stored in 'opex_m' for 'Insurance' row

        # Final delivered quantity from the last (TOTAL) row of data_raw
        final_commodity_kg = data_raw[-1][6] if data_raw and len(data_raw[-1]) > 6 else 0.0

        # Calculate total_money as the sum of all distinct cost components
        total_money = total_opex_money + total_capex_money + total_carbon_tax_money + total_insurance_money

        local_sourcing_results = None
        green_premium_data = None
        farm_name = None
        price_farm = None

        farm_region = openai_get_nearest_farm_region(current_food_params['name'], end_country)

        if farm_region:
            farm_lat = farm_region['latitude']
            farm_lon = farm_region['longitude']
            farm_name = farm_region['farm_region_name']
            price_farm = openai_get_food_price(current_food_params['name'], farm_name)
            
            local_dist_str, local_dur_str = inland_routes_cal((farm_lat, farm_lon), (coor_end_lat, coor_end_lng))
            local_distance_km = float(re.sub(r'[^\d.]', '', local_dist_str))
            local_duration_mins = time_to_minutes(local_dur_str)
            
            comparison_weight = final_commodity_kg
            precooling_full_params = {**current_food_params.get('precooling_params', {}), **current_food_params.get('general_params', {})}
            local_precool_opex, local_precool_capex, local_precool_carbon_tax, local_precool_energy, local_precool_emissions, _, _, _ = food_precooling_process(comparison_weight, (precooling_full_params, end_electricity_price, CO2e_end, facility_capacity, end_country_name, CARBON_TAX_PER_TON_CO2_DICT))
            
            freezing_full_params = {**current_food_params.get('freezing_params', {}), **current_food_params.get('general_params', {})} 
            local_freeze_opex, local_freeze_capex, local_freeze_carbon_tax, local_freeze_energy, local_freeze_emissions, _, _, _ = food_freezing_process(comparison_weight, (freezing_full_params, end_local_temperature, end_electricity_price, CO2e_end, facility_capacity, end_country_name, CARBON_TAX_PER_TON_CO2_DICT))
            
            local_trucking_args = (current_food_params, local_distance_km, local_duration_mins, diesel_price_end, HHV_diesel, diesel_density, CO2e_diesel, end_local_temperature, driver_daily_salary_end, annual_working_days, MAINTENANCE_COST_PER_KM_TRUCK, truck_capex_params, end_country_name, CARBON_TAX_PER_TON_CO2_DICT) 
            local_trucking_opex, local_trucking_capex, local_trucking_carbon_tax, local_trucking_energy, local_trucking_emissions, _, _, _ = food_road_transport(comparison_weight, local_trucking_args)
            
            local_total_money = (local_precool_opex + local_precool_capex + local_precool_carbon_tax) + \
                                (local_freeze_opex + local_freeze_capex + local_freeze_carbon_tax) + \
                                (local_trucking_opex + local_trucking_capex + local_trucking_carbon_tax) 
            local_total_emissions = local_precool_emissions + local_freeze_emissions + local_trucking_emissions            
            local_sourcing_results = {
                "source_name": farm_name,
                "distance_km": local_distance_km,
                "cost_per_kg": local_total_money / comparison_weight if comparison_weight > 0 else 0,
                "emissions_per_kg": local_total_emissions / comparison_weight if comparison_weight > 0 else 0
            }        

            if price_farm is None:
                price_farm = price_end

            green_premium_data = None
            if price_farm is not None and price_start is not None and final_commodity_kg > 0 and comparison_weight > 0:
                cost_international_transport_per_kg = total_money / final_commodity_kg
                landed_cost_international_per_kg = price_start + cost_international_transport_per_kg

                cost_local_sourcing_per_kg = local_total_money / comparison_weight
                landed_cost_local_per_kg = price_farm + cost_local_sourcing_per_kg

                emissions_international_per_kg = total_emissions / final_commodity_kg
                emissions_local_per_kg = local_total_emissions / comparison_weight

                cost_difference_per_kg = landed_cost_local_per_kg - landed_cost_international_per_kg
                emissions_saved_per_kg = emissions_international_per_kg - emissions_local_per_kg

                green_premium_usd_per_ton_co2 = "N/A (No emission savings)"
                if emissions_saved_per_kg > 0:
                    premium_raw = cost_difference_per_kg / emissions_saved_per_kg
                    green_premium_usd_per_ton_co2 = f"${(premium_raw * 1000):,.2f}"
                elif cost_difference_per_kg < 0:
                    green_premium_usd_per_ton_co2 = "Negative (Win-Win Scenario)"
                
                green_premium_data = [
                    ["Landed Cost (International Shipment)", f"${landed_cost_international_per_kg:.2f}/kg"],
                    ["Landed Cost (Local Sourcing)", f"${landed_cost_local_per_kg:.2f}/kg"],
                    ["Emissions (International Shipment)", f"{emissions_international_per_kg:.2f} kg CO₂e/kg"],
                    ["Emissions (Local Sourcing)", f"{emissions_local_per_kg:.2f} kg CO₂e/kg"],
                    ["Green Premium (Cost per ton of CO₂ saved)", f"{green_premium_usd_per_ton_co2}"]
                ]
                    
        energy_content = current_food_params.get('general_params', {}).get('energy_content_mj_per_kg', 1)
        final_energy_output_mj = final_commodity_kg * energy_content
        final_energy_output_gj = final_energy_output_mj / 1000

        data_with_all_columns = []
        for row in data_raw:
            if len(row) < 8: # Check for 8 columns now
                print(f"Warning: Food row has insufficient data points: {row}. Skipping 'per unit' calculations for this row.")
                data_with_all_columns.append(list(row) + [0]*(16 - len(row)))
                continue

            process_label_raw = row[0]
            current_opex = float(row[1])
            current_capex = float(row[2])
            current_carbon_tax = float(row[3])
            current_energy_total = float(row[4])
            current_emission_total = float(row[5])
            current_commodity_kg_at_step = float(row[6]) # This is the `A` value for the step
            current_spoilage_loss = float(row[7])

            opex_per_kg = 0.0
            insurance_per_kg = 0.0 

            if process_label_raw == "Insurance": # This is the row from the distinct insurance calculation
                insurance_per_kg = current_opex / final_commodity_kg if final_commodity_kg > 0 else 0.0
                opex_per_kg = 0.0 # For the 'Insurance' row itself, OPEX component is zero
            else:
                opex_per_kg = current_opex / final_commodity_kg if final_commodity_kg > 0 else 0.0
                insurance_per_kg = 0.0 # For all other rows, insurance component is zero for this calculation

            capex_per_kg = current_capex / final_commodity_kg if final_commodity_kg > 0 else 0
            carbon_tax_per_kg = current_carbon_tax / final_commodity_kg if final_commodity_kg > 0 else 0
            
            cost_per_kg_total = opex_per_kg + capex_per_kg + carbon_tax_per_kg + insurance_per_kg 
            
            current_total_cost_row = current_opex + current_capex + current_carbon_tax 
            
            cost_per_gj = current_total_cost_row / final_energy_output_gj if final_energy_output_gj > 0 else 0
            emission_per_kg = current_emission_total / final_commodity_kg if final_commodity_kg > 0 else 0
            emission_per_gj = current_emission_total / final_energy_output_gj if final_energy_output_gj > 0 else 0

            new_row_with_additions = [
                process_label_raw, 
                current_opex, current_capex, current_carbon_tax, current_energy_total, current_emission_total, current_commodity_kg_at_step, current_spoilage_loss, 
                opex_per_kg, capex_per_kg, carbon_tax_per_kg, insurance_per_kg, 
                cost_per_kg_total, cost_per_gj, emission_per_kg, emission_per_gj 
            ]
            data_with_all_columns.append(new_row_with_additions)


        relabeled_data = []
        for row in data_with_all_columns:
            relabel_key = row[0]
            new_label = label_map.get(relabel_key, relabel_key)
            relabeled_data.append([new_label] + row[1:])

        data_for_cost_chart_display = [
            row for row in relabeled_data if row[0] not in ["TOTAL", "Harvesting & Preparation"] # Exclude "Harvesting & Preparation"
        ]
        
        emission_chart_exclusions_food = ["TOTAL", "Harvesting & Preparation", "Insurance"] 
        data_for_emission_chart = [row for row in relabeled_data if row[0] not in emission_chart_exclusions_food]

        detailed_data_formatted = []
        for row in relabeled_data: 
            formatted_row = [row[0]] 
            for item in row[1:]: 
                if isinstance(item, (int, float)):
                    formatted_row.append(f"{item:,.2f}")
                else:
                    formatted_row.append(item)
            detailed_data_formatted.append(formatted_row)

        new_detailed_headers = ["Process Step", "Opex ($)", "Capex ($)", "Carbon Tax ($)", "Energy (MJ)", "eCO2 (kg)", "Commodity (kg)", "Spoilage (kg)", "Opex/kg ($/kg)", "Capex/kg ($/kg)", "Carbon Tax/kg ($/kg)", "Insurance/kg ($/kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "eCO2/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
        opex_per_kg_for_chart_idx = new_detailed_headers.index("Opex/kg ($/kg)")
        capex_per_kg_for_chart_idx = new_detailed_headers.index("Capex/kg ($/kg)")
        carbon_tax_per_kg_for_chart_idx = new_detailed_headers.index("Carbon Tax/kg ($/kg)")
        insurance_per_kg_for_chart_idx = new_detailed_headers.index("Insurance/kg ($/kg)") 
        eco2_per_kg_for_chart_idx = new_detailed_headers.index("eCO2/kg (kg/kg)")
        
        cost_per_kg = total_money / final_commodity_kg if final_commodity_kg > 0 else 0
        energy_per_kg = total_energy / final_commodity_kg if final_commodity_kg > 0 else 0
        emissions_per_kg = total_emissions / final_commodity_kg if final_commodity_kg > 0 else 0

        summary1_data = [
            ["Cost ($/kg food)", f"{cost_per_kg:.2f}"],
            ["Consumed Energy (MJ/kg food)", f"{energy_per_kg:.2f}"],
            ["Emission (kg CO2eq/kg food)", f"{emissions_per_kg:.2f}"]
        ]

        summary2_data = [
            ["Cost ($/GJ)", f"{total_money / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Energy consumed (MJ_in/GJ_out)", f"{total_energy / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Emission (kg CO2eq/GJ)", f"{total_emissions / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"]
        ]

        assumed_prices_data = [
            [f"Electricity Price at {start}*", f"{start_electricity_price[2]:.4f} $/MJ"],
            [f"Electricity Price at {end}*", f"{end_electricity_price[2]:.4f} $/MJ"],
            [f"Diesel Price at {start}", f"{diesel_price_start:.2f} $/gal"],
            [f"Diesel Price at {end_port_name}", f"{diesel_price_end:.2f} $/gal"],
            [f"Marine Fuel ({marine_fuel_choice}) Price at {start_port_name}*", f"{dynamic_price:.2f} $/ton"],
        ]
        if 'farm_name' in locals() and 'price_farm' in locals() and price_farm is not None:
            assumed_prices_data.append([f"{food_name_for_lookup} Price at {farm_name}*", f"${price_farm:.2f}/kg"])

        cost_overlay_text = (
            f"Context:\n"
            f"• Retail price in {start_country}: {price_start_text}\n"
            f"• Retail price in {end_country}: {price_end_text}"
        )
        
        emission_overlay_text = ""
        production_co2e = current_food_params.get('general_params', {}).get('production_CO2e_kg_per_kg', 0)

        if production_co2e > 0:
            ratio_emission = emissions_per_kg / production_co2e
            emission_overlay_text = (
                f"Context:\n"
                f"• Logistics Emissions: {emissions_per_kg:.2f} kg CO2eq/kg\n"
                f"• Farming Emissions alone for {current_food_params['name']}: {production_co2e:.2f} kg CO2eq/kg\n"
                f"• Logistics add {ratio_emission:.1f}X the farming emissions."
            )

        cost_chart_base64 = create_breakdown_chart(
            data_for_cost_chart_display, 
            opex_per_kg_for_chart_idx,
            capex_per_kg_for_chart_idx,
            carbon_tax_per_kg_for_chart_idx,
            insurance_per_kg_for_chart_idx, 
            'Cost Breakdown per kg of Delivered Food',
            'Cost ($/kg)',
            overlay_text=cost_overlay_text,
            is_emission_chart=False
        )
        emission_chart_base64 = create_breakdown_chart(
            data_for_emission_chart, 
            eco2_per_kg_for_chart_idx,      
            eco2_per_kg_for_chart_idx,      
            eco2_per_kg_for_chart_idx,      
            eco2_per_kg_for_chart_idx,      
            'CO2eq Breakdown per kg of Delivered Food',
            'CO2eq (kg/kg)',
            overlay_text=emission_overlay_text,
            is_emission_chart=True
        )        
            
        response = {
            "status": "success",
            "map_data": { "coor_start": {"lat": coor_start_lat, "lng": coor_start_lng}, "coor_end": {"lat": coor_end_lat, "lng": coor_end_lng}, "start_port": {"lat": start_port_lat, "lng": start_port_lng, "name": start_port_name}, "end_port": {"lat": end_port_lat, "lng": end_port_lng, "name": end_port_name}, "road_route_start_coords": road_route_start_coords, "road_route_end_coords": road_route_end_coords, "sea_route_coords": searoute_coor },
            "table_data": { 
                "detailed_headers": new_detailed_headers, "detailed_data": detailed_data_formatted, 
                "summary1_headers": ["Metric", "Value"], "summary1_data": summary1_data, 
                "summary2_headers": ["Per Energy Output", "Value"], "summary2_data": summary2_data, 
                "assumed_prices_headers": ["Assumed Price", "Value"], "assumed_prices_data": assumed_prices_data,
                "green_premium_headers": ["Metric", "Value"],
                "green_premium_data": green_premium_data
            },
            "csv_data": [new_detailed_headers] + detailed_data_formatted,
            "charts": { "cost_chart_base64": cost_chart_base64, "emission_chart_base64": emission_chart_base64 },
            "local_sourcing_comparison": local_sourcing_results,
            "food_type": food_type
        }
        return response    

# --- Flask API Endpoint ---
@app.route('/calculate', methods=['POST'])
def calculate_endpoint():
    try:
        inputs = request.get_json()
        if not inputs:
            return jsonify({"status": "error", "message": "Invalid JSON input"}), 400
        results = run_lca_model(inputs)
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Main execution block ---
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, port=5000)
