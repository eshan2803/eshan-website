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
import gc  # Add garbage collection for memory management

# Import all constants from constants.py
from constants import *

# Import parallel API client
from async_api_client import run_parallel_api_calls

# ===== IMPORT NEW MODULES =====
# Utility functions
from utils.helpers import (
    decode_polyline as decode_polyline_module,
    time_to_minutes as time_to_minutes_module,
    detect_canal_transit as detect_canal_transit_module,
    calculate_route_risk_multiplier,
    get_diesel_price as get_diesel_price_module,
    calculate_dynamic_cop as calculate_dynamic_cop_module,
    straight_dis as straight_dis_module,
    get_country_from_coords as get_country_from_coords_helper_module  # NEW
)

from utils.api_helpers import (  # NEW MODULE
    extract_lat_long as extract_lat_long_helper_module,
    extract_route_coor as extract_route_coor_helper_module,
    inland_routes_cal as inland_routes_cal_helper_module,
    local_temperature as local_temperature_helper_module,
    carbon_intensity as carbon_intensity_helper_module
)

from utils.ship_helpers import (  # NEW MODULE
    calculate_ship_power_kw as calculate_ship_power_kw_helper_module
)

from utils.conversions import (
    PH2_pressure_fnc as PH2_pressure_fnc_module,
    PH2_density_fnc as PH2_density_fnc_module,
    multistage_compress as multistage_compress_module,
    PH2_transport_energy,
    PH2_pressure_fnc_simple,  # NEW
    PH2_density_fnc_simple,  # NEW
    PH2_density_fnc_helper_simple,  # NEW
    PH2_transport_energy_simple,  # NEW
    liquification_data_fitting as liquification_data_fitting_helper_module  # NEW
)

# Service integrations
from services.geocoding import (
    get_country_from_coords as get_country_from_coords_module,
    geocode_address
)

from services.openai_service import (
    openai_get_nearest_port as openai_get_nearest_port_module,
    openai_get_hydrogen_production_cost,
    openai_get_electricity_price as openai_get_electricity_price_helper_module,  # NEW
    openai_get_hydrogen_cost as openai_get_hydrogen_cost_helper_module,  # NEW
    openai_get_marine_fuel_price as openai_get_marine_fuel_price_helper_module,  # NEW
    openai_get_food_price as openai_get_food_price_helper_module,  # NEW
    openai_get_nearest_farm_region as openai_get_nearest_farm_region_helper_module  # NEW
)

from services.weather_service import (
    get_weather_temperature,
    estimate_ambient_temperature
)

from services.carbon_service import (
    get_carbon_intensity as get_carbon_intensity_module,
    calculate_electricity_emissions
)

# Business logic models
from models.ship_calculations import (
    calculate_ship_speed,
    calculate_ship_fuel_consumption,
    calculate_ship_emissions,
    estimate_ship_gross_tonnage
)

from models.insurance_model import (
    calculate_insurance_cost,
    calculate_total_insurance_and_fees
)

from models.capex_calculations import (
    calculate_liquefaction_capex as calc_liq_capex_module,
    calculate_storage_capex as calc_storage_capex_module,
    calculate_loading_unloading_capex as calc_loading_capex_module,
    calculate_voyage_overheads as calc_voyage_overheads_module,
    calculate_food_infra_capex as calc_food_capex_module
)

# Phase 4: Process modules
from models.fuel_processes import (
    site_A_chem_production,
    site_A_chem_liquification,
    fuel_pump_transfer,
    fuel_road_transport,
    fuel_storage,
    chem_loading_to_ship,
    port_to_port,
    chem_convert_to_H2,
    PH2_pressurization_at_site_A,
    PH2_site_A_to_port_A,
    port_A_liquification,
    H2_pressurization_at_port_B,
    PH2_port_B_to_site_B,
    PH2_storage_at_site_B
)

from models.food_processes import (
    food_harvest_and_prep,
    food_freezing_process,
    food_road_transport,
    food_precooling_process,
    calculate_ca_energy_kwh,
    food_sea_transport,
    food_cold_storage,
    calculate_single_reefer_service_cost,
    calculate_food_infra_capex as calculate_food_infra_capex_nested
)

