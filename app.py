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
def run_lca_model(inputs):
    """
    This single function encapsulates all logic for both Fuel and Food pathways.
    All helper functions, parameters, and process steps are defined and called
    within this function to ensure correct variable scoping.
    """
    # =================================================================
    # <<<                       HELPER FUNCTIONS                    >>>
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
            # Log the problematic string to understand why it failed
            print(f"DEBUG: Could not convert latitude '{lat_str}' or longitude '{lon_str}' to float.")
            return None, None, None # Return None for all if conversion fails for either

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

    def create_breakdown_chart(data, column_index, title, x_label, overlay_text=None):
        try:
            if not data:
                print("Chart creation skipped: No data provided.")
                return ""
            labels = [row[0] for row in data]
            values = []
            for row in data:
                try:
                    values.append(float(row[column_index]))
                except (ValueError, TypeError):
                    values.append(0.0)
                    print(f"Warning: Could not convert value '{row[column_index]}' to a number for chart '{title}'. Defaulting to 0.")
            plt.style.use('seaborn-v0_8-whitegrid')
            fig, ax = plt.subplots(figsize=(10, len(labels) * 0.5))
            
            y_pos = np.arange(len(labels))
            ax.barh(y_pos, values, align='center', color='#4CAF50', edgecolor='black')
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=12)
            ax.invert_yaxis()  # labels read top-to-bottom
            ax.set_xlabel(x_label, fontsize=14, weight='bold')
            ax.set_title(title, fontsize=16, weight='bold', pad=20)
            
            for i, v in enumerate(values):
                ax.text(v, i, f' {v:,.2f}', color='black', va='center', fontweight='bold')
                
            plt.tight_layout(pad=2.0)
            
            if overlay_text:
                fig.text(0.95, 0.15, overlay_text,
                        ha='right', va='bottom', size=10,
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.6))

            # --- Saving the plot to a memory buffer ---
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100) # Increased dpi for better quality
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig) # Explicitly close the figure to free up memory
            
            return img_base64

        # --- NEW: Catch any exception during chart creation ---
        except Exception as e:
            # Print a detailed error message to your backend logs
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"CRITICAL ERROR generating chart '{title}': {e}")
            import traceback
            traceback.print_exc()
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # Return an empty string so the frontend doesn't break
            return ""
    # =================================================================
    # <<<                   FUEL PROCESS FUNCTIONS                  >>>
    # =================================================================
    
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
        x = H2_plant_capacity*(1000/24) #convert TPD to kg/hr
        y0, x0, A1, A2, A3, t1, t2, t3 = 37.76586, -11.05773, 6248.66187, 80.56526, 25.95391, 2.71336, 32.3875, 685.33284
        return y0 + A1*np.exp(-(x-x0)/t1) + A2*np.exp(-(x-x0)/t2) + A3*np.exp(-(x-x0)/t3)

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
        opex_money = liquify_ener_consumed * start_electricity_price_tuple_arg[2] # Access the price float
        total_money = opex_money
        G_emission_from_energy = liquify_ener_consumed * 0.2778 * CO2e_start_arg * 0.001
        BOG_loss = 0.016 * A
        A_after_loss = A - BOG_loss
        G_emission_from_bog = BOG_loss * GWP_chem_list_arg[B_fuel_type] 
        G_emission = G_emission_from_energy + G_emission_from_bog
        return total_money, liquify_ener_consumed, G_emission, A_after_loss, BOG_loss
    
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
        fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg, \
        driver_daily_salary_start_arg, annual_working_days_arg = process_args_tuple # ADDED DRIVER SALARY ARGS

        # Original logic of the function, using the unpacked '_arg' variables
        number_of_trucks = math.ceil(A / chem_in_truck_weight_arg[B_fuel_type])
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

        trip_days = max(1, math.ceil(duration_A_to_port_arg / 1440)) # At least 1 day, round up
        driver_cost_per_truck = (driver_daily_salary_start_arg / annual_working_days_arg) * trip_days
        total_driver_cost = driver_cost_per_truck * number_of_trucks
        money += total_driver_cost # Add to total money

        return money, total_energy, G_emission, A_after_loss, net_BOG_loss

    def port_A_unloading_to_storage(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):

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
        
        opex_money = ener_consumed_refrig * start_electricity_price_tuple_arg[2]
        total_energy_consumed = ener_consumed_refrig # Initial total energy
        G_emission = total_energy_consumed * 0.2778 * CO2e_start_arg * 0.001 + current_BOG_loss * GWP_chem_list_arg[B_fuel_type]
        net_BOG_loss = current_BOG_loss # This will be updated if recirculation occurs

        # Recirculation logic
        # C_recirculation_BOG is user_define[2], E_storage_apply is user_define[4]
        if C_recirculation_BOG == 2: # If BOG recirculation is active
            if E_storage_apply == 1: # 1) Re-liquefy BOG
                usable_BOG = current_BOG_loss * BOG_recirculation_storage_percentage_arg * 0.01
                BOG_flowrate = usable_BOG / storage_time_A_arg * 1 / 24 # kg/hr
                
                reliq_ener_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
                reliq_ener_consumed = reliq_ener_required * usable_BOG
                total_energy_consumed += reliq_ener_consumed # Add energy for re-liquefaction
                opex_money = total_energy_consumed * start_electricity_price_tuple_arg[2] # Recalculate money
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
                opex_money = total_energy_consumed * start_electricity_price_tuple_arg[2] # Recalculate money
                
                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                # A_after_loss remains A - current_BOG_loss, as BOG is consumed
                
                G_emission = total_energy_consumed * 0.2778 * CO2e_start_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]
        total_money = opex_money
        return total_money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss
    
    def chem_loading_to_ship(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
        # Unpack all necessary arguments
        (V_flowrate_arg, number_of_cryo_pump_load_ship_port_A_arg, dBOR_dT_arg, 
        start_local_temperature_arg, BOR_loading_arg, liquid_chem_density_arg, head_pump_arg, 
        pump_power_factor_arg, EIM_cryo_pump_arg, ss_therm_cond_arg, pipe_length_arg, pipe_inner_D_arg, 
        pipe_thick_arg, boiling_point_chem_arg, EIM_refrig_eff_arg, start_electricity_price_tuple_arg, 
        CO2e_start_arg, GWP_chem_list_arg, calculated_storage_area_arg, ship_tank_metal_thick_arg, 
        ship_tank_insulation_thick_arg, ship_tank_metal_density_arg, ship_tank_insulation_density_arg, 
        ship_tank_metal_specific_heat_arg, ship_tank_insulation_specific_heat_arg, 
        COP_cooldown_arg, COP_refrig_arg, ship_number_of_tanks_arg, pipe_metal_specific_heat_arg) = process_args_tuple

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
                
        ener_consumed_cooldown_pipes = 0
        if B_fuel_type in [0, 1]: # Cooldown only for cryogenic fuels (LH2, NH3)
            # Calculate volume of pipe metal: (Outer Area - Inner Area) * Length
            pipe_outer_D = pipe_inner_D_arg + 2 * pipe_thick_arg
            pipe_metal_volume = (np.pi * (pipe_outer_D/2)**2 - np.pi * (pipe_inner_D_arg/2)**2) * pipe_length_arg
            
            # Assuming pipe_metal_density is similar to ship_tank_metal_density for stainless steel
            pipe_metal_density = ship_tank_metal_density # Using existing parameter for consistency
            
            mass_metal_pipes = pipe_metal_volume * pipe_metal_density
            
            # Delta T from ambient to boiling point of the chemical
            delta_T_pipes = (start_local_temperature_arg + 273.15) - boiling_point_chem_arg[B_fuel_type]

            Q_cooling_pipes = mass_metal_pipes * pipe_metal_specific_heat_arg * delta_T_pipes

            # Use the same cooldown COP as for tanks for simplicity
            cooldown_cop_pipes = COP_cooldown_arg[B_fuel_type]
            if cooldown_cop_pipes > 0:
                ener_consumed_cooldown_pipes = Q_cooling_pipes / cooldown_cop_pipes
                
        
        # --- Final Totals for this step ---
        ener_consumed = ener_consumed_pumping + ener_consumed_pipe_refrig + ener_consumed_cooldown + ener_consumed_cooldown_pipes
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
        
        opex_money = ener_consumed_refrig * end_electricity_price_tuple_arg[2]
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
                opex_money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                
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
                opex_money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                
                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                
                G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end
        total_money = opex_money
        return total_money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss

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
        fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg, \
        driver_daily_salary_end_arg, annual_working_days_arg = process_args_tuple # ADDED DRIVER SALARY ARGS

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

        # ADDITION: Calculate and add driver salary cost
        trip_days = max(1, math.ceil(duration_port_to_B_arg / 1440)) # At least 1 day, round up
        driver_cost_per_truck = (driver_daily_salary_end_arg / annual_working_days_arg) * trip_days
        total_driver_cost = driver_cost_per_truck * number_of_trucks
        money += total_driver_cost # Add to total money

        return money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss

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
        
        opex_money = ener_consumed_refrig * end_electricity_price_tuple_arg[2] # Using end_electricity_price
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
                opex_money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                
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
                opex_money = total_energy_consumed * end_electricity_price_tuple_arg[2] # Using end_electricity_price
                
                net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
                # A_after_loss remains A - current_BOG_loss, as BOG is consumed
                
                G_emission = total_energy_consumed * 0.2778 * CO2e_end_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type] # Using CO2e_end
        total_money = opex_money
        return total_money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss

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
        COP_refrig_opt, EIM_refrig_eff_opt, pipe_metal_specific_heat_opt, COP_cooldown_opt,
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
        tank_insulator_thickness_opt, BOG_recirculation_storage_opt,
        driver_daily_salary_start_opt, annual_working_days_opt # ADDED FOR OPTIMIZER
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
                    fuel_cell_eff_opt, EIM_fuel_cell_opt, LHV_chem_opt,
                    driver_daily_salary_start_opt, annual_working_days_opt # ADDED
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

            elif func_to_call.__name__ == "chem_loading_to_ship":
                process_args_for_current_func = (
                    V_flowrate_opt, number_of_cryo_pump_load_ship_port_A_opt, dBOR_dT_opt,
                    start_local_temperature_opt, BOR_loading_opt, liquid_chem_density_opt, head_pump_opt,
                    pump_power_factor_opt, EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt,
                    pipe_thick_opt, boiling_point_chem_opt, EIM_refrig_eff_opt, start_electricity_price_opt,
                    CO2e_start_opt, GWP_chem_opt, storage_area, ship_tank_metal_thickness, 
                    ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density, 
                    ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat, 
                    COP_cooldown, COP_refrig, ship_number_of_tanks, pipe_metal_specific_heat
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
    
    def calculate_liquefaction_capex(capacity_tpd, fuel_type):
        """
        Estimates the amortized capital cost per kg for liquefaction of hydrogen, ammonia, or methanol.
        Source: Based on industry data for hydrogen and ammonia liquefaction costs; methanol assumed zero.
        Parameters:
            capacity_tpd: Daily throughput in tons
            fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol
        Returns:
            Amortized CAPEX per kg in USD
        """
        # Cost models for different fuels
        cost_models = {
            0: {  # Hydrogen
                "small_scale": {"base_capex_M_usd": 138.6, "base_capacity": 27, "power_law_exp": 0.66},  # <100 TPD
                "large_scale": {"base_capex_M_usd": 762.67, "base_capacity": 800, "power_law_exp": 0.62}  # >100 TPD
            },
            1: {  # Ammonia
                "default": {"base_capex_M_usd": 36.67, "base_capacity": 100, "power_law_exp": 0.7}
            },
            2: {  # Methanol
                "default": {"base_capex_M_usd": 0, "base_capacity": 1, "power_law_exp": 0}  # No liquefaction
            }
        }
        
        # Select model based on fuel type
        if fuel_type not in cost_models:
            return 0
        
        if fuel_type == 0:  # Hydrogen
            model = cost_models[0]["large_scale"] if capacity_tpd > 100 else cost_models[0]["small_scale"]
        else:  # Ammonia or Methanol
            model = cost_models[fuel_type]["default"]
        
        # Calculate total capital cost using power law
        total_capex_usd = (model['base_capex_M_usd'] * 1000000) * (capacity_tpd / model['base_capacity']) ** model['power_law_exp']
        
        # Amortize over 20 years with 8% cost of capital
        annualized_capex = total_capex_usd * 0.09
        
        # Calculate annual throughput
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
            0: {  # Hydrogen
                "base_capex_M_usd": 35, "base_capacity": 335000, "power_law_exp": 0.7
            },
            1: {  # Ammonia
                "base_capex_M_usd": 15, "base_capacity": 6650000, "power_law_exp": 0.7
            },
            2: {  # Methanol
                "base_capex_M_usd": 0, "base_capacity": 1, "power_law_exp": 0
            }
        }
        
        if fuel_type not in cost_models:
            return 0
        
        model = cost_models[fuel_type]
        
        # Calculate total capital cost using power law
        total_capex_usd = (model['base_capex_M_usd'] * 1000000) * (A / model['base_capacity']) ** model['power_law_exp']
        
        # Amortize over 20 years with 8% cost of capital
        annualized_capex = total_capex_usd * 0.09
        
        # Calculate annual throughput
        if fuel_type in [0, 1]:  # Hydrogen or Ammonia
            if storage_days == 0:
                return 0
            cycles_per_year = 330 / storage_days
            annual_throughput_kg = A * cycles_per_year
        else:  # Methanol
            annual_throughput_kg = capacity_tpd * 1000 * 330
        
        if annual_throughput_kg == 0:
            return 0
            
        capex_per_kg = annualized_capex / annual_throughput_kg
        return capex_per_kg
        
    def calculate_loading_unloading_capex(fuel_type): # Removed A_shipment_kg from parameters
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

            return capex_per_kg_throughput # Now returns a rate   
        
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
                process_args_for_this_call_tc = (road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance_A_to_port, HHV_diesel, diesel_density, diesel_price_start, truck_tank_radius, truck_tank_length, truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness, insulator_thermal_conduct, OHTC_ship, start_local_temperature, COP_refrig, EIM_refrig_eff, duration_A_to_port, dBOR_dT, BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel, GWP_chem, BOG_recirculation_truck, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem, driver_daily_salary_start, annual_working_days)
            elif func_to_call.__name__ == "port_A_unloading_to_storage":
                process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_storage_port_A, dBOR_dT, start_local_temperature, BOR_unloading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem)
            elif func_to_call.__name__ == "chem_storage_at_port_A":
                process_args_for_this_call_tc = (liquid_chem_density, storage_volume, dBOR_dT, start_local_temperature, BOR_land_storage, storage_time_A, storage_radius, tank_metal_thickness, metal_thermal_conduct, tank_insulator_thickness, insulator_thermal_conduct, COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, BOG_recirculation_storage, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem)
            elif func_to_call.__name__ == "chem_loading_to_ship":
                process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_ship_port_A, dBOR_dT, start_local_temperature, BOR_loading, liquid_chem_density, head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick, boiling_point_chem, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem, storage_area, ship_tank_metal_thickness, ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density, ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat, COP_cooldown, COP_refrig, ship_number_of_tanks, pipe_metal_specific_heat)
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
                process_args_for_this_call_tc = (road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance_port_to_B, HHV_diesel, diesel_density, diesel_price_end, truck_tank_radius, truck_tank_length, truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness, insulator_thermal_conduct, OHTC_ship, end_local_temperature, COP_refrig, EIM_refrig_eff, duration_port_to_B, dBOR_dT, BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel, GWP_chem, BOG_recirculation_truck, LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem, driver_daily_salary_end, annual_working_days)
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

    # =================================================================
    # <<<                  FOOD PROCESSING FUNCTIONS                >>>
    # =================================================================
 
    def food_harvest_and_prep(A, args):
        return 0, 0, 0, A, 0

    def food_freezing_process(A, args):
        params, start_temp, elec_price, co2_factor = args
        energy_sensible_heat1 = A * params['specific_heat_fresh_mj_kgK'] * (start_temp - 0)
        energy_latent_heat = A * params['latent_heat_fusion_mj_kg']
        energy_sensible_heat2 = A * params['specific_heat_frozen_mj_kgK'] * (0 - params['target_temp_celsius'])
        total_heat_to_remove = energy_sensible_heat1 + energy_latent_heat + energy_sensible_heat2
        energy = total_heat_to_remove / params['cop_freezing_system']
        opex_money = energy * elec_price[2]
        capex_money = 0
        if include_overheads:
            capex_per_kg = calculate_food_infra_capex("freezing", facility_capacity, A,0)
            capex_money = A * capex_per_kg
        emissions = energy * 0.2778 * co2_factor * 0.001
        loss = 0.005 * A
        total_money = opex_money + capex_money
        return total_money, energy, emissions, A - loss, loss

    def food_road_transport(A, args):
        params, distance, duration_mins, diesel_price, hh_diesel, dens_diesel, co2_diesel, ambient_temp, driver_daily_salary_arg, annual_working_days_arg = args # ADDED DRIVER SALARY ARGS
        base_spoilage_rate = params['general_params']['spoilage_rate_per_day']

        # Increase spoilage rate by 20% for every 5 degrees above the ideal temp
        temp_sensitivity_factor = 1 + (0.20 * ((ambient_temp - params['general_params']['target_temp_celsius']) / 5))
        if temp_sensitivity_factor < 1:
            temp_sensitivity_factor = 1 # Spoilage doesn't slow down below target
        dynamic_spoilage_rate = base_spoilage_rate * temp_sensitivity_factor
        LITERS_PER_GALLON = 3.78541
        num_trucks = math.ceil(A / params['general_params']['cargo_per_truck_kg'])
        truck_economy_km_per_L = 4.0
        diesel_for_propulsion_L = (distance / truck_economy_km_per_L) * num_trucks
        duration_hr = duration_mins / 60.0
        diesel_for_reefer_L = params['general_params']['reefer_truck_fuel_consumption_L_hr'] * duration_hr * num_trucks
        total_diesel_L = diesel_for_propulsion_L + diesel_for_reefer_L
        total_diesel_gal = total_diesel_L / LITERS_PER_GALLON
        money = total_diesel_gal * diesel_price
        energy = total_diesel_gal * dens_diesel * hh_diesel
        emissions = total_diesel_gal * co2_diesel
        duration_days = duration_hr / 24.0
        loss = A * dynamic_spoilage_rate * duration_days

        # ADDITION: Calculate and add driver salary cost
        trip_days = max(1, math.ceil(duration_mins / 1440)) # At least 1 day, round up
        driver_cost_per_truck = (driver_daily_salary_arg / annual_working_days_arg) * trip_days
        total_driver_cost = driver_cost_per_truck * num_trucks
        money += total_driver_cost # Add to total money

        return money, energy, emissions, A - loss, loss

    def food_precooling_process(A, args):
        """
        Calculates the cost and energy for pre-cooling produce (e.g., forced-air cooling)
        to remove initial field heat before storage or transport.
        """
        # 1. Unpack the arguments passed from the orchestrator
        # A is the initial weight of the food (in kg)
        precool_params, elec_price, co2_factor = args

        # 2. Calculate the total heat that needs to be removed (in MJ)
        # This is based on the formula: Q = m * c * ΔT
        delta_T = (precool_params['initial_field_heat_celsius'] - 
                precool_params['target_precool_temperature_celsius'])

        # Ensure delta_T is not negative; if it is, no cooling is needed.
        if delta_T <= 0:
            return 0, 0, 0, A, 0

        # Q (heat to remove) = mass * specific heat * change in temperature
        heat_to_remove_mj = A * precool_params['specific_heat_fresh_mj_kgK'] * delta_T

        # 3. Calculate the actual energy consumed by the cooling system
        # Energy = Heat Removed / Coefficient of Performance (COP) of the system
        energy_mj = heat_to_remove_mj / precool_params['cop_precooling_system']

        # 4. Calculate the financial cost and CO2 emissions
        opex_money = energy_mj * elec_price[2] # elec_price[2] is the price per MJ
        capex_money = 0
        if include_overheads:
            capex_per_kg = calculate_food_infra_capex("precool", facility_capacity, A,0)
            capex_money = A * capex_per_kg        
        total_money = opex_money + capex_money
        # Convert MJ to kWh for emission calculation (1 MJ ≈ 0.2778 kWh)
        emissions = energy_mj * 0.2778 * co2_factor * 0.001

        # 5. Calculate weight loss due to moisture evaporation during forced-air cooling
        loss = A * precool_params['moisture_loss_percent']

        # 6. Return the standard tuple of results
        return total_money, energy_mj, emissions, A - loss, loss
    
    def calculate_ca_energy_kwh(A, food_params, duration_hrs):
        """
        Calculates the energy consumption of a Controlled Atmosphere system
        based on physics and biological properties.
        """
        if not food_params.get('process_flags', {}).get('needs_controlled_atmosphere', False):
            return 0 # No CA needed for this fruit

        ca_p = food_params['ca_params']
        gen_p = food_params['general_params']
        
        num_containers = math.ceil(A / gen_p['cargo_per_truck_kg'])
        container_volume_m3 = 76 # Approx. volume of a 40ft container

        # 1. Energy for Nitrogen Generation (to counter leakage)
        # Total volume of air that leaks in and must be displaced by N2
        leaked_air_m3 = num_containers * container_volume_m3 * ca_p['container_leakage_rate_ach'] * duration_hrs
        energy_n2_kwh = leaked_air_m3 * ca_p['n2_generator_efficiency_kwh_per_m3']

        # 2. Energy for CO2 Scrubbing (to counter respiration)
        # Convert mL CO2 -> L -> m3 -> kg
        co2_density_kg_per_m3 = 1.98
        total_co2_produced_kg = (A * ca_p['respiration_rate_ml_co2_per_kg_hr'] * duration_hrs) / 1000000 * co2_density_kg_per_m3
        energy_co2_scrub_kwh = total_co2_produced_kg * ca_p['co2_scrubber_efficiency_kwh_per_kg_co2']

        # 3. Energy for Humidification (simplified)
        # Assume we need to add ~2 liters of water per container per day to maintain humidity
        water_to_add_liters = num_containers * 2.0 * (duration_hrs / 24.0)
        energy_humidity_kwh = water_to_add_liters * ca_p['humidifier_efficiency_kwh_per_liter']

        # 4. Energy for Baseline Controls
        energy_base_kwh = num_containers * ca_p['base_control_power_kw'] * duration_hrs
        
        total_ca_energy_kwh = energy_n2_kwh + energy_co2_scrub_kwh + energy_humidity_kwh + energy_base_kwh
        
        return total_ca_energy_kwh

    def food_sea_transport(A, args):
        """
        Calculates energy for the sea voyage, with DECOUPLED calculations for
        propulsion and auxiliary engine fuel consumption.
        """
        # Unpack arguments
        food_params, duration_hrs, selected_fuel, avg_ship_kw = args
        
        # --- 1. Calculate Fuel Mass for Each System ---

        # A) Auxiliary Fuel for Reefers and CA Systems
        total_auxiliary_energy_kwh = calculate_ca_energy_kwh(A, food_params, duration_hrs)
        reefer_power_kw = math.ceil(A / food_params['general_params']['cargo_per_truck_kg']) * food_params['general_params']['reefer_container_power_kw']
        total_auxiliary_energy_kwh += reefer_power_kw * duration_hrs
        
        aux_sfoc_g_kwh = 200 # g/kWh for auxiliary engines
        fuel_for_auxiliary_kg = (total_auxiliary_energy_kwh * aux_sfoc_g_kwh) / 1000.0

        # B) Propulsion Fuel for Main Engine
        propulsion_work_kwh = avg_ship_kw * duration_hrs
        fuel_for_propulsion_kg = (propulsion_work_kwh * selected_fuel['sfoc_g_per_kwh']) / 1000.0
        
        # --- 2. Calculate Cost, Energy, and Emissions for Each Fuel SEPARATELY ---

        # A) For Auxiliary Fuel (MGO)
        money_aux = (fuel_for_auxiliary_kg / 1000.0) * auxiliary_fuel_params['price_usd_per_ton']
        energy_aux_mj = fuel_for_auxiliary_kg * auxiliary_fuel_params['hhv_mj_per_kg']
        emissions_aux = fuel_for_auxiliary_kg * auxiliary_fuel_params['co2_emissions_factor_kg_per_kg_fuel']

        # B) For Propulsion Fuel (User's Choice)
        money_prop = (fuel_for_propulsion_kg / 1000.0) * selected_fuel['price_usd_per_ton']
        energy_prop_mj = fuel_for_propulsion_kg * selected_fuel['hhv_mj_per_kg']
        emissions_prop = fuel_for_propulsion_kg * selected_fuel['co2_emissions_factor_kg_per_kg_fuel']
        # Note: We can add separate N2O/Methane slip emissions here if needed for propulsion fuel

        # --- 3. Sum the Results for the Final Totals ---
        total_money = money_aux + money_prop
        total_energy_mj = energy_aux_mj + energy_prop_mj
        total_emissions = emissions_aux + emissions_prop
        
        # Spoilage calculation remains the same
        duration_days = duration_hrs / 24.0
        spoilage_rate = food_params['general_params']['spoilage_rate_per_day'] # Default rate
        if food_params['process_flags'].get('needs_controlled_atmosphere'):
            # If CA is active, use the lower spoilage rate
            spoilage_rate = food_params['general_params']['spoilage_rate_ca_per_day']
        loss = A * spoilage_rate * duration_days
        return total_money, total_energy_mj, total_emissions, A - loss, loss
    
    def food_cold_storage(A, args):
        params, storage_days, elec_price, co2_factor, ambient_temp = args
        
        # The 'params' dictionary now has a nested 'general_params' key
        volume_m3 = A / params['general_params']['density_kg_per_m3']
        
        # The rest of the dynamic calculation uses the 'ambient_temp' passed into the function
        base_energy_factor_kwh_m3_day = 0.5
        temp_adjustment_factor = 1 + (0.03 * (ambient_temp - 20))
        if temp_adjustment_factor < 0.5: 
            temp_adjustment_factor = 0.5 # Set a floor
            
        dynamic_energy_factor = base_energy_factor_kwh_m3_day * temp_adjustment_factor
        energy_kwh_per_day = dynamic_energy_factor * volume_m3
        total_energy_kwh = energy_kwh_per_day * storage_days
        
        energy_mj = total_energy_kwh * 3.6
        opex_money = energy_mj * elec_price[2]
        capex_money = 0
        if include_overheads:
            capex_per_kg = calculate_food_infra_capex("cold_storage", facility_capacity, A, storage_days)
            capex_money = A * capex_per_kg
        total_money = opex_money + capex_money
        emissions = energy_mj * 0.2778 * co2_factor * 0.001
        # Spoilage calculation becomes dynamic
        spoilage_rate = params['general_params']['spoilage_rate_per_day'] # Default rate
        if params['process_flags'].get('needs_controlled_atmosphere'):
            # If CA is active, use the lower spoilage rate
            spoilage_rate = params['general_params']['spoilage_rate_ca_per_day']
            
        loss = A * spoilage_rate * storage_days        
        
        return total_money, energy_mj, emissions, A - loss, loss

