"""
models/orchestration.py

Orchestration functions for LCA calculations.

This module contains high-level orchestration functions that coordinate multiple process steps:
1. optimization_chem_weight - Optimizes chemical weight using scipy.optimize.minimize
2. total_chem_base - Orchestrates complete fuel/chemical supply chain LCA
3. total_food_lca - Orchestrates complete food supply chain LCA

These functions were extracted from app.py to improve code organization and modularity.
They call process functions from fuel_processes and food_processes modules.

Extracted from app.py (lines 1173-1987) on 2025-10-29.
"""

from scipy.optimize import minimize

# Import all necessary constants from constants.py
from constants import (
    IMPORT_TARIFF_RATES_DICT,
    ANNUAL_FINANCING_RATE,
    BROKERAGE_AND_AGENT_FEE_USD,
    SAFETY_CERTIFICATION_COST_PER_KG,
    FOOD_INSPECTION_COST_PER_SHIPMENT,
    CONTINGENCY_PERCENTAGE,
    MAINTENANCE_COST_PER_KM_TRUCK,
    EU_MEMBER_COUNTRIES,
    ANNUAL_WORKING_DAYS
)
# Alias for backward compatibility
annual_working_days = ANNUAL_WORKING_DAYS

# Import fuel process functions
from models.fuel_processes import (
    site_A_chem_production,
    site_A_chem_liquification,
    fuel_pump_transfer,
    fuel_road_transport,
    fuel_storage,
    chem_loading_to_ship,
    port_to_port
)

# Import food process functions
from models.food_processes import (
    food_harvest_and_prep,
    food_precooling_process,
    food_freezing_process,
    food_road_transport,
    food_cold_storage,
    food_sea_transport,
    calculate_ca_energy_kwh
)

# Import helper functions
from models.insurance_model import calculate_total_insurance_cost
from models.capex_calculations import calculate_food_infra_capex


