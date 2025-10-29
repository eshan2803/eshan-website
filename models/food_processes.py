"""
models/food_processes.py

Food supply chain process functions for Life Cycle Assessment (LCA).
Extracted from app.py for better code organization and modularity.

This module contains all food-related process functions including:
- Harvesting and preparation
- Pre-cooling and freezing
- Cold storage
- Road transport (refrigerated trucks)
- Sea transport (reefer containers)
- Controlled atmosphere (CA) energy calculations

Each function returns a standardized 8-tuple:
(opex_money, capex_money, carbon_tax_money, energy, emissions, current_weight, loss, insurance_cost)
"""

import math
import numpy as np


def food_harvest_and_prep(A, args):
    """
    Calculate costs and emissions for harvesting and preparation stage of food supply chain.

    This function handles the initial stage of the food supply chain, primarily focusing on
    insurance cost calculations based on cargo value and route risk factors.

    Args:
        A (float): Mass of food product in kg
        args (tuple): Contains:
            - price_start_arg (float): Price per kg of food at origin (USD/kg)
            - start_country_name_arg (str): Name of origin country
            - carbon_tax_per_ton_co2_dict_arg (dict): Carbon tax rates by country (USD/ton CO2)
            - food_name_arg (str): Name of food commodity
            - searoute_coor_arg (list): Sea route coordinates for insurance calculation
            - port_to_port_duration_arg (float): Duration of marine transport in hours

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Operational costs in USD
            - capex_money (float): Capital costs in USD
            - carbon_tax_money (float): Carbon tax costs in USD
            - energy (float): Energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Remaining mass after losses in kg
            - loss (float): Mass lost during process in kg
            - insurance_cost (float): Insurance costs in USD

    Notes:
        - This function requires calculate_total_insurance_cost to be available in scope
        - Insurance cost is returned separately for tracking purposes
        - No direct energy consumption or emissions in this stage
    """
    (price_start_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg,
     food_name_arg, searoute_coor_arg, port_to_port_duration_arg) = args

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0
    energy = 0
    emissions = 0
    loss = 0
    insurance_cost = 0

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
    """
    Calculate costs, energy, and emissions for freezing food products.

    This function models the industrial freezing process for food preservation, calculating:
    - Sensible heat removal (cooling to 0°C)
    - Latent heat of fusion (phase change)
    - Further sensible heat removal (cooling to target frozen temperature)
    - Energy consumption based on coefficient of performance (COP)
    - Capital costs based on facility capacity

    Args:
        A (float): Mass of food product in kg
        args (tuple): Contains:
            - params (dict): Freezing parameters including:
                - specific_heat_fresh_mj_kgK: Specific heat of fresh product (MJ/kg·K)
                - latent_heat_fusion_mj_kg: Latent heat of fusion (MJ/kg)
                - specific_heat_frozen_mj_kgK: Specific heat of frozen product (MJ/kg)
                - target_temp_celsius: Target freezing temperature (°C)
                - cop_freezing_system: Coefficient of performance for freezing system
            - start_temp (float): Initial temperature of product (°C)
            - elec_price (tuple): Electricity price tuple, [2] is price in USD/MJ
            - co2_factor (float): CO2 emission factor for electricity (kg CO2/kWh)
            - facility_capacity_arg (float): Facility capacity in tons per day
            - start_country_name_arg (str): Country name for carbon tax
            - carbon_tax_per_ton_co2_dict_arg (dict): Carbon tax rates by country

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Operational costs in USD (electricity)
            - capex_money (float): Amortized capital costs in USD
            - carbon_tax_money (float): Carbon tax costs in USD
            - energy (float): Total energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Remaining mass after losses (0.5% spoilage)
            - loss (float): Mass lost during freezing (0.5% spoilage rate)
            - insurance_cost (float): Insurance costs (0 for this process)

    Notes:
        - Assumes 0.5% product loss during freezing
        - Uses power law scaling for capital cost estimation
        - Conversion factor 0.2778 used to convert MJ to kWh (1/3.6)
    """
    params, start_temp, elec_price, co2_factor, facility_capacity_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg = args

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

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

    return opex_money, capex_money, carbon_tax_money, energy, emissions, A - loss, loss, 0