from models.orchestration import (
    optimization_chem_weight,
    constraint,
    total_chem_base,
    total_food_lca
)

# --- Initialize Flask App ---
app = Flask(__name__)
# Enhanced CORS configuration with explicit method support
CORS(app, resources={
    r"/calculate": {
        "origins": ["https://eshansingh.xyz", "http://localhost:8000", "http://127.0.0.1:8000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False
    }
})

# Initialize API cache
api_cache = {}

def clean_cache_if_needed():
    """Remove oldest cache entries if cache grows too large"""
    global api_cache
    if len(api_cache) > MAX_CACHE_SIZE:
        # Remove 20% of oldest entries (simple FIFO approach)
        keys_to_remove = list(api_cache.keys())[:int(MAX_CACHE_SIZE * 0.2)]
        for key in keys_to_remove:
            del api_cache[key]
        print(f"[INFO] Cache cleaned. Removed {len(keys_to_remove)} entries. Cache size now: {len(api_cache)}")
        gc.collect()

def fetch_api_data_parallel(start_address, end_address):
    """
    Fetch all API data in parallel with caching.

    Args:
        start_address: Starting location address
        end_address: Ending location address

    Returns:
        dict: All API data from parallel calls
    """
    # Create cache key from addresses
    cache_key = f"api_data_{start_address}_{end_address}"

    # Check cache first
    if cache_key in api_cache:
        print(f"[INFO] Using cached API data for {start_address} -> {end_address}")
        return api_cache[cache_key]

    # Fetch data in parallel
    print(f"[INFO] Fetching API data in parallel for {start_address} -> {end_address}")
    api_data = run_parallel_api_calls(start_address, end_address)

    # Cache the result
    api_cache[cache_key] = api_data
    clean_cache_if_needed()

    return api_data

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
        cache_key = f"extract_lat_long_{address_or_postalcode}"
        if cache_key in api_cache:
            return api_cache[cache_key]

        endpoint = f'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': address_or_postalcode, 'key': API_KEY_GOOGLE}
        url = f'{endpoint}?{urlencode(params)}'
        r = requests.get(url)
        if r.status_code not in range(200, 299):
            cached_value = (None, None, None)
            api_cache[cache_key] = cached_value
            return cached_value
        data = r.json()
        if not data.get('results'):
            cached_value = (None, None, None)
            api_cache[cache_key] = cached_value
            return cached_value
        latlng = data['results'][0]['geometry']['location']
        state_name = next((comp['long_name'] for comp in data['results'][0]['address_components'] if 'administrative_area_level_1' in comp['types']), None)
        
        cached_value = (latlng.get("lat"), latlng.get("lng"), state_name)
        api_cache[cache_key] = cached_value
        return cached_value

    # DELETED: decode_polyline - now imported from utils.helpers as decode_polyline_module

    def extract_route_coor(origin, destination):
        endpoint = "https://maps.googleapis.com/maps/api/directions/json"
        params = {'origin': f"{origin[0]},{origin[1]}", 'destination': f"{destination[0]},{destination[1]}", 'key': API_KEY_GOOGLE, 'mode': 'driving'}
        response = requests.get(f'{endpoint}?{urlencode(params)}')
        if response.status_code not in range(200, 299) or not response.json().get('routes'):
            return []
        points = response.json()['routes'][0]['overview_polyline']['points']
        return decode_polyline(points)

    def openai_get_nearest_port(port_coor_str):
        cache_key = f"nearest_port_{port_coor_str}"
        if cache_key in api_cache:
            return api_cache[cache_key]        
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY_OPENAI)
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
            return None, None, None # Cache None results too, if appropriate

        cached_value = (lat, lon, port_name)
        api_cache[cache_key] = cached_value
        return cached_value

    def inland_routes_cal(start_coords, end_coords):
        cache_key = f"inland_routes_cal_{start_coords[0]},{start_coords[1]}_{end_coords[0]},{end_coords[1]}"
        if cache_key in api_cache:
            return api_cache[cache_key]

        endpoint = f'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {"origins": f"{start_coords[0]},{start_coords[1]}", "destinations": f"{end_coords[0]},{end_coords[1]}", "key": API_KEY_GOOGLE}
        output = requests.get(f'{endpoint}?{urlencode(params)}').json()
        if output.get('rows') and output['rows'][0].get('elements') and output['rows'][0]['elements'][0].get('distance'):
            distance_text = output['rows'][0]['elements'][0]['distance']['text']
            duration_text = output['rows'][0]['elements'][0]['duration']['text']
            cached_value = (distance_text, duration_text)
            api_cache[cache_key] = cached_value
            return cached_value
        
        cached_value = ("0 km", "0 min")
        api_cache[cache_key] = cached_value
        return cached_value

    # DELETED: time_to_minutes - now imported from utils.helpers as time_to_minutes_module

    def local_temperature(lat, lon):
        cache_key = f"local_temperature_{lat}_{lon}"
        if cache_key in api_cache:
            return api_cache[cache_key]

        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY_WEATHER}&q={lat},{lon}"
        response = requests.get(url)
        if response.status_code == 200:
            temp_c = response.json()['current']['temp_c']
            api_cache[cache_key] = temp_c
            return temp_c
        
        default_temp = 25.0
        api_cache[cache_key] = default_temp
        return default_temp

    def carbon_intensity(lat, lng):
        cache_key = f"carbon_intensity_{lat}_{lng}"
        if cache_key in api_cache:
            return api_cache[cache_key]

        url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
        headers = {"auth-token": API_KEY_ELECTRICITYMAP}
        response = requests.get(url, headers=headers, params={"lat": lat, "lon": lng})
        if response.status_code == 200:
            intensity = float(response.json()['carbonIntensity'])
            api_cache[cache_key] = intensity
            return intensity
        
        default_intensity = 200.0
        api_cache[cache_key] = default_intensity
        return default_intensity

    # DELETED: get_country_from_coords - now imported from services.geocoding as get_country_from_coords_module
    # DELETED: get_diesel_price - now imported from utils.helpers as get_diesel_price_module
    # DELETED: openai_get_electricity_price - now imported from services.openai_service as openai_get_electricity_price_helper_module
    # DELETED: openai_get_hydrogen_cost - now imported from services.openai_service as openai_get_hydrogen_cost_helper_module
    # DELETED: openai_get_marine_fuel_price - now imported from services.openai_service as openai_get_marine_fuel_price_helper_module
    # DELETED: calculate_ship_power_kw - now imported from utils.ship_helpers as calculate_ship_power_kw_helper_module
    
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

    # DELETED: calculate_total_insurance_cost - now imported from models.insurance_model

    # DELETED: calculate_dynamic_cop - now imported from utils.helpers as calculate_dynamic_cop_module

    # Matplotlib chart generation removed - now using Plotly.js on frontend for interactive charts
    # =================================================================
    # <<<                   FUEL PROCESS FUNCTIONS                  >>>
    # =================================================================

    def PH2_pressure_fnc(density): return density * 1.2
    def multistage_compress(pressure): return pressure * 0.05
    def kinematic_viscosity_PH2(pressure): return 1e-5 / (pressure/10)
    def solve_colebrook(Re, epsilon, D): return 0.02
    def PH2_transport_energy(L): return L * 0.001
    def PH2_density_fnc(pressure): return pressure / 1.2
    def PH2_density_fnc_helper(pressure): return 0.25
    #actual process functions
    # DELETED: liquification_data_fitting - now imported from utils.conversions as liquification_data_fitting_helper_module

    # DELETED: site_A_chem_production - now imported from models.fuel_processes
    
    # DELETED: site_A_chem_liquification - now imported from models.fuel_processes
    
    # DELETED: fuel_pump_transfer - now imported from models.fuel_processes

    # DELETED: fuel_road_transport - now imported from models.fuel_processes

    # DELETED: fuel_storage - now imported from models.fuel_processes

    # DELETED: chem_loading_to_ship - now imported from models.fuel_processes

    # DELETED: port_to_port - now imported from models.fuel_processes
    
    # DELETED: chem_convert_to_H2 - now imported from models.fuel_processes

    # DELETED: PH2_pressurization_at_site_A - now imported from models.fuel_processes

    # DELETED: PH2_site_A_to_port_A - now imported from models.fuel_processes

    # DELETED: port_A_liquification - now imported from models.fuel_processes

    # DELETED: H2_pressurization_at_port_B - now imported from models.fuel_processes

    # DELETED: PH2_port_B_to_site_B - now imported from models.fuel_processes

    # DELETED: PH2_storage_at_site_B - now imported from models.fuel_processes

    # DELETED: optimization_chem_weight - now imported from models.orchestration

    # DELETED: constraint - now imported from models.orchestration

    # DELETED: calculate_liquefaction_capex - now imported from models.capex_calculations as calc_liq_capex_module

    # DELETED: calculate_storage_capex - now imported from models.capex_calculations as calc_storage_capex_module

    # DELETED: calculate_loading_unloading_capex - now imported from models.capex_calculations as calc_loading_capex_module

    # DELETED: calculate_voyage_overheads - now imported from models.capex_calculations as calc_voyage_overheads_module

    # DELETED: total_chem_base - now imported from models.orchestration            
  
    # =================================================================
    # <<<                  FOOD PROCESSING FUNCTIONS                >>>
    # =================================================================

    # UPDATED food_harvest_and_prep
    # DELETED: food_harvest_and_prep - now imported from models.food_processes
    
    # DELETED: food_freezing_process - now imported from models.food_processes

    # DELETED: food_road_transport - now imported from models.food_processes

    # DELETED: food_precooling_process - now imported from models.food_processes

    # DELETED: calculate_ca_energy_kwh - now imported from models.food_processes

    # DELETED: food_sea_transport - now imported from models.food_processes
    
    # DELETED: food_cold_storage - now imported from models.food_processes

    # DELETED: calculate_food_infra_capex - now imported from models.food_processes

    # DELETED: total_food_lca - now imported from models.orchestration

    # DELETED: openai_get_food_price - now imported from services.openai_service as openai_get_food_price_helper_module
    # DELETED: openai_get_nearest_farm_region - now imported from services.openai_service as openai_get_nearest_farm_region_helper_module

    # DELETED: detect_canal_transit - now imported from utils.helpers as detect_canal_transit_module

    # DELETED: calculate_single_reefer_service_cost - now imported from models.food_processes

    new_detailed_headers = ["Process Step", "Opex ($)", "Capex ($)", "Carbon Tax ($)", "Energy (MJ)", "CO2eq (kg)", "Chem (kg)", "BOG (kg)", "Opex/kg ($/kg)", "Capex/kg ($/kg)", "Carbon Tax/kg ($/kg)", "Insurance/kg ($/kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "CO2eq/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
    overhead_labels = ["Insurance", "Import Tariffs & Duties", "Financing Costs", "Brokerage & Agent Fees", "Contingency (10%)", "Safety Certifications", "Food Inspections"]

    # =================================================================
    # <<< MAIN CONDITIONAL BRANCH STARTS HERE >>>
    # =================================================================
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

    # ===== PARALLEL API CALLS =====
    # Fetch all API data in parallel instead of sequentially
    api_data = fetch_api_data_parallel(start, end)

    # Extract geocoding data
    coor_start_lat, coor_start_lng, _ = api_data["start_geocode"]
    coor_end_lat, coor_end_lng, _ = api_data["end_geocode"]

    # Extract port data
    start_port_lat, start_port_lng, start_port_name = api_data.get("start_port", (None, None, None))
    end_port_lat, end_port_lng, end_port_name = api_data.get("end_port", (None, None, None))

    # Extract inland routes (already calculated in parallel)
    start_to_port_dist_str, start_to_port_dur_str = api_data.get("inland_route_start", (None, None))
    port_to_end_dist_str, port_to_end_dur_str = api_data.get("inland_route_end", (None, None))

    # Fallback: If parallel calls failed, use original sequential methods
    if not start_port_lat or not start_port_lng:
        start_port_lat, start_port_lng, start_port_name = openai_get_nearest_port(f"{coor_start_lat},{coor_start_lng}")
    if not end_port_lat or not end_port_lng:
        end_port_lat, end_port_lng, end_port_name = openai_get_nearest_port(f"{coor_end_lat},{coor_end_lng}")
    if not start_to_port_dist_str:
        start_to_port_dist_str, start_to_port_dur_str = inland_routes_cal((coor_start_lat, coor_start_lng), (start_port_lat, start_port_lng))
    if not port_to_end_dist_str:
        port_to_end_dist_str, port_to_end_dur_str = inland_routes_cal((end_port_lat, end_port_lng), (coor_end_lat, coor_end_lng))

    # Continue with sea route calculation (not parallelized as it depends on ports)
    _, hydrogen_production_cost = openai_get_hydrogen_cost(f"{coor_start_lat},{coor_start_lng}")
    route = sr.searoute((start_port_lng, start_port_lat), (end_port_lng, end_port_lat), units="nm")
    searoute_coor = [[lat, lon] for lon, lat in route.geometry['coordinates']]
    port_to_port_dis = route.properties['length'] * 1.852
    canal_transits = detect_canal_transit(route)

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
        boiling_point_chem = [20, 239.66, 337.7]; start_temp_kelvin = start_local_temperature + 273.15
        COP_liq_dyn = calculate_dynamic_cop(start_temp_kelvin, boiling_point_chem[fuel_type])
        COP_cooldown_dyn = COP_liq_dyn 
        
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

        all_shared_params_tuple = (
            LH2_plant_capacity, EIM_liquefication, specific_heat_chem,
            start_local_temperature, boiling_point_chem, latent_H_chem,
            COP_liq_dyn, start_electricity_price, CO2e_start, GWP_chem,
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
            EIM_refrig_eff, pipe_metal_specific_heat, COP_cooldown_dyn,
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
            MAINTENANCE_COST_PER_KM_TRUCK,
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
            
            if process_label_raw in overhead_labels:
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

        for row in data_with_all_columns:
            formatted_row = [row[0]] # Keep the label as is
            for item in row[1:]: # Format numeric values
                if isinstance(item, (int, float)):
                    formatted_row.append(f"{item:,.2f}")
                else:
                    formatted_row.append(item)
            detailed_data_formatted.append(formatted_row)        
        
        aggregated_data_for_chart = []
        aggregated_overheads_row = ["Overheads & Fees", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        overhead_per_kg_col_idx = new_detailed_headers.index("Insurance/kg ($/kg)")
        for row in data_with_all_columns:
            label = row[0]
            if label in overhead_labels:
                aggregated_overheads_row[overhead_per_kg_col_idx] += float(row[overhead_per_kg_col_idx])
            elif label not in ["TOTAL", "Initial Production (Placeholder)", "Harvesting & Preparation"]:
                aggregated_data_for_chart.append(row)
        aggregated_data_for_chart.append(aggregated_overheads_row)
        emission_chart_exclusions = [
            "TOTAL", "Initial Production (Placeholder)", "Insurance",
            "Import Tariffs & Duties", "Financing Costs",
            "Brokerage & Agent Fees", "Contingency (10%)", "Safety Certifications",
        ]
        data_for_emission_chart = [row for row in data_with_all_columns if row[0] not in emission_chart_exclusions]

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
                f"*These costs are estimates. Take with a pinch of salt."
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

        opex_per_kg_for_chart_idx = new_detailed_headers.index("Opex/kg ($/kg)")
        capex_per_kg_for_chart_idx = new_detailed_headers.index("Capex/kg ($/kg)")
        carbon_tax_per_kg_for_chart_idx = new_detailed_headers.index("Carbon Tax/kg ($/kg)")
        insurance_per_kg_for_chart_idx = new_detailed_headers.index("Insurance/kg ($/kg)")
        eco2_per_kg_for_chart_idx = new_detailed_headers.index("CO2eq/kg (kg/kg)")
        # Prepare chart data for Plotly.js (interactive charts in browser)
        cost_chart_data = {
            'labels': [row[0] for row in aggregated_data_for_chart],
            'opex': [row[opex_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'capex': [row[capex_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'carbon_tax': [row[carbon_tax_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'insurance': [row[insurance_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'title': 'Cost Breakdown per kg of Delivered Fuel',
            'x_label': 'Cost ($/kg)',
            'overlay_text': cost_overlay_text
        }

        emission_chart_data = {
            'labels': [row[0] for row in data_for_emission_chart],
            'emissions': [row[eco2_per_kg_for_chart_idx] for row in data_for_emission_chart],
            'title': 'CO2eq Breakdown per kg of Delivered Fuel',
            'x_label': 'CO2eq (kg/kg)',
            'overlay_text': emission_overlay_text
        }
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
                "cost_chart_data": cost_chart_data,
                "emission_chart_data": emission_chart_data
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
        final_results_raw, data_raw = total_food_lca(
            initial_weight, current_food_params, CARBON_TAX_PER_TON_CO2_DICT, 
            HHV_diesel, diesel_density, CO2e_diesel,
            food_name_for_lookup, searoute_coor, port_to_port_duration, shipment_size_containers 
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

        # Local sourcing comparison - calculates alternative from nearby farm
        # Re-enabled now that infinite loop bug is fixed
        enable_local_sourcing = True

        farm_region = None
        if enable_local_sourcing:
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

            # Pre-cooling (if needed)
            local_precool_opex = local_precool_capex = local_precool_carbon_tax = local_precool_energy = local_precool_emissions = 0
            if current_food_params['process_flags'].get('needs_precooling', False):
                precooling_full_params = {**current_food_params.get('precooling_params', {}), **current_food_params.get('general_params', {})}
                local_precool_opex, local_precool_capex, local_precool_carbon_tax, local_precool_energy, local_precool_emissions, _, _, _ = food_precooling_process(comparison_weight, (precooling_full_params, end_electricity_price, CO2e_end, facility_capacity, end_country_name, CARBON_TAX_PER_TON_CO2_DICT))

            # Freezing (only if needed - not for Hass Avocado or Banana)
            local_freeze_opex = local_freeze_capex = local_freeze_carbon_tax = local_freeze_energy = local_freeze_emissions = 0
            if current_food_params['process_flags'].get('needs_freezing', False):
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

            if process_label_raw in overhead_labels: # This is the row from the distinct insurance calculation
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

        # FIX: Don't append while iterating! Create new list instead
        relabeled_data = []
        for row in data_with_all_columns:
            relabel_key = row[0]
            new_label = label_map.get(relabel_key, relabel_key)
            relabeled_data.append([new_label] + row[1:])
        data_with_all_columns = relabeled_data
     
        aggregated_data_for_chart = []
        aggregated_overheads_row = ["Overheads & Fees", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        overhead_per_kg_col_idx = new_detailed_headers.index("Insurance/kg ($/kg)")
        for row in data_with_all_columns:
            label = row[0]
            if label in overhead_labels:
                aggregated_overheads_row[overhead_per_kg_col_idx] += float(row[overhead_per_kg_col_idx])
            elif label not in ["TOTAL", "Initial Production (Placeholder)", "Harvesting & Preparation"]:
                aggregated_data_for_chart.append(row)
        aggregated_data_for_chart.append(aggregated_overheads_row)

        emission_chart_exclusions_food = [
            "TOTAL", "Harvesting & Preparation", "Insurance",
            "Import Tariffs & Duties", "Financing Costs",
            "Brokerage & Agent Fees", "Contingency (10%)"
        ]        
        data_for_emission_chart = [row for row in data_with_all_columns if row[0] not in emission_chart_exclusions_food]

        detailed_data_formatted = []
        for row in data_with_all_columns: 
            formatted_row = [row[0]] 
            for item in row[1:]: 
                if isinstance(item, (int, float)):
                    formatted_row.append(f"{item:,.2f}")
                else:
                    formatted_row.append(item)
            detailed_data_formatted.append(formatted_row)
        csv_data = [new_detailed_headers] + detailed_data_formatted
        opex_per_kg_for_chart_idx = new_detailed_headers.index("Opex/kg ($/kg)")
        capex_per_kg_for_chart_idx = new_detailed_headers.index("Capex/kg ($/kg)")
        carbon_tax_per_kg_for_chart_idx = new_detailed_headers.index("Carbon Tax/kg ($/kg)")
        insurance_per_kg_for_chart_idx = new_detailed_headers.index("Insurance/kg ($/kg)") 
        eco2_per_kg_for_chart_idx = new_detailed_headers.index("CO2eq/kg (kg/kg)")
        
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

        # Prepare chart data for Plotly.js (interactive charts in browser)
        cost_chart_data = {
            'labels': [row[0] for row in aggregated_data_for_chart],
            'opex': [row[opex_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'capex': [row[capex_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'carbon_tax': [row[carbon_tax_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'insurance': [row[insurance_per_kg_for_chart_idx] for row in aggregated_data_for_chart],
            'title': 'Cost Breakdown per kg of Delivered Food',
            'x_label': 'Cost ($/kg)',
            'overlay_text': cost_overlay_text
        }

        emission_chart_data = {
            'labels': [row[0] for row in data_for_emission_chart],
            'emissions': [row[eco2_per_kg_for_chart_idx] for row in data_for_emission_chart],
            'title': 'CO2eq Breakdown per kg of Delivered Food',
            'x_label': 'CO2eq (kg/kg)',
            'overlay_text': emission_overlay_text
        }        
            
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
            "charts": { "cost_chart_data": cost_chart_data, "emission_chart_data": emission_chart_data },
            "local_sourcing_comparison": local_sourcing_results,
            "food_type": food_type
        }
        return response    

# --- Flask API Endpoints ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({"status": "ok", "message": "Server is running"}), 200

@app.route('/calculate', methods=['POST', 'OPTIONS'])
def calculate_endpoint():
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'https://eshansingh.xyz')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200

    try:
        print(f"[INFO] Received {request.method} request to /calculate")
        print(f"[INFO] Request headers: {dict(request.headers)}")

        inputs = request.get_json()
        if not inputs:
            print("[ERROR] Invalid JSON input received")
            return jsonify({"status": "error", "message": "Invalid JSON input"}), 400

        print(f"[INFO] Processing inputs: {inputs}")
        results = run_lca_model(inputs)
        print("[INFO] Calculation completed successfully")

        # Create the response
        response = jsonify(results)

        # CRITICAL: Clear results from memory before Flask serializes it
        # This prevents double memory usage (Python object + JSON string)
        del results

        # Register cleanup to run after response is sent
        @response.call_on_close
        def cleanup():
            print("[INFO] Response sent, forcing garbage collection")
            gc.collect()

        return response
    except Exception as e:
        print(f"[ERROR] Exception occurred: {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Main execution block ---
if __name__ == '__main__':
    print("=" * 60)
    print("Starting Flask server...")
    print(f"API Keys loaded: Google={bool(API_KEY_GOOGLE)}, OpenAI={bool(API_KEY_OPENAI)}")
    print("Server ready to accept requests")
    print("=" * 60)

    # Use PORT environment variable for Render, default to 5000 for local
    port = int(os.environ.get('PORT', 5000))
    # Use debug=False in production (when PORT is set by Render)
    debug_mode = os.environ.get('PORT') is None
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

# Print startup message for production (Gunicorn)
print("=" * 60)
print("[STARTUP] Flask app initialized successfully")
print(f"[STARTUP] API Keys status: Google={bool(API_KEY_GOOGLE != 'ESHAN_API_KEY_GOOGLE')}, OpenAI={bool(API_KEY_OPENAI != 'ESHAN_API_KEY_OPENAI')}")
print("=" * 60)