# REPLACE your old total_food_lca function with this one

    def total_food_lca(initial_weight, food_params):
        # Start with a base list of processes that always happen
        food_funcs_sequence = [
            (food_harvest_and_prep, "Harvesting & Preparation"),
        ]
    
        # Dynamically add steps based on the food's flags
        flags = food_params['process_flags']
        if flags.get('needs_precooling', False):
            food_funcs_sequence.append((food_precooling_process, f"Pre-cooling in {start}"))
    
        if flags.get('needs_freezing', False):
            food_funcs_sequence.append((food_freezing_process, f"Freezing in {start}"))
    
        # Add the universal transport and storage steps
        food_funcs_sequence.extend([
            (food_road_transport, f"Road Transport: {start} to {start_port_name}"),
            (food_cold_storage, f"Cold Storage at {start_port_name}"),
            (food_sea_transport, f"Marine Transport: {start_port_name} to {end_port_name}")
        ])
    
        # Add the remaining universal steps
        food_funcs_sequence.extend([
            (food_cold_storage, f"Cold Storage at {end_port_name}"),
            (food_road_transport, f"Road Transport: {end_port_name} to {end}"),
            (food_cold_storage, f"Cold Storage at {end} (Destination)"),
        ])
    
        current_weight = initial_weight
        results_list = []
        for func, label in food_funcs_sequence:
            args_for_func = ()
            if func == food_precooling_process:
                precooling_full_params = {**food_params['precooling_params'], **food_params['general_params']}
                args_for_func = (precooling_full_params, start_electricity_price, CO2e_start)
            elif func == food_freezing_process:
                freezing_full_params = {**food_params.get('freezing_params', {}), **food_params['general_params']}
                args_for_func = (freezing_full_params, start_local_temperature, start_electricity_price, CO2e_start)
            elif func == food_road_transport and start_port_name in label:
                # This is the first leg: from start city TO start port
                args_for_func = (food_params, distance_A_to_port, duration_A_to_port, diesel_price_start, HHV_diesel, diesel_density, CO2e_diesel, start_local_temperature, driver_daily_salary_start, annual_working_days)
            elif func == food_road_transport and end_port_name in label:
                # This is the second leg: from end port TO end city
                args_for_func = (food_params, distance_port_to_B, duration_port_to_B, diesel_price_end, HHV_diesel, diesel_density, CO2e_diesel, end_local_temperature, driver_daily_salary_end, annual_working_days)
            elif func == food_sea_transport:
                args_for_func = (food_params, port_to_port_duration, selected_marine_fuel_params, avg_ship_power_kw)
            elif func == food_cold_storage and "at " + start_port_name in label:
                args_for_func = (food_params, storage_time_A, start_port_electricity_price, CO2e_start, start_local_temperature)
            elif func == food_cold_storage and "at " + end_port_name in label:
                args_for_func = (food_params, storage_time_B, end_port_electricity_price, CO2e_end, end_local_temperature)
            elif func == food_cold_storage and "Destination" in label:
                args_for_func = (food_params, storage_time_C, end_electricity_price, CO2e_end, end_local_temperature)
            elif func == food_harvest_and_prep:
                args_for_func = () 
            else:
                args_for_func = (food_params,)
    
            money, energy, emissions, current_weight, loss = func(current_weight, args_for_func)
            results_list.append([label, money, energy, emissions, current_weight, loss])
            
        return results_list
    
    def openai_get_food_price(food_name, location_name):
        """
        Uses an AI model to find, parse, and convert the retail price of a
        food item to USD per kg for a given location.
        """
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        
        # Improved prompt to handle broader locations
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
                temperature=0, # Set to 0 for more deterministic, factual responses
                messages=prompt_messages
            )
            result = json.loads(response.choices[0].message.content)
            price = result.get("price_usd_per_kg")
            
            # Ensure the price is a valid number, return None otherwise
            if isinstance(price, (int, float)):
                return price
            else:
                return None
                
        except Exception as e:
            print(f"AI price lookup failed: {e}")
            return None
        
    def openai_get_nearest_farm_region(food_name, location_name):
        """
        Uses an AI model to find a major commercial farming region for a food item
        nearest to a given destination.
        """
        from openai import OpenAI
        client = OpenAI(api_key=api_key_openAI)
        
        # This prompt guides the AI to provide a realistic, commercially viable origin
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
            
            # Ensure all keys exist and are valid before returning
            if all(k in result for k in ['farm_region_name', 'latitude', 'longitude']) and isinstance(result['latitude'], (int, float)):
                return result
            else:
                return None
                
        except Exception as e:
            print(f"AI farm region lookup failed: {e}")
            return None

    def detect_canal_transit(route_object):
        """
        Inspects the route's geographic coordinates to detect major canal transits.
        This is more reliable than checking text-based properties.
        Returns a dictionary with flags for each major canal.
        """
        transits = {
            "suez": False,
            "panama": False
        }

        # Define the geographic bounding boxes for the canals.
        # Format is (min_longitude, min_latitude, max_longitude, max_latitude)
        PANAMA_CANAL_BBOX = (-80.5, 8.5, -78.5, 9.5)
        SUEZ_CANAL_BBOX = (32.0, 29.5, 33.0, 31.5)

        try:
            # The coordinates from searoute are in [longitude, latitude] format.
            route_coords = route_object.geometry['coordinates']
            
            for lon, lat in route_coords:
                # Check for Panama Canal transit
                if (PANAMA_CANAL_BBOX[0] <= lon <= PANAMA_CANAL_BBOX[2] and
                    PANAMA_CANAL_BBOX[1] <= lat <= PANAMA_CANAL_BBOX[3]):
                    transits["panama"] = True
                    break  # Exit the loop once a transit is confirmed

                # Check for Suez Canal transit
                if (SUEZ_CANAL_BBOX[0] <= lon <= SUEZ_CANAL_BBOX[2] and
                    SUEZ_CANAL_BBOX[1] <= lat <= SUEZ_CANAL_BBOX[3]):
                    transits["suez"] = True
                    break # Exit the loop once a transit is confirmed

            # If we finished the loop and found a transit, we don't need to do the old check.
            if transits["panama"] or transits["suez"]:
                return transits
                
            # Fallback to the old method just in case, though less likely to be needed.
            # This part can be removed if you trust the geographic check completely.
            route_info_string = json.dumps(route_object.properties).lower()
            if "suez" in route_info_string:
                transits["suez"] = True
            if "panama" in route_info_string:
                transits["panama"] = True
                
        except Exception as e:
            print(f"Could not parse route properties for canal detection: {e}")
        
        return transits                

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
    
    def calculate_single_reefer_service_cost(duration_hrs, food_params):

        # Calculate energy needed for the reefer unit + CA system for one container
        # Dummy mass of 1kg is used because the CA energy function scales by container, not mass
        ca_energy_kwh_per_container = calculate_ca_energy_kwh(1, food_params, duration_hrs)
        reefer_energy_kwh_per_container = food_params['general_params']['reefer_container_power_kw'] * duration_hrs
        
        total_energy_kwh = ca_energy_kwh_per_container + reefer_energy_kwh_per_container
        
        # Calculate fuel burned by auxiliary engine to provide this electricity
        aux_sfoc_g_kwh = 200 # g/kWh for auxiliary engines
        fuel_kg = (total_energy_kwh * aux_sfoc_g_kwh) / 1000.0
        
        # Calculate cost, energy, and emissions from that fuel
        cost = (fuel_kg / 1000.0) * auxiliary_fuel_params['price_usd_per_ton']
        energy_mj = fuel_kg * auxiliary_fuel_params['hhv_mj_per_kg']
        emissions = fuel_kg * auxiliary_fuel_params['co2_emissions_factor_kg_per_kg_fuel']
        
        return cost, energy_mj, emissions

    def calculate_food_infra_capex(process_name, capacity_tons_per_day, A, storage_days):
        """
        Estimates the amortized capital cost per kg for food processing facilities.
        Source: Based on general industry capital cost estimates for food processing and cold chain logistics.
        Parameters:
            process_name: Type of facility (e.g., 'cold_storage')
            capacity_tons_per_day: Daily throughput in tons (used for precool/freezing)
            A: Total mass held in kg (used for cold storage)
            storage_days: Average storage duration in days
        """
        cost_models = {
            "precool": {"base_cost_M_usd": 1.5, "power_law_exp": 0.6, "reference_capacity": 50},
            "freezing": {"base_cost_M_usd": 3, "power_law_exp": 0.65, "reference_capacity": 30},
            "cold_storage": {"base_cost_M_usd": 0.82, "power_law_exp": 0.7, "reference_capacity": 5000000}  # 5,000 tons = 5M kg
        }
        
        model = cost_models.get(process_name)
        if not model:
            return 0

        # Calculate total capital cost using a power law
        if process_name == "cold_storage":
            total_capex_usd = (model['base_cost_M_usd'] * 1000000) * (A / model['reference_capacity']) ** model['power_law_exp']
        else:
            total_capex_usd = (model['base_cost_M_usd'] * 1000000) * (capacity_tons_per_day / model['reference_capacity']) ** model['power_law_exp']
        
        # Amortize over 20 years with 8% cost of capital
        annualized_capex = total_capex_usd * 0.1 
        
        # Calculate capex_per_kg
        if process_name == "cold_storage":
            if storage_days == 0:
                return 0  # Facility not used
            cycles_per_year = 330 / storage_days  # Number of storage cycles per year
            annual_throughput_kg = A * cycles_per_year  # Total kg processed annually
        else:
            annual_throughput_kg = capacity_tons_per_day * 1000 * 330  # Throughput for precool/freezing
        
        if annual_throughput_kg == 0:
            return 0
            
        capex_per_kg = annualized_capex / annual_throughput_kg
        return capex_per_kg

    # =================================================================
    # <<< MAIN CONDITIONAL BRANCH STARTS HERE >>>
    # =================================================================

    # --- 1. Unpack user inputs from the frontend ---
    start = inputs['start']
    end = inputs['end']
    commodity_type = inputs.get('commodity_type', 'fuel')
    marine_fuel_choice = inputs.get('marine_fuel_choice', 'VLSFO')
    include_overheads = inputs.get('include_overheads', True)
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
    port_to_port_duration = float(port_to_port_dis) / (16 * 1.852) # Avg ship speed 16 knots

    CO2e_start = carbon_intensity(coor_start_lat, coor_start_lng)
    CO2e_end = carbon_intensity(coor_end_lat, coor_end_lng)

    start_electricity_price = openai_get_electricity_price(f"{coor_start_lat},{coor_start_lng}")
    end_electricity_price = openai_get_electricity_price(f"{coor_end_lat},{coor_end_lng}")
    start_port_electricity_price = openai_get_electricity_price(f"{start_port_lat},{start_port_lng}")
    end_port_electricity_price = openai_get_electricity_price(f"{end_port_lat},{end_port_lng}")

    road_route_start_coords = extract_route_coor((coor_start_lat, coor_start_lng), (start_port_lat, start_port_lng))
    road_route_end_coords = extract_route_coor((end_port_lat, end_port_lng), (coor_end_lat, end_port_lng))
    diesel_price_country = {
        "Venezuela": 0.016,
        "Iran": 0.022,
        "Libya": 0.104,
        "Algeria": 0.834,
        "Turkmenistan": 1.082,
        "Egypt": 1.181,
        "Angola": 1.238,
        "Kuwait": 1.419,
        "Saudi Arabia": 1.675,
        "Ecuador": 1.798,
        "Bahrain": 1.807,
        "Qatar": 2.027,
        "Bolivia": 2.038,
        "Kazakhstan": 2.145,
        "Nigeria": 2.222,
        "Azerbaijan": 2.227,
        "Syria": 2.389,
        "Trinidad and Tobago": 2.46,
        "Trinidad & Tobago": 2.46,
        "Malaysia": 2.47,
        "Sudan": 2.482,
        "United Arab Emirates": 2.525,
        "UAE": 2.525,
        "Oman": 2.54,
        "Vietnam": 2.553,
        "Colombia": 2.553,
        "Bhutan": 2.58,
        "Lebanon": 2.673,
        "Tunisia": 2.797,
        "Myanmar": 2.907,
        "Burma": 2.907,
        "Panama": 2.917,
        "Puerto Rico": 2.949,
        "Belarus": 3.006,
        "Guyana": 3.044,
        "Honduras": 3.059,
        "Indonesia": 3.07,
        "Afghanistan": 3.101,
        "Taiwan": 3.128,
        "Bangladesh": 3.158,
        "Laos": 3.185,
        "Kyrgyzstan": 3.189,
        "Ethiopia": 3.228,
        "Paraguay": 3.278,
        "El Salvador": 3.3,
        "Cambodia": 3.304,
        "Curacao": 3.379,
        "Russia": 3.404,
        "Pakistan": 3.405,
        "Maldives": 3.408,
        "Guatemala": 3.412,
        "China": 3.442,
        "United States": 3.452,
        "USA": 3.452,
        "Jordan": 3.47,
        "Philippines": 3.502,
        "Zambia": 3.54,
        "Liberia": 3.546,
        "Uzbekistan": 3.59,
        "Peru": 3.648,
        "Fiji": 3.677,
        "Thailand": 3.703,
        "Dominican Republic": 3.751,
        "Dom. Rep.": 3.751,
        "Gabon": 3.78,
        "Chile": 3.839,
        "Congo, Dem. Rep.": 3.882,
        "DR Congo": 3.882,
        "Georgia": 3.91,
        "Canada": 3.934,
        "Nepal": 3.947,
        "Aruba": 3.951,
        "Brazil": 3.977,
        "Grenada": 3.978,
        "Australia": 3.988,
        "India": 3.998,
        "Cape Verde": 4.032,
        "Tanzania": 4.036,
        "Costa Rica": 4.051,
        "Moldova": 4.071,
        "Sri Lanka": 4.108,
        "Japan": 4.143,
        "Cuba": 4.147,
        "Lesotho": 4.194,
        "Botswana": 4.212,
        "Mongolia": 4.229,
        "Argentina": 4.24,
        "Madagascar": 4.246,
        "Uruguay": 4.268,
        "New Zealand": 4.271,
        "South Korea": 4.31,
        "Suriname": 4.315,
        "Namibia": 4.357,
        "Jamaica": 4.389,
        "Rwanda": 4.404,
        "Burkina Faso": 4.438,
        "Nicaragua": 4.444,
        "Turkey": 4.462,
        "South Africa": 4.473,
        "Eswatini": 4.523,
        "Swaziland": 4.523,
        "North Macedonia": 4.548,
        "N. Maced.": 4.548,
        "Togo": 4.569,
        "Dominica": 4.58,
        "Ivory Coast": 4.602,
        "Côte d'Ivoire": 4.602,
        "Morocco": 4.633,
        "Haiti": 4.734,
        "Benin": 4.734,
        "Mali": 4.767,
        "Uganda": 4.788,
        "Kenya": 4.793,
        "Ghana": 4.801,
        "Armenia": 4.832,
        "Bahamas": 4.869,
        "Mauritius": 4.912,
        "Bosnia and Herzegovina": 4.917,
        "Bosnia-Herzegovina": 4.917,
        "Ukraine": 4.94,
        "Senegal": 4.964,
        "Burundi": 4.989,
        "Cayman Islands": 5.023,
        "Mexico": 5.056,
        "Saint Lucia": 5.084,
        "Seychelles": 5.094,
        "Andorra": 5.105,
        "Mozambique": 5.141,
        "Malta": 5.208,
        "Guinea": 5.239,
        "Sierra Leone": 5.271,
        "Bulgaria": 5.328,
        "Cameroon": 5.444,
        "Montenegro": 5.509,
        "Belize": 5.606,
        "Czech Republic": 5.631,
        "Zimbabwe": 5.754,
        "Poland": 5.789,
        "Spain": 5.817,
        "Luxembourg": 5.871,
        "Estonia": 5.914,
        "Malawi": 5.966,
        "Mayotte": 5.983,
        "Cyprus": 6.0,
        "Slovakia": 6.039,
        "Romania": 6.058,
        "Lithuania": 6.09,
        "Croatia": 6.142,
        "Latvia": 6.159,
        "Slovenia": 6.168,
        "Hungary": 6.195,
        "Sweden": 6.266,
        "Austria": 6.314,
        "San Marino": 6.318,
        "Greece": 6.344,
        "Barbados": 6.374,
        "Portugal": 6.512,
        "Germany": 6.615,
        "Monaco": 6.624,
        "France": 6.655,
        "Belgium": 6.787,
        "Serbia": 6.866,
        "Italy": 6.892,
        "Netherlands": 6.912,
        "Finland": 7.011,
        "Norway": 7.026,
        "United Kingdom": 7.067,
        "UK": 7.067,
        "Ireland": 7.114,
        "Wallis and Futuna": 7.114,
        "Singapore": 7.195,
        "Israel": 7.538,
        "Albania": 7.597,
        "Denmark": 7.649,
        "Switzerland": 8.213,
        "Central African Republic": 8.218,
        "C. Afr. Rep.": 8.218,
        "Liechtenstein": 8.36,
        "Iceland": 9.437,
        "Hong Kong": 12.666
    }
    diesel_price_start = get_diesel_price(coor_start_lat, coor_start_lng, diesel_price_country)
    diesel_price_end = get_diesel_price(end_port_lat, end_port_lng, diesel_price_country)

    truck_driver_annual_salaries = {
        "Afghanistan": 3535.00,
        "Albania": 9366.00,
        "Algeria": 9366.00,
        "Andorra": 49000.00,
        "Angola": 9366.00,
        "Antigua and Barbuda": 14895.00,
        "Argentina": 7466.00,
        "Armenia": 8022.00,
        "Australia": 67568.00,
        "Austria": 52886.00,
        "Azerbaijan": 8022.00,
        "Bahamas": 35452.00,
        "Bahrain": 27627.00,
        "Bangladesh": 3535.00,
        "Barbados": 14895.00,
        "Belarus": 5040.00,
        "Belgium": 55097.00,
        "Belize": 10243.00,
        "Benin": 9366.00,
        "Bhutan": 3535.00,
        "Bolivia": 10243.00,
        "Bosnia and Herzegovina": 12812.00,
        "Bosnia-Herzegovina": 12812.00,
        "Botswana": 9366.00,
        "Brazil": 10875.00,
        "Trinidad and Tobago": 12800.00,
        "Trinidad & Tobago": 12800.00,
        "Brunei": 40149.00,
        "Bulgaria": 14901.00,
        "Burkina Faso": 9366.00,
        "Burundi": 3535.00,
        "Cambodia": 4652.00,
        "Cameroon": 9366.00,
        "Canada": 46276.00,
        "Cape Verde": 9366.00,
        "Central African Republic": 9366.00,
        "C. Afr. Rep.": 9366.00,
        "Chad": 9366.00,
        "Chile": 14675.00,
        "China": 16881.00,
        "Colombia": 10494.00,
        "Comoros": 9366.00,
        "Congo, Dem. Rep.": 9366.00,
        "DR Congo": 9366.00,
        "Congo, Rep.": 9366.00,
        "Costa Rica": 18581.00,
        "Croatia": 19858.00,
        "Cuba": 10243.00,
        "Cyprus": 27225.00,
        "Czech Republic": 22545.00,
        "Denmark": 64323.00,
        "Djibouti": 9366.00,
        "Dominica": 14895.00,
        "Dominican Republic": 6623.00,
        "Dom. Rep.": 6623.00,
        "Ecuador": 13737.00,
        "Egypt": 3363.00,
        "El Salvador": 10243.00,
        "Equatorial Guinea": 9366.00,
        "Eritrea": 9366.00,
        "Estonia": 20789.00,
        "Eswatini": 9366.00,
        "Swaziland": 9366.00,
        "Ethiopia": 9366.00,
        "Fiji": 10243.00,
        "Finland": 52822.00,
        "France": 39047.00,
        "Gabon": 9366.00,
        "Gambia": 9366.00,
        "Georgia": 8022.00,
        "Germany": 49000.00,
        "Ghana": 9366.00,
        "Greece": 27225.00,
        "Grenada": 14895.00,
        "Guatemala": 11533.00,
        "Guinea": 9366.00,
        "Guinea-Bissau": 9366.00,
        "Guyana": 10243.00,
        "Haiti": 10243.00,
        "Honduras": 10243.00,
        "Hong Kong": 40678.00,
        "Hungary": 17505.00,
        "Iceland": 66184.00,
        "India": 7116.00,
        "Indonesia": 12778.00,
        "Iran": 14022.00,
        "Iraq": 14022.00,
        "Ireland": 51465.00,
        "Israel": 32004.00,
        "Italy": 37483.00,
        "Ivory Coast": 9366.00,
        "Côte d'Ivoire": 9366.00,
        "Jamaica": 12018.00,
        "Japan": 30959.00,
        "Jordan": 9366.00,
        "Kazakhstan": 12955.00,
        "Kenya": 9366.00,
        "Kiribati": 10243.00,
        "Kuwait": 27627.00,
        "Kyrgyzstan": 5040.00,
        "Laos": 4652.00,
        "Latvia": 17458.00,
        "Lebanon": 9366.00,
        "Lesotho": 9366.00,
        "Liberia": 9366.00,
        "Libya": 9366.00,
        "Liechtenstein": 82171.00,
        "Lithuania": 21632.00,
        "Luxembourg": 62117.00,
        "Madagascar": 9366.00,
        "Malawi": 9366.00,
        "Malaysia": 11903.00,
        "Maldives": 12778.00,
        "Mali": 9366.00,
        "Malta": 25803.00,
        "Marshall Islands": 10243.00,
        "Mauritania": 9366.00,
        "Mauritius": 9366.00,
        "Mexico": 11622.00,
        "Micronesia": 10243.00,
        "Moldova": 5040.00,
        "Monaco": 82171.00,
        "Mongolia": 5040.00,
        "Montenegro": 12812.00,
        "Morocco": 11351.00,
        "Mozambique": 9366.00,
        "Myanmar": 3535.00,
        "Burma": 3535.00,
        "Namibia": 9366.00,
        "Nauru": 10243.00,
        "Nepal": 3535.00,
        "Netherlands": 49758.00,
        "New Zealand": 43970.00,
        "Nicaragua": 10243.00,
        "Niger": 9366.00,
        "Nigeria": 9366.00,
        "North Korea": 5000.00,
        "North Macedonia": 12812.00,
        "N. Maced.": 12812.00,
        "Norway": 48295.00,
        "Oman": 27627.00,
        "Pakistan": 3537.00,
        "Palau": 10243.00,
        "Panama": 19593.00,
        "Papua New Guinea": 10243.00,
        "Paraguay": 10243.00,
        "Peru": 10149.00,
        "Philippines": 6312.00,
        "Poland": 23511.00,
        "Portugal": 26116.00,
        "Qatar": 27627.00,
        "Romania": 21847.00,
        "Russia": 9382.00,
        "Rwanda": 9366.00,
        "Saint Kitts and Nevis": 14895.00,
        "Saint Lucia": 14895.00,
        "Saint Vincent and the Grenadines": 14895.00,
        "Samoa": 10243.00,
        "San Marino": 37483.00,
        "Sao Tome and Principe": 9366.00,
        "Saudi Arabia": 27627.00,
        "Senegal": 9366.00,
        "Serbia": 12812.00,
        "Seychelles": 9366.00,
        "Sierra Leone": 9366.00,
        "Singapore": 40104.00,
        "Slovakia": 22517.00,
        "Slovenia": 27225.00,
        "Solomon Islands": 10243.00,
        "Somalia": 3535.00,
        "South Africa": 14510.00,
        "South Korea": 31721.00,
        "South Sudan": 9366.00,
        "Spain": 35413.00,
        "Sri Lanka": 3535.00,
        "Sudan": 9366.00,
        "Suriname": 10243.00,
        "Sweden": 46322.00,
        "Switzerland": 82171.00,
        "Syria": 9366.00,
        "Taiwan": 26178.00,
        "Tajikistan": 5040.00,
        "Tanzania": 9366.00,
        "Thailand": 10455.00,
        "Timor-Leste": 10243.00,
        "Togo": 9366.00,
        "Tonga": 10243.00,
        "Tunisia": 9366.00,
        "Turkey": 17788.00,
        "Turkmenistan": 5040.00,
        "Tuvalu": 10243.00,
        "Uganda": 9366.00,
        "Ukraine": 6539.00,
        "United Arab Emirates": 35608.00,
        "UAE": 35608.00,
        "United Kingdom": 47179.00,
        "UK": 47179.00,
        "United States": 72415.00,
        "USA": 72415.00,
        "Uruguay": 14959.00,
        "Uzbekistan": 5040.00,
        "Vanuatu": 10243.00,
        "Venezuela": 10243.00,
        "Vietnam": 4652.00,
        "Yemen": 9366.00,
        "Zambia": 9366.00,
        "Zimbabwe": 9366.00
    }
    
    start_country_name = get_country_from_coords(coor_start_lat, coor_start_lng)
    end_country_name = get_country_from_coords(coor_end_lat, coor_end_lng)

    driver_daily_salary_start = truck_driver_annual_salaries.get(start_country_name, 30000) / 330 # Default to 30k if not found
    driver_daily_salary_end = truck_driver_annual_salaries.get(end_country_name, 30000) / 330 # Default to 30k if not found
    annual_working_days = 330 # Standard assumption for working days in a year for a truck driver


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
        # Source: Estimates derived from various port authority tariff sheets and maritime economic reports
        'North Europe': 3.50,
        'US West Coast': 3.20,
        'US East Coast': 3.00,
        'East Asia': 2.80,
        'Middle East': 2.50,
        'Default': 3.00 # A global average fallback
    }
    if ship_archetype_key == 'custom':
        # Custom ship logic...
        selected_ship_params = {
            'volume_m3': inputs['total_ship_volume'],
            'num_tanks': inputs['ship_number_of_tanks'],
            'shape': inputs['ship_tank_shape'],
            # Estimate GT for custom ships, e.g., by scaling from standard
            'gross_tonnage': 165000 * (inputs['total_ship_volume'] / 174000)
        }
    else:
        selected_ship_params = ship_archetypes[ship_archetype_key]
        # Add the key to the params for later lookup
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
        'price_usd_per_ton': 750.0,  # Price can be different from main fuels
        'hhv_mj_per_kg': 45.5,
        'co2_emissions_factor_kg_per_kg_fuel': 3.206 # Specific CO2 factor for MGO
    }
    HHV_diesel = 45.6
    diesel_density = 3.22 # kg per gal
    CO2e_diesel = 10.21
    VOYAGE_OVERHEADS_DATA = {
        'small':    {'daily_operating_cost_usd': 8500, 'daily_capital_cost_usd': 10000, 'port_fee_usd': 30000, 'suez_toll_per_gt_usd': 9.00, 'panama_toll_per_gt_usd': 9.00},
        'midsized': {'daily_operating_cost_usd': 15500, 'daily_capital_cost_usd': 20000, 'port_fee_usd': 50000, 'suez_toll_per_gt_usd': 8.50, 'panama_toll_per_gt_usd': 9.50},
        'standard': {'daily_operating_cost_usd': 22000, 'daily_capital_cost_usd': 35000, 'port_fee_usd': 60000, 'suez_toll_per_gt_usd': 8.00, 'panama_toll_per_gt_usd': 9.00},
        'q-flex':   {'daily_operating_cost_usd': 20000, 'daily_capital_cost_usd': 55000, 'port_fee_usd': 80000, 'suez_toll_per_gt_usd': 7.50, 'panama_toll_per_gt_usd': 8.00},
        'q-max':    {'daily_operating_cost_usd': 25000, 'daily_capital_cost_usd': 75000, 'port_fee_usd': 90000, 'suez_toll_per_gt_usd': 7.00, 'panama_toll_per_gt_usd': 7.50}
    }
    food_params = {
                'strawberry': {
                    'name': 'Strawberry', # The common name for the commodity.
                    'process_flags': { # These flags determine which process functions are called for this commodity.
                        'needs_precooling': True, # Set to True because rapid cooling after harvest is critical for berries. Source: Postharvest handling guides.
                        'needs_freezing': True, # This model assumes strawberries are transported frozen for long-distance sea freight. Source: Industry practice.
                        'needs_controlled_atmosphere': False, # Typically not required for frozen products. Source: CA storage guides.
                    },
                    'general_params': { # Parameters used across multiple stages of the supply chain.
                        'density_kg_per_m3': 600, # The bulk density of whole strawberries in a container. Source: Food engineering databases.
                        'target_temp_celsius': -24.0, # Standard international temperature for frozen goods. Source: ISO standards, food logistics guides.
                        'spoilage_rate_per_day': 0.0001, # Estimated degradation/loss rate for frozen products, representing handling/quality loss. Source: Shelf-life studies.
                        'reefer_container_power_kw': 3.5, # Average power draw for a reefer container holding frozen goods. Source: Reefer manufacturer specifications (e.g., Carrier, Thermo King).
                        'cargo_per_truck_kg': 20000, # Standard maximum payload for a 40ft refrigerated container. Source: Freight and logistics industry standards.
                        'specific_heat_fresh_mj_kgK': 0.0039, # Thermodynamic property based on high water content (~91%). Source: Food science literature, ASHRAE handbooks.
                        'reefer_truck_fuel_consumption_L_hr': 1.5,
                        'production_CO2e_kg_per_kg': 0.747, # Average CO2 emissions from strawberry production per kg. Source: Reducing food’s environmental impacts through producers and consumers.
                    },
                    'precooling_params': { # Parameters for the initial pre-cooling process.
                        'initial_field_heat_celsius': 28.0, # Represents a typical ambient temperature during a summer harvest season in a region like California. Source: Agricultural and meteorological data.
                        'target_precool_temperature_celsius': 1.0, # Ideal temperature to reach before freezing to ensure quality. Source: Postharvest handling guides (e.g., UC Davis).
                        'cop_precooling_system': 2.0, # Coefficient of Performance for a typical forced-air cooling system. Source: HVAC/R engineering principles (ASHRAE).
                        'moisture_loss_percent': 0.015, # Estimated water weight loss during forced-air cooling. Source: Postharvest studies on berry desiccation.
                    },
                    'freezing_params': { # Parameters for the main freezing process.
                        'specific_heat_frozen_mj_kgK': 0.0018, # Thermodynamic property of the frozen product (ice has a lower specific heat than water). Source: Food science literature.
                        'latent_heat_fusion_mj_kg': 0.300, # Energy required to freeze the water content of the fruit. Source: Physics handbooks, food engineering data.
                        'cop_freezing_system': 2.5 # Coefficient of Performance for an industrial blast freezer. Source: HVAC/R engineering principles (ASHRAE).
                    }
                },
                'hass_avocado': {
                    'name': 'Hass Avocado', # The common name for the commodity.
                    'process_flags': { # These flags determine which process functions are called for this commodity.
                        'needs_precooling': True, # Pre-cooling is essential for avocados. Source: Postharvest handling guides.
                        'needs_freezing': False, # Avocados are shipped chilled, not frozen. Source: Industry practice.
                        'needs_controlled_atmosphere': True, # CA is critical for extending the shelf-life of avocados. Source: CA storage guides, UC Davis Postharvest Center.
                    },
                    'general_params': { # Parameters used across multiple stages of the supply chain.
                        'density_kg_per_m3': 600, # Bulk density of whole avocados. Source: Food engineering databases.
                        'target_temp_celsius': 5.0, # Optimal transport temperature for Hass avocados to control ripening. Source: UC Davis Postharvest Technology Center.
                        'spoilage_rate_per_day': 0.0005, # Estimated loss rate for chilled avocados under CA. Source: Shelf-life studies.
                        'spoilage_rate_ca_per_day': 0.0002, # Lower spoilage rate under CA
                        'reefer_container_power_kw': 1.5, # Lower average power draw for chilled goods compared to frozen. Source: Reefer manufacturer specifications.
                        'cargo_per_truck_kg': 20000, # Standard maximum payload for a 40ft refrigerated container. Source: Freight and logistics industry standards.
                        'specific_heat_fresh_mj_kgK': 0.0035, # Thermodynamic property based on the fruit's composition. Source: Food science literature.
                        'reefer_truck_fuel_consumption_L_hr': 1.5,
                        'production_CO2e_kg_per_kg': 1.725, # Average CO2 emissions from strawberry production per kg. Source: Carbon Cloud.
                    },
                    'precooling_params': { # Parameters for the initial pre-cooling process.
                        'initial_field_heat_celsius': 25.0, # A typical field heat for avocados from subtropical/tropical climates. Source: Agricultural data.
                        'target_precool_temperature_celsius': 6.0, # Target temperature after pre-cooling. Source: Postharvest handling guides.
                        'cop_precooling_system': 2.0, # Coefficient of Performance for a forced-air cooling system. Source: HVAC/R engineering principles.
                        'moisture_loss_percent': 0.01, # Estimated water weight loss. Source: Postharvest studies.
                    },
                    'ca_params': { # Parameters for the Controlled Atmosphere system.
                        'o2_target_percent': 5.0, # Optimal low-oxygen level for avocados. Source: UC Davis Postharvest Technology Center.
                        'co2_target_percent': 5.0, # Optimal carbon dioxide level to slow ripening. Source: UC Davis Postharvest Technology Center.
                        'humidity_target_rh_percent': 90.0, # Target relative humidity to prevent shriveling. Source: Postharvest handling guides.
                        'respiration_rate_ml_co2_per_kg_hr': 15.0, # A typical respiration rate for avocados at their target temperature. Source: Postharvest biology research papers.
                        'container_leakage_rate_ach': 0.02, # Air Changes per Hour, representing the leakiness of a modern container. Source: ISO standards for freight containers.
                        'n2_generator_efficiency_kwh_per_m3': 0.4, # Energy needed for an onboard nitrogen generator to produce 1 m³ of N2. Source: Manufacturer specifications.
                        'co2_scrubber_efficiency_kwh_per_kg_co2': 0.2, # Energy needed for a CO2 scrubber to remove 1 kg of CO2. Source: Chemical engineering process design.
                        'humidifier_efficiency_kwh_per_liter': 0.05, # Energy to atomize 1 liter of water for humidification. Source: HVAC/R equipment specifications.
                        'base_control_power_kw': 0.1 # Baseline constant power draw for sensors and control units. Source: Equipment specifications.
                    }
                },
                'banana': {
                    'name': 'Banana', # The common name for the commodity.
                    'process_flags': { # These flags determine which process functions are called for this commodity.
                        'needs_precooling': True, # Pre-cooling is standard practice. Source: Postharvest handling guides for bananas.
                        'needs_freezing': False, # Bananas are highly sensitive to cold and are never frozen for fresh market. Source: Industry practice.
                        'needs_controlled_atmosphere': True, # CA is widely used to manage ripening during long sea voyages. Source: Postharvest handling guides.
                    },
                    'general_params': { # Parameters used across multiple stages of the supply chain.
                        'density_kg_per_m3': 650, # Bulk density for hands of bananas in cartons. Source: Food engineering databases.
                        'target_temp_celsius': 13.5, # Critical temperature to prevent chilling injury while managing ripening. Source: UC Davis Postharvest Technology Center.
                        'spoilage_rate_per_day': 0.001, # Higher spoilage rate due to sensitivity. Source: Shelf-life studies on bananas.
                        'spoilage_rate_ca_per_day': 0.0004, # Lower spoilage rate under CA
                        'reefer_container_power_kw': 1.8, # Power draw for this specific chilled temperature. Source: Reefer manufacturer specifications.
                        'cargo_per_truck_kg': 20000, # Standard maximum payload. Source: Freight and logistics industry standards.
                        'specific_heat_fresh_mj_kgK': 0.0033, # Thermodynamic property. Source: Food science literature.
                        'reefer_truck_fuel_consumption_L_hr': 1.5,
                        'production_CO2e_kg_per_kg': 0.241, # Average CO2 emissions from banana production per kg. Source: Reducing food’s environmental impacts through producers and consumers.
                    },
                    'precooling_params': { # Parameters for the initial pre-cooling process.
                        'initial_field_heat_celsius': 30.0, # Represents a typical field heat in a tropical harvesting environment. Source: Agricultural and meteorological data.
                        'target_precool_temperature_celsius': 14.0, # Target temperature after pre-cooling. Source: Postharvest handling guides.
                        'cop_precooling_system': 2.0, # COP for forced-air cooling rooms at packing houses. Source: HVAC/R engineering principles.
                        'moisture_loss_percent': 0.01, # Estimated water weight loss. Source: Postharvest studies.
                    },
                    'ca_params': { # Parameters for the Controlled Atmosphere system.
                        'o2_target_percent': 2.0, # Very low oxygen is needed to put bananas "to sleep". Source: UC Davis Postharvest Technology Center.
                        'co2_target_percent': 5.0, # High CO2 level helps inhibit ripening. Source: UC Davis Postharvest Technology Center.
                        'humidity_target_rh_percent': 90.0, # Target relative humidity. Source: Postharvest handling guides.
                        'respiration_rate_ml_co2_per_kg_hr': 25.0, # Bananas have a very high respiration rate compared to other fruits. Source: Postharvest biology research papers.
                        'container_leakage_rate_ach': 0.02, # Air Changes per Hour for the container. Source: ISO standards.
                        'n2_generator_efficiency_kwh_per_m3': 0.4, # Equipment efficiency. Source: Manufacturer specifications.
                        'co2_scrubber_efficiency_kwh_per_kg_co2': 0.2, # Equipment efficiency. Source: Chemical engineering process design.
                        'humidifier_efficiency_kwh_per_liter': 0.05, # Equipment efficiency. Source: HVAC/R equipment specifications.
                        'base_control_power_kw': 0.1 # Baseline power draw for control systems. Source: Equipment specifications.
                    }
                }
            }

    data_raw = []
    response_data = {}
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
        LH2_plant_capacity = facility_capacity
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
        truck_economy = [13.84, 10.14, 9.66]  # km/gal Grok Analysis

        # ADD THESE NEW PARAMETERS FOR TANK COOLDOWN
        # Sourced from Table 2 in the provided study 
        ship_tank_metal_specific_heat = 0.47 / 1000  # MJ/kg-K
        ship_tank_insulation_specific_heat = 1.5 / 1000 # MJ/kg-K
        ship_tank_metal_density = 7900  # kg/m^3
        ship_tank_insulation_density = 100 # kg/m^3
        pipe_metal_specific_heat = 0.5 / 1000  # MJ/kg-K (for stainless steel)
        # Sourced from the study's text and Table 6 
        ship_tank_metal_thickness = 0.05 # m
        # Using onshore storage insulation thickness as a proxy from the study 
        ship_tank_insulation_thickness = [0.66, 0.09, 0] # m (H2, NH3, Methanol)
        
        # Sourced from Table 6 for the "Cooldown" scenario 
        COP_cooldown = [0.131, 1.714, 0] # (H2, NH3, Methanol)
        SMR_EMISSIONS_KG_PER_KG_H2 = 9.3 # kg CO2e / kg H2 for unabated Steam Methane Reforming

        # --- 5. Optimization ---
        target_weight = total_ship_volume * liquid_chem_density[fuel_type] * 0.98  # kg, ref [3] section 2.1:  the filling limit is defined as 98% for ships cargo tank.
        
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
            COP_refrig, EIM_refrig_eff, pipe_metal_specific_heat,
            COP_cooldown,

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
            BOG_recirculation_storage, # This is the percentage from inputs
            # COP_refrig, EIM_refrig_eff, start_electricity_price, CO2e_start, GWP_chem,
            # LH2_plant_capacity, EIM_liquefication, fuel_cell_eff, EIM_fuel_cell, LHV_chem are already above
            driver_daily_salary_start, annual_working_days # ADDED FOR OPTIMIZER

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
                        
        if result.success:
            chem_weight = result.x[0]
        else:
            # If the optimization fails, raise an exception with the optimizer's message.
            # This will be caught by the main try...except block and returned as a JSON error.
            raise Exception(f"Optimization failed: {result.message}")
        
        # --- 6. Final Calculation ---
        
        final_results_raw, data_raw = total_chem_base(chem_weight, user_define[1], user_define[2], 
                                                    user_define[3], user_define[4], user_define[5])

        # --- Correctly Handle Overheads and Infrastructure CAPEX ---
        if include_overheads:
            # --- 1. Calculate Voyage Overheads (Non-Fuel Ship Costs) ---
            start_port_country = get_country_from_coords(start_port_lat, start_port_lng)
            end_port_country = get_country_from_coords(end_port_lat, end_port_lng)
            port_regions = {'start': start_port_country, 'end': end_port_country}
            voyage_duration_days = port_to_port_duration / 24.0
            total_voyage_overheads = calculate_voyage_overheads(voyage_duration_days, selected_ship_params, canal_transits, port_regions)

            # --- 2. Calculate Prorated Infrastructure CAPEX (Liquefaction & Storage) ---
            # Get the amortized $/kg rates for the facilities
            liquefaction_capex_per_kg = calculate_liquefaction_capex(LH2_plant_capacity, fuel_type)

            # Calculate the CAPEX cost for this specific shipment
            # Liquefaction happens once at the start with the initial weight
            total_liquefaction_capex = liquefaction_capex_per_kg * chem_weight

            # Storage happens multiple times. We find the weight at each stage from the results.
            total_storage_capex = 0
            storage_A_weight = next((row[4] for row in data_raw if row[0] == "chem_storage_at_port_A"), 0)
            storage_B_weight = next((row[4] for row in data_raw if row[0] == "chem_storage_at_port_B"), 0)
            storage_C_weight = next((row[4] for row in data_raw if row[0] == "chem_storage_at_site_B"), 0)
            storage_capex_A_per_kg = calculate_storage_capex(fuel_type, LH2_plant_capacity, storage_A_weight, storage_time_A)
            storage_capex_B_per_kg = calculate_storage_capex(fuel_type, LH2_plant_capacity, storage_B_weight, storage_time_B)
            storage_capex_C_per_kg = calculate_storage_capex(fuel_type, LH2_plant_capacity, storage_C_weight, storage_time_C)

            total_storage_capex += storage_capex_A_per_kg * storage_A_weight
            total_storage_capex += storage_capex_B_per_kg * storage_B_weight
            total_storage_capex += storage_capex_C_per_kg * storage_C_weight

            truck_capex_params = {
                0: {'cost_usd_per_truck': 1500000, 'useful_life_years': 10, 'annualization_factor': 0.15}, # LH2 specialized cryogenic
                1: {'cost_usd_per_truck': 800000,  'useful_life_years': 10, 'annualization_factor': 0.15}, # Ammonia specialized pressurized/cryogenic
                2: {'cost_usd_per_truck': 200000,  'useful_life_years': 10, 'annualization_factor': 0.15}  # Methanol standard chemical tanker
            }

            truck_model = truck_capex_params.get(fuel_type, truck_capex_params[0]) # Default to LH2 if not found
            annual_truck_cost_usd = truck_model['cost_usd_per_truck'] * truck_model['annualization_factor']

            loading_unloading_capex_params = {
                0: {'total_capex_M_usd': 500, 'annualization_factor': 0.08}, # LH2 (very high due to cryogenics, safety, specialized equipment)
                1: {'total_capex_M_usd': 200, 'annualization_factor': 0.08}, # Ammonia (still high due to pressure/cryo, toxicity, safety)
                2: {'total_capex_M_usd': 80,  'annualization_factor': 0.08}  # Methanol (standard chemical liquid terminal)
            }
            # Reference annual throughput for these terminals (metric tons per year)
            # This is a critical assumption for prorating CAPEX per kg.
            reference_annual_throughput_tons = {
                0: 1000000, # 1 Million tons/year LH2 terminal
                1: 5000000, # 5 Million tons/year Ammonia terminal
                2: 10000000 # 10 Million tons/year Methanol terminal
            }
            capex_rate_loading_unloading_per_kg = calculate_loading_unloading_capex(fuel_type)
            amount_loaded_onto_ship = next((row[4] for row in data_raw if row[0] == "chem_loading_to_ship"), 0)
            amount_unloaded_from_ship = next((row[4] for row in data_raw if row[0] == "chem_unloading_from_ship"), 0)
            capex_loading_origin = capex_rate_loading_unloading_per_kg * amount_loaded_onto_ship
            capex_unloading_destination = capex_rate_loading_unloading_per_kg * amount_unloaded_from_ship
            total_loading_unloading_capex = capex_loading_origin + capex_unloading_destination

            # To prorate by distance and number of trucks/trips:
            # We need the number of trucks for each leg, and their daily utilization/throughput.
            # A common way to allocate truck CAPEX is per tonne-km or per trip.
            # For simplicity in an LCA, we can estimate based on number of trucks * number of trips annually
            # or based on the total mass moved and distance.

            # We'll use the 'number_of_trucks' values from the respective transport steps.
            # Assuming these trucks are utilized for 330 days/year, handling capacity_tpd
            # This is an estimate, a detailed fleet model would be more precise.

            # Get truck data for site_A_to_port_A
            # We need to re-calculate number_of_trucks specific to the initial_weight in the context of chem_in_truck_weight
            # and then amortize the truck for that specific delivery.
            # Instead of daily amortization, let's consider the cost per *trip* based on capacity.

            # Re-calculate number of trucks for initial leg A->Port A based on initial chem_weight
            num_trucks_A_to_PortA = math.ceil(chem_weight / chem_in_truck_weight[fuel_type])
            # Re-calculate number of trucks for final leg Port B->B based on final delivered weight (final_results_raw[3])
            final_delivered_weight = final_results_raw[3] # This is the final remaining chemical
            num_trucks_PortB_to_B = math.ceil(final_delivered_weight / chem_in_truck_weight[fuel_type])

            # Calculate the amortized cost per truck trip. Assume trucks average 100,000 km/year, useful life 10 years.
            # A more direct way: Annual cost of truck / (Annual km / avg_trip_km) / truck_capacity
            # Simpler: Amortized cost per truck trip = Annual truck cost / (Annual operating days * Trips per day)
            # Let's assume a truck can make 1 round trip per day for this distance.
            # Annual trips per truck = 330 days * 1 trip/day = 330 trips
            annual_trips_per_truck = 330

            capex_per_truck_trip_usd = annual_truck_cost_usd / annual_trips_per_truck if annual_trips_per_truck > 0 else 0

            # Total trucking CAPEX for this single shipment
            # Assuming each truck contributes its amortized cost per trip it makes for THIS specific shipment
            total_trucking_capex = 0
            if num_trucks_A_to_PortA > 0:
                total_trucking_capex += capex_per_truck_trip_usd * num_trucks_A_to_PortA
            if num_trucks_PortB_to_B > 0:
                total_trucking_capex += capex_per_truck_trip_usd * num_trucks_PortB_to_B

            # --- 3. Add All Calculated CAPEX and Overheads to Final Totals and Insert Rows for Display ---
            final_results_raw[0] += total_voyage_overheads
            final_results_raw[0] += total_liquefaction_capex
            final_results_raw[0] += total_storage_capex
            final_results_raw[0] += total_trucking_capex 
            final_results_raw[0] += total_loading_unloading_capex

            # Create and insert display rows into the detailed data list
            # Insert Voyage Overheads row after marine transport
            marine_transport_index = next((i for i, row in enumerate(data_raw) if row[0] == "port_to_port"), -1)
            if marine_transport_index != -1:
                overhead_row = ["Voyage Overheads", total_voyage_overheads, 0, 0, data_raw[marine_transport_index][4], 0]
                data_raw.insert(marine_transport_index + 1, overhead_row)

            # Insert Liquefaction CAPEX row after liquefaction OPEX
            liquefaction_index = next((i for i, row in enumerate(data_raw) if row[0] == "site_A_chem_liquification"), -1)
            if liquefaction_index != -1:
                liquefaction_capex_row = ["Liquefaction Facility CAPEX", total_liquefaction_capex, 0, 0, chem_weight, 0]
                data_raw.insert(liquefaction_index + 1, liquefaction_capex_row)
            
            # Insert Storage CAPEX row (we'll add one consolidated row for simplicity)
            # Find the index of the last storage step to insert after it
            last_storage_index = next((i for i, row in reversed(list(enumerate(data_raw))) if "chem_storage_at" in row[0]), -1)
            if last_storage_index != -1:
                storage_capex_row = ["Storage Facilities CAPEX (Total)", total_storage_capex, 0, 0, data_raw[last_storage_index][4], 0]
                data_raw.insert(last_storage_index + 1, storage_capex_row)
            
            # NEW: Insert Trucking CAPEX row
            # Best place to insert is after the first road transport or consolidated.
            # Let's insert it after the first road transport for chronological order.
            road_transport_A_index = next((i for i, row in enumerate(data_raw) if row[0] == "site_A_to_port_A"), -1)
            if road_transport_A_index != -1:
                trucking_capex_row = ["Trucking System CAPEX (Total)", total_trucking_capex, 0, 0, data_raw[road_transport_A_index][4], 0]
                data_raw.insert(road_transport_A_index + 1, trucking_capex_row)
        
            ship_loading_index = next((i for i, row in enumerate(data_raw) if row[0] == "chem_loading_to_ship"), -1)
            if ship_loading_index != -1:
                loading_unloading_capex_row = ["Loading/Unloading Infrastructure CAPEX", total_loading_unloading_capex, 0, 0, data_raw[ship_loading_index][4], 0]
                data_raw.insert(ship_loading_index + 1, loading_unloading_capex_row)
        
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
            "voyage_overheads": "Voyage Overheads (Non-Fuel)", 
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
        data_for_display_common = [row for row in detailed_data_formatted if row[0] != "TOTAL"]

        emission_chart_exclusions = [
            "Voyage Overheads",
            "Liquefaction Facility CAPEX",
            "Trucking System CAPEX (Total)",
            "Loading/Unloading Infrastructure CAPEX",
            "Storage Facilities CAPEX (Total)",
            "TOTAL" # Still exclude the total row for the chart
        ]
        
        # Filter for the charts (removes the placeholder AND the TOTAL row)
        data_for_emission_chart = [row for row in data_for_display_common if row[0] not in emission_chart_exclusions]

        # --- PREPARE CONTEXTUAL OVERLAY TEXT FOR CHARTS ---
        cost_overlay_text = ""
        if hydrogen_production_cost > 0:
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

        # --- DEFINE HEADERS, INDICES, AND PACKAGE FINAL RESPONSE ---
        new_detailed_headers = ["Process Step", "Cost ($)", "Energy (MJ)", "CO2eq (kg)", "Chem (kg)", "BOG (kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "CO2eq/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
        csv_data = [new_detailed_headers] + detailed_data_formatted
        cost_per_kg_index = new_detailed_headers.index("Cost/kg ($/kg)")
        eco2_per_kg_index = new_detailed_headers.index("CO2eq/kg (kg/kg)")

        cost_chart_base64 = create_breakdown_chart(
            data_for_display_common,
            cost_per_kg_index,
            'Cost Breakdown per kg of Delivered Fuel',
            'Cost ($/kg)',
            overlay_text=cost_overlay_text
        )
        emission_chart_base64 = create_breakdown_chart(
            data_for_emission_chart,
            eco2_per_kg_index,
            'CO2eq Breakdown per kg of Delivered Fuel',
            'CO2eq (kg/kg)',
            overlay_text=emission_overlay_text
        )

        summary1_data = [
            ["Cost ($/kg chemical)", f"{chem_cost:.2f}"],
            ["Consumed Energy (MJ/kg chemical)", f"{chem_energy:.2f}"],
            ["Emission (kg CO2eq/kg chemical)", f"{chem_CO2e:.2f}"]
        ]

        summary2_data = [
            ["Cost ($/GJ)", f"{total_results[0] / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Energy consumed (MJ_in/GJ_out)", f"{total_results[1] / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"],
            ["Emission (kg CO2eq/GJ)", f"{total_results[2] / final_energy_output_gj:.2f}" if final_energy_output_gj > 0 else "N/A"]
        ]

        assumed_prices_data = [
            [f"Electricity Price at {start}*", f"{start_electricity_price[2]:.4f} $/MJ"],
            [f"Electricity Price at {end}*", f"{end_electricity_price[2]:.4f} $/MJ"],
            [f"Diesel Price at {start}", f"{diesel_price_start:.2f} $/gal"],
            [f"Diesel Price at {end_port_name}", f"{diesel_price_end:.2f} $/gal"],
            [f"Marine Fuel ({marine_fuel_choice}) Price at {start_port_name}*", f"{dynamic_price:.2f} $/ton"],
            [f"Green H2 Production Price at {start}*", f"{hydrogen_production_cost:.2f} $/kg"],
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
        # --- 1. UNPACK INPUTS & GET SHIP DETAILS ---
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
        
        # Initialize final_commodity_kg to avoid UnboundLocalError
        final_commodity_kg = 0
        total_money = 0
        total_energy = 0
        total_emissions = 0

        # Get total container capacity of the selected ship
        total_ship_container_capacity = math.floor(total_ship_volume / 76)

        # --- RUN LAND-BASED LCA & INITIAL PRORATED SEA COSTS BEFORE LOCAL SOURCING ---
        initial_weight = shipment_size_containers * current_food_params['general_params']['cargo_per_truck_kg']
        data_raw = total_food_lca(initial_weight, current_food_params)
        
        # Calculate BASE costs (Propulsion + Overheads) for the ENTIRE SHIP
        propulsion_fuel_kwh = avg_ship_power_kw * port_to_port_duration
        propulsion_fuel_kg = (propulsion_fuel_kwh * selected_marine_fuel_params['sfoc_g_per_kwh']) / 1000.0
        propulsion_cost = (propulsion_fuel_kg / 1000.0) * selected_marine_fuel_params['price_usd_per_ton']
        
        voyage_duration_days = port_to_port_duration / 24.0
        total_overhead_cost = 0
        if include_overheads:
            start_port_country = get_country_from_coords(start_port_lat, start_port_lng)
            end_port_country = get_country_from_coords(end_port_lat, end_port_lng)
            port_regions = {'start': start_port_country, 'end': end_port_country} 
            voyage_duration_days = port_to_port_duration / 24.0
            total_overhead_cost = calculate_voyage_overheads(voyage_duration_days, selected_ship_params, canal_transits, port_regions)

        # Calculate the BASE COST PER DRY SLOT on the ship
        total_base_voyage_cost = propulsion_cost
        base_cost_per_slot = total_base_voyage_cost / total_ship_container_capacity if total_ship_container_capacity > 0 else 0

        # Calculate the ADDITIONAL cost for the REEFER SERVICE for ONE container
        reefer_service_cost, reefer_service_energy, reefer_service_emissions = calculate_single_reefer_service_cost(port_to_port_duration, current_food_params)
        
        # Inject the new, more detailed sea transport costs into the results
        marine_transport_index = next((i for i, row in enumerate(data_raw) if "Marine Transport" in row[0]), -1)
        if marine_transport_index != -1:
            # Base freight cost for the user's shipment
            base_freight_cost = base_cost_per_slot * shipment_size_containers
            
            # Preserve the commodity weight at this stage
            commodity_weight_at_marine_transport = data_raw[marine_transport_index][4]

            data_raw[marine_transport_index][0] = "Marine Transport (Base Freight)"
            data_raw[marine_transport_index][1] = base_freight_cost
            # We can approximate propulsion energy/emissions for the user's share
            propulsion_emissions = (propulsion_fuel_kg * selected_marine_fuel_params['co2_emissions_factor_kg_per_kg_fuel'])
            data_raw[marine_transport_index][3] = (propulsion_emissions / total_ship_container_capacity) * shipment_size_containers if total_ship_container_capacity > 0 else 0
            data_raw[marine_transport_index][2] = (propulsion_fuel_kwh * 3.6 / total_ship_container_capacity) * shipment_size_containers if total_ship_container_capacity > 0 else 0

            # Add a new row for the reefer service cost
            reefer_service_total_cost = reefer_service_cost * shipment_size_containers
            reefer_service_total_energy = reefer_service_energy * shipment_size_containers
            reefer_service_total_emissions = reefer_service_emissions * shipment_size_containers
            reefer_row = ["Reefer & CA Services", reefer_service_total_cost, reefer_service_total_energy, reefer_service_total_emissions, commodity_weight_at_marine_transport, 0]
            data_raw.insert(marine_transport_index + 1, reefer_row)

            # Add a new row for Overheads if included
            if include_overheads:
                prorated_overhead_cost = (total_overhead_cost / total_ship_container_capacity) * shipment_size_containers if total_ship_container_capacity > 0 else 0
                overhead_row = ["Voyage Overheads (Prorated)", prorated_overhead_cost, 0, 0, commodity_weight_at_marine_transport, 0]
                data_raw.insert(marine_transport_index + 1, overhead_row)

        # Now, calculate the overall totals *after* all rows have been adjusted/inserted
        total_money = sum(row[1] for row in data_raw)
        total_energy = sum(row[2] for row in data_raw)
        total_emissions = sum(row[3] for row in data_raw)
        final_weight = data_raw[-1][4] # The last row from total_food_lca is the overall total
        final_commodity_kg = final_weight # Now final_commodity_kg is correctly defined and up-to-date
        
        # --- LOCAL SOURCING COMPARISON (Can now safely use final_commodity_kg) ---
        local_sourcing_results = None
        green_premium_data = None
        farm_name = None # Ensure farm_name is initialized for checks outside the if block
        price_farm = None # Ensure price_farm is initialized for checks outside the if block

        farm_region = openai_get_nearest_farm_region(current_food_params['name'], end_country)

        if farm_region:
            # We have a local farm, now calculate the logistics from farm to destination
            farm_lat = farm_region['latitude']
            farm_lon = farm_region['longitude']
            farm_name = farm_region['farm_region_name']
            price_farm = openai_get_food_price(current_food_params['name'], farm_name)
            
            # Calculate local trucking distance and duration
            local_dist_str, local_dur_str = inland_routes_cal((farm_lat, farm_lon), (coor_end_lat, coor_end_lng))
            local_distance_km = float(re.sub(r'[^\d.]', '', local_dist_str))
            local_duration_mins = time_to_minutes(local_dur_str)
            
            # Use the final delivered weight for an apples-to-apples comparison
            comparison_weight = final_commodity_kg
            
            # Initialize local processing costs to zero
            local_precool_money, local_precool_energy, local_precool_emissions = 0, 0, 0
            local_freeze_money, local_freeze_energy, local_freeze_emissions = 0, 0, 0

            # Conditionally calculate pre-cooling costs if needed
            if current_food_params['process_flags'].get('needs_precooling'):
                precooling_full_params = {**current_food_params.get('precooling_params', {}), **current_food_params.get('general_params', {})}
                local_precool_money, local_precool_energy, local_precool_emissions, _, _ = food_precooling_process(comparison_weight, (precooling_full_params, end_electricity_price, CO2e_end))

            # Conditionally calculate freezing costs if needed
            if current_food_params['process_flags'].get('needs_freezing'):
                freezing_full_params = {**current_food_params.get('freezing_params', {}), **current_food_params.get('general_params', {})}
                local_freeze_money, local_freeze_energy, local_freeze_emissions, _, _ = food_freezing_process(comparison_weight, (freezing_full_params, end_local_temperature, end_electricity_price, CO2e_end))

            # Calculate local trucking costs (this call is already correct)
            local_trucking_args = (current_food_params, local_distance_km, local_duration_mins, diesel_price_end, HHV_diesel, diesel_density, CO2e_diesel, end_local_temperature)
            local_trucking_money, local_trucking_energy, local_trucking_emissions, _, _ = food_road_transport(comparison_weight, local_trucking_args)

            # Sum all costs for the local scenario
            local_total_money = local_precool_money + local_freeze_money + local_trucking_money
            local_total_emissions = local_precool_emissions + local_freeze_emissions + local_trucking_emissions
            
            # Store the results
            local_sourcing_results = {
                "source_name": farm_name,
                "distance_km": local_distance_km,
                "cost_per_kg": local_total_money / comparison_weight if comparison_weight > 0 else 0,
                "emissions_per_kg": local_total_emissions / comparison_weight if comparison_weight > 0 else 0
            }        

            if price_farm is None:
                price_farm = price_end # Use the national UK price as a fallback

            green_premium_data = None
            # Only proceed if we have valid prices for comparison
            if price_farm is not None and price_start is not None and final_commodity_kg > 0 and comparison_weight > 0:
                # Calculate total landed cost per kg for both scenarios
                cost_international_transport_per_kg = total_money / final_commodity_kg
                landed_cost_international_per_kg = price_start + cost_international_transport_per_kg

                cost_local_sourcing_per_kg = local_total_money / comparison_weight
                landed_cost_local_per_kg = price_farm + cost_local_sourcing_per_kg

                # Calculate total emissions per kg for both scenarios
                emissions_international_per_kg = total_emissions / final_commodity_kg
                emissions_local_per_kg = local_total_emissions / comparison_weight

                # Calculate the difference in cost and emissions
                cost_difference_per_kg = landed_cost_local_per_kg - landed_cost_international_per_kg
                emissions_saved_per_kg = emissions_international_per_kg - emissions_local_per_kg

                # Calculate the Green Premium (cost of carbon abatement)
                green_premium_usd_per_ton_co2 = "N/A (No emission savings)"
                if emissions_saved_per_kg > 0:
                    # Formula: ($/kg_food) / (kg_CO2/kg_food) -> $/kg_CO2. Then * 1000 for $/ton_CO2
                    premium_raw = cost_difference_per_kg / emissions_saved_per_kg
                    green_premium_usd_per_ton_co2 = f"${(premium_raw * 1000):,.2f}"
                elif cost_difference_per_kg < 0:
                    # Cheaper AND lower emissions
                    green_premium_usd_per_ton_co2 = "Negative (Win-Win Scenario)"
                
                # Package the data for the frontend table
                green_premium_data = [
                    ["Landed Cost (International Shipment)", f"${landed_cost_international_per_kg:.2f}/kg"],
                    ["Landed Cost (Local Sourcing)", f"${landed_cost_local_per_kg:.2f}/kg"],
                    ["Emissions (International Shipment)", f"{emissions_international_per_kg:.2f} kg CO₂e/kg"],
                    ["Emissions (Local Sourcing)", f"{emissions_local_per_kg:.2f} kg CO₂e/kg"],
                    ["Green Premium (Cost per ton of CO₂ saved)", f"{green_premium_usd_per_ton_co2}"]
                ]
                    
        # --- 4. PROCESS FINAL DATA FOR TABLES AND CHARTS ---
        # Add the final TOTAL row after all dynamic insertions
        data_raw.append(["TOTAL", total_money, total_energy, total_emissions, final_commodity_kg, sum(row[5] for row in data_raw[:-1])])
        
        energy_content = current_food_params.get('general_params', {}).get('energy_content_mj_per_kg', 1)
        final_energy_output_mj = final_commodity_kg * energy_content
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
        data_for_display_common = [row for row in detailed_data_formatted if row[0] != "TOTAL"]
        emission_chart_exclusions_food = [
            "Voyage Overheads (Prorated)", # For food, this is 'Prorated'
        ]
        data_for_emission_chart = [row for row in data_for_display_common if row[0] not in emission_chart_exclusions_food]
        new_detailed_headers = ["Process Step", "Cost ($)", "Energy (MJ)", "eCO2 (kg)", "Commodity (kg)", "Spoilage (kg)", "Cost/kg ($/kg)", "Cost/GJ ($/GJ)", "eCO2/kg (kg/kg)", "eCO2/GJ (kg/GJ)"]
        cost_per_kg_index = new_detailed_headers.index("Cost/kg ($/kg)")
        eco2_per_kg_index = new_detailed_headers.index("eCO2/kg (kg/kg)")
        
        # Calculate per-kg metrics for summary table 1
        cost_per_kg = total_money / final_commodity_kg if final_commodity_kg > 0 else 0
        energy_per_kg = total_energy / final_commodity_kg if final_commodity_kg > 0 else 0
        emissions_per_kg = total_emissions / final_commodity_kg if final_commodity_kg > 0 else 0
        
        summary1_data = [
            ["Cost ($/kg food)", f"{cost_per_kg:.2f}"],
            ["Consumed Energy (MJ/kg food)", f"{energy_per_kg:.2f}"],
            ["Emission (kg CO2eq/kg food)", f"{emissions_per_kg:.2f}"]
        ]

        # Calculate per-GJ metrics for summary table 2
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
            [f"{food_name_for_lookup} Price in {start_country}*", f"${price_start:.2f}/kg" if price_start is not None else "N/A"],
            [f"{food_name_for_lookup} Price in {end_country}*", f"${price_end:.2f}/kg" if price_end is not None else "N/A"],
        ]
        if 'farm_name' in locals() and 'price_farm' in locals() and price_farm is not None:
            assumed_prices_data.append([f"{food_name_for_lookup} Price at {farm_name}*", f"${price_farm:.2f}/kg"])

        # --- 5. CREATE CHARTS AND CONTEXT ---

# --- 5. CREATE CHARTS AND CONTEXT ---
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
        cost_chart_base64 = create_breakdown_chart(data_for_display_common, cost_per_kg_index, f'Cost Breakdown per kg of Delivered {current_food_params["name"]}', 'Cost ($/kg)', overlay_text=cost_overlay_text)
        emission_chart_base64 = create_breakdown_chart(data_for_emission_chart, eco2_per_kg_index, f'CO2eq Breakdown per kg of Delivered {current_food_params["name"]}', 'CO2eq (kg/kg)', overlay_text=emission_overlay_text)
            
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