def optimization_chem_weight(A_initial_guess, args_for_optimizer_tuple, target_weight):
    """
    Optimization function used by scipy.optimize.minimize to find the initial chemical weight
    needed to deliver a target weight after accounting for all losses in the supply chain.

    This function runs through a subset of the supply chain processes (up to ship loading)
    to calculate total losses, then returns the absolute difference between the remaining
    weight and the target weight. The optimizer minimizes this difference.

    Args:
        A_initial_guess (list): List containing initial weight guess [weight_kg]
        args_for_optimizer_tuple (tuple): Contains:
            - user_define_params (list): User-defined parameters for fuel type, BOG handling, etc.
            - process_funcs_for_optimization (list): Process functions to run during optimization
            - all_shared_params_tuple (tuple): All shared parameters for process functions
        target_weight (float): Target delivery weight in kg

    Returns:
        float: Absolute difference between final weight and target weight (to be minimized)

    Notes:
        - This function is called repeatedly by scipy's minimize() optimizer
        - It simulates a partial supply chain to estimate losses
        - The optimizer finds the initial weight that results in the target final weight
    """
    user_define_params, process_funcs_for_optimization, all_shared_params_tuple = args_for_optimizer_tuple

    (LH2_plant_capacity_opt, EIM_liquefication_opt, specific_heat_chem,
    start_local_temperature_opt, boiling_point_chem, latent_H_chem,
    COP_liq_dyn, start_electricity_price_opt, CO2e_start_opt, GWP_chem,
    V_flowrate, number_of_cryo_pump_load_truck_site_A_opt,
    number_of_cryo_pump_load_storage_port_A_opt, number_of_cryo_pump_load_ship_port_A_opt,
    dBOR_dT, BOR_loading, BOR_unloading, head_pump_opt, pump_power_factor_opt,
    EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt,
    pipe_thick_opt, COP_refrig, EIM_refrig_eff_opt, pipe_metal_specific_heat, COP_cooldown_dyn,
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
    MAINTENANCE_COST_PER_KM_TRUCK,
    hydrogen_production_cost_opt,
    start_country_name_opt, start_port_country_name_opt, CARBON_TAX_PER_TON_CO2_DICT,
    port_regions_opt, selected_fuel_name_opt, searoute_coor_opt, port_to_port_duration_opt,
    storage_area, ship_tank_metal_thickness, ship_tank_insulation_thickness,
    ship_number_of_tanks, ship_tank_metal_density, ship_tank_insulation_density,
    ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat
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

        if func_to_call.__name__ == "site_A_chem_production":
            process_args_for_current_func = (
                GWP_chem, hydrogen_production_cost_opt, start_country_name_opt,
                CARBON_TAX_PER_TON_CO2_DICT, selected_fuel_name_opt,
                searoute_coor_opt, port_to_port_duration_opt
            )

        elif func_to_call.__name__ == "site_A_chem_liquification":
            process_args_for_current_func = (
                LH2_plant_capacity_opt, EIM_liquefication_opt, specific_heat_chem,
                start_local_temperature_opt, boiling_point_chem, latent_H_chem,
                COP_liq_dyn, start_electricity_price_opt, CO2e_start_opt, GWP_chem,
                calculate_liquefaction_capex_helper_opt, start_country_name_opt, CARBON_TAX_PER_TON_CO2_DICT
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
                    country_for_transfer, CARBON_TAX_PER_TON_CO2_DICT
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
                    country_for_transfer, CARBON_TAX_PER_TON_CO2_DICT
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
                MAINTENANCE_COST_PER_KM_TRUCK, truck_capex_params_opt,
                country_for_road, CARBON_TAX_PER_TON_CO2_DICT
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
                calculate_storage_capex_helper_opt, country_for_storage, CARBON_TAX_PER_TON_CO2_DICT
            )

        elif func_to_call.__name__ == "chem_loading_to_ship":
            # Note: This references some variables not in all_shared_params_tuple
            # These would need to be added if this function is called during optimization
            # For now, keeping the structure as-is from original code
            process_args_for_current_func = (
                V_flowrate, number_of_cryo_pump_load_ship_port_A_opt, dBOR_dT,
                start_local_temperature_opt, BOR_loading, liquid_chem_density, head_pump_opt,
                pump_power_factor_opt, EIM_cryo_pump_opt, ss_therm_cond_opt, pipe_length_opt, pipe_inner_D_opt,
                pipe_thick_opt, boiling_point_chem, EIM_refrig_eff_opt, start_electricity_price_opt,
                CO2e_start_opt, GWP_chem, storage_area, ship_tank_metal_thickness,
                ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density,
                ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat,
                COP_cooldown_dyn, COP_refrig, ship_number_of_tanks, pipe_metal_specific_heat,
                calculate_loading_unloading_capex_helper_opt, start_country_name_opt, CARBON_TAX_PER_TON_CO2_DICT
            )

        # Call the current process function with its tailored arguments
        # Update the return signature of func_to_call to include carbon_tax_money and insurance_cost
        opex_m, capex_m, carbon_tax_m, Y_energy, Z_emission, X, S_bog_loss, insurance_m = func_to_call(X,
                                    user_define_params[1],
                                    user_define_params[2],
                                    user_define_params[3],
                                    user_define_params[4],
                                    user_define_params[5],
                                    process_args_for_current_func)

    return abs(X - target_weight)


def constraint(A, target_weight):
    """
    Constraint function for optimization ensuring weight is not less than target.

    Args:
        A (list): List containing weight value [weight_kg]
        target_weight (float): Target weight in kg

    Returns:
        float: Difference (A[0] - target_weight), must be >= 0 for valid solution
    """
    return A[0] - target_weight


def total_chem_base(A_optimized_chem_weight, B_fuel_type_tc, C_recirculation_BOG_tc,
                    D_truck_apply_tc, E_storage_apply_tc, F_maritime_apply_tc, carbon_tax_per_ton_co2_dict_tc,
                    selected_fuel_name_tc, searoute_coor_tc, port_to_port_duration_tc,
                    start_is_port, end_is_port,  # NEW: Port detection flags
                    # All parameters needed from parent scope
                    GWP_chem, hydrogen_production_cost, start_country_name,
                    LH2_plant_capacity, EIM_liquefication, specific_heat_chem, start_local_temperature,
                    boiling_point_chem, latent_H_chem, COP_liq_dyn, start_electricity_price, CO2e_start,
                    calculate_liquefaction_capex, V_flowrate, number_of_cryo_pump_load_truck_site_A,
                    dBOR_dT, BOR_loading, liquid_chem_density, head_pump, pump_power_factor,
                    EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick,
                    COP_refrig, EIM_refrig_eff, start_port_country_name,
                    number_of_cryo_pump_load_storage_port_A, BOR_unloading,
                    calculate_loading_unloading_capex, road_delivery_ener, HHV_chem,
                    chem_in_truck_weight, truck_economy, distance_A_to_port, HHV_diesel,
                    diesel_density, diesel_price_start, truck_tank_radius, truck_tank_length,
                    truck_tank_metal_thickness, metal_thermal_conduct, truck_tank_insulator_thickness,
                    insulator_thermal_conduct, OHTC_ship, COP_refrig_alias, duration_A_to_port,
                    BOR_truck_trans, diesel_engine_eff, EIM_truck_eff, CO2e_diesel,
                    BOG_recirculation_truck, fuel_cell_eff, EIM_fuel_cell, LHV_chem,
                    driver_daily_salary_start, truck_capex_params,
                    storage_volume, start_local_temperature_alias, BOR_land_storage, storage_time_A,
                    storage_radius, tank_metal_thickness, tank_insulator_thickness,
                    BOG_recirculation_storage, calculate_storage_capex,
                    number_of_cryo_pump_load_ship_port_A, pipe_metal_specific_heat,
                    storage_area, ship_tank_metal_thickness, ship_tank_insulation_thickness,
                    ship_tank_metal_density, ship_tank_insulation_density, ship_tank_metal_specific_heat,
                    ship_tank_insulation_specific_heat, COP_cooldown_dyn, ship_number_of_tanks,
                    end_local_temperature, selected_marine_fuel_params, port_to_port_duration,
                    dBOR_dT_alias, BOR_ship_trans, BOG_recirculation_mati_trans,
                    avg_ship_power_kw, GWP_N2O, calculate_voyage_overheads,
                    selected_ship_params, canal_transits, port_regions, end_country_name,
                    end_port_country_name, number_of_cryo_pump_load_storage_port_B,
                    end_electricity_price, CO2e_end, end_local_temperature_alias,
                    number_of_cryo_pump_load_truck_port_B, distance_port_to_B,
                    diesel_price_end, duration_port_to_B, driver_daily_salary_end,
                    number_of_cryo_pump_load_storage_site_B, storage_time_B, storage_time_C,
                    label_map):
    """
    Orchestrate complete fuel/chemical supply chain Life Cycle Assessment (LCA).

    This function coordinates all process steps from production through delivery, including:
    - Chemical production and liquefaction
    - Pump transfers at multiple stages
    - Road transport (start and end legs)
    - Storage at ports and sites
    - Ship loading and marine transport
    - Additional costs (tariffs, financing, certification, etc.)

    Args:
        A_optimized_chem_weight (float): Optimized initial chemical weight in kg
        B_fuel_type_tc (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        C_recirculation_BOG_tc (int): BOG recirculation strategy
        D_truck_apply_tc (bool): Apply truck BOG recirculation
        E_storage_apply_tc (bool): Apply storage BOG recirculation
        F_maritime_apply_tc (bool): Apply maritime BOG recirculation
        carbon_tax_per_ton_co2_dict_tc (dict): Carbon tax rates by country (USD/ton CO2)
        selected_fuel_name_tc (str): Name of selected fuel
        searoute_coor_tc (list): Sea route coordinates for insurance calculation
        port_to_port_duration_tc (float): Port-to-port duration in hours
        start_is_port (bool): True if start location is a port city (skips inland transport)
        end_is_port (bool): True if end location is a port city (skips inland transport)
        ... (many more parameters from parent scope - see function signature)

    Returns:
        tuple: (final_total_result_tc, data_results_list)
            - final_total_result_tc (list): [total_cost, total_energy, total_emissions, final_weight]
            - data_results_list (list): List of lists containing detailed results for each process step
                Each row: [label, opex, capex, carbon_tax, energy, emissions, weight, bog_loss]

    Notes:
        - This function processes the complete supply chain sequentially
        - Accumulates costs, energy, emissions, and tracks weight changes
        - Adds overhead costs (tariffs, financing, certification, contingency)
        - Separates insurance costs into dedicated rows for transparency
        - Conditionally skips truck transport steps if start/end locations are ports
    """
    # Build process sequence conditionally based on port detection
    funcs_sequence = [
        site_A_chem_production,
        site_A_chem_liquification,
    ]

    # Start location transport to port (skip if start is already a port)
    if not start_is_port:
        funcs_sequence.extend([
            (fuel_pump_transfer, 'siteA_to_truck'),
            (fuel_road_transport, 'start_leg'),
            (fuel_pump_transfer, 'portA_to_storage'),
        ])

    # Storage at starting port and loading to ship
    funcs_sequence.extend([
        (fuel_storage, 'port_A'),
        chem_loading_to_ship,
        port_to_port,
        (fuel_pump_transfer, 'ship_to_portB'),
        (fuel_storage, 'port_B'),
    ])

    # End location transport from port (skip if end is already a port)
    if not end_is_port:
        funcs_sequence.extend([
            (fuel_pump_transfer, 'portB_to_truck'),
            (fuel_road_transport, 'end_leg'),
            (fuel_pump_transfer, 'truck_to_siteB'),
            (fuel_storage, 'site_B'),
        ])

    # Final use
    funcs_sequence.append((fuel_pump_transfer, 'siteB_to_use'))

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
        if func_to_call.__name__ == "site_A_chem_production":
            process_args_for_this_call_tc = (
                GWP_chem, hydrogen_production_cost, start_country_name, carbon_tax_per_ton_co2_dict_tc,
                selected_fuel_name_tc, searoute_coor_tc, port_to_port_duration_tc
            )
        elif func_to_call.__name__ == "site_A_chem_liquification":
            process_args_for_this_call_tc = (LH2_plant_capacity, EIM_liquefication, specific_heat_chem, start_local_temperature, boiling_point_chem, latent_H_chem, COP_liq_dyn, start_electricity_price, CO2e_start, GWP_chem, calculate_liquefaction_capex, start_country_name, carbon_tax_per_ton_co2_dict_tc)
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
            process_args_for_this_call_tc = (V_flowrate, number_of_cryo_pump_load_ship_port_A,
                                             dBOR_dT, start_local_temperature, BOR_loading, liquid_chem_density,
                                             head_pump, pump_power_factor, EIM_cryo_pump, ss_therm_cond, pipe_length,
                                             pipe_inner_D, pipe_thick, boiling_point_chem, EIM_refrig_eff,
                                             start_electricity_price, CO2e_start, GWP_chem, storage_area,
                                             ship_tank_metal_thickness, ship_tank_insulation_thickness,
                                             ship_tank_metal_density, ship_tank_insulation_density,
                                             ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat,
                                             COP_cooldown_dyn, COP_refrig, ship_number_of_tanks, pipe_metal_specific_heat,
                                             calculate_loading_unloading_capex, start_country_name, carbon_tax_per_ton_co2_dict_tc)
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
                calculate_voyage_overheads,
                selected_ship_params, canal_transits, port_regions, end_country_name, carbon_tax_per_ton_co2_dict_tc,
                EU_MEMBER_COUNTRIES
            )
        elif func_to_call.__name__ == "chem_convert_to_H2":
            # This function is not in the default funcs_sequence but kept for completeness
            # Would need: mass_conversion_to_H2, eff_energy_chem_to_H2, energy_chem_to_H2
            pass

        opex_money, capex_money, carbon_tax_money_current, Y_energy, Z_emission, R_current_chem, S_bog_loss, insurance_money_current = \
            func_to_call(R_current_chem, B_fuel_type_tc, C_recirculation_BOG_tc, D_truck_apply_tc,
                        E_storage_apply_tc, F_maritime_apply_tc, process_args_for_this_call_tc)

        unique_key = func_to_call.__name__
        if leg_type:
            unique_key = f"{func_to_call.__name__}_{leg_type}"
        elif transfer_context:
            unique_key = f"{func_to_call.__name__}_{transfer_context}"
        elif storage_location_type:
            unique_key = f"{func_to_call.__name__}_{storage_location_type}"
        descriptive_label = label_map.get(unique_key, unique_key)
        data_results_list.append([descriptive_label, opex_money, capex_money, carbon_tax_money_current, Y_energy, Z_emission, R_current_chem, S_bog_loss])

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
            insurance_money_current = 0 # Reset for this specific row if it was production
        total_opex_money_tc += opex_money
        total_capex_money_tc += capex_money
        total_carbon_tax_money_tc += carbon_tax_money_current
        total_ener_consumed_tc += Y_energy
        total_G_emission_tc += Z_emission
        total_S_bog_loss_tc += S_bog_loss

    # ========================================================================
    # TRANSPORT SERVICE COSTS END HERE
    # Everything above represents actual transport/logistics service costs
    # ========================================================================

    # Calculate transport-only subtotal (for benchmarking against pure freight rates)
    transport_service_total = total_opex_money_tc + total_capex_money_tc + total_carbon_tax_money_tc + total_insurance_money_tc

    # ========================================================================
    # IMPORT/COMMERCIAL COSTS (NOT TRANSPORT SERVICE COSTS)
    # The following costs are commercial/regulatory, not freight service costs
    # Exclude these when comparing to transport-only benchmarks
    # ========================================================================

    # 1. Calculate the CIF Value (Cost of Goods + Insurance + Freight)
    initial_cargo_value = A_optimized_chem_weight * hydrogen_production_cost
    # The freight cost is the sum of all transport-related costs
    freight_and_insurance_cost = total_opex_money_tc + total_capex_money_tc + total_carbon_tax_money_tc + total_insurance_money_tc
    cif_value = initial_cargo_value + freight_and_insurance_cost

    # 2. Calculate Tariff Cost (IMPORT DUTY - NOT A TRANSPORT COST)
    tariff_rate = IMPORT_TARIFF_RATES_DICT.get(end_country_name, 0.05)
    tariff_cost = cif_value * tariff_rate
    data_results_list.append(["Import Tariffs & Duties", tariff_cost, 0.0, 0.0, 0.0, 0.0, R_current_chem, 0.0])

    # 3. Calculate Financing Cost (COMMERCIAL COST - NOT A TRANSPORT COST)
    # This is working capital cost on cargo value, not freight service cost
    total_duration_days = (duration_A_to_port / 1440) + (port_to_port_duration / 24) + (duration_port_to_B / 1440) + storage_time_A + storage_time_B + storage_time_C
    financing_cost = initial_cargo_value * (ANNUAL_FINANCING_RATE / 365) * total_duration_days
    data_results_list.append(["Financing Costs", financing_cost, 0.0, 0.0, 0.0, 0.0, R_current_chem, 0.0])

    # 4. Add Brokerage & Agent Fees
    data_results_list.append(["Brokerage & Agent Fees", BROKERAGE_AND_AGENT_FEE_USD, 0.0, 0.0, 0.0, 0.0, R_current_chem, 0.0])

    # 5. Calculate Safety Certification Cost
    cert_params = SAFETY_CERTIFICATION_COST_PER_KG.get(B_fuel_type_tc, {})
    base_cost = cert_params.get('base_cost_usd', 0)
    per_kg_rate = cert_params.get('per_kg_rate', 0)
    threshold = cert_params.get('threshold_kg', 0)

    certification_cost = base_cost
    if A_optimized_chem_weight > threshold:
        certification_cost += (A_optimized_chem_weight - threshold) * per_kg_rate

    data_results_list.append(["Safety Certifications", certification_cost, 0.0, 0.0, 0.0, 0.0, R_current_chem, 0.0])

    # 6. Calculate Contingency Cost
    contingency_cost = (total_opex_money_tc + total_carbon_tax_money_tc + total_insurance_money_tc) * CONTINGENCY_PERCENTAGE
    data_results_list.append(["Contingency (10%)", contingency_cost, 0.0, 0.0, 0.0, 0.0, R_current_chem, 0.0])

    # --- FINAL COST CALCULATIONS END HERE ---

    # Now update the final totals with these new costs
    total_opex_money_tc += (tariff_cost + financing_cost + BROKERAGE_AND_AGENT_FEE_USD + certification_cost + contingency_cost)
    final_total_money = total_opex_money_tc + total_capex_money_tc + total_carbon_tax_money_tc + total_insurance_money_tc
    final_total_result_tc = [final_total_money, total_ener_consumed_tc, total_G_emission_tc, R_current_chem]

    # Update the 'TOTAL' row with the correct final totals
    data_results_list.append(["TOTAL", total_opex_money_tc, total_capex_money_tc, total_carbon_tax_money_tc, total_ener_consumed_tc, total_G_emission_tc, R_current_chem, total_S_bog_loss_tc])

    return final_total_result_tc, data_results_list