def food_road_transport(A, args):
    """
    Calculate costs, energy, and emissions for refrigerated road transport of food.

    This function models refrigerated truck transport (reefer trucks) including:
    - Fuel consumption for propulsion and refrigeration
    - Driver labor costs
    - Vehicle maintenance costs
    - Amortized truck capital costs
    - Temperature-dependent spoilage rates

    Args:
        A (float): Mass of food product in kg
        args (tuple): Contains:
            - params (dict): Food parameters with general_params containing:
                - spoilage_rate_per_day: Base spoilage rate (fraction/day)
                - target_temp_celsius: Target refrigeration temperature (°C)
                - cargo_per_truck_kg: Truck capacity in kg
                - reefer_truck_fuel_consumption_L_hr: Reefer fuel consumption (L/hr)
            - distance (float): Transport distance in km
            - duration_mins (float): Transport duration in minutes
            - diesel_price (float): Diesel price (USD/gallon)
            - hh_diesel (float): Higher heating value of diesel (MJ/gallon)
            - dens_diesel (float): Density of diesel (kg/gallon)
            - co2_diesel (float): CO2 emissions factor for diesel (kg CO2/gallon)
            - ambient_temp (float): Ambient temperature (°C)
            - driver_daily_salary_arg (float): Driver daily salary (USD/day)
            - annual_working_days_arg (float): Annual working days
            - maintenance_cost_per_km_truck_arg (float): Maintenance cost (USD/km)
            - truck_capex_params_arg (list): Truck capital cost parameters
            - country_of_road_transport_arg (str): Country name for carbon tax
            - carbon_tax_per_ton_co2_dict_arg (dict): Carbon tax rates

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Total operational costs (fuel, driver, maintenance)
            - capex_money (float): Amortized truck capital costs
            - carbon_tax_money (float): Carbon tax costs
            - energy (float): Total energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Remaining mass after spoilage
            - loss (float): Mass lost to spoilage during transport
            - insurance_cost (float): Insurance costs (0 for this process)

    Notes:
        - Assumes truck fuel economy of 4.0 km/L
        - Spoilage rate increases with temperature differential
        - Uses 3.78541 L per gallon conversion
        - Assumes 330 annual trips for capital cost amortization
    """
    params, distance, duration_mins, diesel_price, hh_diesel, dens_diesel, co2_diesel, ambient_temp, driver_daily_salary_arg, annual_working_days_arg, maintenance_cost_per_km_truck_arg, truck_capex_params_arg, country_of_road_transport_arg, carbon_tax_per_ton_co2_dict_arg = args

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

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
    capex_per_truck_trip_usd = annual_truck_cost_usd / 330  # Assuming 330 annual trips
    capex_money += capex_per_truck_trip_usd * num_trucks

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_road_transport_arg, 0) * (emissions / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, energy, emissions, A - loss, loss, 0


def food_precooling_process(A, args):
    """
    Calculate costs, energy, and emissions for pre-cooling fresh produce.

    Pre-cooling is the rapid removal of field heat from fresh produce immediately after
    harvest to extend shelf life and maintain quality. This function calculates:
    - Sensible heat removal based on temperature differential
    - Energy consumption based on COP of cooling system
    - Capital costs for pre-cooling facility
    - Moisture loss during pre-cooling

    Args:
        A (float): Mass of food product in kg
        args (tuple): Contains:
            - precool_params (dict): Pre-cooling parameters including:
                - initial_field_heat_celsius: Initial temperature of harvested product (°C)
                - target_precool_temperature_celsius: Target temperature after pre-cooling (°C)
                - specific_heat_fresh_mj_kgK: Specific heat of fresh product (MJ/kg·K)
                - cop_precooling_system: Coefficient of performance for pre-cooling
                - moisture_loss_percent: Fractional moisture loss during pre-cooling
            - elec_price (tuple): Electricity price tuple, [2] is price in USD/MJ
            - co2_factor (float): CO2 emission factor for electricity (kg CO2/kWh)
            - facility_capacity_arg (float): Facility capacity in tons per day
            - start_country_name_arg (str): Country name for carbon tax
            - carbon_tax_per_ton_co2_dict_arg (dict): Carbon tax rates by country

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Operational costs (electricity)
            - capex_money (float): Amortized capital costs
            - carbon_tax_money (float): Carbon tax costs
            - energy (float): Total energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Remaining mass after moisture loss
            - loss (float): Mass lost as moisture during pre-cooling
            - insurance_cost (float): Insurance costs (0 for this process)

    Notes:
        - Returns zeros if temperature differential is <= 0 (no cooling needed)
        - Moisture loss is a fixed percentage of input mass
        - Capital costs scale with facility capacity using power law
    """
    precool_params, elec_price, co2_factor, facility_capacity_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg = args

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    delta_T = (precool_params['initial_field_heat_celsius'] -
            precool_params['target_precool_temperature_celsius'])

    if delta_T <= 0:
        return 0, 0, 0, 0, 0, A, 0, 0

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

    return opex_money, capex_money, carbon_tax_money, energy_mj, emissions, A - loss, loss, 0


def calculate_ca_energy_kwh(A, food_params, duration_hrs):
    """
    Calculate energy consumption for Controlled Atmosphere (CA) systems.

    Controlled atmosphere storage modifies the composition of air around produce to
    extend shelf life by reducing respiration rates. This function calculates energy
    needed for:
    - Nitrogen generation to displace oxygen
    - CO2 scrubbing to remove excess CO2 from respiration
    - Humidity control to maintain optimal moisture levels
    - Base control system power

    Args:
        A (float): Mass of food product in kg
        food_params (dict): Food parameters containing:
            - process_flags (dict): Contains 'needs_controlled_atmosphere' boolean
            - ca_params (dict): CA system parameters:
                - container_leakage_rate_ach: Container air changes per hour
                - n2_generator_efficiency_kwh_per_m3: N2 generation energy (kWh/m³)
                - respiration_rate_ml_co2_per_kg_hr: CO2 production rate (mL/(kg·hr))
                - co2_scrubber_efficiency_kwh_per_kg_co2: CO2 scrubbing energy (kWh/kg)
                - humidifier_efficiency_kwh_per_liter: Humidification energy (kWh/L)
                - base_control_power_kw: Base control system power (kW)
            - general_params (dict): Contains:
                - cargo_per_truck_kg: Container capacity in kg
        duration_hrs (float): Duration of CA operation in hours

    Returns:
        float: Total energy consumption in kWh

    Notes:
        - Returns 0 if CA is not needed for the product
        - Assumes standard 76 m³ container volume
        - CO2 density assumed as 1.98 kg/m³
        - Humidity addition rate: 2 liters per container per day
    """
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
    """
    Calculate costs, energy, and emissions for maritime transport of refrigerated food.

    This function models ocean transport in reefer containers, including:
    - Refrigeration energy (reefer container power)
    - Controlled atmosphere (CA) system energy if required
    - Ship propulsion fuel allocation based on container share
    - Voyage overhead costs (crew, insurance, canal fees, port fees)
    - Spoilage during transport (with CA adjustment if applicable)
    - Carbon taxes including EU ETS for European destinations

    Args:
        A (float): Mass of food product in kg
        args (tuple): Contains:
            - food_params (dict): Food parameters with general_params, process_flags, ca_params
            - duration_hrs (float): Voyage duration in hours
            - selected_fuel (dict): Marine fuel parameters (price, emissions factor, HHV, SFOC)
            - avg_ship_kw (float): Average ship power in kW
            - calculate_voyage_overheads_helper_arg (function): Function to calculate voyage overheads
            - selected_ship_params_arg (dict): Ship parameters
            - canal_transits_arg (list): List of canal transits
            - port_regions_arg (list): Port regions for fees
            - end_country_name_arg (str): Destination country name
            - carbon_tax_per_ton_co2_dict_arg (dict): Carbon tax rates by country
            - eu_member_countries_arg (list): List of EU member countries
            - shipment_size_containers_arg (int): Number of containers in shipment
            - total_ship_container_capacity_arg (int): Total ship container capacity

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Operational costs (reefer service, fuel, overheads)
            - capex_money (float): Capital costs (ship amortization share)
            - carbon_tax_money (float): Carbon tax costs (including EU ETS if applicable)
            - energy (float): Total energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Remaining mass after spoilage
            - loss (float): Mass lost to spoilage during voyage
            - insurance_cost (float): Insurance costs (0 - handled separately)

    Notes:
        - Costs and emissions are allocated proportionally based on container share
        - EU destinations incur 50% EU ETS charge on emissions
        - CA-enabled products have reduced spoilage rates
        - Calls calculate_single_reefer_service_cost for per-container reefer costs
    """
    food_params, duration_hrs, selected_fuel, avg_ship_kw, calculate_voyage_overheads_helper_arg, selected_ship_params_arg, canal_transits_arg, port_regions_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg, eu_member_countries_arg, shipment_size_containers_arg, total_ship_container_capacity_arg = args

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    reefer_service_cost_per_container, _, _, reefer_service_energy_per_container, reefer_service_emissions_per_container, _, _, _ = calculate_single_reefer_service_cost(duration_hrs, food_params)
    total_reefer_cost_shipment = reefer_service_cost_per_container * shipment_size_containers_arg
    total_reefer_energy_shipment = reefer_service_energy_per_container * shipment_size_containers_arg
    total_reefer_emissions_shipment = reefer_service_emissions_per_container * shipment_size_containers_arg

    total_ship_propulsion_work_kwh = avg_ship_kw * duration_hrs
    total_ship_propulsion_fuel_kg = (total_ship_propulsion_work_kwh * selected_fuel['sfoc_g_per_kwh']) / 1000.0
    total_ship_propulsion_cost = (total_ship_propulsion_fuel_kg / 1000.0) * selected_fuel['price_usd_per_ton']
    total_ship_propulsion_emissions = total_ship_propulsion_fuel_kg * selected_fuel['co2_emissions_factor_kg_per_kg_fuel']
    total_ship_propulsion_energy_mj = total_ship_propulsion_fuel_kg * selected_fuel['hhv_mj_per_kg']

    propulsion_cost_for_shipment = (total_ship_propulsion_cost / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
    propulsion_emissions_for_shipment = (total_ship_propulsion_emissions / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
    propulsion_energy_for_shipment = (total_ship_propulsion_energy_mj / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0

    opex_money += total_reefer_cost_shipment + propulsion_cost_for_shipment
    total_energy_mj = total_reefer_energy_shipment + propulsion_energy_for_shipment
    total_emissions = total_reefer_emissions_shipment + propulsion_emissions_for_shipment

    voyage_duration_days = duration_hrs / 24.0
    voyage_opex_overheads, voyage_capex_overheads = calculate_voyage_overheads_helper_arg(voyage_duration_days, selected_ship_params_arg, canal_transits_arg, port_regions_arg)

    # Apportion overheads based on container share
    opex_money_for_shipment = (voyage_opex_overheads / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
    capex_money_for_shipment = (voyage_capex_overheads / total_ship_container_capacity_arg) * shipment_size_containers_arg if total_ship_container_capacity_arg > 0 else 0
    opex_money += opex_money_for_shipment
    capex_money += capex_money_for_shipment

    duration_days = duration_hrs / 24.0
    spoilage_rate = food_params['general_params']['spoilage_rate_per_day']
    if food_params['process_flags'].get('needs_controlled_atmosphere'):
        spoilage_rate = food_params['general_params']['spoilage_rate_ca_per_day']
    loss = A * spoilage_rate * duration_days

    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (total_emissions / 1000)
    carbon_tax_money += carbon_tax

    if end_country_name_arg in eu_member_countries_arg:
        eu_ets_emissions_tons = (total_emissions / 1000) * 0.50
        eu_ets_tax = eu_ets_emissions_tons * carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0)
        carbon_tax_money += eu_ets_tax

    return opex_money, capex_money, carbon_tax_money, total_energy_mj, total_emissions, A - loss, loss, 0


def food_cold_storage(A, args):
    """
    Calculate costs, energy, and emissions for cold storage of food products.

    This function models refrigerated warehouse storage, including:
    - Energy consumption based on product volume and storage duration
    - Temperature adjustment factors based on ambient conditions
    - Capital costs for cold storage facilities
    - Spoilage losses during storage (with CA adjustment if applicable)

    Args:
        A (float): Mass of food product in kg
        args (tuple): Contains:
            - params (dict): Food parameters with general_params and process_flags
            - storage_days (float): Duration of storage in days
            - elec_price (tuple): Electricity price tuple, [2] is price in USD/MJ
            - co2_factor (float): CO2 emission factor for electricity (kg CO2/kWh)
            - ambient_temp (float): Ambient temperature (°C)
            - facility_capacity_arg (float): Facility capacity in tons per day
            - country_of_storage_arg (str): Country name for carbon tax
            - carbon_tax_per_ton_co2_dict_arg (dict): Carbon tax rates by country

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Operational costs (electricity)
            - capex_money (float): Amortized capital costs
            - carbon_tax_money (float): Carbon tax costs
            - energy (float): Total energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Remaining mass after spoilage
            - loss (float): Mass lost to spoilage during storage
            - insurance_cost (float): Insurance costs (0 for this process)

    Notes:
        - Base energy factor: 0.5 kWh/m³/day
        - Temperature adjustment: 3% increase per degree above 20°C
        - Minimum temperature adjustment factor: 0.5
        - Product volume calculated using density from general_params
        - Spoilage rate varies with CA availability
    """
    params, storage_days, elec_price, co2_factor, ambient_temp, facility_capacity_arg, country_of_storage_arg, carbon_tax_per_ton_co2_dict_arg = args

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

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

    return opex_money, capex_money, carbon_tax_money, energy_mj, emissions, A - loss, loss, 0


def calculate_food_infra_capex(process_name, capacity_tons_per_day, A, storage_days):
    """
    Calculate amortized capital costs for food processing infrastructure.

    This function estimates the capital cost per kg for various food processing facilities
    using power law scaling based on capacity. It covers:
    - Pre-cooling facilities
    - Freezing facilities
    - Cold storage warehouses

    The capital costs are annualized (10% factor) and then divided by annual throughput
    to obtain a cost per kg processed.

    Args:
        process_name (str): Type of facility - "precool", "freezing", or "cold_storage"
        capacity_tons_per_day (float): Daily processing capacity in tons
            (used for precool/freezing, required but not used for cold_storage)
        A (float): Total mass of product in kg (used for cold_storage)
        storage_days (float): Average storage duration in days (used for cold_storage only)

    Returns:
        float: Amortized capital cost per kg of product in USD/kg

    Cost Models:
        Pre-cool:
            - Base cost: $1.5M for 50 tons/day reference capacity
            - Scaling exponent: 0.6
        Freezing:
            - Base cost: $3M for 30 tons/day reference capacity
            - Scaling exponent: 0.65
        Cold Storage:
            - Base cost: $0.82M for 5,000 tons reference capacity
            - Scaling exponent: 0.7

    Notes:
        - Assumes 10% annualization factor for capital recovery
        - Assumes 330 operating days per year
        - For cold storage, calculates cycles per year from storage duration
        - Returns 0 if process_name not recognized or throughput is zero
        - Source: Based on general industry capital cost estimates for food
          processing and cold chain logistics
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


def calculate_single_reefer_service_cost(duration_hrs, food_params):
    """
    Calculate costs and emissions for a single reefer container service.

    This helper function calculates the energy, fuel consumption, costs, and emissions
    for operating a refrigerated (reefer) shipping container for a given duration.
    It includes:
    - Controlled atmosphere (CA) system energy if required
    - Base reefer refrigeration power
    - Auxiliary fuel consumption for power generation

    Args:
        duration_hrs (float): Duration of reefer service in hours
        food_params (dict): Food parameters containing:
            - process_flags (dict): Contains 'needs_controlled_atmosphere' boolean
            - general_params (dict): Contains:
                - reefer_container_power_kw: Reefer power consumption (kW)
            - ca_params (dict): CA system parameters (if CA is needed)

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, energy, emissions,
                current_weight, loss, insurance_cost)
            - opex_money (float): Operating cost for reefer service in USD
            - capex_money (float): Capital costs (0 - not attributed at this level)
            - carbon_tax_money (float): Carbon tax (0 - handled at higher level)
            - energy (float): Total energy consumed in MJ
            - emissions (float): CO2 equivalent emissions in kg
            - current_weight (float): Placeholder value of 1 (per-container basis)
            - loss (float): No spoilage calculated at this micro-level (0)
            - insurance_cost (float): Insurance (0 - handled separately)

    Notes:
        - Assumes auxiliary generator SFOC of 200 g/kWh
        - Uses auxiliary_fuel_params for fuel price, HHV, and emissions factor
        - auxiliary_fuel_params must be available in the calling scope
        - This is a "per container" calculation (current_weight = 1)
        - Spoilage is not calculated at this granular level
        - Carbon tax is handled at the food_sea_transport level
    """
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

    return opex_money, capex_money, carbon_tax_money, energy_mj, emissions, current_weight, loss, 0
