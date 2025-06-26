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
#CORS(app) # Allows the frontend to make requests
CORS(app, resources={r"/calculate": {"origins": "https://eshansingh.xyz"}})
# --- API KEYS ---
# Place your actual API keys here.
api_key_google = os.environ.get("API_KEY_GOOGLE", "ESHAN_API_KEY_GOOGLE")
api_key_searoutes = os.environ.get("API_KEY_SEAROUTES", "ESHAN_API_KEY_SEAROUTES")
api_key_EIA = os.environ.get("API_KEY_EIA", "ESHAN_API_KEY_EIA")
api_key_weather = os.environ.get("API_KEY_WEATHER", "ESHAN_API_KEY_WEATHER")
api_key_openAI = os.environ.get("API_KEY_OPENAI", "ESHAN_API_KEY_OPENAI")
api_key_electricity_map = os.environ.get("API_KEY_ELECTRICITYMAP", "ESHAN_API_KEY_ELECTRICITYMAP")


# ==============================================================================
# MAIN CALCULATION FUNCTION
# ==============================================================================
# ==============================================================================
# MAIN CALCULATION FUNCTION
# ==============================================================================
def run_lca_model(inputs):
    """
    This single function encapsulates all logic for both Fuel and Food pathways.
    All helper functions, parameters, and process steps are defined and called
    within this function to ensure correct variable scoping.
    """

    # --- 1. Unpack user inputs from the frontend ---
    start = inputs['start']
    end = inputs['end']
    commodity_type = inputs.get('commodity_type', 'fuel')
    marine_fuel_choice = inputs.get('marine_fuel_choice', 'VLSFO')
    
    # Repurposed inputs (used by both pathways)
    storage_time_A = inputs['storage_time_A']
    storage_time_B = inputs['storage_time_B']
    storage_time_C = inputs['storage_time_C']
    # We repurpose LH2_plant_capacity as a generic 'facility_capacity'
    facility_capacity = inputs['LH2_plant_capacity']


    # =================================================================
    # <<< STEP 1: MOVE ALL HELPER FUNCTIONS HERE (COMMON SCOPE) >>>
    # =================================================================
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
        index, lat, lng, coordinates = 0, 0, 0, []
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
        if response.status_code not in range(200, 299) or response.json()['status'] != 'OK': return []
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
        return float(result.get("latitude")), float(result.get("longitude")), result.get("nearest_port")

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
            
    def openai_get_hydrogen_price(coords_str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        default_price_usd_per_kg = 6.5
        try:
            # ... (omitted for brevity, no changes needed here)
            return coords_str, default_price_usd_per_kg # Placeholder
        except Exception:
            return coords_str, default_price_usd_per_kg

    def openai_get_marine_fuel_price(fuel_name, port_coords_tuple, port_name_str):
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        default_prices = {'VLSFO': 650.0, 'LNG': 550.0, 'Methanol': 700.0, 'Ammonia': 800.0}
        default_price_usd_per_mt = default_prices.get(fuel_name, 650.0)
        try:
             # ... (omitted for brevity, no changes needed here)
            return port_name_str, default_price_usd_per_mt # Placeholder
        except Exception:
            return port_name_str, default_price_usd_per_mt

    def calculate_ship_power_kw(ship_volume_m3):
        power_scaling_data = [(20000, 7000), (90000, 15000), (174000, 19900), (210000, 25000), (266000, 43540)]
        volumes_m3 = [p[0] for p in power_scaling_data]
        powers_kw = [p[1] for p in power_scaling_data]
        return np.interp(ship_volume_m3, volumes_m3, powers_kw)

    def create_breakdown_chart(data, column_index, title, x_label, overlay_text=None):
        # ... (omitted for brevity, no changes needed here)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=90)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        return img_base64


    # =================================================================
    # <<< STEP 2: MOVE ALL COMMON PARAMS & API CALLS HERE >>>
    # =================================================================
    coor_start_lat, coor_start_lng, _ = extract_lat_long(start)
    coor_end_lat, coor_end_lng, _ = extract_lat_long(end)
    start_port_lat, start_port_lng, start_port_name = openai_get_nearest_port(f"{coor_start_lat},{coor_start_lng}")
    end_port_lat, end_port_lng, end_port_name = openai_get_nearest_port(f"{coor_end_lat},{coor_end_lng}")
    
    route = sr.searoute((start_port_lng, start_port_lat), (end_port_lng, end_port_lat), units="nm")
    searoute_coor = [[lat, lon] for lon, lat in route.geometry['coordinates']]
    port_to_port_dis = route.properties['length'] * 1.852

    start_to_port_dist_str, start_to_port_dur_str = inland_routes_cal((coor_start_lat, coor_start_lng), (start_port_lat, start_port_lng))
    port_to_end_dist_str, port_to_end_dur_str = inland_routes_cal((end_port_lat, end_port_lng), (coor_end_lat, coor_end_lng))

    distance_A_to_port = float(re.sub(r'[^\d.]', '', start_to_port_dist_str))
    distance_port_to_B = float(re.sub(r'[^\d.]', '', port_to_end_dist_str))
    duration_A_to_port = time_to_minutes(start_to_port_dur_str)
    duration_port_to_B = time_to_minutes(port_to_end_dur_str)

    start_local_temperature = local_temperature(coor_start_lat, coor_start_lng)
    end_local_temperature = local_temperature(coor_end_lat, coor_end_lng)
    port_to_port_duration = float(port_to_port_dis) / (16 * 1.852) # Avg ship speed 16 knots

    CO2e_start = carbon_intensity(coor_start_lat, coor_start_lng)
    CO2e_end = carbon_intensity(coor_end_lat, coor_end_lng)

    start_electricity_price = openai_get_electricity_price(f"{coor_start_lat},{coor_start_lng}")
    end_electricity_price = openai_get_electricity_price(f"{coor_end_lat},{coor_end_lng}")
    start_port_electricity_price = openai_get_electricity_price(f"{start_port_lat},{start_port_lng}")
    end_port_electricity_price = openai_get_electricity_price(f"{end_port_lat},{end_port_lng}")

    road_route_start_coords = extract_route_coor((coor_start_lat, coor_start_lng), (start_port_lat, start_port_lng))
    road_route_end_coords = extract_route_coor((end_port_lat, end_port_lng), (coor_end_lat, end_port_lng))

    diesel_price_country = {"Venezuela": 0.016, "Iran": 0.022, "USA": 3.452, "United States": 3.452, "Germany": 6.615, "Netherlands": 6.912 } # Shortened for brevity
    diesel_price_start = get_diesel_price(coor_start_lat, coor_start_lng, diesel_price_country)
    diesel_price_end = get_diesel_price(end_port_lat, end_port_lng, diesel_price_country)

    _, dynamic_price = openai_get_marine_fuel_price(marine_fuel_choice, (start_port_lat, start_port_lng), start_port_name)

    marine_fuels_data = {
        'VLSFO': {'price_usd_per_ton': 650.0, 'sfoc_g_per_kwh': 185, 'hhv_mj_per_kg': 41.0, 'co2_emissions_factor_kg_per_kg_fuel': 3.114, 'methane_slip_gwp100': 0},
        'LNG': {'price_usd_per_ton': 550.0, 'sfoc_g_per_kwh': 135, 'hhv_mj_per_kg': 50.0, 'co2_emissions_factor_kg_per_kg_fuel': 2.75, 'methane_slip_gwp100': (0.03 * 28)},
        'Methanol': {'price_usd_per_ton': 700.0, 'sfoc_g_per_kwh': 380, 'hhv_mj_per_kg': 22.7, 'co2_emissions_factor_kg_per_kg_fuel': 1.375, 'methane_slip_gwp100': 0},
        'Ammonia': {'price_usd_per_ton': 800.0, 'sfoc_g_per_kwh': 320, 'hhv_mj_per_kg': 22.5, 'co2_emissions_factor_kg_per_kg_fuel': 0, 'methane_slip_gwp100': 0, 'n2o_emission_factor_g_per_kwh': 0.05, 'nox_emission_factor_g_per_kwh': 2.0}
    }
    selected_marine_fuel_params = marine_fuels_data[marine_fuel_choice]
    selected_marine_fuel_params['price_usd_per_ton'] = dynamic_price
    
    # Common physical parameters (can be split later if needed)
    HHV_diesel = 45.6
    diesel_density = 3.22 # kg per gal
    CO2e_diesel = 10.21

    # =================================================================
    # <<< STEP 3: MOVE SHIP PARAMETER LOGIC HERE (COMMON SCOPE) >>>
    # =================================================================
    ship_archetype_key = inputs.get('ship_archetype', 'standard')
    ship_archetypes = {
        'small': {'name': 'Small-Scale Carrier', 'volume_m3': 20000, 'num_tanks': 2, 'shape': 2},
        'midsized': {'name': 'Midsized Carrier', 'volume_m3': 90000, 'num_tanks': 4, 'shape': 2},
        'standard': {'name': 'Standard Modern Carrier', 'volume_m3': 174000, 'num_tanks': 4, 'shape': 1},
        'q-flex': {'name': 'Q-Flex Carrier', 'volume_m3': 210000, 'num_tanks': 5, 'shape': 1},
        'q-max': {'name': 'Q-Max Carrier', 'volume_m3': 266000, 'num_tanks': 5, 'shape': 1}
    }
    if ship_archetype_key == 'custom':
        total_ship_volume = inputs['total_ship_volume']
        ship_number_of_tanks = inputs['ship_number_of_tanks']
        ship_tank_shape = inputs['ship_tank_shape']
    else:
        selected_ship_params = ship_archetypes[ship_archetype_key]
        total_ship_volume = selected_ship_params['volume_m3']
        ship_number_of_tanks = selected_ship_params['num_tanks']
        ship_tank_shape = selected_ship_params['shape']
    
    avg_ship_power_kw = calculate_ship_power_kw(total_ship_volume)


    # =================================================================
    # <<< MAIN CONDITIONAL BRANCH STARTS HERE >>>
    # =================================================================

    if commodity_type == 'fuel':
        # --- Unpack FUEL specific inputs ---
        fuel_type = inputs['fuel_type']
        recirculation_BOG = inputs['recirculation_BOG']
        BOG_recirculation_truck = inputs['BOG_recirculation_truck']
        BOG_recirculation_truck_apply = inputs['BOG_recirculation_truck_apply']
        BOG_recirculation_storage = inputs['BOG_recirculation_storage']
        BOG_recirculation_storage_apply = inputs['BOG_recirculation_storage_apply']
        BOG_recirculation_mati_trans = inputs['BOG_recirculation_mati_trans']
        BOG_recirculation_mati_trans_apply = inputs['BOG_recirculation_mati_trans_apply']
        user_define = [0, fuel_type, int(recirculation_BOG), int(BOG_recirculation_truck_apply), int(BOG_recirculation_storage_apply), int(BOG_recirculation_mati_trans_apply)]
        volume_per_tank = total_ship_volume / ship_number_of_tanks
        if ship_tank_shape == 1: # Capsule (Membrane)
            # Derived from volume formula V = (4/3)*pi*r^3 + pi*r^2*h where h = 8r
            ship_tank_radius = np.cbrt(volume_per_tank/( (4/3)*np.pi + 8*np.pi ))
            ship_tank_height = 8 * ship_tank_radius # Assuming a standard aspect ratio for capsule tanks
            storage_area = 2*np.pi*(ship_tank_radius*ship_tank_height) + 4*np.pi*ship_tank_radius**2
        else: # Spherical
            ship_tank_radius = np.cbrt(volume_per_tank/(4/3*np.pi))
            storage_area = 4*np.pi*ship_tank_radius**2
        # ALL Parameters from your script are here
        HHV_chem = [142, 22.5, 22.7]; LHV_chem = [120, 18.6, 19.9]; boiling_point_chem = [20, 239.66, 337.7];
        latent_H_chem = [449.6/1000, 1.37, 1.1]; specific_heat_chem = [14.3/1000, 4.7/1000, 2.5/1000];
        HHV_heavy_fuel = 40; HHV_diesel = 45.6; liquid_chem_density = [71, 682, 805];
        CO2e_diesel = 10.21; CO2e_heavy_fuel = 11.27; GWP_chem = [33, 0, 0]; GWP_N2O = 273; # GWP for Nitrous Oxide (IPCC AR6)
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
        ship_fuel_consumption = 0.23; OHTC_ship = [0.05, 0.22, 0.02];
        COP_cooldown = [0.131, 1.714, 2]; COP_liq = [0.131, 1.714, 2]; COP_refrig = [0.036, 1.636, 2];
        dBOR_dT = [(0.02538-0.02283)/(45-15)/4, (0.000406-0.0006122)/(45-15)/4, 0];
        EIM_liquefication=100; EIM_cryo_pump=100; EIM_truck_eff=100; EIM_ship_eff=100; EIM_refrig_eff=100; EIM_fuel_cell=100;
        diesel_density = 3.22; #kg per gal
        diesel_engine_eff = 0.4; heavy_fuel_density = 3.6; propul_eff = 0.55;
        NH3_ship_cosumption = (18.8*682*4170)/20000
        # Need to check the numbers below for accuracy
        mass_conversion_to_H2 = [1, 0.176, 0.1875] # NH3, CH3OH
        eff_energy_chem_to_H2 = [0, 0.7, 0.75]
        energy_chem_to_H2 = [0, 9.3, 5.3]
        PH2_storage_V = 150.0 
        numbers_of_PH2_storage_at_start = 50.0
        multistage_eff = 0.85
        pipeline_diameter = 0.5 # meters
        epsilon = 0.000045 # pipe roughness
        compressor_velocity = 20.0 # m/s
        gas_chem_density = [0.08, 0.73, 1.42] # H2, NH3, CH3OH densities at STP
        target_pressure_site_B = 300 # bar
        latent_H_H2 = 0.4496 # MJ/kg
        specific_heat_H2 = 14.3 # MJ/kg-K
        numbers_of_PH2_storage = 50.0
        ship_engine_eff = 0.6
        PH2_pressure = 800
        truck_economy = [13.84, 10.14, 9.66]  # mi/gal Grok Analysis

        # ADD THESE NEW PARAMETERS FOR TANK COOLDOWN
        # Sourced from Table 2 in the provided study 
        ship_tank_metal_specific_heat = 0.47 / 1000  # MJ/kg-K
        ship_tank_insulation_specific_heat = 1.5 / 1000 # MJ/kg-K
        ship_tank_metal_density = 7900  # kg/m^3
        ship_tank_insulation_density = 100 # kg/m^3
        
        # Sourced from the study's text and Table 6 
        ship_tank_metal_thickness = 0.05 # m
        # Using onshore storage insulation thickness as a proxy from the study 
        ship_tank_insulation_thickness = [0.66, 0.09, 0] # m (H2, NH3, Methanol)
        
        # Sourced from Table 6 for the "Cooldown" scenario 
        COP_cooldown = [0.131, 1.714, 0] # (H2, NH3, Methanol)
        SMR_EMISSIONS_KG_PER_KG_H2 = 9.3 # kg CO2e / kg H2 for unabated Steam Methane Reforming

        marine_fuels_data = {
            'VLSFO': {
                'price_usd_per_ton': 650.0,
                'sfoc_g_per_kwh': 185,
                'hhv_mj_per_kg': 41.0, # Higher Heating Value
                'co2_emissions_factor_kg_per_kg_fuel': 3.114,
                'methane_slip_gwp100': 0 # Negligible for VLSFO
            },
            'LNG': {
                'price_usd_per_ton': 550.0,
                'sfoc_g_per_kwh': 135,
                'hhv_mj_per_kg': 50.0,
                'co2_emissions_factor_kg_per_kg_fuel': 2.75,
                # Methane slip is critical for LNG. Assumes 3% slip, GWP100 of 28 for CH4.
                'methane_slip_gwp100': (0.03 * 28)
            },
            'Methanol': {
                'price_usd_per_ton': 700.0,
                'sfoc_g_per_kwh': 380, # Methanol is less energy-dense, so SFOC is higher.
                'hhv_mj_per_kg': 22.7,
                'co2_emissions_factor_kg_per_kg_fuel': 1.375,
                'methane_slip_gwp100': 0
            },
            'Ammonia': {
                'price_usd_per_ton': 800.0,
                'sfoc_g_per_kwh': 320, # Also less energy-dense than VLSFO/LNG.
                'hhv_mj_per_kg': 22.5,
                'co2_emissions_factor_kg_per_kg_fuel': 0, # No carbon in the fuel.
                'methane_slip_gwp100': 0,
                'n2o_emission_factor_g_per_kwh': 0.05, # Based on DNV research for NH3 engines
                'nox_emission_factor_g_per_kwh': 2.0   # Assumes IMO Tier III compliance with SCR
            }
        }
        selected_marine_fuel_params = marine_fuels_data[marine_fuel_choice]
        selected_marine_fuel_params['price_usd_per_ton'] = dynamic_price
        avg_ship_power_kw = calculate_ship_power_kw(total_ship_volume)
        # --- 4. Process Functions (Copied from LCA_WebApp.py) ---
        #placeholder functions need to be filled in. 
        def PH2_pressure_fnc(density): return density * 1.2 # Simplified placeholder
        def multistage_compress(pressure): return pressure * 0.05 # Simplified placeholder
        def kinematic_viscosity_PH2(pressure): return 1e-5 / (pressure/10) # Simplified placeholder
        def solve_colebrook(Re, epsilon, D): return 0.02 # Simplified placeholder for friction factor
        def PH2_transport_energy(L): return L * 0.001 # Simplified placeholder
        def PH2_density_fnc(pressure): return pressure / 1.2 # Simplified placeholder
        def straight_dis(coor_start_lang,coor_start_lat,coor_end_lang,coor_end_lat): return 1000
        def PH2_density_fnc_helper(pressure): return 0.25
        #actual process functions
        def liquification_data_fitting(H2_plant_capacity):
            x = H2_plant_capacity
            y0, x0, A1, A2, A3, t1, t2, t3 = 37.76586, -11.05773, 6248.66187, 80.56526, 25.95391, 2.71336, 32.3875, 685.33284
            return y0 + A1*np.exp(-(x-x0)/t1) + A2*np.exp(-(x-x0)/t2) + A3*np.exp(-(x-x0)/t3)

    # This definition goes inside run_lca_model
        def site_A_chem_production(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs.
            # Even if currently minimal, this maintains the pattern.
            # For this function, based on its simple return, only GWP_chem might be relevant
            # if BOG_loss was non-zero and its GWP impact needed to be calculated.
            
            (GWP_chem_list_arg,) = process_args_tuple # Unpacking a tuple with one element

            # Original logic from your snippet:
            money = 0
            convert_energy_consumed = 0 # Or just ener_consumed if preferred
            G_emission = 0
            BOG_loss = 0
            
            # If BOG_loss were potentially non-zero in a more detailed version of this function,
            # you would calculate G_emission like this:
            # G_emission = (convert_energy_consumed * 0.2778 * CO2e_start_arg * 0.001) + (BOG_loss * GWP_chem_list_arg[B_fuel_type])
            # But since BOG_loss and convert_energy_consumed are 0, G_emission is 0.

            # A (amount of chemical) does not change in this initial production step in your snippet
            return money, convert_energy_consumed, G_emission, A, BOG_loss

    # This definition goes inside run_lca_model
        def site_A_chem_liquification(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_specific_args_tuple):
            # Unpack the specific arguments this function needs
            LH2_plant_capacity_arg, \
            EIM_liquefication_arg, \
            specific_heat_chem_arg, \
            start_local_temperature_arg, \
            boiling_point_chem_arg, \
            latent_H_chem_arg, \
            COP_liq_arg, \
            start_electricity_price_tuple_arg, \
            CO2e_start_arg, \
            GWP_chem_list_arg = process_specific_args_tuple # GWP_chem_list_arg is your list [33,0,0]

            if B_fuel_type == 0:  # LH2
                liquify_energy_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
            elif B_fuel_type == 1:  # Ammonia
                liquify_heat_required = specific_heat_chem_arg[B_fuel_type] * (start_local_temperature_arg + 273 - boiling_point_chem_arg[B_fuel_type]) + latent_H_chem_arg[B_fuel_type]
                liquify_energy_required = liquify_heat_required / COP_liq_arg[B_fuel_type]
            else:  # Methanol
                liquify_energy_required = 0

            liquify_ener_consumed = liquify_energy_required * A
            money = liquify_ener_consumed * start_electricity_price_tuple_arg[2] # Access the price float
            
            G_emission_from_energy = liquify_ener_consumed * 0.2778 * CO2e_start_arg * 0.001
            BOG_loss = 0.016 * A
            
            A_after_loss = A - BOG_loss
            
            # ** THE FIX IS HERE: **
            # Select the correct GWP value from the list using B_fuel_type as the index
            G_emission_from_bog = BOG_loss * GWP_chem_list_arg[B_fuel_type] 
            
            G_emission = G_emission_from_energy + G_emission_from_bog

            return money, liquify_ener_consumed, G_emission, A_after_loss, BOG_loss
        
        def chem_site_A_loading_to_truck(A, B, C, D, E, F, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed
            # into the tuple when this function is called from optimization_chem_weight.

            V_flowrate_arg, \
            number_of_cryo_pump_load_arg, \
            dBOR_dT_arg, \
            start_local_temperature_arg, \
            BOR_loading_arg, \
            liquid_chem_density_arg, \
            head_pump_arg, \
            pump_power_factor_arg, \
            EIM_cryo_pump_arg, \
            ss_therm_cond_arg, \
            pipe_length_arg, \
            pipe_inner_D_arg, \
            pipe_thick_arg, \
            COP_refrig_arg, \
            EIM_refrig_eff_arg, \
            start_electricity_price_tuple_arg, \
            CO2e_start_arg, \
            GWP_chem_list_arg = process_args_tuple

            # Now use the unpacked local variables from the tuple in your calculations:
            duration = A / (V_flowrate_arg[B]) / number_of_cryo_pump_load_arg  # hr = kg/(kg/hr)
            local_BOR_loading = dBOR_dT_arg[B] * (start_local_temperature_arg - 25) + BOR_loading_arg[B]  # dBOR/dT = (BOR_local - BOR_default)/(T_local - 25)
            BOG_loss = local_BOR_loading * (1 / 24) * duration * A  # kg = %/day * day/hr *hr * kg
            
            pumping_power = liquid_chem_density_arg[B] * V_flowrate_arg[B] * (1 / 3600) * head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100) # W
            
            # Ensure log10 argument is > 0. If pipe_inner_D is very small or equal to pipe_thick, this could be an issue.
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            if log_arg <= 0:
                q_pipe = 0 # Or handle error appropriately
            else:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * (start_local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))  # W
            
            ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600  # MJ
            ener_consumed = pumping_power * duration * 3600 * 1 / 1000000 + ener_consumed_refrig  # MJ
            
            A_after_loss = A - BOG_loss # Calculate net amount
            
            money = ener_consumed * start_electricity_price_tuple_arg[2]  # MJ*$/MJ = $
            G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B]  # kgCO2

            return money, ener_consumed, G_emission, A_after_loss, BOG_loss
        
    # This definition goes inside run_lca_model
        def site_A_to_port_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed
            # into the tuple when this function is called.

            road_delivery_ener_arg, HHV_chem_arg, chem_in_truck_weight_arg, truck_economy_arg, distance_A_to_port_arg, \
            HHV_diesel_arg, diesel_density_arg, diesel_price_start_arg, truck_tank_radius_arg, \
            truck_tank_length_arg, truck_tank_metal_thickness_arg, metal_thermal_conduct_arg, \
            truck_tank_insulator_thickness_arg, insulator_thermal_conduct_arg, OHTC_ship_arg, \
            start_local_temperature_arg, COP_refrig_arg, EIM_refrig_eff_arg, duration_A_to_port_arg, \
            dBOR_dT_arg, BOR_truck_trans_arg, diesel_engine_eff_arg, EIM_truck_eff_arg, \
            CO2e_diesel_arg, GWP_chem_arg, \
            BOG_recirculation_truck_percentage_arg, \
            LH2_plant_capacity_arg, EIM_liquefication_arg, \
            fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg = process_args_tuple

            # Original logic of the function, using the unpacked '_arg' variables
            number_of_trucks = A / chem_in_truck_weight_arg[B_fuel_type] # Local variable
            truck_energy_consumed = road_delivery_ener_arg[B_fuel_type] * HHV_chem_arg[B_fuel_type]
            #trans_energy_required = truck_energy_consumed * distance_A_to_port_arg * A
            trans_energy_required = number_of_trucks * distance_A_to_port_arg * HHV_diesel_arg * diesel_density_arg / truck_economy_arg[B_fuel_type]
            diesel_money = trans_energy_required / HHV_diesel_arg / diesel_density_arg * diesel_price_start_arg
            
            storage_area_truck = 2 * np.pi * truck_tank_radius_arg * truck_tank_length_arg
            if B_fuel_type == 0:
                thermal_resist = truck_tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                                truck_tank_insulator_thickness_arg / insulator_thermal_conduct_arg
                OHTC = 1 / thermal_resist if thermal_resist > 0 else float('inf') # Avoid division by zero
            else:
                OHTC = OHTC_ship_arg[B_fuel_type]

            heat_required = OHTC * storage_area_truck * (start_local_temperature_arg + 273 - 20) # Assuming 20K is target temp
            refrig_ener_consumed = (heat_required / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * 60 * duration_A_to_port_arg * number_of_trucks
            
            local_BOR_truck_trans = dBOR_dT_arg[B_fuel_type] * (start_local_temperature_arg - 25) + BOR_truck_trans_arg[B_fuel_type]
            current_BOG_loss = A * local_BOR_truck_trans / (24 * 60) * duration_A_to_port_arg # Renamed to avoid conflict in recirculation

            refrig_money = (refrig_ener_consumed / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / diesel_density_arg * diesel_price_start_arg
            money = diesel_money + refrig_money
            total_energy = trans_energy_required + refrig_ener_consumed
            
            A_after_loss = A - current_BOG_loss # Initial state before recirculation
            
            G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
            G_emission = G_emission_energy + current_BOG_loss * GWP_chem_arg[B_fuel_type]

            net_BOG_loss = current_BOG_loss # This will be updated if recirculation occurs

            # Recirculation logic
            # C_recirculation_BOG (user_define[2]) enables overall BOG recirculation
            # D_truck_apply (user_define[3]) is the type of BOG use for trucks
            if C_recirculation_BOG == 2: # If BOG recirculation is active
                if D_truck_apply == 1: # 1) Re-liquefy BOG
                    usable_BOG = current_BOG_loss * BOG_recirculation_truck_percentage_arg * 0.01
                    BOG_flowrate = usable_BOG / duration_A_to_port_arg * 60 # kg/hr
                    # liquification_data_fitting is a global helper, needs LH2_plant_capacity_arg
                    reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                    reliq_ener_consumed = reliq_ener_required * usable_BOG
                    
                    total_energy += reliq_ener_consumed # Add energy for re-liquefaction
                    
                    reliq_money = (reliq_ener_consumed / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / diesel_density_arg * diesel_price_start_arg
                    money += reliq_money # Add cost for re-liquefaction
                    
                    A_after_loss += usable_BOG # Add back re-liquefied BOG
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
                    
                    # Recalculate G_emission_energy with new total_energy
                    G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
                    G_emission = G_emission_energy + net_BOG_loss * GWP_chem_arg[B_fuel_type]

                elif D_truck_apply == 2: # 2) Use BOG as another energy source (e.g., fuel cell)
                    usable_BOG = current_BOG_loss * BOG_recirculation_truck_percentage_arg * 0.01
                    usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
                    
                    # Energy saved from refrigeration, capped at refrig_ener_consumed
                    energy_saved_from_refrig = min(usable_ener, refrig_ener_consumed)
                    money_saved_from_refrig = (energy_saved_from_refrig / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / diesel_density_arg * diesel_price_start_arg
                    
                    total_energy = trans_energy_required + (refrig_ener_consumed - energy_saved_from_refrig)
                    money = diesel_money + (refrig_money - money_saved_from_refrig)
                    
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
                    # A_after_loss remains A - current_BOG_loss because the BOG is consumed, not added back as liquid
                    
                    G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
                    G_emission = G_emission_energy + net_BOG_loss * GWP_chem_arg[B_fuel_type]
            
            return money, total_energy, G_emission, A_after_loss, net_BOG_loss
        
    # This definition goes inside run_lca_model
        def port_A_unloading_to_storage(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            V_flowrate_arg, \
            number_of_cryo_pump_load_storage_port_A_arg, \
            dBOR_dT_arg, \
            start_local_temperature_arg, \
            BOR_unloading_arg, \
            liquid_chem_density_arg, \
            head_pump_arg, \
            pump_power_factor_arg, \
            EIM_cryo_pump_arg, \
            ss_therm_cond_arg, \
            pipe_length_arg, \
            pipe_inner_D_arg, \
            pipe_thick_arg, \
            COP_refrig_arg, \
            EIM_refrig_eff_arg, \
            start_electricity_price_tuple_arg, \
            CO2e_start_arg, \
            GWP_chem_list_arg = process_args_tuple
            # Note: Your original snippet used BOR_loading for this function.
            # I've used BOR_unloading_arg based on the function name, assuming it's distinct.
            # If it's meant to be BOR_loading, adjust the variable name here and in the packing stage.

            # Original logic of the function, using the unpacked '_arg' variables
            duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_storage_port_A_arg  # hr
            
            # Using BOR_unloading_arg as per unpacking
            local_BOR_unloading_or_loading = dBOR_dT_arg[B_fuel_type] * (start_local_temperature_arg - 25) + BOR_unloading_arg[B_fuel_type]
            BOG_loss = local_BOR_unloading_or_loading * (1 / 24) * duration * A  # kg
            
            pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * \
                            head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100) # W
            
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            if log_arg <= 0:
                q_pipe = 0 
            else:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * \
                        (start_local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))  # W
            
            ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600  # MJ
            ener_consumed = pumping_power * duration * 3600 * 1 / 1000000 + ener_consumed_refrig  # MJ
            
            A_after_loss = A - BOG_loss # Net amount
            
            money = ener_consumed * start_electricity_price_tuple_arg[2]  # $
            G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]  # kgCO2
            
            return money, ener_consumed, G_emission, A_after_loss, BOG_loss
        
    # This definition goes inside run_lca_model
        def chem_storage_at_port_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            liquid_chem_density_arg, storage_volume_arg, dBOR_dT_arg, start_local_temperature_arg, \
            BOR_land_storage_arg, storage_time_A_arg, storage_radius_arg, tank_metal_thickness_arg, \
            metal_thermal_conduct_arg, tank_insulator_thickness_arg, insulator_thermal_conduct_arg, \
            COP_refrig_arg, EIM_refrig_eff_arg, start_electricity_price_tuple_arg, CO2e_start_arg, \
            GWP_chem_list_arg, BOG_recirculation_storage_percentage_arg, \
            LH2_plant_capacity_arg, EIM_liquefication_arg, \
            fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg = process_args_tuple

            # Original logic of the function, using the unpacked '_arg' variables
            number_of_storage = math.ceil(A / liquid_chem_density_arg[B_fuel_type] / storage_volume_arg[B_fuel_type])
            local_BOR_storage = dBOR_dT_arg[B_fuel_type] * (start_local_temperature_arg - 25) + BOR_land_storage_arg[B_fuel_type]
            current_BOG_loss = A * local_BOR_storage * storage_time_A_arg # Renamed BOG_loss to current_BOG_loss
            
            A_after_loss = A - current_BOG_loss # Initial chemical amount after BOG loss, before recirculation
            
            storage_area_val = 4 * np.pi * (storage_radius_arg[B_fuel_type]**2) * number_of_storage
            
            thermal_resist_val = tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                                tank_insulator_thickness_arg / insulator_thermal_conduct_arg
            OHTC_val = 1 / thermal_resist_val if thermal_resist_val > 0 else float('inf') # Avoid division by zero
            
            heat_required_val = OHTC_val * storage_area_val * (start_local_temperature_arg + 273 - 20) # Assuming 20K target
            ener_consumed_refrig = (heat_required_val / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * 86400 * storage_time_A_arg
            
            money = ener_consumed_refrig * start_electricity_price_tuple_arg[2]
            total_energy_consumed = ener_consumed_refrig # Initial total energy
            
            G_emission = total_energy_consumed * 0.2778 * CO2e_start_arg * 0.001 + current_BOG_loss * GWP_chem_list_arg[B_fuel_type]
            net_BOG_loss = current_BOG_loss # This will be updated if recirculation occurs

            # Recirculation logic
            # C_recirculation_BOG is user_define[2], E_storage_apply is user_define[4]
            if C_recirculation_BOG == 2: # If BOG recirculation is active
                if E_storage_apply == 1: # 1) Re-liquefy BOG
                    usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                    BOG_flowrate = usable_BOG / storage_time_A_arg * 1 / 24 # kg/hr
                    
                    # liquification_data_fitting is a global helper
                    reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                    reliq_ener_consumed = reliq_ener_required * usable_BOG
                    
                    total_energy_consumed += reliq_ener_consumed # Add energy for re-liquefaction
                    money = total_energy_consumed * start_electricity_price_tuple_arg[2] # Recalculate money
                    
                    A_after_loss += usable_BOG # Add back re-liquefied BOG
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                    
                    G_emission = total_energy_consumed * 0.2778 * CO2e_start_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]

                elif E_storage_apply == 2: # 2) Use BOG as another energy source (e.g., fuel cell)
                    usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                    usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
                    
                    initial_refrig_energy = ener_consumed_refrig # Store initial refrigeration energy
                    ener_consumed_refrig -= usable_ener # Reduce refrigeration energy by BOG-derived energy
                    if ener_consumed_refrig < 0:
                        ener_consumed_refrig = 0
                    
                    total_energy_consumed = ener_consumed_refrig # Update total energy (only refrigeration part changes)
                    money = total_energy_consumed * start_electricity_price_tuple_arg[2] # Recalculate money
                    
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                    # A_after_loss remains A - current_BOG_loss, as BOG is consumed
                    
                    G_emission = total_energy_consumed * 0.2778 * CO2e_start_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]
            
            return money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss
        
    # This definition goes inside run_lca_model

        def chem_loading_to_ship(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack all necessary arguments
            (V_flowrate_arg, number_of_cryo_pump_load_ship_port_A_arg, dBOR_dT_arg, 
            start_local_temperature_arg, BOR_loading_arg, liquid_chem_density_arg, head_pump_arg, 
            pump_power_factor_arg, EIM_cryo_pump_arg, ss_therm_cond_arg, pipe_length_arg, pipe_inner_D_arg, 
            pipe_thick_arg, boiling_point_chem_arg, EIM_refrig_eff_arg, start_electricity_price_tuple_arg, 
            CO2e_start_arg, GWP_chem_list_arg, calculated_storage_area_arg, ship_tank_metal_thick_arg, 
            ship_tank_insulation_thick_arg, ship_tank_metal_density_arg, ship_tank_insulation_density_arg, 
            ship_tank_metal_specific_heat_arg, ship_tank_insulation_specific_heat_arg, 
            COP_cooldown_arg, COP_refrig_arg, ship_number_of_tanks_arg) = process_args_tuple

            # --- Existing Calculations ---
            duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_ship_port_A_arg
            local_BOR_loading_val = dBOR_dT_arg[B_fuel_type] * (start_local_temperature_arg - 25) + BOR_loading_arg[B_fuel_type]
            BOG_loss = local_BOR_loading_val * (1 / 24) * duration * A
            # Be sure to add EIM_cryo_pump_arg to the arguments tuple for this function
            pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100) 
            ener_consumed_pumping = pumping_power * duration * 3600 / 1000000

            # Pipe refrigeration calculation
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            q_pipe = 0
            if log_arg > 0:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * (start_local_temperature_arg + 273.15 - boiling_point_chem_arg[B_fuel_type]) / (np.log(log_arg))
            
            ener_consumed_pipe_refrig = 0
            pipe_refrig_cop = COP_refrig_arg[B_fuel_type]
            if pipe_refrig_cop > 0:
                ener_consumed_pipe_refrig = (q_pipe / (pipe_refrig_cop * (EIM_refrig_eff_arg / 100))) / 1000000 * duration * 3600

            # --- NEW COOLDOWN CALCULATION ---
            ener_consumed_cooldown = 0
            if B_fuel_type in [0, 1]: # Cooldown only needed for cryogenic fuels
                mass_metal = calculated_storage_area_arg * ship_tank_metal_thick_arg * ship_tank_metal_density_arg * ship_number_of_tanks_arg
                mass_insulation = calculated_storage_area_arg * ship_tank_insulation_thick_arg[B_fuel_type] * ship_tank_insulation_density_arg * ship_number_of_tanks_arg
                
                H_tank_metal = ship_tank_metal_specific_heat_arg * mass_metal
                H_tank_insulation = ship_tank_insulation_specific_heat_arg * mass_insulation
                
                delta_T = (start_local_temperature_arg + 273.15) - boiling_point_chem_arg[B_fuel_type]
                Q_cooling = (H_tank_metal + H_tank_insulation) * delta_T
                
                cooldown_cop = COP_cooldown_arg[B_fuel_type]
                if cooldown_cop > 0:
                    ener_consumed_cooldown = Q_cooling / cooldown_cop
            
            # --- Final Totals for this step ---
            ener_consumed = ener_consumed_pumping + ener_consumed_pipe_refrig + ener_consumed_cooldown
            A_after_loss = A - BOG_loss
            
            money = ener_consumed * start_electricity_price_tuple_arg[2]
            G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]
            
            return money, ener_consumed, G_emission, A_after_loss, BOG_loss
        def port_to_port(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            """
            Calculates the cost, emissions, and losses for the maritime transportation leg.
            This version includes a corrected N2O calculation for Ammonia fuel.
            """
            # --- 1. Unpack all incoming arguments ---
            (
                start_local_temperature_arg, end_local_temperature_arg, OHTC_ship_arg,
                calculated_storage_area_arg, ship_number_of_tanks_arg, COP_refrig_arg, EIM_refrig_eff_arg,
                port_to_port_duration_arg, selected_fuel_params_arg,
                dBOR_dT_arg, BOR_ship_trans_arg, GWP_chem_list_arg,
                BOG_recirculation_maritime_percentage_arg, LH2_plant_capacity_arg, EIM_liquefication_arg,
                fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg,
                avg_ship_power_kw_arg,
                aux_engine_efficiency_arg,
                GWP_N2O_arg
            ) = process_args_tuple
        
            # --- 2. Calculate Base Propulsion Requirements ---
            propulsion_work_kwh = avg_ship_power_kw_arg * port_to_port_duration_arg
            
            # --- 3. Calculate BOG & Refrigeration ---
            # **FIX IS HERE**: T_avg is now defined BEFORE it is used.
            T_avg = (start_local_temperature_arg + end_local_temperature_arg) / 2
            
            refrig_work_mj = 0
            if B_fuel_type == 0: # LH2 requires active refrigeration
                heat_required_watts = OHTC_ship_arg[B_fuel_type] * calculated_storage_area_arg * (T_avg + 273 - 20) * ship_number_of_tanks_arg
                refrig_work_mj = (heat_required_watts / (COP_refrig_arg[B_fuel_type] * (EIM_refrig_eff_arg / 100))) / 1000000 * 3600 * port_to_port_duration_arg
        
            local_BOR_transportation = dBOR_dT_arg[B_fuel_type] * (T_avg - 25) + BOR_ship_trans_arg[B_fuel_type]
            current_BOG_loss = local_BOR_transportation * (1 / 24) * port_to_port_duration_arg * A
            
            # --- 4. Handle BOG Recirculation ---
            net_BOG_loss = current_BOG_loss
            A_after_loss = A - current_BOG_loss
            reliq_work_mj = 0
            energy_saved_from_bog_mj = 0
        
            if C_recirculation_BOG == 2:
                usable_BOG = current_BOG_loss * (BOG_recirculation_maritime_percentage_arg / 100.0)
                net_BOG_loss -= usable_BOG
                if F_maritime_apply == 1: # Re-liquefy
                    A_after_loss += usable_BOG
                    reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                    reliq_work_mj = reliq_ener_required * usable_BOG
                elif F_maritime_apply == 2: # Use as fuel
                    energy_saved_from_bog_mj = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
        
            # --- 5. Calculate Total Fuel Consumed ---
            fuel_hhv_mj_per_kg = selected_fuel_params_arg['hhv_mj_per_kg']
            sfoc_g_per_kwh = selected_fuel_params_arg['sfoc_g_per_kwh']
            
            # Calculate total work the engines must produce (in MJ)
            total_engine_work_mj = (propulsion_work_kwh * 3.6) + refrig_work_mj + reliq_work_mj - energy_saved_from_bog_mj
            if total_engine_work_mj < 0: total_engine_work_mj = 0 # Cannot have negative work
                
            total_engine_work_kwh = total_engine_work_mj / 3.6
            
            # Calculate fuel needed for this work, based on engine efficiency (SFOC)
            total_fuel_consumed_kg = (total_engine_work_kwh * sfoc_g_per_kwh) / 1000
            
            # --- 6. Aggregate Final Cost and Emissions ---
            total_money = (total_fuel_consumed_kg / 1000) * selected_fuel_params_arg['price_usd_per_ton']
        
            # Emissions from fuel combustion (CO2 and CH4)
            co2_factor = selected_fuel_params_arg['co2_emissions_factor_kg_per_kg_fuel']
            methane_factor = selected_fuel_params_arg['methane_slip_gwp100']
            fuel_emissions_co2e = (total_fuel_consumed_kg * co2_factor) + (total_fuel_consumed_kg * methane_factor)
            
            # Emissions from N2O (for Ammonia fuel)
            n2o_emissions_co2e = 0
            if 'n2o_emission_factor_g_per_kwh' in selected_fuel_params_arg:
                n2o_factor_g_kwh = selected_fuel_params_arg['n2o_emission_factor_g_per_kwh']
                n2o_emissions_kg = (total_engine_work_kwh * n2o_factor_g_kwh) / 1000
                n2o_emissions_co2e = n2o_emissions_kg * GWP_N2O_arg
        
            # Emissions from vented cargo BOG
            bog_emissions_co2e = net_BOG_loss * GWP_chem_list_arg[B_fuel_type]
            
            # Sum all emissions sources
            total_G_emission = fuel_emissions_co2e + bog_emissions_co2e + n2o_emissions_co2e
            
            # Total chemical energy consumed is the HHV of the fuel burned
            total_energy_consumed_mj = total_fuel_consumed_kg * fuel_hhv_mj_per_kg
            
            return total_money, total_energy_consumed_mj, total_G_emission, A_after_loss, net_BOG_loss
            
        # This definition goes inside run_lca_model
        def chem_unloading_from_ship(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            V_flowrate_arg, \
            number_of_cryo_pump_load_storage_port_B_arg, \
            dBOR_dT_arg, \
            end_local_temperature_arg, \
            BOR_unloading_arg, \
            liquid_chem_density_arg, \
            head_pump_arg, \
            pump_power_factor_arg, \
            EIM_cryo_pump_arg, \
            ss_therm_cond_arg, \
            pipe_length_arg, \
            pipe_inner_D_arg, \
            pipe_thick_arg, \
            COP_refrig_arg, \
            EIM_refrig_eff_arg, \
            end_electricity_price_tuple_arg, \
            CO2e_end_arg, \
            GWP_chem_list_arg = process_args_tuple
            # Note: I've included EIM_cryo_pump_arg for consistency in pumping_power calculation.
            # If your original script intentionally omits it for this specific function, you can remove it
            # from unpacking and the formula below, and adjust the packing in total_chem.

            # Original logic of the function, using the unpacked '_arg' variables
            duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_storage_port_B_arg  # hr
            
            local_BOR_unloading_val = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_unloading_arg[B_fuel_type]
            BOG_loss = local_BOR_unloading_val * (1 / 24) * duration * A  # kg
            
            pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * \
                            head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100) # W
            
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            if log_arg <= 0: # Safety check
                q_pipe = 0
            else:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * \
                        (end_local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))  # W
            
            ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600  # MJ
            ener_consumed = pumping_power * duration * 3600 * 1 / 1000000 + ener_consumed_refrig  # MJ
            
            A_after_loss = A - BOG_loss # Net amount
            
            money = ener_consumed * end_electricity_price_tuple_arg[2]  # $
            G_emission = ener_consumed * 0.2778 * CO2e_end_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]  # kgCO2
            
            return money, ener_consumed, G_emission, A_after_loss, BOG_loss

    # This definition goes inside run_lca_model
        def chem_storage_at_port_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            liquid_chem_density_arg, storage_volume_arg, dBOR_dT_arg, end_local_temperature_arg, \
            BOR_land_storage_arg, storage_time_B_arg, storage_radius_arg, tank_metal_thickness_arg, \
            metal_thermal_conduct_arg, tank_insulator_thickness_arg, insulator_thermal_conduct_arg, \
            COP_refrig_arg, EIM_refrig_eff_arg, end_electricity_price_tuple_arg, CO2e_end_arg, \
            GWP_chem_list_arg, BOG_recirculation_storage_percentage_arg, \
            LH2_plant_capacity_arg, EIM_liquefication_arg, \
            fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg = process_args_tuple

            # Original logic of the function, using the unpacked '_arg' variables
            number_of_storage = math.ceil(A / liquid_chem_density_arg[B_fuel_type] / storage_volume_arg[B_fuel_type])
            local_BOR_storage = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_land_storage_arg[B_fuel_type]
            current_BOG_loss = A * local_BOR_storage * storage_time_B_arg
            
            A_after_loss = A - current_BOG_loss
            
            storage_area_val = 4 * np.pi * (storage_radius_arg[B_fuel_type]**2) * number_of_storage
            
            thermal_resist_val = tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                                tank_insulator_thickness_arg / insulator_thermal_conduct_arg
            OHTC_val = 1 / thermal_resist_val if thermal_resist_val > 0 else float('inf')
            
            heat_required_val = OHTC_val * storage_area_val * (end_local_temperature_arg + 273 - 20) # Using end_local_temperature
            ener_consumed_refrig = (heat_required_val / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * 86400 * storage_time_B_arg
            
            money = ener_consumed_refrig * end_electricity_price_tuple_arg[2] # Using end_electricity_price
            total_energy_consumed = ener_consumed_refrig
            
            G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + current_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end
            net_BOG_loss = current_BOG_loss

            # Recirculation logic (C_recirculation_BOG is user_define[2], E_storage_apply is user_define[4])
            if C_recirculation_BOG == 2:
                if E_storage_apply == 1: # Re-liquefy BOG
                    usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                    BOG_flowrate = usable_BOG / storage_time_B_arg * 1 / 24
                    
                    reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                    reliq_ener_consumed = reliq_ener_required * usable_BOG
                    
                    total_energy_consumed += reliq_ener_consumed
                    money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                    
                    A_after_loss += usable_BOG
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                    
                    G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end

                elif E_storage_apply == 2: # Use BOG as another energy source
                    usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                    usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
                    
                    ener_consumed_refrig_original = ener_consumed_refrig # Store original refrigeration energy
                    ener_consumed_refrig -= usable_ener
                    if ener_consumed_refrig < 0:
                        ener_consumed_refrig = 0
                    
                    total_energy_consumed = ener_consumed_refrig # Update total energy
                    money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                    
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                    
                    G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end
            
            return money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss

    # This definition goes inside run_lca_model
        def port_B_unloading_from_storage(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            V_flowrate_arg, \
            number_of_cryo_pump_load_truck_port_B_arg, \
            dBOR_dT_arg, \
            end_local_temperature_arg, \
            BOR_unloading_arg, \
            liquid_chem_density_arg, \
            head_pump_arg, \
            pump_power_factor_arg, \
            EIM_cryo_pump_arg, \
            ss_therm_cond_arg, \
            pipe_length_arg, \
            pipe_inner_D_arg, \
            pipe_thick_arg, \
            COP_refrig_arg, \
            EIM_refrig_eff_arg, \
            end_electricity_price_tuple_arg, \
            CO2e_end_arg, \
            GWP_chem_list_arg = process_args_tuple
            # Note: I've included EIM_cryo_pump_arg for consistency in pumping_power calculation.
            # Adjust if your original script intentionally omits it for this specific function.

            # Original logic of the function, using the unpacked '_arg' variables
            duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_truck_port_B_arg  # hr
            
            local_BOR_unloading_val = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_unloading_arg[B_fuel_type]
            BOG_loss = local_BOR_unloading_val * (1 / 24) * duration * A  # kg
            
            pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * \
                            head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100) # W
            
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            if log_arg <= 0: # Safety check
                q_pipe = 0
            else:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * \
                        (end_local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))  # W
            
            ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600  # MJ
            ener_consumed = pumping_power * duration * 3600 * 1 / 1000000 + ener_consumed_refrig  # MJ
            
            A_after_loss = A - BOG_loss # Net amount
            
            money = ener_consumed * end_electricity_price_tuple_arg[2]  # $ (using end_electricity_price)
            G_emission = ener_consumed * 0.2778 * CO2e_end_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]  # kgCO2 (using CO2e_end)
            
            return money, ener_consumed, G_emission, A_after_loss, BOG_loss

    # This definition goes inside run_lca_model
        def port_B_to_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            road_delivery_ener_arg, HHV_chem_arg, chem_in_truck_weight_arg, truck_economy_arg, distance_port_to_B_arg, \
            HHV_diesel_arg, diesel_density_arg, diesel_price_end_arg, truck_tank_radius_arg, \
            truck_tank_length_arg, truck_tank_metal_thickness_arg, metal_thermal_conduct_arg, \
            truck_tank_insulator_thickness_arg, insulator_thermal_conduct_arg, OHTC_ship_arg, \
            end_local_temperature_arg, COP_refrig_arg, EIM_refrig_eff_arg, duration_port_to_B_arg, \
            dBOR_dT_arg, BOR_truck_trans_arg, diesel_engine_eff_arg, EIM_truck_eff_arg, \
            CO2e_diesel_arg, GWP_chem_list_arg, \
            BOG_recirculation_truck_percentage_arg, \
            LH2_plant_capacity_arg, EIM_liquefication_arg, \
            fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg = process_args_tuple

            # Original logic of the function, using the unpacked '_arg' variables
            number_of_trucks = A / chem_in_truck_weight_arg[B_fuel_type] # Local variable
            truck_energy_consumed = road_delivery_ener_arg[B_fuel_type] * HHV_chem_arg[B_fuel_type]
            #trans_energy_required = truck_energy_consumed * distance_port_to_B_arg * A # Using distance_port_to_B
            trans_energy_required = number_of_trucks * distance_port_to_B_arg * HHV_diesel_arg * diesel_density_arg / truck_economy_arg[B_fuel_type]
            diesel_money = trans_energy_required / HHV_diesel_arg / diesel_density_arg * diesel_price_end_arg
            
            storage_area_truck = 2 * np.pi * truck_tank_radius_arg * truck_tank_length_arg
            
            # Consistent OHTC calculation for trucks, similar to site_A_to_port_A
            if B_fuel_type == 0:
                thermal_resist_val = truck_tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                                    truck_tank_insulator_thickness_arg / insulator_thermal_conduct_arg
                OHTC = 1 / thermal_resist_val if thermal_resist_val > 0 else float('inf')
            else:
                # Assuming if not LH2 (B_fuel_type != 0), truck OHTC might be different,
                # or you might want a specific truck OHTC value instead of OHTC_ship.
                # For now, replicating the logic from your site_A_to_port_A for OHTC.
                OHTC = OHTC_ship_arg[B_fuel_type] # Or a truck-specific OHTC value if available

            heat_required_val = OHTC * storage_area_truck * (end_local_temperature_arg + 273 - 20) # Using end_local_temperature
            refrig_ener_consumed = (heat_required_val / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / \
                                1000000 * 60 * duration_port_to_B_arg * number_of_trucks # Using duration_port_to_B
            
            local_BOR_truck_trans_val = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_truck_trans_arg[B_fuel_type] # Using end_local_temperature
            current_BOG_loss = A * local_BOR_truck_trans_val / (24 * 60) * duration_port_to_B_arg # Using duration_port_to_B

            refrig_money = (refrig_ener_consumed / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / \
                        diesel_density_arg * diesel_price_end_arg
            money = diesel_money + refrig_money
            total_energy_consumed = trans_energy_required + refrig_ener_consumed
            
            A_after_loss = A - current_BOG_loss
            
            G_emission_energy = (total_energy_consumed * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
            G_emission = G_emission_energy + current_BOG_loss * GWP_chem_list_arg[B_fuel_type]
            net_BOG_loss = current_BOG_loss

            # Recirculation logic (C_recirculation_BOG is user_define[2], D_truck_apply is user_define[3])
            if C_recirculation_BOG == 2:
                if D_truck_apply == 1: # Re-liquefy BOG
                    usable_BOG = current_BOG_loss * BOG_recirculation_truck_percentage_arg * 0.01
                    BOG_flowrate = usable_BOG / duration_port_to_B_arg * 60 # kg/hr
                    
                    reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                    reliq_ener_consumed = reliq_ener_required * usable_BOG
                    
                    total_energy_consumed += reliq_ener_consumed
                    reliq_money = (reliq_ener_consumed / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / \
                                diesel_density_arg * diesel_price_end_arg
                    money = diesel_money + reliq_money + refrig_money
                    
                    A_after_loss += usable_BOG
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
                    
                    G_emission_energy = (total_energy_consumed * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
                    G_emission = G_emission_energy + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]

                elif D_truck_apply == 2: # Use BOG as another energy source
                    usable_BOG = current_BOG_loss * BOG_recirculation_truck_percentage_arg * 0.01
                    usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
                    
                    energy_saved_from_refrig = min(usable_ener, refrig_ener_consumed)
                    money_saved_from_refrig = (energy_saved_from_refrig / (HHV_diesel_arg * diesel_engine_eff_arg * EIM_truck_eff_arg / 100)) / \
                                            diesel_density_arg * diesel_price_end_arg
                    
                    total_energy_consumed = trans_energy_required + (refrig_ener_consumed - energy_saved_from_refrig)
                    money = diesel_money + (refrig_money - money_saved_from_refrig)
                    
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
                    
                    G_emission_energy = (total_energy_consumed * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
                    G_emission = G_emission_energy + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]
            
            return money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss

    # This definition goes inside run_lca_model
        def chem_site_B_unloading_from_truck(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            V_flowrate_arg, \
            number_of_cryo_pump_load_storage_site_B_arg, \
            dBOR_dT_arg, \
            end_local_temperature_arg, \
            BOR_unloading_arg, \
            liquid_chem_density_arg, \
            head_pump_arg, \
            pump_power_factor_arg, \
            EIM_cryo_pump_arg, \
            ss_therm_cond_arg, \
            pipe_length_arg, \
            pipe_inner_D_arg, \
            pipe_thick_arg, \
            COP_refrig_arg, \
            EIM_refrig_eff_arg, \
            end_electricity_price_tuple_arg, \
            CO2e_end_arg, \
            GWP_chem_list_arg = process_args_tuple
            # Note: Your snippet for pumping_power in this function did not include EIM_cryo_pump.
            # I've included EIM_cryo_pump_arg for consistency with similar pumping calculations.
            # If your original LCA_WebApp.py for this specific function intentionally omits it,
            # you can remove EIM_cryo_pump_arg from unpacking and the formula below,
            # and adjust the packing in total_chem.

            # Original logic of the function, using the unpacked '_arg' variables
            duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_storage_site_B_arg  # hr
            
            local_BOR_unloading_val = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_unloading_arg[B_fuel_type]
            BOG_loss = local_BOR_unloading_val * (1 / 24) * duration * A  # kg
            
            # Using EIM_cryo_pump_arg in the formula
            pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * \
                            head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100) # W
            
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            if log_arg <= 0: # Safety check
                q_pipe = 0
            else:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * \
                        (end_local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))  # W
            
            ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600  # MJ
            ener_consumed = pumping_power * duration * 3600 * 1 / 1000000 + ener_consumed_refrig  # MJ
            
            A_after_loss = A - BOG_loss # Net amount
            
            money = ener_consumed * end_electricity_price_tuple_arg[2]  # $ (using end_electricity_price)
            G_emission = ener_consumed * 0.2778 * CO2e_end_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]  # kgCO2 (using CO2e_end)
            
            return money, ener_consumed, G_emission, A_after_loss, BOG_loss

    # This definition goes inside run_lca_model
        def chem_storage_at_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            liquid_chem_density_arg, storage_volume_arg, dBOR_dT_arg, end_local_temperature_arg, \
            BOR_land_storage_arg, storage_time_C_arg, storage_radius_arg, tank_metal_thickness_arg, \
            metal_thermal_conduct_arg, tank_insulator_thickness_arg, insulator_thermal_conduct_arg, \
            COP_refrig_arg, EIM_refrig_eff_arg, end_electricity_price_tuple_arg, CO2e_end_arg, \
            GWP_chem_list_arg, BOG_recirculation_storage_percentage_arg, \
            LH2_plant_capacity_arg, EIM_liquefication_arg, \
            fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg = process_args_tuple

            # Original logic of the function, using the unpacked '_arg' variables
            number_of_storage = math.ceil(A / liquid_chem_density_arg[B_fuel_type] / storage_volume_arg[B_fuel_type])
            local_BOR_storage = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_land_storage_arg[B_fuel_type]
            current_BOG_loss = A * local_BOR_storage * storage_time_C_arg
            
            A_after_loss = A - current_BOG_loss
            
            storage_area_val = 4 * np.pi * (storage_radius_arg[B_fuel_type]**2) * number_of_storage
            
            thermal_resist_val = tank_metal_thickness_arg / metal_thermal_conduct_arg + \
                                tank_insulator_thickness_arg / insulator_thermal_conduct_arg
            OHTC_val = 1 / thermal_resist_val if thermal_resist_val > 0 else float('inf')
            
            heat_required_val = OHTC_val * storage_area_val * (end_local_temperature_arg + 273 - 20) # Using end_local_temperature
            ener_consumed_refrig = (heat_required_val / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * 86400 * storage_time_C_arg
            
            money = ener_consumed_refrig * end_electricity_price_tuple_arg[2] # Using end_electricity_price
            total_energy_consumed = ener_consumed_refrig
            
            G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + current_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end
            net_BOG_loss = current_BOG_loss

            # Recirculation logic (C_recirculation_BOG is user_define[2], E_storage_apply is user_define[4])
            if C_recirculation_BOG == 2:
                if E_storage_apply == 1: # Re-liquefy BOG
                    usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                    BOG_flowrate = usable_BOG / storage_time_C_arg * 1 / 24 # kg/hr
                    
                    reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                    reliq_ener_consumed = reliq_ener_required * usable_BOG
                    
                    total_energy_consumed += reliq_ener_consumed
                    money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                    
                    A_after_loss += usable_BOG
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                    
                    G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end

                elif E_storage_apply == 2: # Use BOG as another energy source
                    usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                    usable_ener = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
                    
                    # ener_consumed here refers to ener_consumed_refrig from before the BOG logic
                    initial_refrig_energy = ener_consumed_refrig 
                    ener_consumed_refrig_after_bog = initial_refrig_energy - usable_ener
                    if ener_consumed_refrig_after_bog < 0:
                        ener_consumed_refrig_after_bog = 0
                    
                    total_energy_consumed = ener_consumed_refrig_after_bog # Update total energy
                    money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                    
                    net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                    # A_after_loss remains A - current_BOG_loss, as BOG is consumed
                    
                    G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end
            
            return money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss

    # This definition goes inside run_lca_model
        def chem_unloading_from_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            V_flowrate_arg, \
            number_of_cryo_pump_load_storage_site_B_arg, \
            dBOR_dT_arg, \
            end_local_temperature_arg, \
            BOR_unloading_arg, \
            liquid_chem_density_arg, \
            head_pump_arg, \
            pump_power_factor_arg, \
            EIM_cryo_pump_arg, \
            ss_therm_cond_arg, \
            pipe_length_arg, \
            pipe_inner_D_arg, \
            pipe_thick_arg, \
            COP_refrig_arg, \
            EIM_refrig_eff_arg, \
            end_electricity_price_tuple_arg, \
            CO2e_end_arg, \
            GWP_chem_list_arg = process_args_tuple
            # Note: Your snippet for pumping_power in this function did not include EIM_cryo_pump
            # in the denominator. I've included EIM_cryo_pump_arg for consistency with
            # similar pumping calculations in other functions. If your original LCA_WebApp.py
            # for this specific function intentionally omits it, you can remove EIM_cryo_pump_arg
            # from unpacking and the formula below, and adjust the packing in total_chem.

            # Original logic of the function, using the unpacked '_arg' variables
            duration = A / (V_flowrate_arg[B_fuel_type]) / number_of_cryo_pump_load_storage_site_B_arg  # hr
            
            local_BOR_unloading_val = dBOR_dT_arg[B_fuel_type] * (end_local_temperature_arg - 25) + BOR_unloading_arg[B_fuel_type]
            BOG_loss = local_BOR_unloading_val * (1 / 24) * duration * A  # kg
            
            # Using EIM_cryo_pump_arg in the formula for consistency
            pumping_power = liquid_chem_density_arg[B_fuel_type] * V_flowrate_arg[B_fuel_type] * (1 / 3600) * \
                            head_pump_arg * 9.8 / (367 * pump_power_factor_arg) / (EIM_cryo_pump_arg / 100)  # W
            
            log_arg = (pipe_inner_D_arg + 2 * pipe_thick_arg) / pipe_inner_D_arg
            if log_arg <= 0: # Safety check
                q_pipe = 0
            else:
                q_pipe = 2 * np.pi * ss_therm_cond_arg * pipe_length_arg * \
                        (end_local_temperature_arg - (-253)) / (2.3 * np.log10(log_arg))  # W
            
            ener_consumed_refrig = (q_pipe / (COP_refrig_arg[B_fuel_type] * EIM_refrig_eff_arg / 100)) / 1000000 * duration * 3600  # MJ
            ener_consumed = pumping_power * duration * 3600 * 1 / 1000000 + ener_consumed_refrig  # MJ
            
            A_after_loss = A - BOG_loss # Net amount
            
            money = ener_consumed * end_electricity_price_tuple_arg[2]  # $ (using end_electricity_price)
            G_emission = ener_consumed * 0.2778 * CO2e_end_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]  # kgCO2 (using CO2e_end)
            
            return money, ener_consumed, G_emission, A_after_loss, BOG_loss

    # This definition goes inside run_lca_model
        def chem_convert_to_H2(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            mass_conversion_to_H2_arg, \
            eff_energy_chem_to_H2_arg, \
            energy_chem_to_H2_arg, \
            CO2e_end_arg, \
            end_electricity_price_tuple_arg = process_args_tuple
            # Note: GWP_chem is not used in the snippet for BOG_loss here, as BOG_loss is set to 0.
            # If BOG_loss could be non-zero and have a GWP impact, GWP_chem_list_arg would be needed.

            # Original logic of the function, using the unpacked '_arg' variables
            if B_fuel_type == 0:  # If it's already Hydrogen
                money = 0
                convert_energy = 0
                BOG_loss = 0 # No BOG loss during conversion if it's already H2
                G_emission = 0
                # A remains A (no change in amount or type)
            else:
                # Convert chemical (NH3 or CH3OH) to H2 weight
                convert_to_H2_weight = A * mass_conversion_to_H2_arg[B_fuel_type]
                
                convert_energy = energy_chem_to_H2_arg[B_fuel_type] * A / eff_energy_chem_to_H2_arg[B_fuel_type]  # Total energy for conversion
                
                G_emission = convert_energy * 0.2778 * CO2e_end_arg * 0.001  # Emissions from energy use
                money = convert_energy * end_electricity_price_tuple_arg[2]   # Cost of energy
                
                BOG_loss = 0 # Assuming no BOG loss during the chemical conversion process itself
                A = convert_to_H2_weight # The chemical amount is now the H2 equivalent weight
                
                # Note: The GWP of the original chemical is not accounted for here as it's being converted,
                # and BOG_loss from this specific process is assumed to be 0.
                # If there were fugitive emissions of the original chemical *during conversion*,
                # GWP_chem_list_arg would be needed.

            return money, convert_energy, G_emission, A, BOG_loss

        #################################### PH2 section:
    # This definition goes inside run_lca_model
        def PH2_pressurization_at_site_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            PH2_storage_V_arg, \
            numbers_of_PH2_storage_at_start_arg, \
            PH2_pressure_fnc_helper, \
            multistage_compress_helper, \
            multistage_eff_arg, \
            start_electricity_price_tuple_arg, \
            CO2e_start_arg = process_args_tuple
            # Note: GWP_chem is not used in this function as leak_loss is 0.
            # If leak_loss could be non-zero and have a GWP, GWP_chem_list_arg would be needed.

            # Original logic of the function, using the unpacked '_arg' variables and helper functions
            # Ensure B_fuel_type is 0 for PH2 pathway, otherwise density calculations might be off
            # or PH2_storage_V might need to be an array specific to fuel type if this function
            # were ever to be used for something other than pure H2.
            # For now, assuming this function is only for B_fuel_type == 0 (Hydrogen).
            
            PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_start_arg)  # kg/m3
            PH2_pressure = PH2_pressure_fnc_helper(PH2_density)  # bar
            
            compress_energy = multistage_compress_helper(PH2_pressure) * A / (multistage_eff_arg / 100) # MJ (assuming multistage_eff is in %)
            
            money = start_electricity_price_tuple_arg[2] * compress_energy  # $
            G_emission = compress_energy * 0.2778 * CO2e_start_arg * 0.001  # kgCO2
            
            leak_loss = 0 # As per your snippet
            
            # A (amount of chemical) does not change in this pressurization step, only its state.
            # The 'leak_loss' is returned, which is 0.
            
            # It's good practice to avoid print statements in functions that are part of a web backend,
            # as they will go to the server console and not the user.
            # For debugging, you can use app.logger.debug(f'H2 pressure...: {PH2_pressure}')
            # print(f'H2 pressure at pressurization process at site A (bar): {PH2_pressure}') 
            
            return money, compress_energy, G_emission, A, leak_loss

    # This definition goes inside run_lca_model
        def PH2_site_A_to_port_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            PH2_storage_V_arg, \
            numbers_of_PH2_storage_at_start_arg, \
            PH2_pressure_fnc_helper, \
            coor_start_lat_arg, coor_start_lng_arg, \
            start_port_lat_arg, start_port_lng_arg, \
            straight_line_dis_helper, \
            kinematic_viscosity_PH2_helper, \
            compressor_velocity_arg, \
            pipeline_diameter_arg, \
            solve_colebrook_helper, \
            epsilon_arg, \
            PH2_transport_energy_helper, \
            gas_chem_density_arg, \
            numbers_of_PH2_storage_arg, \
            start_electricity_price_tuple_arg, \
            CO2e_start_arg = process_args_tuple
            # Note: GWP_chem is not used in this function as trans_loss is not directly tied to GWP here.
            # If trans_loss (leakage) had a GWP impact, GWP_chem_list_arg would be needed.

            # Original logic of the function, using the unpacked '_arg' variables and helper functions
            # Assuming B_fuel_type is 0 (Hydrogen) for this PH2 specific function
            
            PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_start_arg)  # kg/m3
            PH2_pressure = PH2_pressure_fnc_helper(PH2_density)  # bar

            # Calculate distance L using the passed coordinates and helper
            L_km = straight_line_dis_helper(coor_start_lat_arg, coor_start_lng_arg, start_port_lat_arg, start_port_lng_arg) # km
            L_meters = L_km * 1000 # Convert km to meters for P_drop calculation

            kine_vis = kinematic_viscosity_PH2_helper(PH2_pressure)
            Re = compressor_velocity_arg * pipeline_diameter_arg / kine_vis
            f_D = solve_colebrook_helper(Re, epsilon_arg, pipeline_diameter_arg)
            
            # Pressure drop calculation using L_meters
            P_drop_Pa = L_meters * f_D * PH2_density * (compressor_velocity_arg**2) / (2 * pipeline_diameter_arg) # Pa
            P_drop_bar = P_drop_Pa / 100000  # bar
            
            # Pumping power and energy (commented out in your snippet, but calculations shown)
            # pipe_area = np.pi * (pipeline_diameter_arg**2) / 4
            # pumping_power_watts = P_drop_Pa * compressor_velocity_arg * pipe_area # Watts
            # duration_seconds = A / PH2_density / pipe_area / compressor_velocity_arg # seconds
            # pumping_ener_MJ = pumping_power_watts * duration_seconds / 1000000 # MJ
            # print('pumping energy (calculated from P_drop): ',pumping_ener_MJ)

            ener_consumed = PH2_transport_energy_helper(L_km) * A  # MJ (assuming PH2_transport_energy takes km)
            final_P_PH2 = PH2_pressure - P_drop_bar

            # Ensure final pressure is not negative
            if final_P_PH2 < 0:
                final_P_PH2 = 0 # Or handle as an error indicating insufficient initial pressure
                # This would also affect final_PH2_density and A_final

            final_PH2_density = PH2_density_fnc_helper(final_P_PH2) # Helper for density from pressure
            A_final = final_PH2_density * PH2_storage_V_arg * numbers_of_PH2_storage_arg # Using the general numbers_of_PH2_storage
            
            # Ensure A_final is not greater than A (can happen if P_drop is negative due to issues)
            A_final = min(A, A_final) if final_P_PH2 > 0 else 0

            trans_loss = A - A_final
            if trans_loss < 0: trans_loss = 0 # Loss cannot be negative

            money = start_electricity_price_tuple_arg[2] * ener_consumed 
            G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001
            
            # print(f'PH2 site A to port A - P_drop (bar): {P_drop_bar}')
            # print(f'PH2 site A to port A - final pressure at port A (bar): {final_P_PH2}')
            
            return money, ener_consumed, G_emission, A_final, trans_loss

    # This definition goes inside run_lca_model
        def port_A_liquification(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            liquification_data_fitting_helper, \
            LH2_plant_capacity_arg, \
            EIM_liquefication_arg, \
            start_port_electricity_price_tuple_arg, \
            CO2e_start_arg = process_args_tuple
            # Note: GWP_chem is not used in your snippet for this function's emission calculation,
            # as BOG_loss is calculated but not explicitly added to G_emission with its GWP factor.
            # Also, 'A' is returned without BOG_loss being subtracted from it in your snippet.

            # Original logic of the function, using the unpacked '_arg' variables and helper functions
            # This function is specific to B_fuel_type == 0 (Hydrogen) being liquefied.
            
            if B_fuel_type != 0:
                # This function is intended for liquefying H2 that arrived as gas.
                # If the chemical is not H2, this step might be different or skipped.
                # Returning zero impact if called with non-H2 for safety.
                return 0, 0, 0, A, 0

            LH2_energy_required = liquification_data_fitting_helper(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)  # MJ/kg
            LH2_ener_consumed = LH2_energy_required * A  # MJ
            
            # Using electricity price at Port A
            LH2_money = LH2_ener_consumed * start_port_electricity_price_tuple_arg[2]  # $
            
            # Using CO2e at Port A (assuming CO2e_start is representative of Port A's grid,
            # or you might have a CO2e_port_A variable if it's different)
            G_emission = LH2_ener_consumed * 0.2778 * CO2e_start_arg * 0.001  # kgCO2
            
            BOG_loss = 0.016 * A  # kg; ref [11] page 21
            
            # In your snippet, 'A' (the amount of chemical) is NOT reduced by BOG_loss in the return.
            # The BOG_loss is calculated and returned, but the original amount 'A' is passed through.
            # If A should be reduced, it would be: A_after_loss = A - BOG_loss, then return A_after_loss.
            # Also, G_emission does not include GWP of BOG_loss here.
            
            return LH2_money, LH2_ener_consumed, G_emission, A, BOG_loss

    # This definition goes inside run_lca_model
        def H2_pressurization_at_port_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            latent_H_H2_arg, \
            specific_heat_H2_arg, \
            PH2_storage_V_arg, \
            numbers_of_PH2_storage_arg, \
            PH2_pressure_fnc_helper, \
            multistage_compress_helper, \
            multistage_eff_arg, \
            end_port_electricity_price_tuple_arg, \
            CO2e_end_arg = process_args_tuple
            # Note: GWP_chem is not used in this function as leak_loss is 0.
            # If leak_loss could be non-zero and have a GWP, GWP_chem_list_arg would be needed.

            # Original logic of the function, using the unpacked '_arg' variables and helper functions
            # This function is specific to B_fuel_type == 0 (Hydrogen).
            
            if B_fuel_type != 0:
                # This function is intended for pressurizing H2.
                # If the chemical is not H2, this step is likely irrelevant.
                # Returning zero impact if called with non-H2 for safety.
                return 0, 0, 0, A, 0

            # Energy for vaporization (if input A is liquid H2 at its boiling point)
            Q_latent = latent_H_H2_arg * A  # MJ
            # Energy to raise temperature from boiling point (approx 20K for H2) to 300K (approx 27C)
            # Assuming input A is at boiling point after vaporization.
            # The (300-20) implies heating from 20K to 300K.
            Q_sensible = A * specific_heat_H2_arg * (300 - 20)  # MJ 

            # Density and pressure calculation for compression
            # This assumes 'A' is now gaseous H2 at some initial (likely low) pressure post-vaporization
            # and the PH2_storage_V is for the compressed gas.
            # If A is the mass of H2, then PH2_density is mass/volume.
            # This part might need adjustment based on the state of A entering this compression stage.
            # For now, assuming A is mass of H2 gas at some initial state to be compressed into storage.
            PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_arg)  # kg/m3
            PH2_pressure = PH2_pressure_fnc_helper(PH2_density)  # bar
            
            compress_energy = multistage_compress_helper(PH2_pressure) * A / (multistage_eff_arg / 100)  # MJ (assuming multistage_eff is in %)
            
            total_energy_consumed = compress_energy + Q_latent + Q_sensible
            
            # Using electricity price at Port B
            money = end_port_electricity_price_tuple_arg[2] * total_energy_consumed  # $
            
            # Using CO2e at Port B (end location)
            G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001  # kgCO2
            
            leak_loss = 0  # As per your snippet
            
            # 'A' (amount of chemical) does not change by mass in this pressurization step,
            # only its state (temperature and pressure).
            # The 'leak_loss' is returned, which is 0.
            
            # print(f'H2 pressure at pressurization process at port B (bar): {PH2_pressure}')
            
            return money, total_energy_consumed, G_emission, A, leak_loss

    # This definition goes inside run_lca_model
        def PH2_port_B_to_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            PH2_density_fnc_helper, \
            target_pressure_site_B_arg, \
            PH2_storage_V_arg, \
            numbers_of_PH2_storage_at_port_B_arg, \
            PH2_pressure_fnc_helper, \
            end_port_lat_arg, end_port_lng_arg, \
            coor_end_lat_arg, coor_end_lng_arg, \
            straight_line_dis_helper, \
            kinematic_viscosity_PH2_helper, \
            compressor_velocity_arg, \
            pipeline_diameter_arg, \
            solve_colebrook_helper, \
            epsilon_arg, \
            PH2_transport_energy_helper, \
            end_port_electricity_price_tuple_arg, \
            CO2e_end_arg = process_args_tuple
            # Note: GWP_chem is not used as trans_loss GWP impact isn't explicitly calculated here.
            #       numbers_of_PH2_storage_at_port_B_arg is assumed for calculating initial density/pressure at Port B.
            #       Your snippet had 'numbers_of_PH2_storage' for final density, I'll assume it's the same
            #       unless a different 'numbers_of_PH2_storage_at_site_B' is intended and passed.

            # Original logic of the function, using the unpacked '_arg' variables and helper functions
            # This function is specific to B_fuel_type == 0 (Hydrogen).
            
            if B_fuel_type != 0:
                return 0, 0, 0, A, 0 # Should not be called for non-H2

            # Calculate initial conditions at Port B for pipeline transport
            # Assuming 'A' is the mass of H2 in storage at Port B
            initial_PH2_density_at_port_B = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_port_B_arg)
            initial_PH2_pressure_at_port_B = PH2_pressure_fnc_helper(initial_PH2_density_at_port_B)

            # Calculate pipeline length (L)
            L_km = straight_line_dis_helper(end_port_lat_arg, end_port_lng_arg, coor_end_lat_arg, coor_end_lng_arg) # km
            L_meters = L_km * 1000 # meters

            kine_vis = kinematic_viscosity_PH2_helper(initial_PH2_pressure_at_port_B) # Use initial pressure at Port B
            Re = compressor_velocity_arg * pipeline_diameter_arg / kine_vis
            f_D = solve_colebrook_helper(Re, epsilon_arg, pipeline_diameter_arg)
            
            # Pressure drop calculation using initial density at Port B
            P_drop_Pa = L_meters * f_D * initial_PH2_density_at_port_B * (compressor_velocity_arg**2) / (2 * pipeline_diameter_arg) # Pa
            P_drop_bar = P_drop_Pa / 100000  # bar
            
            # Commented out pumping power calculation from your snippet
            # pipe_area = np.pi * (pipeline_diameter_arg**2) / 4
            # pumping_power_watts = P_drop_Pa * compressor_velocity_arg * pipe_area 
            # duration_seconds = A / initial_PH2_density_at_port_B / pipe_area / compressor_velocity_arg
            # pumping_ener_MJ = pumping_power_watts * duration_seconds / 1000000
            # print('pumping energy (calculated from P_drop): ', pumping_ener_MJ)

            ener_consumed = PH2_transport_energy_helper(L_km) * A  # MJ (assuming PH2_transport_energy takes km)
            
            final_P_PH2_at_site_B = initial_PH2_pressure_at_port_B - P_drop_bar

            # Ensure final pressure is not negative
            if final_P_PH2_at_site_B < 0:
                final_P_PH2_at_site_B = 0 
            
            # Density at Site B based on the actual final pressure after pipeline transport
            final_PH2_density_at_site_B = PH2_density_fnc_helper(final_P_PH2_at_site_B)
            
            # Your snippet calculates numbers_of_PH2_storage based on target_pressure_site_B.
            # This seems to be for sizing destination storage, let's retain that part for A_final.
            # However, the actual A_final should be based on what's physically left.
            target_density_at_site_B = PH2_density_fnc_helper(target_pressure_site_B_arg)
            # If using a fixed number of storage units at Site B (e.g., numbers_of_PH2_storage_arg for Site B)
            # then A_final would be:
            # A_final = final_PH2_density_at_site_B * PH2_storage_V_arg * numbers_of_PH2_storage_at_site_B_arg (if passed)
            # For now, let's assume the number of storage units at site B is flexible to hold A at target density,
            # or that A_final is determined by the final density in the available total storage volume.

            # The crucial part is that the mass A does not change due to pressure drop, only its density/pressure.
            # Transport loss here implies leakage, which is not explicitly calculated in P_drop.
            # If PH2_transport_energy_helper already accounts for energy for re-compression to overcome P_drop
            # and fugitive losses, then trans_loss might be a fixed percentage or part of that helper.
            # For now, let's assume trans_loss represents unrecoverable gas due to pressure becoming too low,
            # or actual leakage. If pressure is 0, all is lost for practical purposes.
            
            A_final = A # Assuming no mass loss unless pressure drops to zero
            if final_P_PH2_at_site_B <= 0: # If pressure drops too much, assume unusable
                A_final = 0
            
            trans_loss = A - A_final
            if trans_loss < 0: trans_loss = 0

            # Cost of energy for transport (e.g., for intermediate compressors if PH2_transport_energy represents this)
            # Using electricity price at Port B (origin of this pipeline segment)
            money = end_port_electricity_price_tuple_arg[2] * ener_consumed 
            
            # Emissions from energy consumption for transport
            G_emission = ener_consumed * 0.2778 * CO2e_end_arg * 0.001
            
            # print(f'PH2 port B to site B - P_drop (bar): {P_drop_bar}')
            # print(f'PH2 port B to site B - final pressure at site B (bar): {final_P_PH2_at_site_B}')
            
            return money, ener_consumed, G_emission, A_final, trans_loss
        
    # This definition goes inside run_lca_model
        def PH2_storage_at_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
            # Unpack the specific arguments this function needs from the passed-in tuple.
            # The order of variables here MUST EXACTLY MATCH the order they are packed.

            PH2_storage_V_at_site_B_arg, \
            numbers_of_PH2_storage_at_site_B_arg, \
            PH2_pressure_fnc_helper = process_args_tuple
            # Note: No other parameters like electricity price, CO2e, GWP are needed
            # as this function, per your snippet, has no associated operational costs or emissions.

            # Original logic of the function, using the unpacked '_arg' variables and helper functions
            # This function is specific to B_fuel_type == 0 (Hydrogen).
            
            if B_fuel_type != 0:
                # This function is for PH2 storage.
                # If the chemical is not H2, this step is likely irrelevant or different.
                return 0, 0, 0, A, 0 # Return zero impact

            # Calculate density and pressure based on the amount A and Site B storage configuration
            # Ensure PH2_storage_V_at_site_B_arg and numbers_of_PH2_storage_at_site_B_arg are positive
            if PH2_storage_V_at_site_B_arg <= 0 or numbers_of_PH2_storage_at_site_B_arg <= 0:
                # Handle error or set default pressure if storage volume/number is invalid
                PH2_density = 0
                PH2_pressure = 0
                # Or raise an error: raise ValueError("Storage volume and number must be positive.")
            else:
                PH2_density = A / (PH2_storage_V_at_site_B_arg * numbers_of_PH2_storage_at_site_B_arg)  # kg/m3
                PH2_pressure = PH2_pressure_fnc_helper(PH2_density)  # bar
            
            # As per your snippet, this step has no operational costs, energy, or emissions.
            money = 0
            ener_consumed = 0
            G_emission = 0
            BOG_loss = 0 # Assuming BOG_loss is specific to a storage *duration*, which isn't a factor here,
                        # or that this function just notes the state, not losses over time.
            
            # The amount of chemical A does not change in this state-defining step.
            # Any losses would have occurred in previous transport or timed storage steps.
            
            # print(f'PH2 pressure at final storage at site B (bar): {PH2_pressure}')
            
            return money, ener_consumed, G_emission, A, BOG_loss

        # --- 5. Optimization ---
        target_weight = total_ship_volume * liquid_chem_density[fuel_type] * 0.98  # kg, ref [3] section 2.1:  the filling limit is defined as 98% for ships cargo tank.
        
        def optimization_chem_weight(A_initial_guess, args_for_optimizer_tuple):
            # Unpack the main arguments bundle passed from minimize
            user_define_params, \
            process_funcs_for_optimization, \
            all_shared_params_tuple = args_for_optimizer_tuple

            # Unpack ALL shared parameters that ANY of the first 7 functions might need.
            # The order here MUST MATCH how they were packed into all_shared_params_tuple
            # in run_lca_model.
            (LH2_plant_capacity_opt, EIM_liquefication_opt, specific_heat_chem_opt,
            start_local_temperature_opt, boiling_point_chem_opt, latent_H_chem_opt,
            COP_liq_opt, start_electricity_price_opt, CO2e_start_opt, GWP_chem_opt,
            V_flowrate_opt,
            number_of_cryo_pump_load_truck_site_A_opt, # Assuming this is for site A truck loading
            number_of_cryo_pump_load_storage_port_A_opt, # For port A storage unloading
            number_of_cryo_pump_load_ship_port_A_opt, # For port A ship loading
            dBOR_dT_opt, BOR_loading_opt, BOR_unloading_opt, # Added BOR_unloading
            head_pump_opt, pump_power_factor_opt, EIM_cryo_pump_opt,
            ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt, pipe_thick_opt,
            COP_refrig_opt, EIM_refrig_eff_opt,
            road_delivery_ener_opt, HHV_chem_opt, distance_A_to_port_opt,
            chem_in_truck_weight_opt, truck_economy_opt, truck_tank_radius_opt, truck_tank_length_opt,
            truck_tank_metal_thickness_opt, metal_thermal_conduct_opt,
            truck_tank_insulator_thickness_opt, insulator_thermal_conduct_opt,
            OHTC_ship_opt, duration_A_to_port_opt, BOR_truck_trans_opt,
            HHV_diesel_opt, diesel_engine_eff_opt, EIM_truck_eff_opt,
            diesel_density_opt, diesel_price_start_opt, diesel_price_end_opt, CO2e_diesel_opt,
            BOG_recirculation_truck_opt, # This is the BOG_recirculation_truck_percentage
            fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem_opt,
            storage_time_A_opt, liquid_chem_density_opt, storage_volume_opt,
            storage_radius_opt, BOR_land_storage_opt, tank_metal_thickness_opt,
            tank_insulator_thickness_opt, BOG_recirculation_storage_opt # BOG_recirculation_storage_percentage
            ) = all_shared_params_tuple

            X = A_initial_guess[0]  # Current chemical weight being optimized

            # Loop through the first 7 process functions
            for func_to_call in process_funcs_for_optimization:
                process_args_for_current_func = () 

                if func_to_call.__name__ == "site_A_chem_production":
                    # Only needs GWP_chem_opt if there were potential BOG with GWP.
                    # Assuming it matches the refactored version that takes minimal args.
                    process_args_for_current_func = (GWP_chem_opt,) 
                
                elif func_to_call.__name__ == "site_A_chem_liquification":
                    process_args_for_current_func = (
                        LH2_plant_capacity_opt, EIM_liquefication_opt, specific_heat_chem_opt,
                        start_local_temperature_opt, boiling_point_chem_opt, latent_H_chem_opt,
                        COP_liq_opt, start_electricity_price_opt, CO2e_start_opt, GWP_chem_opt
                    )
                
                elif func_to_call.__name__ == "chem_site_A_loading_to_truck":
                    process_args_for_current_func = (
                        V_flowrate_opt, 
                        number_of_cryo_pump_load_truck_site_A_opt, # Specific pump number for this stage
                        dBOR_dT_opt, start_local_temperature_opt, BOR_loading_opt, 
                        liquid_chem_density_opt, head_pump_opt, pump_power_factor_opt, 
                        EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt,
                        pipe_inner_D_opt, pipe_thick_opt, COP_refrig_opt, EIM_refrig_eff_opt,
                        start_electricity_price_opt, CO2e_start_opt, GWP_chem_opt
                    )
                
                elif func_to_call.__name__ == "site_A_to_port_A":
                    process_args_for_current_func = (
                        road_delivery_ener_opt, HHV_chem_opt, chem_in_truck_weight_opt, truck_economy_opt,
                        distance_A_to_port_opt, HHV_diesel_opt, diesel_density_opt, 
                        diesel_price_start_opt, truck_tank_radius_opt, truck_tank_length_opt, 
                        truck_tank_metal_thickness_opt, metal_thermal_conduct_opt, 
                        truck_tank_insulator_thickness_opt, insulator_thermal_conduct_opt, 
                        OHTC_ship_opt, start_local_temperature_opt, COP_refrig_opt, 
                        EIM_refrig_eff_opt, duration_A_to_port_opt, dBOR_dT_opt, 
                        BOR_truck_trans_opt, diesel_engine_eff_opt, EIM_truck_eff_opt, 
                        CO2e_diesel_opt, GWP_chem_opt,
                        BOG_recirculation_truck_opt, # This is the BOG_recirculation_truck_percentage
                        LH2_plant_capacity_opt, EIM_liquefication_opt,
                        fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem_opt
                    )
                
                elif func_to_call.__name__ == "port_A_unloading_to_storage":
                    process_args_for_current_func = (
                        V_flowrate_opt, 
                        number_of_cryo_pump_load_storage_port_A_opt, # Specific pump number
                        dBOR_dT_opt, start_local_temperature_opt, 
                        BOR_unloading_opt, # Use BOR_unloading for this stage
                        liquid_chem_density_opt, head_pump_opt, pump_power_factor_opt, 
                        EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt,
                        pipe_inner_D_opt, pipe_thick_opt, COP_refrig_opt, EIM_refrig_eff_opt,
                        start_electricity_price_opt, CO2e_start_opt, GWP_chem_opt
                    )
                
                elif func_to_call.__name__ == "chem_storage_at_port_A":
                    process_args_for_current_func = (
                        liquid_chem_density_opt, storage_volume_opt, dBOR_dT_opt, 
                        start_local_temperature_opt, BOR_land_storage_opt, storage_time_A_opt, 
                        storage_radius_opt, tank_metal_thickness_opt, metal_thermal_conduct_opt, 
                        tank_insulator_thickness_opt, insulator_thermal_conduct_opt, 
                        COP_refrig_opt, EIM_refrig_eff_opt, start_electricity_price_opt, 
                        CO2e_start_opt, GWP_chem_opt, 
                        BOG_recirculation_storage_opt, # This is BOG_recirculation_storage_percentage
                        LH2_plant_capacity_opt, EIM_liquefication_opt,
                        fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem_opt
                    )
                
    # This is inside the optimization_chem_weight function's loop

                elif func_to_call.__name__ == "chem_loading_to_ship":
                    process_args_for_current_func = (
                        V_flowrate_opt, number_of_cryo_pump_load_ship_port_A_opt, dBOR_dT_opt,
                        start_local_temperature_opt, BOR_loading_opt, liquid_chem_density_opt, head_pump_opt,
                        pump_power_factor_opt, EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt,
                        pipe_thick_opt, boiling_point_chem_opt, EIM_refrig_eff_opt, start_electricity_price_opt,
                        CO2e_start_opt, GWP_chem_opt, storage_area, ship_tank_metal_thickness, 
                        ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density, 
                        ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat, 
                        COP_cooldown, COP_refrig, ship_number_of_tanks
                    )
                # Call the current process function with its tailored arguments
                # user_define_params[0] is the initial placeholder for chem_weight (or target_weight later)
                # user_define_params[1] is B_fuel_type
                # user_define_params[2] is C_recirculation_BOG
                # user_define_params[3] is D_truck_apply
                # user_define_params[4] is E_storage_apply
                # user_define_params[5] is F_maritime_apply
                _, _, _, X, _ = func_to_call(X, 
                                            user_define_params[1], 
                                            user_define_params[2], 
                                            user_define_params[3], 
                                            user_define_params[4], 
                                            user_define_params[5], 
                                            process_args_for_current_func)
            
            # target_weight is accessible from the enclosing run_lca_model scope
            return abs(X - target_weight)

        def constraint(A):
            """Ensures the optimized weight is not less than the target weight."""
            return A[0] - target_weight # This must be >= 0
        con = {'type': 'ineq', 'fun': constraint}

        # This is the target_weight for the optimization
        target_weight = total_ship_volume * liquid_chem_density[fuel_type] * 0.98

        # List of the first 7 process function objects for optimization
        process_funcs_for_optimization = [
            site_A_chem_production, site_A_chem_liquification, chem_site_A_loading_to_truck,
            site_A_to_port_A, port_A_unloading_to_storage, chem_storage_at_port_A,
            chem_loading_to_ship
        ]

        # Bundle ALL shared parameters that ANY of the first 7 functions might need.
        # The order here MUST MATCH the unpacking order in optimization_chem_weight.
        all_shared_params_tuple = (
            # Parameters for site_A_chem_liquification
            LH2_plant_capacity, EIM_liquefication, specific_heat_chem,
            start_local_temperature, boiling_point_chem, latent_H_chem,
            COP_liq, start_electricity_price, CO2e_start, GWP_chem,

            # Parameters for loading/unloading/pumping (general and specific)
            V_flowrate, 
            number_of_cryo_pump_load_truck_site_A,  # For loading truck at Site A
            number_of_cryo_pump_load_storage_port_A, # For unloading to storage at Port A
            number_of_cryo_pump_load_ship_port_A,    # For loading ship at Port A
            dBOR_dT, BOR_loading, BOR_unloading,     # BOR types
            head_pump, pump_power_factor, EIM_cryo_pump,
            ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick,
            COP_refrig, EIM_refrig_eff,

            # Parameters for site_A_to_port_A (truck transport)
            road_delivery_ener, HHV_chem, distance_A_to_port,
            chem_in_truck_weight, truck_economy, truck_tank_radius, truck_tank_length,
            truck_tank_metal_thickness, metal_thermal_conduct,
            truck_tank_insulator_thickness, insulator_thermal_conduct,
            OHTC_ship, # Or a truck-specific OHTC if defined
            duration_A_to_port, BOR_truck_trans,
            HHV_diesel, diesel_engine_eff, EIM_truck_eff,
            diesel_density, diesel_price_start, diesel_price_end, CO2e_diesel,
            BOG_recirculation_truck, # This is the percentage from inputs

            # Parameters for BOG recirculation (if used in first 7 funcs)
            fuel_cell_eff, EIM_fuel_cell, LHV_chem, 
            # LH2_plant_capacity, EIM_liquefication are already above for site_A_chem_liquification

            # Parameters for chem_storage_at_port_A
            storage_time_A, liquid_chem_density, storage_volume, 
            storage_radius, BOR_land_storage, tank_metal_thickness, 
            tank_insulator_thickness, # metal_thermal_conduct, insulator_thermal_conduct already above
            BOG_recirculation_storage # This is the percentage from inputs
            # COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem,
            # LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem are already above
        )

        # This is the tuple that will be passed to scipy.optimize.minimize
        args_for_optimizer_tuple = (
            user_define,                      # Contains B,C,D,E,F parameters
            process_funcs_for_optimization,   # List of function objects
            all_shared_params_tuple           # Tuple of all other parameters
        )

        initial_guess = [target_weight / 0.9] # Initial guess assuming ~10% loss
        
        # Call minimize, passing the new args_for_optimizer_tuple
        result = minimize(optimization_chem_weight,
                        initial_guess,
                        args=(args_for_optimizer_tuple,),
                        method='SLSQP',
                        bounds=[(0, None)],
                        constraints=[con])
                        
        # --- ADD THIS CHECK ---
        if result.success:
            chem_weight = result.x[0]
        else:
            # If the optimization fails, raise an exception with the optimizer's message.
            # This will be caught by the main try...except block and returned as a JSON error.
            raise Exception(f"Optimization failed: {result.message}")
        
        # --- 6. Final Calculation ---
        # This is the 'base' function that runs the main sequence of calculations
        def total_chem_base(A_optimized_chem_weight, B_fuel_type_tc, C_recirculation_BOG_tc, 
                            D_truck_apply_tc, E_storage_apply_tc, F_maritime_apply_tc):
                
                funcs_sequence = [
                    site_A_chem_production, site_A_chem_liquification, chem_site_A_loading_to_truck,
                    site_A_to_port_A, port_A_unloading_to_storage, chem_storage_at_port_A,
                    chem_loading_to_ship, port_to_port, chem_unloading_from_ship,
                    chem_storage_at_port_B, port_B_unloading_from_storage, port_B_to_site_B,
                    chem_site_B_unloading_from_truck, chem_storage_at_site_B,
                    chem_unloading_from_site_B
                ]
                
                R_current_chem = A_optimized_chem_weight
                data_results_list = []
                total_money_tc = 0.0
                total_ener_consumed_tc = 0.0
                total_G_emission_tc = 0.0
                total_S_bog_loss_tc = 0.0
        
                for func_to_call in funcs_sequence:
                    # This block is copied directly from your file and is correct
                    # --- (The entire if/elif chain for packing process_args_for_this_call_tc goes here) ---
                    if func_to_call.__name__ == "site_A_chem_production":
                        process_args_for_this_call_tc = (GWP_chem,)
                    elif func_to_call.__name__ == "site_A_chem_liquification":
                        process_args_for_this_call_tc = (LH2_plant_capacity, EIM_liquefication, specific_heat_chem, start_local_temperature, boiling_point_chem, latent_H_chem, COP_liq, start_electricity_price, CO2e_start, GWP_chem)
                    elif func_to_call.__name__ == "chem_site_A_loading_to_truck":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_truck_site_A, dBOR_dT, start_local_temperature, BOR_loading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem)
                    elif func_to_call.__name__ == "site_A_to_port_A":
                        process_args_for_this_call_tc = (road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance_A_to_port, HHV_diesel, diesel_density, diesel_price_start, truck_tank_radius, truck_tank_length, truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness, insulator_thermal_conduct, OHTC_ship, start_local_temperature, COP_refrig, EIM_refrig_eff, duration_A_to_port, dBOR_dT, BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel, GWP_chem, BOG_recirculation_truck, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem)
                    elif func_to_call.__name__ == "port_A_unloading_to_storage":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_port_A, dBOR_dT, start_local_temperature, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem)
                    elif func_to_call.__name__ == "chem_storage_at_port_A":
                        process_args_for_this_call_tc = (liquid_chem_density, storage_volume, dBOR_dT, start_local_temperature, BOR_land_storage, storage_time_A, storage_radius, tank_metal_thickness, metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem)
                    elif func_to_call.__name__ == "chem_loading_to_ship":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_ship_port_A, dBOR_dT, start_local_temperature, BOR_loading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, boiling_point_chem, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, storage_area, ship_tank_metal_thickness, ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density, ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat, COP_cooldown, COP_refrig, ship_number_of_tanks)
                    elif func_to_call.__name__ == "port_to_port":
                        process_args_for_this_call_tc = (
                            start_local_temperature, end_local_temperature, OHTC_ship,
                            storage_area, ship_number_of_tanks, COP_refrig, EIM_refrig_eff, 
                            port_to_port_duration, selected_marine_fuel_params,
                            dBOR_dT, BOR_ship_trans, GWP_chem, 
                            BOG_recirculation_mati_trans, LH2_plant_capacity, EIM_liquefication, 
                            fuel_cell_eff, EIM_fuel_cell, LHV_chem,
                            avg_ship_power_kw,
                            0.45, # Assumed auxiliary engine efficiency (45%)
                            GWP_N2O
                        )
                    elif func_to_call.__name__ == "chem_unloading_from_ship":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_port_B, dBOR_dT, end_local_temperature, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem)
                    elif func_to_call.__name__ == "chem_storage_at_port_B":
                        process_args_for_this_call_tc = (liquid_chem_density, storage_volume, dBOR_dT, end_local_temperature, BOR_land_storage, storage_time_B, storage_radius, tank_metal_thickness, metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem)
                    elif func_to_call.__name__ == "port_B_unloading_from_storage":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_truck_port_B, dBOR_dT, end_local_temperature, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem)
                    elif func_to_call.__name__ == "port_B_to_site_B":
                        process_args_for_this_call_tc = (road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance_port_to_B, HHV_diesel, diesel_density, diesel_price_end, truck_tank_radius, truck_tank_length, truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness, insulator_thermal_conduct, OHTC_ship, end_local_temperature, COP_refrig, EIM_refrig_eff, duration_port_to_B, dBOR_dT, BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel, GWP_chem, BOG_recirculation_truck, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem)
                    elif func_to_call.__name__ == "chem_site_B_unloading_from_truck":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_site_B, dBOR_dT, end_local_temperature, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem)
                    elif func_to_call.__name__ == "chem_storage_at_site_B":
                        process_args_for_this_call_tc = (liquid_chem_density, storage_volume, dBOR_dT, end_local_temperature, BOR_land_storage, storage_time_C, storage_radius, tank_metal_thickness, metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem)
                    elif func_to_call.__name__ == "chem_unloading_from_site_B":
                        process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_site_B, dBOR_dT, end_local_temperature, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, end_electricity_price, CO2e_end, GWP_chem)
        
                    X_money, Y_energy, Z_emission, R_current_chem, S_bog_loss = \
                        func_to_call(R_current_chem, B_fuel_type_tc, C_recirculation_BOG_tc, D_truck_apply_tc, 
                                    E_storage_apply_tc, F_maritime_apply_tc, process_args_for_this_call_tc)
                    
                    data_results_list.append([func_to_call.__name__, X_money, Y_energy, Z_emission, R_current_chem, S_bog_loss])
                    total_money_tc += X_money
                    total_ener_consumed_tc += Y_energy
                    total_G_emission_tc += Z_emission
                    total_S_bog_loss_tc += S_bog_loss
        
                final_total_result_tc = [total_money_tc, total_ener_consumed_tc, total_G_emission_tc, R_current_chem]
                data_results_list.append(["TOTAL", total_money_tc, total_ener_consumed_tc, total_G_emission_tc, R_current_chem, total_S_bog_loss_tc])
                
                return final_total_result_tc, data_results_list
        
            # --- Start of main execution flow for final calculations ---
        
        # 1. Get the raw results from the base calculation
        final_results_raw, data_raw = total_chem_base(chem_weight, user_define[1], user_define[2], 
                                                    user_define[3], user_define[4], user_define[5])

        # 2. If the fuel is not H2, run the conversion step and update the raw results
        if user_define[1] != 0:
            amount_before_conversion = final_results_raw[3]
            args_for_conversion = (mass_conversion_to_H2, eff_energy_chem_to_H2, energy_chem_to_H2, CO2e_end, end_electricity_price)
            
            money_conv, energy_conv, emission_conv, amount_after_conversion, bog_conv = \
                chem_convert_to_H2(amount_before_conversion, user_define[1], user_define[2], user_define[3], 
                                user_define[4], user_define[5], args_for_conversion)
            
            data_raw.insert(-1, ["chem_convert_to_H2", money_conv, energy_conv, emission_conv, amount_after_conversion, bog_conv])
            
            final_results_raw[0] += money_conv
            final_results_raw[1] += energy_conv
            final_results_raw[2] += emission_conv
            final_results_raw[3] = amount_after_conversion

            data_raw[-1] = ["TOTAL", final_results_raw[0], final_results_raw[1], final_results_raw[2], final_results_raw[3], 0]
        
        # 3. Now that all calculations are done, define the final denominators
        final_chem_kg_denominator = final_results_raw[3]
        # NEW: Calculate final energy in GigaJoules (MJ / 1000)
        final_energy_gj_denominator = (final_results_raw[3] * HHV_chem[fuel_type]) / 1000 if final_chem_kg_denominator > 0 else 0
        
        # 4. Create the final data list, now including the "per unit" calculations
        data_with_all_columns = []
        for row in data_raw:
            current_cost = float(row[1])
            current_emission = float(row[3])
        
            cost_per_kg = current_cost / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0
            # NEW: Calculate "Cost per GJ"
            cost_per_gj = current_cost / final_energy_gj_denominator if final_energy_gj_denominator > 0 else 0
            
            emission_per_kg = current_emission / final_chem_kg_denominator if final_chem_kg_denominator > 0 else 0
            # NEW: Calculate "eCO2 per GJ"
            emission_per_gj = current_emission / final_energy_gj_denominator if final_energy_gj_denominator > 0 else 0
            
            # Append the new values in the correct order
            new_row_with_additions = list(row) + [cost_per_kg, cost_per_gj, emission_per_kg, emission_per_gj]
            data_with_all_columns.append(new_row_with_additions)
        
        # 5. Assign the fully processed data to the final variables
        data = data_with_all_columns
        total_results = final_results_raw # This already holds the correct total values

    # --- 7. Format Results for Frontend ---
        final_weight = total_results[3]
        chem_cost = total_results[0] / final_weight if final_weight > 0 else 0
        chem_energy = total_results[1] / final_weight if final_weight > 0 else 0
        chem_CO2e = total_results[2] / final_weight if final_weight > 0 else 0
        final_energy_output_mj = final_weight * HHV_chem[fuel_type]
        final_energy_output_gj = final_energy_output_mj / 1000

        # Define human-readable labels
        fuel_names = ['Liquid Hydrogen', 'Ammonia', 'Methanol']
        selected_fuel_name = fuel_names[fuel_type]

        # --- FIX IS HERE: Added the missing key for "site_A_chem_production" ---
        label_map = {
            "site_A_chem_production": "Initial Production (Placeholder)",
            "site_A_chem_liquification": f"Liquifaction in {start}",
            "chem_site_A_loading_to_truck": f"Loading {selected_fuel_name} on trucks",
            "site_A_to_port_A": f"Road transport: {start} to {start_port_name}",
            "port_A_unloading_to_storage": f"Unloading at {start_port_name}",
            "chem_storage_at_port_A": f"Storing {selected_fuel_name} at {start_port_name}",
            "chem_loading_to_ship": f"Loading {selected_fuel_name} on Ship",
            "port_to_port": f"Marine transport: {start_port_name} to {end_port_name}",
            "chem_unloading_from_ship": f"Unloading {selected_fuel_name} from Ship",
            "chem_storage_at_port_B": f"Storing {selected_fuel_name} at {end_port_name}",
            "port_B_unloading_from_storage": "Loading from Storage to Truck",
            "port_B_to_site_B": f"Road transport: {end_port_name} to {end}",
            "chem_site_B_unloading_from_truck": f"Unloading {selected_fuel_name} at {end}",
            "chem_storage_at_site_B": f"Storing {selected_fuel_name} at {end}",
            "chem_unloading_from_site_B": "Unloading for final use",
            "chem_convert_to_H2": "Cracking/Reforming to H2",
            "TOTAL": "TOTAL"
        }

        # Apply the new labels to the data
        relabeled_data = []
        for row in data:
            function_name = row[0]
            if function_name in label_map:
                new_row = row[:]
                new_row[0] = label_map[function_name]
                relabeled_data.append(new_row)
            else:
                relabeled_data.append(row[:])

        # Apply filtering correctly for table and charts
        # This filter will now work correctly because the placeholder is in the map.
        detailed_data_formatted = [row for row in relabeled_data if row[0] != label_map.get("site_A_chem_production")]

        # Filter for the charts (removes the placeholder AND the TOTAL row)
        data_for_display = [row for row in detailed_data_formatted if row[0] != "TOTAL"]

        # --- PREPARE CONTEXTUAL OVERLAY TEXT FOR CHARTS ---
        cost_overlay_text = ""
        if hydrogen_production_price > 0:
            ratio_cost = chem_cost / hydrogen_production_price
            cost_overlay_text = (
                f"Context:\n"
                f"• Production Cost in {start}: ${hydrogen_production_price:.2f}/kg*\n"
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
                f"• Gray Hydrogen (SMR) Emission: {SMR_EMISSIONS_KG_PER_KG_H2:.2f} kg CO₂e/kg\n"
                f"• Total Transport Emission: {chem_CO2e:.2f} kg CO₂e/kg\n"
                f"• Transport emission is {ratio_emission:.1f} times the SMR emission."
            )

        # --- DEFINE HEADERS, INDICES, AND PACKAGE FINAL RESPONSE ---
        new_detailed_headers = ["Process Step", "Cost ($)", "Energy (MJ)", "eCO2 (kg)", "Chem (kg)", "BOG (kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "eCO2/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
        csv_data = [new_detailed_headers] + detailed_data_formatted
        cost_per_kg_index = new_detailed_headers.index("Cost/kg ($/kg)")
        eco2_per_kg_index = new_detailed_headers.index("eCO2/kg (kg/kg)")

        cost_chart_base64 = create_breakdown_chart(
            data_for_display,
            cost_per_kg_index,
            'Cost Breakdown per kg of Delivered Fuel',
            'Cost ($/kg)',
            overlay_text=cost_overlay_text
        )
        emission_chart_base64 = create_breakdown_chart(
            data_for_display,
            eco2_per_kg_index,
            'CO2eq Breakdown per kg of Delivered Fuel',
            'CO2eq (kg/kg)',
            overlay_text=emission_overlay_text
        )

        summary1_data = [
            ["Cost ($/kg chemical)", f"{chem_cost:.2f}"],
            ["Consumed Energy (MJ/kg chemical)", f"{chem_energy:.2f}"],
            ["Emission (kg CO2/kg chemical)", f"{chem_CO2e:.2f}"]
        ]

        summary2_data = [
            ["Cost ($/GJ)", f"{total_results[0] / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Energy consumed (MJ_in/GJ_out)", f"{total_results[1] / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Emission (kg CO2/GJ)", f"{total_results[2] / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"]
        ]

        assumed_prices_data = [
            [f"Electricity Price at {start}*", f"{start_electricity_price[2]:.4f} $/MJ"],
            [f"Electricity Price at {end}*", f"{end_electricity_price[2]:.4f} $/MJ"],
            [f"Diesel Price at {start}", f"{diesel_price_start:.2f} $/gal"],
            [f"Diesel Price at {end_port_name}", f"{diesel_price_end:.2f} $/gal"],
            [f"Marine Fuel ({marine_fuel_choice}) Price at {start_port_name}*", f"{dynamic_price:.2f} $/ton"],
            [f"Green H2 Production Price at {start}*", f"{hydrogen_production_price:.2f} $/kg"],
        ]

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
            "csv_data": csv_data,
            "charts": {
                "cost_chart_base64": cost_chart_base64,
                "emission_chart_base64": emission_chart_base64
            }
        }
        return response
    
    elif commodity_type == 'food':
        # --- Unpack FOOD specific inputs ---
        food_type = inputs.get('food_type')

        # --- Define FOOD specific parameters ---
        food_params = {
            'strawberry': {
                'name': 'Strawberry', 'density_kg_per_m3': 450, 'target_temp_celsius': -18.0,
                'spoilage_rate_per_day': 0.0001, 'energy_content_mj_per_kg': 1.5,
                'specific_heat_fresh_mj_kgK': 0.0039, 'specific_heat_frozen_mj_kgK': 0.0018,
                'latent_heat_fusion_mj_kg': 0.300, 'cop_freezing_system': 2.5,
                'reefer_truck_fuel_consumption_L_hr': 1.5, 'reefer_container_power_kw': 3.5,
                'cargo_per_truck_kg': 20000
            }
        }
        current_food_params = food_params[food_type]

        # --- Define FOOD specific process functions ---
        def food_harvest_and_prep(A, args):
            return 0, 0, 0, A, 0

        def food_freezing_process(A, args):
            params, start_temp, elec_price, co2_factor = args
            energy_sensible_heat1 = A * params['specific_heat_fresh_mj_kgK'] * (start_temp - 0)
            energy_latent_heat = A * params['latent_heat_fusion_mj_kg']
            energy_sensible_heat2 = A * params['specific_heat_frozen_mj_kgK'] * (0 - params['target_temp_celsius'])
            total_heat_to_remove = energy_sensible_heat1 + energy_latent_heat + energy_sensible_heat2
            energy = total_heat_to_remove / params['cop_freezing_system']
            money = energy * elec_price[2]
            emissions = energy * 0.2778 * co2_factor * 0.001
            loss = 0.005 * A
            return money, energy, emissions, A - loss, loss

        def food_road_transport(A, args):
            params, distance, duration_mins, diesel_price, hh_diesel, dens_diesel, co2_diesel = args
            num_trucks = math.ceil(A / params['cargo_per_truck_kg'])
            truck_economy_km_per_L = 4.0
            diesel_for_propulsion_L = (distance / truck_economy_km_per_L) * num_trucks
            duration_hr = duration_mins / 60.0
            diesel_for_reefer_L = params['reefer_truck_fuel_consumption_L_hr'] * duration_hr * num_trucks
            total_diesel_L = diesel_for_propulsion_L + diesel_for_reefer_L
            energy = total_diesel_L * (hh_diesel / dens_diesel)
            money = total_diesel_L * diesel_price
            emissions = total_diesel_L * co2_diesel
            duration_days = duration_hr / 24.0
            loss = A * params['spoilage_rate_per_day'] * duration_days
            return money, energy, emissions, A - loss, loss

        def food_sea_transport(A, args):
            params, duration_hrs, selected_fuel, avg_ship_kw = args
            num_reefers = math.ceil(A / 20000)
            total_reefer_power_kw = num_reefers * params['reefer_container_power_kw']
            reefer_energy_kwh = total_reefer_power_kw * duration_hrs
            aux_sfoc_g_kwh = 200
            fuel_for_reefers_kg = (reefer_energy_kwh * aux_sfoc_g_kwh) / 1000.0
            propulsion_work_kwh = avg_ship_kw * duration_hrs
            main_engine_sfoc_g_kwh = selected_fuel['sfoc_g_per_kwh']
            fuel_for_propulsion_kg = (propulsion_work_kwh * main_engine_sfoc_g_kwh) / 1000.0
            total_fuel_consumed_kg = fuel_for_reefers_kg + fuel_for_propulsion_kg
            money = (total_fuel_consumed_kg / 1000.0) * selected_fuel['price_usd_per_ton']
            energy_mj = total_fuel_consumed_kg * selected_fuel['hhv_mj_per_kg']
            emissions = total_fuel_consumed_kg * selected_fuel['co2_emissions_factor_kg_per_kg_fuel']
            duration_days = duration_hrs / 24.0
            loss = A * params['spoilage_rate_per_day'] * duration_days
            return money, energy_mj, emissions, A - loss, loss

        def food_cold_storage(A, args):
            params, storage_days, elec_price, co2_factor = args
            volume_m3 = A / params['density_kg_per_m3']
            energy_kwh_per_day = 0.5 * volume_m3
            total_energy_kwh = energy_kwh_per_day * storage_days
            energy_mj = total_energy_kwh * 3.6
            money = energy_mj * elec_price[2]
            emissions = energy_mj * 0.2778 * co2_factor * 0.001
            loss = A * params['spoilage_rate_per_day'] * storage_days
            return money, energy_mj, emissions, A - loss, loss

        # --- Define main calculation loop for Food ---
        def total_food_lca(initial_weight, food_params):
            food_funcs_sequence = [
                (food_harvest_and_prep, "Harvesting & Preparation"),
                (food_freezing_process, f"Freezing in {start}"),
                (food_road_transport, f"Road Transport: {start} to {start_port_name}"),
                (food_cold_storage, f"Cold Storage at {start_port_name}"),
                (food_sea_transport, f"Marine Transport: {start_port_name} to {end_port_name}"),
                (food_cold_storage, f"Cold Storage at {end_port_name}"),
                (food_road_transport, f"Road Transport: {end_port_name} to {end}"),
                (food_cold_storage, f"Cold Storage at {end} (Destination)"),
            ]
            current_weight = initial_weight
            results_list = []
            for func, label in food_funcs_sequence:
                args_for_func = ()
                if func == food_freezing_process:
                    args_for_func = (food_params, start_local_temperature, start_electricity_price, CO2e_start)
                elif func == food_road_transport and "start" in label:
                    args_for_func = (food_params, distance_A_to_port, duration_A_to_port, diesel_price_start, HHV_diesel, diesel_density, CO2e_diesel)
                elif func == food_road_transport and "end" in label:
                    args_for_func = (food_params, distance_port_to_B, duration_port_to_B, diesel_price_end, HHV_diesel, diesel_density, CO2e_diesel)
                elif func == food_sea_transport:
                    args_for_func = (food_params, port_to_port_duration, selected_marine_fuel_params, avg_ship_power_kw)
                elif func == food_cold_storage and "start" in label:
                    args_for_func = (food_params, storage_time_A, start_port_electricity_price, CO2e_start)
                elif func == food_cold_storage and "end" in label:
                    args_for_func = (food_params, storage_time_B, end_port_electricity_price, CO2e_end)
                elif func == food_cold_storage and "Destination" in label:
                    args_for_func = (food_params, storage_time_C, end_electricity_price, CO2e_end)
                else:
                    args_for_func = (food_params,)
                money, energy, emissions, current_weight, loss = func(current_weight, args_for_func)
                results_list.append([label, money, energy, emissions, current_weight, loss])
            return results_list

        # --- Run the Food LCA and Format the Output ---
        num_containers = math.floor(total_ship_volume / 76)
        initial_food_weight_kg = num_containers * 20000
        data_raw = total_food_lca(initial_food_weight_kg, current_food_params)
        
        total_money = sum(row[1] for row in data_raw)
        total_energy = sum(row[2] for row in data_raw)
        total_emissions = sum(row[3] for row in data_raw)
        final_weight = data_raw[-1][4]
        data_raw.append(["TOTAL", total_money, total_energy, total_emissions, final_weight, sum(row[5] for row in data_raw)])

        final_commodity_kg = final_weight
        final_energy_output_mj = final_commodity_kg * current_food_params.get('energy_content_mj_per_kg', 1)
        final_energy_output_gj = final_energy_output_mj / 1000

        data_with_all_columns = []
        for row in data_raw:
            new_row = list(row) + [
                row[1] / final_commodity_kg if final_commodity_kg > 0 else 0, # cost/kg
                row[1] / final_energy_output_gj if final_energy_output_gj > 0 else 0, # cost/gj
                row[3] / final_commodity_kg if final_commodity_kg > 0 else 0, # emission/kg
                row[3] / final_energy_output_gj if final_energy_output_gj > 0 else 0, # emission/gj
            ]
            data_with_all_columns.append(new_row)
            
        detailed_data_formatted = data_with_all_columns
        data_for_display = [row for row in detailed_data_formatted if row[0] != "TOTAL"]
        new_detailed_headers = ["Process Step", "Cost ($)", "Energy (MJ)", "eCO2 (kg)", "Commodity (kg)", "Spoilage (kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "eCO2/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
        cost_per_kg_index = new_detailed_headers.index("Cost/kg ($/kg)")
        eco2_per_kg_index = new_detailed_headers.index("eCO2/kg (kg/kg)")
        
        cost_chart_base64 = create_breakdown_chart(data_for_display, cost_per_kg_index, f'Cost Breakdown per kg of Delivered {current_food_params["name"]}', 'Cost ($/kg)')
        emission_chart_base64 = create_breakdown_chart(data_for_display, eco2_per_kg_index, f'CO2eq Breakdown per kg of Delivered {current_food_params["name"]}', 'CO2eq (kg/kg)')
        
        summary1_data = [
            [f"Transport Cost ($/kg {current_food_params['name']})", f"{total_money / final_commodity_kg:.2f}" if final_commodity_kg > 0 else "N/A"],
            [f"Consumed Energy (MJ/kg {current_food_params['name']})", f"{total_energy / final_commodity_kg:.2f}" if final_commodity_kg > 0 else "N/A"],
            [f"Emission (kg CO2/kg {current_food_params['name']})", f"{total_emissions / final_commodity_kg:.2f}" if final_commodity_kg > 0 else "N/A"]
        ]
        summary2_data = [
            ["Cost ($/GJ)", f"{total_money / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Energy consumed (MJ_in/GJ_out)", f"{total_energy / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Emission (kg CO2/GJ)", f"{total_emissions / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"]
        ]
        assumed_prices_data = [
            [f"Electricity Price at {start}*", f"{start_electricity_price[2]:.4f} $/MJ"],
            [f"Electricity Price at {end}*", f"{end_electricity_price[2]:.4f} $/MJ"],
            [f"Diesel Price at {start}", f"{diesel_price_start:.2f} $/gal"],
            [f"Diesel Price at {end_port_name}", f"{diesel_price_end:.2f} $/gal"],
            [f"Marine Fuel ({marine_fuel_choice}) Price at {start_port_name}*", f"{dynamic_price:.2f} $/ton"],
        ]
        
        response = {
            "status": "success",
            "map_data": { "coor_start": {"lat": coor_start_lat, "lng": coor_start_lng}, "coor_end": {"lat": coor_end_lat, "lng": coor_end_lng}, "start_port": {"lat": start_port_lat, "lng": start_port_lng, "name": start_port_name}, "end_port": {"lat": end_port_lat, "lng": end_port_lng, "name": end_port_name}, "road_route_start_coords": road_route_start_coords, "road_route_end_coords": road_route_end_coords, "sea_route_coords": searoute_coor },
            "table_data": { "detailed_headers": new_detailed_headers, "detailed_data": detailed_data_formatted, "summary1_headers": ["Metric", "Value"], "summary1_data": summary1_data, "summary2_headers": ["Per Energy Output", "Value"], "summary2_data": summary2_data, "assumed_prices_headers": ["Assumed Price", "Value"], "assumed_prices_data": assumed_prices_data },
            "csv_data": [new_detailed_headers] + detailed_data_formatted,
            "charts": { "cost_chart_base64": cost_chart_base64, "emission_chart_base64": emission_chart_base64 }
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