def total_food_lca(initial_weight, food_params, carbon_tax_per_ton_co2_dict_tl, HHV_diesel_tl, diesel_density_tl, CO2e_diesel_tl,
                   food_name_tl, searoute_coor_tl, port_to_port_duration_tl, shipment_size_containers,
                   start_is_port, end_is_port,  # NEW: Port detection flags
                   # All parameters needed from parent scope
                   start, start_port_name, end_port_name, end,
                   price_start, start_country_name, facility_capacity,
                   start_electricity_price, CO2e_start, start_local_temperature,
                   distance_A_to_port, duration_A_to_port, diesel_price_start,
                   driver_daily_salary_start, truck_capex_params,
                   storage_time_A, start_port_electricity_price, start_port_country_name,
                   port_to_port_duration, selected_marine_fuel_params, avg_ship_power_kw,
                   calculate_voyage_overheads, selected_ship_params, canal_transits,
                   port_regions, end_country_name, total_ship_container_capacity,
                   storage_time_B, end_port_electricity_price, end_local_temperature,
                   end_port_country_name, distance_port_to_B, duration_port_to_B,
                   diesel_price_end, driver_daily_salary_end, storage_time_C,
                   end_electricity_price, CO2e_end):
    """
    Orchestrate complete food supply chain Life Cycle Assessment (LCA).

    This function coordinates all process steps for food transport from farm to consumer, including:
    - Harvesting and preparation
    - Pre-cooling and/or freezing (if required by food type)
    - Road transport to/from ports
    - Cold storage at multiple locations
    - Marine transport in reefer containers
    - Additional costs (tariffs, financing, inspections, etc.)

    Args:
        initial_weight (float): Initial weight of food product in kg
        food_params (dict): Food-specific parameters including process flags and technical specs
        carbon_tax_per_ton_co2_dict_tl (dict): Carbon tax rates by country (USD/ton CO2)
        HHV_diesel_tl (float): Higher heating value of diesel in MJ/kg
        diesel_density_tl (float): Density of diesel in kg/L
        CO2e_diesel_tl (float): CO2 equivalent emissions factor for diesel in kg CO2/kg
        food_name_tl (str): Name of food commodity
        searoute_coor_tl (list): Sea route coordinates for insurance calculation
        port_to_port_duration_tl (float): Port-to-port duration in hours
        shipment_size_containers (int): Number of containers in shipment
        start_is_port (bool): True if start location is a port city (skips inland transport)
        end_is_port (bool): True if end location is a port city (skips inland transport)
        ... (many more parameters from parent scope - see function signature)

    Returns:
        tuple: (final_total_result_tl, data_raw)
            - final_total_result_tl (list): [total_cost, total_energy, total_emissions, final_weight]
            - data_raw (list): List of lists containing detailed results for each process step
                Each row: [label, opex, capex, carbon_tax, energy, emissions, weight, loss]

    Notes:
        - Process sequence adapts based on food_params['process_flags']
        - Automatically includes precooling/freezing steps if needed
        - Accumulates costs, energy, emissions, and tracks weight/spoilage
        - Adds overhead costs (tariffs, financing, inspections, contingency)
        - Separates insurance costs into dedicated rows for transparency
        - Conditionally skips road transport steps if start/end locations are ports
    """
    # Build process sequence conditionally based on port detection
    food_funcs_sequence = [
        (food_harvest_and_prep, "Harvesting & Preparation"),
    ]

    # Add precooling/freezing if needed
    flags = food_params['process_flags']
    if flags.get('needs_precooling', False):
        food_funcs_sequence.append((food_precooling_process, f"Pre-cooling in {start}"))

    if flags.get('needs_freezing', False):
        food_funcs_sequence.append((food_freezing_process, f"Freezing in {start}"))

    # Road transport to port (skip if start is already a port)
    if not start_is_port:
        food_funcs_sequence.append((food_road_transport, f"Road Transport: {start} to {start_port_name}"))

    # Storage at start port and marine transport
    food_funcs_sequence.extend([
        (food_cold_storage, f"Cold Storage at {start_port_name}"),
        (food_sea_transport, f"Marine Transport: {start_port_name} to {end_port_name}"),
        (food_cold_storage, f"Cold Storage at {end_port_name}"),
    ])

    # Road transport from port (skip if end is already a port)
    if not end_is_port:
        food_funcs_sequence.extend([
            (food_road_transport, f"Road Transport: {end_port_name} to {end}"),
            (food_cold_storage, f"Cold Storage at {end} (Destination)"),
        ])

    current_weight = initial_weight
    total_opex_money_tl = 0.0
    total_capex_money_tl = 0.0
    total_carbon_tax_money_tl = 0.0
    total_ener_consumed_tl = 0.0
    total_G_emission_tl = 0.0
    total_S_spoilage_loss_tl = 0.0
    total_insurance_money_tl = 0.0 # New accumulator for insurance
    data_raw = []

    for func_entry in food_funcs_sequence:
        func_to_call, label = func_entry
        args_for_func = ()

        if func_to_call == food_harvest_and_prep:
            args_for_func = (price_start, start_country_name, carbon_tax_per_ton_co2_dict_tl,
                             food_name_tl, searoute_coor_tl, port_to_port_duration_tl)
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
            args_for_func = (food_params, port_to_port_duration, selected_marine_fuel_params, avg_ship_power_kw, calculate_voyage_overheads, selected_ship_params, canal_transits, port_regions, end_country_name, carbon_tax_per_ton_co2_dict_tl, EU_MEMBER_COUNTRIES, shipment_size_containers, total_ship_container_capacity)
        elif func_to_call == food_cold_storage and "at " + start_port_name in label:
            args_for_func = (food_params, storage_time_A, start_port_electricity_price, CO2e_start, start_local_temperature, facility_capacity, start_port_country_name, carbon_tax_per_ton_co2_dict_tl)
        elif func_to_call == food_cold_storage and "at " + end_port_name in label:
            args_for_func = (food_params, storage_time_B, end_port_electricity_price, CO2e_end, end_local_temperature, facility_capacity, end_port_country_name, carbon_tax_per_ton_co2_dict_tl)
        elif func_to_call == food_cold_storage and "Destination" in label:
            args_for_func = (food_params, storage_time_C, end_electricity_price, CO2e_end, end_local_temperature, facility_capacity, end_country_name, carbon_tax_per_ton_co2_dict_tl)

        opex_m, capex_m, carbon_tax_m, energy, emissions, current_weight, loss, insurance_m = func_to_call(current_weight, args_for_func)
        data_raw.append([label, opex_m, capex_m, carbon_tax_m, energy, emissions, current_weight, loss])

        # For 'Harvesting & Preparation', split out insurance into a separate line
        if func_to_call == food_harvest_and_prep:
            data_raw.append([
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

        total_opex_money_tl += opex_m
        total_capex_money_tl += capex_m
        total_carbon_tax_money_tl += carbon_tax_m
        total_ener_consumed_tl += energy
        total_G_emission_tl += emissions
        total_S_spoilage_loss_tl += loss

    # 1. Calculate Cargo Value & CIF (Corrected to use food price and initial weight)
    initial_cargo_value = initial_weight * price_start
    freight_and_insurance_cost = total_opex_money_tl + total_capex_money_tl + total_carbon_tax_money_tl + total_insurance_money_tl
    cif_value = initial_cargo_value + freight_and_insurance_cost

    # 2. Calculate Tariff Cost
    tariff_rate = IMPORT_TARIFF_RATES_DICT.get(end_country_name, 0.05)
    tariff_cost = cif_value * tariff_rate
    data_raw.append(["Import Tariffs & Duties", tariff_cost, 0.0, 0.0, 0.0, 0.0, current_weight, 0.0])

    # 3. Calculate Financing Cost (Corrected to use initial_weight's value)
    total_duration_days = (duration_A_to_port / 1440) + (port_to_port_duration / 24) + (duration_port_to_B / 1440) + storage_time_A + storage_time_B + storage_time_C
    financing_cost = initial_cargo_value * (ANNUAL_FINANCING_RATE / 365) * total_duration_days
    data_raw.append(["Financing Costs", financing_cost, 0.0, 0.0, 0.0, 0.0, current_weight, 0.0])

    # 4. Add Brokerage & Agent Fees
    data_raw.append(["Brokerage & Agent Fees", BROKERAGE_AND_AGENT_FEE_USD, 0.0, 0.0, 0.0, 0.0, current_weight, 0.0])

    # 5. Add Food Inspection Fees
    insp_params = FOOD_INSPECTION_COST_PER_SHIPMENT.get(food_name_tl, {})
    base_cost = insp_params.get('base_cost_usd', 0)
    per_container_rate = insp_params.get('per_container_usd', 0)
    num_containers = shipment_size_containers

    inspection_cost = base_cost + (per_container_rate * num_containers)
    data_raw.append(["Food Inspections", inspection_cost, 0.0, 0.0, 0.0, 0.0, current_weight, 0.0])

    # 6. Calculate Contingency Cost
    contingency_cost = (total_opex_money_tl + total_carbon_tax_money_tl + total_insurance_money_tl) * CONTINGENCY_PERCENTAGE
    data_raw.append(["Contingency (10%)", contingency_cost, 0.0, 0.0, 0.0, 0.0, current_weight, 0.0])

    # --- FINAL COST CALCULATIONS END HERE ---

    # Now update the final totals with these new costs
    total_opex_money_tl += (tariff_cost + financing_cost + BROKERAGE_AND_AGENT_FEE_USD + inspection_cost + contingency_cost)
    final_total_money_tl = total_opex_money_tl + total_capex_money_tl + total_carbon_tax_money_tl + total_insurance_money_tl

    # Add the final TOTAL row
    data_raw.append(["TOTAL", total_opex_money_tl, total_capex_money_tl, total_carbon_tax_money_tl, total_ener_consumed_tl, total_G_emission_tl, current_weight, total_S_spoilage_loss_tl])

    # CHANGE: Return a tuple consistent with the fuel path
    final_total_result_tl = [final_total_money_tl, total_ener_consumed_tl, total_G_emission_tl, current_weight]
    return final_total_result_tl, data_raw
