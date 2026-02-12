"""
models/fuel_processes.py

This module contains all fuel process functions for the hydrogen supply chain simulation.
These functions calculate costs, emissions, energy consumption, and losses for various
stages of hydrogen and hydrogen carrier (ammonia, methanol) production, transport, and storage.

Each process function follows a standard signature:
    - A: Mass of fuel/chemical (kg)
    - B_fuel_type: Integer indicating fuel type (0=LH2, 1=Ammonia, 2=Methanol)
    - C_recirculation_BOG: BOG handling strategy
    - D_truck_apply: Truck BOG recirculation option
    - E_storage_apply: Storage BOG recirculation option
    - F_maritime_apply: Maritime BOG recirculation option
    - process_args_tuple: Tuple containing process-specific parameters

Each function returns an 8-element tuple:
    (opex_money, capex_money, carbon_tax_money, energy_consumed, G_emission,
     A_after_loss, loss_amount, insurance_cost)

NOTE: The function `calculate_total_insurance_cost` is imported locally within
site_A_chem_production from models.insurance_model. If this function doesn't exist
in insurance_model.py, you will need to add it there (it's currently defined in
app.py around line 332).

Extracted from app.py for better code organization and modularity.
"""

import numpy as np
import math

# Import required constants
from constants import BOG_EQUIPMENT_CAPEX, ANNUAL_WORKING_DAYS, EU_MEMBER_COUNTRIES
# Alias for backward compatibility with nested function code
annual_working_days = ANNUAL_WORKING_DAYS

# Import helper functions from other modules
from utils.conversions import liquification_data_fitting as liquification_data_fitting_helper_module
from models.capex_calculations import (
    calculate_liquefaction_capex as calculate_liquefaction_capex_helper,
    calculate_storage_capex as calculate_storage_capex_helper,
    calculate_loading_unloading_capex as calculate_loading_unloading_capex_helper,
    calculate_voyage_overheads as calculate_voyage_overheads_helper
)

# Define the module-level alias for liquification_data_fitting
liquification_data_fitting = liquification_data_fitting_helper_module


def site_A_chem_production(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for chemical production at Site A.

    For LH2 and SAF:
    - Assumes fuel is already produced (no synthesis step modeled)
    - Calculates insurance based on hydrogen_production_cost

    For Ammonia and Methanol:
    - Models H2-to-carrier synthesis (Haber-Bosch or methanol synthesis)
    - Calculates synthesis energy, costs, and emissions
    - Then calculates insurance based on total value

    Args:
        A (float): Mass of chemical to produce (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol, 3=SAF)
        C_recirculation_BOG (int): BOG handling strategy
        D_truck_apply (int): Truck BOG recirculation option
        E_storage_apply (int): Storage BOG recirculation option
        F_maritime_apply (int): Maritime BOG recirculation option
        process_args_tuple (tuple): Contains GWP_chem_list, hydrogen_production_cost,
            start_country_name, carbon_tax_per_ton_co2_dict, selected_fuel_name,
            searoute_coor, port_to_port_duration, start_electricity_price,
            CO2e_start, facility_capacity

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, convert_energy_consumed,
                G_emission, A, BOG_loss, insurance_cost)
    """
    from models.insurance_model import calculate_total_insurance_cost

    # Unpack arguments - need to handle both old and new formats
    if len(process_args_tuple) == 7:
        # Old format (for backward compatibility)
        (GWP_chem_list_arg, hydrogen_production_cost_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg,
         selected_fuel_name_arg, searoute_coor_arg, port_to_port_duration_arg) = process_args_tuple
        start_electricity_price_arg = None
        CO2e_start_arg = None
        facility_capacity_arg = None
    else:
        # New format with synthesis parameters
        (GWP_chem_list_arg, hydrogen_production_cost_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg,
         selected_fuel_name_arg, searoute_coor_arg, port_to_port_duration_arg,
         start_electricity_price_arg, CO2e_start_arg, facility_capacity_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0
    insurance_cost = 0
    convert_energy_consumed = 0
    G_emission = 0
    BOG_loss = 0

    # For Ammonia (1) and Methanol (2), model synthesis from H2 if parameters are available
    if (B_fuel_type == 1 or B_fuel_type == 2) and start_electricity_price_arg is not None:
        # Calculate H2 mass needed to produce A kg of carrier
        # Must account for synthesis efficiency: to get A kg output, need A/efficiency kg input
        if B_fuel_type == 1:  # Ammonia
            synthesis_efficiency = 0.95
            mass_ratio = 5.67
            h2_mass_needed = A / (mass_ratio * synthesis_efficiency)  # Account for 95% efficiency
        else:  # Methanol
            synthesis_efficiency = 0.92
            mass_ratio = 5.33
            h2_mass_needed = A / (mass_ratio * synthesis_efficiency)  # Account for 92% efficiency

        # Call synthesis function
        synthesis_args = (start_electricity_price_arg, CO2e_start_arg, start_country_name_arg,
                         carbon_tax_per_ton_co2_dict_arg, facility_capacity_arg)

        synth_opex, synth_capex, synth_carbon_tax, synth_energy, synth_emission, carrier_produced, h2_loss, _ = \
            H2_to_carrier_synthesis(h2_mass_needed, B_fuel_type, synthesis_args)

        # Add synthesis costs
        opex_money += synth_opex
        capex_money += synth_capex
        carbon_tax_money += synth_carbon_tax
        convert_energy_consumed += synth_energy
        G_emission += synth_emission
        BOG_loss += h2_loss

        # H2 production cost (for the H2 input to synthesis)
        h2_production_cost = h2_mass_needed * hydrogen_production_cost_arg

        # Total cargo value = H2 cost + synthesis costs
        cargo_value = h2_production_cost + synth_opex + synth_capex + synth_carbon_tax

        # CRITICAL: Return the actual produced mass (carrier_produced), not the input (A)
        # This ensures downstream processes calculate costs for the correct mass
        final_mass_to_return = carrier_produced

    else:
        # For LH2 (0) and SAF (3), or if synthesis parameters not available
        cargo_value = A * hydrogen_production_cost_arg
        final_mass_to_return = A

    # Calculate insurance based on cargo value
    insurance_cost = calculate_total_insurance_cost(
        initial_cargo_value_usd=cargo_value,
        commodity_type_str=selected_fuel_name_arg,
        searoute_coords_list=searoute_coor_arg,
        port_to_port_duration_hrs=port_to_port_duration_arg
    )

    return opex_money, capex_money, carbon_tax_money, convert_energy_consumed, G_emission, final_mass_to_return, BOG_loss, insurance_cost


def H2_to_carrier_synthesis(H2_mass_kg, fuel_type, synthesis_args_tuple):
    """
    Convert green hydrogen to ammonia or methanol via synthesis.
    This step models the Haber-Bosch process (for NH3) or methanol synthesis (for MeOH).

    Args:
        H2_mass_kg: Mass of hydrogen to be converted (kg)
        fuel_type: 1 for ammonia, 2 for methanol
        synthesis_args_tuple: (electricity_price_tuple, carbon_intensity, country_name, carbon_tax_dict, facility_capacity)

    Returns:
        tuple: (opex, capex, carbon_tax, energy, emissions, carrier_mass, h2_loss, insurance)
    """
    electricity_price_tuple, carbon_intensity, country_name, carbon_tax_dict, facility_capacity = synthesis_args_tuple
    electricity_price_usd_per_mj = electricity_price_tuple[2]

    # === SYNTHESIS PARAMETERS ===
    # Based on literature for green ammonia/methanol production from electrolytic H2

    if fuel_type == 1:  # Ammonia (Haber-Bosch)
        # Mass conversion: 1 kg H2 → 5.67 kg NH3 (stoichiometric: N2 + 3H2 → 2NH3)
        mass_ratio = 5.67  # kg NH3 per kg H2

        # Energy consumption for synthesis (not including H2 production)
        # Includes: ASU (Air Separation Unit) for N2, compression to 150-300 bar,
        # heating to 400-500°C, cooling, separation
        # Synthesis loop: 2.0-2.5 MJ/kg, ASU: ~0.7 MJ/kg
        # Total: ~2.9 MJ electrical per kg NH3 produced
        specific_energy_mj_per_kg_carrier = 2.9  # MJ electrical per kg NH3

        # Process efficiency (accounts for H2 losses, purge streams)
        efficiency = 0.95  # 95% of H2 is converted to NH3

        # Capital cost for ammonia synthesis plant
        # Commercial-scale green ammonia: ~$1000 per tonne/year capacity
        # Ref: $1.4B for 1.4M tonne/year (IEA, 2024)
        # Annualized over 20 years at 8% discount rate
        capex_usd_per_kg_capacity = 1000 / 1000  # $1.0 per kg annual capacity (total plant cost)
        annualization_factor = 0.08  # 20 years, 8% discount rate

    elif fuel_type == 2:  # Methanol
        # Mass conversion: 1 kg H2 → 5.33 kg MeOH (stoichiometric: CO2 + 3H2 → CH3OH + H2O)
        mass_ratio = 5.33  # kg MeOH per kg H2

        # Energy consumption for methanol synthesis from H2 + CO2
        # Includes: compression, heating, synthesis at 50-100 bar, 250°C
        # NOTE: Does NOT include CO2 capture costs (should be added separately):
        #   - Point-source CO2: $20-100/t CO2 (adds $9-46/t MeOH)
        #   - DAC CO2: $100-600/t CO2 + 1-2 MWh/t energy (adds $50-250/t MeOH)
        #   - Biogenic CO2: $10-50/t CO2 (adds $4.6-23/t MeOH)
        specific_energy_mj_per_kg_carrier = 2.8  # MJ electrical per kg MeOH

        # Process efficiency
        efficiency = 0.92  # 92% of H2 is converted to MeOH

        # Capital cost for methanol synthesis plant
        # E-methanol plants: ~$1000 per tonne/year capacity
        # Similar to ammonia, based on industry estimates
        capex_usd_per_kg_capacity = 1000 / 1000  # $1.0 per kg annual capacity (total plant cost)
        annualization_factor = 0.08  # 20 years, 8% discount rate

    else:
        # Not ammonia or methanol, no synthesis needed
        return 0, 0, 0, 0, 0, H2_mass_kg, 0, 0

    # === CALCULATIONS ===
    # Carrier mass produced
    carrier_mass_kg = H2_mass_kg * mass_ratio * efficiency

    # H2 losses (unconverted)
    h2_loss_kg = H2_mass_kg * (1 - efficiency)

    # Energy consumption (electrical)
    energy_consumed_mj = carrier_mass_kg * specific_energy_mj_per_kg_carrier

    # OPEX: Electricity cost
    opex_electricity = energy_consumed_mj * electricity_price_usd_per_mj

    # OPEX: Maintenance and operations (typically 2-3% of CAPEX per year)
    # CRITICAL: Synthesis plant capacity should scale with actual carrier production,
    # NOT with the UI's facility_capacity input (which is for LH2 liquefaction).
    # Assume plant processes one ship cargo per month (12 voyages/year)
    cargos_per_year = 12
    annual_production_kg = carrier_mass_kg * cargos_per_year

    capex_total = annual_production_kg * capex_usd_per_kg_capacity  # Total plant cost
    capex_annual = capex_total * annualization_factor  # Annualized CAPEX
    opex_maintenance = capex_total * 0.025  # 2.5% of total CAPEX per year
    opex_maintenance_per_kg = opex_maintenance / annual_production_kg if annual_production_kg > 0 else 0
    opex_money = opex_electricity + (opex_maintenance_per_kg * carrier_mass_kg)

    # CAPEX: Annualized capital cost per kg produced
    capex_per_kg = capex_annual / annual_production_kg if annual_production_kg > 0 else 0
    capex_money = capex_per_kg * carrier_mass_kg

    # Emissions from electricity use
    # carbon_intensity is in g CO2/kWh from ElectricityMap API, need to convert to kg CO2/MJ
    # Step 1: g CO2/kWh → g CO2/MJ: divide by 3.6 (since 1 kWh = 3.6 MJ)
    # Step 2: g CO2 → kg CO2: divide by 1000
    carbon_intensity_per_mj = carbon_intensity / 3.6  # g CO2/MJ
    G_emission = (energy_consumed_mj * carbon_intensity_per_mj) / 1000  # Convert g to kg

    # Carbon tax
    G_emission_tons = G_emission / 1000
    # Use country-specific rate, fallback to "Unknown" default (global average)
    carbon_tax_rate = carbon_tax_dict.get(country_name, carbon_tax_dict.get('Unknown', 25.00))
    carbon_tax_money = G_emission_tons * carbon_tax_rate

    # No insurance for synthesis process (included in production)
    insurance_cost = 0

    return opex_money, capex_money, carbon_tax_money, energy_consumed_mj, G_emission, carrier_mass_kg, h2_loss_kg, insurance_cost


def site_A_chem_liquification(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_specific_args_tuple):
    """
    Calculate costs and emissions for chemical liquification at Site A.

    This function handles the liquification process for hydrogen carriers:
    - LH2: Uses data-fitted liquification energy model
    - Ammonia: Calculates cooling and phase change energy requirements
    - Methanol: No liquification needed (already liquid at ambient conditions)

    Includes BOG (Boil-Off Gas) losses during liquification.

    Args:
        A (float): Mass of chemical to liquefy (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        process_specific_args_tuple (tuple): Contains LH2_plant_capacity, EIM_liquefication,
            specific_heat_chem, start_local_temperature, boiling_point_chem, latent_H_chem,
            COP_liq_dyn, start_electricity_price_tuple, CO2e_start, GWP_chem_list,
            calculate_liquefaction_capex_helper, start_country_name, carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, liquify_ener_consumed,
                G_emission, A_after_loss, BOG_loss, insurance_cost=0)
    """
    (LH2_plant_capacity_arg, EIM_liquefication_arg, specific_heat_chem_arg,
    start_local_temperature_arg, boiling_point_chem_arg, latent_H_chem_arg,
    COP_liq_dyn, start_electricity_price_tuple_arg, CO2e_start_arg,
    GWP_chem_list_arg, calculate_liquefaction_capex_helper_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_specific_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    if B_fuel_type == 0:  # LH2
        liquify_energy_required = liquification_data_fitting(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
    elif B_fuel_type == 1:  # Ammonia
        liquify_heat_required = specific_heat_chem_arg[B_fuel_type] * (start_local_temperature_arg + 273 - boiling_point_chem_arg[B_fuel_type]) + latent_H_chem_arg[B_fuel_type]
        liquify_energy_required = liquify_heat_required / COP_liq_dyn
    else:  # Methanol
        liquify_energy_required = 0

    liquify_ener_consumed = liquify_energy_required * A
    opex_money += liquify_ener_consumed * start_electricity_price_tuple_arg[2]

    # CAPEX - pass cargo mass for cycle-based calculation (ammonia)
    capex_per_kg, om_cost_per_kg = calculate_liquefaction_capex_helper_arg(B_fuel_type, LH2_plant_capacity_arg, A)
    capex_money += capex_per_kg * A
    opex_money += om_cost_per_kg * A
    G_emission_from_energy = liquify_ener_consumed * 0.2778 * CO2e_start_arg * 0.001
    BOG_loss = 0.016 * A
    A_after_loss = A - BOG_loss
    G_emission_from_bog = BOG_loss * GWP_chem_list_arg[B_fuel_type]
    G_emission = G_emission_from_energy + G_emission_from_bog

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax
    return opex_money, capex_money, carbon_tax_money, liquify_ener_consumed, G_emission, A_after_loss, BOG_loss, 0


def fuel_pump_transfer(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for cryogenic pump transfer operations.

    This function models the pumping of cryogenic liquids through insulated pipelines:
    - Pumping energy based on flow rate, head pressure, and pump efficiency
    - Refrigeration energy to compensate for heat ingress through pipe walls
    - BOG losses proportional to transfer duration and ambient temperature

    Args:
        A (float): Mass of chemical to transfer (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        process_args_tuple (tuple): Contains V_flowrate, number_of_cryo_pump_load,
            dBOR_dT, BOR_transfer, liquid_chem_density, head_pump, pump_power_factor,
            EIM_cryo_pump, ss_therm_cond, pipe_length, pipe_inner_D, pipe_thick,
            COP_refrig, EIM_refrig_eff, electricity_price_tuple, CO2e, GWP_chem_list,
            local_temperature, calculate_loading_unloading_capex_helper,
            country_of_transfer, carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, ener_consumed,
                G_emission, A_after_loss, BOG_loss, insurance_cost=0)
    """
    (V_flowrate_arg, number_of_cryo_pump_load_arg, dBOR_dT_arg,
    BOR_transfer_arg, liquid_chem_density_arg, head_pump_arg,
    pump_power_factor_arg, EIM_cryo_pump_arg, ss_therm_cond_arg,
    pipe_length_arg, pipe_inner_D_arg, pipe_thick_arg, COP_refrig_arg,
    EIM_refrig_eff_arg, electricity_price_tuple_arg, CO2e_arg,
    GWP_chem_list_arg, local_temperature_arg, calculate_loading_unloading_capex_helper_arg,
    country_of_transfer_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

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
    capex_per_kg, om_cost_per_kg = calculate_loading_unloading_capex_helper_arg(B_fuel_type)
    capex_money += capex_per_kg * A
    opex_money += om_cost_per_kg * A
    G_emission = ener_consumed * 0.2778 * CO2e_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_transfer_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_after_loss, BOG_loss, 0


def fuel_road_transport(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for road transport of cryogenic fuels via truck.

    This function models truck-based transportation including:
    - Diesel fuel consumption for propulsion
    - Refrigeration energy to maintain cryogenic temperatures
    - BOG losses during transport with optional recirculation strategies:
        * Option 1: Reliquefaction (capture and reliquefy BOG)
        * Option 2: Auxiliary fuel integration (use BOG to offset energy needs)
        * Option 3: Burner/flare (controlled combustion of BOG)
    - Driver salary costs
    - Maintenance and repair costs
    - Truck capital costs (annualized)

    Args:
        A (float): Mass of chemical to transport (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        C_recirculation_BOG (int): BOG handling strategy (2=enabled)
        D_truck_apply (int): Truck BOG recirculation option (1=reliq, 2=aux fuel, 3=flare)
        process_args_tuple (tuple): Contains extensive truck parameters including
            road_delivery_ener, HHV_chem, chem_in_truck_weight, truck_economy, distance,
            thermal properties, BOG parameters, efficiency factors, costs, etc.

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, total_energy,
                G_emission, A_after_loss, net_BOG_loss, insurance_cost=0)
    """
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
    carbon_tax_money = 0
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

            bog_reliquefier_cost = BOG_EQUIPMENT_CAPEX['reliquefaction_unit']['truck']['cost_usd']
            bog_reliquefier_annualization = BOG_EQUIPMENT_CAPEX['reliquefaction_unit']['truck']['annualization_factor']
            capex_per_kg_bog_reliquefaction = (bog_reliquefier_cost * bog_reliquefier_annualization) / (330 * chem_in_truck_weight_arg[B_fuel_type])
            capex_money += capex_per_kg_bog_reliquefaction * A

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

            bog_aux_integration_cost = BOG_EQUIPMENT_CAPEX['aux_fuel_integration']['truck']['cost_usd']
            bog_aux_integration_annualization = BOG_EQUIPMENT_CAPEX['aux_fuel_integration']['truck']['annualization_factor']
            capex_per_kg_bog_aux = (bog_aux_integration_cost * bog_aux_integration_annualization) / (330 * chem_in_truck_weight_arg[B_fuel_type])
            capex_money += capex_per_kg_bog_aux * A

            net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
            G_emission_energy = (total_energy * CO2e_diesel_arg) / (HHV_diesel_arg * diesel_density_arg)
            G_emission = G_emission_energy + net_BOG_loss * GWP_chem_arg[B_fuel_type]

        elif D_truck_apply == 3:
            net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_truck_percentage_arg * 0.01)
            G_emission = G_emission_energy + net_BOG_loss * GWP_chem_arg[B_fuel_type]
            bog_burner_flare_cost = BOG_EQUIPMENT_CAPEX['burner_flare']['truck']['cost_usd']
            bog_burner_flare_annualization = BOG_EQUIPMENT_CAPEX['burner_flare']['truck']['annualization_factor']
            capex_per_kg_bog_burner_flare = (bog_burner_flare_cost * bog_burner_flare_annualization) / (330 * chem_in_truck_weight_arg[B_fuel_type])
            capex_money += capex_per_kg_bog_burner_flare * A

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
    capex_per_truck_trip_usd = annual_truck_cost_usd / 330  # Assuming 330 annual trips
    capex_money += capex_per_truck_trip_usd * number_of_trucks

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_road_transport_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, total_energy, G_emission, A_after_loss, net_BOG_loss, 0


def fuel_storage(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for stationary storage of cryogenic fuels.

    This function models large-scale cryogenic storage including:
    - Refrigeration energy to compensate for heat ingress into storage tanks
    - BOG losses proportional to storage duration and ambient temperature
    - Optional BOG recirculation strategies (similar to truck transport)
    - Storage tank capital and operating costs

    BOG handling options (when C_recirculation_BOG=2 and E_storage_apply is set):
        * Option 1: Reliquefaction unit
        * Option 2: Auxiliary fuel integration (use BOG for facility power)
        * Option 3: Burner/flare

    Args:
        A (float): Mass of chemical to store (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        C_recirculation_BOG (int): BOG handling strategy (2=enabled)
        E_storage_apply (int): Storage BOG recirculation option (1=reliq, 2=aux fuel, 3=flare)
        process_args_tuple (tuple): Contains liquid_chem_density, storage_volume, dBOR_dT,
            local_temperature, BOR_land_storage, storage_time, storage_radius,
            tank thermal properties, COP_refrig, electricity_price, emissions factors,
            BOG parameters, capex calculation helper, country, carbon tax dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, total_energy_consumed,
                G_emission, A_after_loss, net_BOG_loss, insurance_cost=0)
    """
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
    carbon_tax_money = 0
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
    capex_per_kg, om_cost_per_kg = calculate_storage_capex_helper_arg(B_fuel_type, LH2_plant_capacity_arg, A, storage_time_arg)
    capex_money += capex_per_kg * A
    opex_money += om_cost_per_kg * A
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
            # CAPEX for storage reliquefaction unit
            reliquefier_cost_per_kg_capacity = BOG_EQUIPMENT_CAPEX['reliquefaction_unit']['storage']['cost_usd_per_kg_capacity']
            reliquefier_annualization = BOG_EQUIPMENT_CAPEX['reliquefaction_unit']['storage']['annualization_factor']

            if storage_time_arg > 0 and annual_working_days > 0:
                cycles_per_year = annual_working_days / storage_time_arg
                annual_throughput_kg_for_capex = A * cycles_per_year
            else:
                annual_throughput_kg_for_capex = A * 330  # Fallback if storage_time_arg is 0

            total_reliquefier_capex_for_current_A = reliquefier_cost_per_kg_capacity * A
            annualized_reliquefier_capex = total_reliquefier_capex_for_current_A * reliquefier_annualization

            capex_per_kg_reliquefier_for_this_A = annualized_reliquefier_capex / annual_throughput_kg_for_capex if annual_throughput_kg_for_capex > 0 else 0
            capex_money += capex_per_kg_reliquefier_for_this_A * A
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
            # CAPEX for storage auxiliary fuel integration
            aux_integration_cost_per_kg_capacity = BOG_EQUIPMENT_CAPEX['aux_fuel_integration']['storage']['cost_usd_per_kg_capacity']
            aux_integration_annualization = BOG_EQUIPMENT_CAPEX['aux_fuel_integration']['storage']['annualization_factor']

            if storage_time_arg > 0 and annual_working_days > 0:
                cycles_per_year = annual_working_days / storage_time_arg
                annual_throughput_kg_for_capex = A * cycles_per_year
            else:
                annual_throughput_kg_for_capex = A * 330

            total_aux_integration_capex_for_current_A = aux_integration_cost_per_kg_capacity * A
            annualized_aux_capex = total_aux_integration_capex_for_current_A * aux_integration_annualization
            capex_per_kg_aux_for_this_A = annualized_aux_capex / annual_throughput_kg_for_capex if annual_throughput_kg_for_capex > 0 else 0
            capex_money += capex_per_kg_aux_for_this_A * A
        elif E_storage_apply == 3:
            net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_storage_percentage_arg * 0.01)
            G_emission = total_energy_consumed * 0.2778 * CO2e_arg * 0.001 + net_BOG_loss * GWP_chem_list_arg[B_fuel_type]
            # CAPEX for storage burner/flare
            burner_cost_per_kg_capacity = BOG_EQUIPMENT_CAPEX['burner_flare']['storage']['cost_usd_per_kg_capacity']
            burner_annualization = BOG_EQUIPMENT_CAPEX['burner_flare']['storage']['annualization_factor']

            if storage_time_arg > 0 and annual_working_days > 0:
                cycles_per_year = annual_working_days / storage_time_arg
                annual_throughput_kg_for_capex = A * cycles_per_year
            else:
                annual_throughput_kg_for_capex = A * 330

            total_burner_capex_for_current_A = burner_cost_per_kg_capacity * A
            annualized_burner_capex = total_burner_capex_for_current_A * burner_annualization
            capex_per_kg_burner_for_this_A = annualized_burner_capex / annual_throughput_kg_for_capex if annual_throughput_kg_for_capex > 0 else 0
            capex_money += capex_per_kg_burner_for_this_A * A
    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(country_of_storage_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, total_energy_consumed, G_emission, A_after_loss, net_BOG_loss, 0


def chem_loading_to_ship(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for loading cryogenic chemicals onto a ship at port.

    This function models the ship loading process including:
    - Pumping energy to transfer liquid to ship tanks
    - Pipe refrigeration to prevent heat ingress during transfer
    - Cool-down energy for ship tanks and transfer pipes (bringing them to cryogenic temperature)
    - BOG losses during loading operation

    Cool-down is required for LH2 and Ammonia to bring ship tanks and piping from
    ambient temperature to the boiling point of the chemical.

    Args:
        A (float): Mass of chemical to load (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        process_args_tuple (tuple): Contains V_flowrate, number_of_cryo_pump_load_ship_port_A,
            dBOR_dT, start_local_temperature, BOR_loading, liquid_chem_density, head_pump,
            pump parameters, thermal conductivity, pipe dimensions, boiling points,
            COP values, electricity price, emissions, tank properties, capex helper

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, ener_consumed,
                G_emission, A_after_loss, BOG_loss, insurance_cost=0)
    """
    (V_flowrate_arg, number_of_cryo_pump_load_ship_port_A_arg, dBOR_dT_arg,
    start_local_temperature_arg, BOR_loading_arg, liquid_chem_density_arg, head_pump_arg,
    pump_power_factor_arg, EIM_cryo_pump_arg, ss_therm_cond_arg, pipe_length_arg, pipe_inner_D_arg,
    pipe_thick_arg, boiling_point_chem_arg, EIM_refrig_eff_arg, start_electricity_price_tuple_arg,
    CO2e_start_arg, GWP_chem_list_arg, calculated_storage_area_arg, ship_tank_metal_thickness,
    ship_tank_insulation_thickness, ship_tank_metal_density, ship_tank_insulation_density,
    ship_tank_metal_specific_heat, ship_tank_insulation_specific_heat,
    COP_cooldown_dyn, COP_refrig_arg, ship_number_of_tanks_arg, pipe_metal_specific_heat_arg,
    calculate_loading_unloading_capex_helper_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

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

        cooldown_cop = COP_cooldown_dyn
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

        cooldown_cop_pipes = COP_cooldown_dyn
        if cooldown_cop_pipes > 0:
            ener_consumed_cooldown_pipes = Q_cooling_pipes / cooldown_cop_pipes

    ener_consumed = ener_consumed_pumping + ener_consumed_pipe_refrig + ener_consumed_cooldown + ener_consumed_cooldown_pipes
    A_after_loss = A - BOG_loss

    opex_money += ener_consumed * start_electricity_price_tuple_arg[2]

    # CAPEX
    capex_per_kg, om_cost_per_kg = calculate_loading_unloading_capex_helper_arg(B_fuel_type)
    capex_money += capex_per_kg * A
    opex_money += om_cost_per_kg * A
    G_emission = ener_consumed * 0.2778 * CO2e_start_arg * 0.001 + BOG_loss * GWP_chem_list_arg[B_fuel_type]

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_after_loss, BOG_loss, 0


def port_to_port(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for maritime transport from port to port.

    This function models ocean shipping including:
    - Main propulsion fuel consumption (based on ship power and voyage duration)
    - Refrigeration energy for cryogenic cargo (LH2 only)
    - BOG losses during voyage with optional recirculation:
        * Option 1: Onboard reliquefaction (recapture BOG)
        * Option 2: Use BOG as auxiliary fuel for ship power
        * Option 3: Burn/flare BOG
    - Voyage overhead costs (crew, port fees, canal fees, insurance, etc.)
    - Ship capital costs (annualized based on voyage duration)
    - Multiple emission sources:
        * Main engine fuel combustion (CO2)
        * Methane slip from LNG engines
        * N2O emissions from combustion
        * Unrecovered BOG emissions
    - EU ETS (Emissions Trading Scheme) carbon costs for EU destinations

    Args:
        A (float): Mass of chemical being transported (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        C_recirculation_BOG (int): BOG handling strategy (2=enabled)
        F_maritime_apply (int): Maritime BOG option (1=reliq, 2=aux fuel, 3=flare)
        process_args_tuple (tuple): Contains temperatures, OHTC, storage area, tanks,
            COP, duration, fuel params, BOG params, ship power, efficiency, voyage
            overheads helper, ship params, canal transits, port regions, country, tax dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, total_energy_consumed_mj,
                total_G_emission, A_after_loss, net_BOG_loss, insurance_cost=0)
    """
    (start_local_temperature_arg, end_local_temperature_arg, OHTC_ship_arg,
    calculated_storage_area_arg, ship_number_of_tanks_arg, COP_refrig_arg, EIM_refrig_eff_arg,
    port_to_port_duration_arg, selected_fuel_params_arg,
    dBOR_dT_arg, BOR_ship_trans_arg, GWP_chem_list_arg,
    BOG_recirculation_maritime_percentage_arg, LH2_plant_capacity_arg, EIM_liquefication_arg,
    fuel_cell_eff_arg, EIM_fuel_cell_arg, LHV_chem_arg,
    avg_ship_power_kw_arg, aux_engine_efficiency_arg, GWP_N2O_arg,
    calculate_voyage_overheads_helper_arg,
    selected_ship_params_arg, canal_transits_arg, port_regions_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg,
    eu_member_countries_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    voyage_duration_days = port_to_port_duration_arg / 24.0
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
            reliquefier_cost_per_m3 = BOG_EQUIPMENT_CAPEX['reliquefaction_unit']['ship']['cost_usd_per_m3_volume']
            reliquefier_annualization = BOG_EQUIPMENT_CAPEX['reliquefaction_unit']['ship']['annualization_factor']
            total_reliquefier_capex = reliquefier_cost_per_m3 * selected_ship_params_arg['volume_m3']
            annualized_reliquefier_capex = total_reliquefier_capex * reliquefier_annualization
            capex_per_voyage_reliquefier = annualized_reliquefier_capex / annual_working_days * voyage_duration_days
            capex_money += capex_per_voyage_reliquefier
        elif F_maritime_apply == 2:
            energy_saved_from_bog_mj = usable_BOG * fuel_cell_eff_arg * (EIM_fuel_cell_arg / 100) * LHV_chem_arg[B_fuel_type]
            aux_integration_cost_per_m3 = BOG_EQUIPMENT_CAPEX['aux_fuel_integration']['ship']['cost_usd_per_m3_volume']
            aux_integration_annualization = BOG_EQUIPMENT_CAPEX['aux_fuel_integration']['ship']['annualization_factor']
            total_aux_integration_capex = aux_integration_cost_per_m3 * selected_ship_params_arg['volume_m3']
            annualized_aux_capex = total_aux_integration_capex * aux_integration_annualization
            capex_per_voyage_aux = annualized_aux_capex / annual_working_days * voyage_duration_days
            capex_money += capex_per_voyage_aux
        elif F_maritime_apply == 3:
            net_BOG_loss = current_BOG_loss * (1 - BOG_recirculation_maritime_percentage_arg * 0.01)
            burner_cost_per_m3 = BOG_EQUIPMENT_CAPEX['burner_flare']['ship']['cost_usd_per_m3_volume']
            burner_annualization = BOG_EQUIPMENT_CAPEX['burner_flare']['ship']['annualization_factor']
            total_burner_capex = burner_cost_per_m3 * selected_ship_params_arg['volume_m3']
            annualized_burner_capex = total_burner_capex * burner_annualization
            capex_per_voyage_burner = annualized_burner_capex / annual_working_days * voyage_duration_days
            capex_money += capex_per_voyage_burner

    fuel_hhv_mj_per_kg = selected_fuel_params_arg['hhv_mj_per_kg']
    sfoc_g_per_kwh = selected_fuel_params_arg['sfoc_g_per_kwh']

    total_engine_work_mj = (propulsion_work_kwh * 3.6) + refrig_work_mj + reliq_work_mj - energy_saved_from_bog_mj
    if total_engine_work_mj < 0: total_engine_work_mj = 0

    total_engine_work_kwh = total_engine_work_mj / 3.6
    total_fuel_consumed_kg = (total_engine_work_kwh * sfoc_g_per_kwh) / 1000.0
    opex_money += (total_fuel_consumed_kg / 1000) * selected_fuel_params_arg['price_usd_per_ton']

    # Voyage Overheads (OPEX and CAPEX)
    voyage_opex_overheads, voyage_capex_overheads = calculate_voyage_overheads_helper_arg(voyage_duration_days, selected_ship_params_arg, canal_transits_arg, port_regions_arg)
    opex_money += voyage_opex_overheads
    capex_money += voyage_capex_overheads

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

    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (total_G_emission / 1000)
    carbon_tax_money += carbon_tax

    if end_country_name_arg in eu_member_countries_arg:
        eu_ets_emissions_tons = (total_G_emission / 1000) * 0.50
        eu_ets_tax = eu_ets_emissions_tons * carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0)
        carbon_tax_money += eu_ets_tax

    total_energy_consumed_mj = total_fuel_consumed_kg * fuel_hhv_mj_per_kg
    return opex_money, capex_money, carbon_tax_money, total_energy_consumed_mj, total_G_emission, A_after_loss, net_BOG_loss, 0


def chem_convert_to_H2(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for converting hydrogen carriers back to hydrogen.

    This function handles the conversion/cracking process:
    - LH2 (fuel_type=0): No conversion needed, pass through
    - Ammonia (fuel_type=1): Crack NH3 to H2 via catalytic decomposition
    - Methanol (fuel_type=2): Reform CH3OH to H2 via steam reforming

    Energy consumption depends on the conversion process efficiency and the
    thermodynamic requirements for breaking chemical bonds.

    Args:
        A (float): Mass of chemical to convert (kg)
        B_fuel_type (int): Fuel type (0=LH2, 1=Ammonia, 2=Methanol)
        process_args_tuple (tuple): Contains mass_conversion_to_H2, eff_energy_chem_to_H2,
            energy_chem_to_H2, CO2e_end, end_electricity_price_tuple, end_country_name,
            carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, convert_energy,
                G_emission, A (converted mass), BOG_loss, insurance_cost=0)
    """
    (mass_conversion_to_H2_arg, eff_energy_chem_to_H2_arg, energy_chem_to_H2_arg,
    CO2e_end_arg, end_electricity_price_tuple_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0
    convert_energy = 0
    G_emission = 0
    BOG_loss = 0

    if B_fuel_type == 0:
        pass
    else:
        convert_to_H2_weight = A * mass_conversion_to_H2_arg[B_fuel_type]
        # CRITICAL FIX: Energy should be per kg of H2 PRODUCED, not per kg of carrier INPUT
        # Old: energy_chem_to_H2 * A / efficiency (incorrectly used carrier mass)
        # New: energy_chem_to_H2 * convert_to_H2_weight / efficiency (uses H2 mass)
        convert_energy = energy_chem_to_H2_arg[B_fuel_type] * convert_to_H2_weight / eff_energy_chem_to_H2_arg[B_fuel_type]

        G_emission = convert_energy * 0.2778 * CO2e_end_arg * 0.001
        opex_money += convert_energy * end_electricity_price_tuple_arg[2]

        # Carbon Tax
        carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(end_country_name_arg, 0) * (G_emission / 1000)
        carbon_tax_money += carbon_tax

        A = convert_to_H2_weight

    return opex_money, capex_money, carbon_tax_money, convert_energy, G_emission, A, BOG_loss, 0


def PH2_pressurization_at_site_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for pressurizing gaseous hydrogen at Site A.

    This function handles compression of hydrogen gas to high pressure for:
    - Storage in pressurized vessels
    - Pipeline transport

    Uses multistage compression to calculate energy requirements based on:
    - Initial and final pressure (derived from density and storage volume)
    - Compressor efficiency
    - Number of compression stages

    Args:
        A (float): Mass of hydrogen to pressurize (kg)
        B_fuel_type (int): Fuel type (only applies to PH2, fuel_type=0 for this pathway)
        process_args_tuple (tuple): Contains PH2_storage_V, numbers_of_PH2_storage_at_start,
            PH2_pressure_fnc_helper, multistage_compress_helper, multistage_eff,
            start_electricity_price_tuple, CO2e_start, start_country_name,
            carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, compress_energy,
                G_emission, A, leak_loss, insurance_cost=0)
    """
    (PH2_storage_V_arg, numbers_of_PH2_storage_at_start_arg, PH2_pressure_fnc_helper,
    multistage_compress_helper, multistage_eff_arg, start_electricity_price_tuple_arg,
    CO2e_start_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    PH2_density = A / (PH2_storage_V_arg * numbers_of_PH2_storage_at_start_arg)
    PH2_pressure = PH2_pressure_fnc_helper(PH2_density)

    compress_energy = multistage_compress_helper(PH2_pressure) * A / (multistage_eff_arg / 100)

    opex_money += start_electricity_price_tuple_arg[2] * compress_energy
    G_emission = compress_energy * 0.2778 * CO2e_start_arg * 0.001

    leak_loss = 0

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_country_name_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, compress_energy, G_emission, A, leak_loss, 0


def PH2_site_A_to_port_A(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for transporting pressurized H2 from Site A to Port A via pipeline.

    This function models high-pressure hydrogen pipeline transport including:
    - Pressure drop calculations using Darcy-Weisbach equation
    - Friction factor from Colebrook equation
    - Energy consumption for maintaining flow
    - Mass losses due to insufficient final pressure

    The pipeline model accounts for:
    - Pipeline diameter and roughness (epsilon)
    - Flow velocity and Reynolds number
    - Distance-dependent pressure drop
    - Kinematic viscosity of compressed hydrogen

    Args:
        A (float): Mass of hydrogen to transport (kg)
        B_fuel_type (int): Fuel type (PH2 pathway)
        process_args_tuple (tuple): Contains PH2_storage_V, numbers_of_PH2_storage_at_start,
            PH2_pressure_fnc_helper, coordinates (start lat/lng, port lat/lng),
            straight_line_dis_helper, kinematic_viscosity_PH2_helper, compressor_velocity,
            pipeline_diameter, solve_colebrook_helper, epsilon, PH2_transport_energy_helper,
            gas_chem_density, numbers_of_PH2_storage, electricity_price, CO2e, country, tax dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, ener_consumed,
                G_emission, A_final, trans_loss, insurance_cost=0)
    """
    (PH2_storage_V_arg, numbers_of_PH2_storage_at_start_arg, PH2_pressure_fnc_helper,
    coor_start_lat_arg, coor_start_lng_arg, start_port_lat_arg, start_port_lng_arg,
    straight_line_dis_helper, kinematic_viscosity_PH2_helper, compressor_velocity_arg,
    pipeline_diameter_arg, solve_colebrook_helper, epsilon_arg, PH2_transport_energy_helper,
    gas_chem_density_arg, numbers_of_PH2_storage_arg, start_electricity_price_tuple_arg,
    CO2e_start_arg, start_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

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

    return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_final, trans_loss, 0


def port_A_liquification(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for liquifying hydrogen at Port A.

    This function handles liquification specifically for the PH2 pathway where:
    - Pressurized gaseous H2 is transported to the port
    - H2 is liquified at the port for maritime transport as LH2
    - Only applies when B_fuel_type=0 (hydrogen pathway)

    Uses data-fitted liquification energy model that accounts for:
    - Plant capacity effects on specific energy consumption
    - Liquification equipment efficiency
    - BOG losses during liquification (1.6% of throughput)

    Args:
        A (float): Mass of hydrogen to liquefy (kg)
        B_fuel_type (int): Fuel type (only applies when =0 for PH2→LH2 pathway)
        process_args_tuple (tuple): Contains liquification_data_fitting_helper,
            LH2_plant_capacity, EIM_liquefication, start_port_electricity_price_tuple,
            CO2e_start, calculate_liquefaction_capex_helper, start_port_country_name,
            carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, LH2_ener_consumed,
                G_emission, A, BOG_loss, insurance_cost=0)
    """
    (liquification_data_fitting_helper, LH2_plant_capacity_arg, EIM_liquefication_arg,
    start_port_electricity_price_tuple_arg, CO2e_start_arg, calculate_liquefaction_capex_helper_arg,
    start_port_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    if B_fuel_type != 0:
        return 0, 0, 0, 0, 0, A, 0, 0

    LH2_energy_required = liquification_data_fitting_helper(LH2_plant_capacity_arg) / (EIM_liquefication_arg / 100)
    LH2_ener_consumed = LH2_energy_required * A

    opex_money += LH2_ener_consumed * start_port_electricity_price_tuple_arg[2]

    # CAPEX
    capex_per_kg, om_cost_per_kg = calculate_liquefaction_capex_helper_arg(B_fuel_type, LH2_plant_capacity_arg)
    capex_money += capex_per_kg * A
    opex_money += om_cost_per_kg * A

    G_emission = LH2_ener_consumed * 0.2778 * CO2e_start_arg * 0.001

    BOG_loss = 0.016 * A

    # Carbon Tax
    carbon_tax = carbon_tax_per_ton_co2_dict_arg.get(start_port_country_name_arg, 0) * (G_emission / 1000)
    carbon_tax_money += carbon_tax

    return opex_money, capex_money, carbon_tax_money, LH2_ener_consumed, G_emission, A, BOG_loss, 0


def H2_pressurization_at_port_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for vaporizing and pressurizing LH2 at Port B.

    This function handles the conversion of LH2 back to pressurized gaseous H2 at the
    destination port (for the LH2 maritime → PH2 land delivery pathway):
    - Latent heat of vaporization (phase change from liquid to gas)
    - Sensible heat to warm gas from cryogenic to ambient temperature
    - Compression energy to reach target pipeline/storage pressure
    - Only applies when B_fuel_type=0 (hydrogen pathway)

    This step is necessary when:
    1. H2 is produced and liquified at Site A
    2. Transported as LH2 by ship
    3. Needs to be regasified and compressed at Port B for pipeline delivery to Site B

    Args:
        A (float): Mass of LH2 to vaporize and pressurize (kg)
        B_fuel_type (int): Fuel type (only applies when =0 for hydrogen)
        process_args_tuple (tuple): Contains latent_H_H2, specific_heat_H2, PH2_storage_V,
            numbers_of_PH2_storage, PH2_pressure_fnc_helper, multistage_compress_helper,
            multistage_eff, end_port_electricity_price_tuple, CO2e_end,
            end_port_country_name, carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, total_energy_consumed,
                G_emission, A, leak_loss, insurance_cost=0)
    """
    (latent_H_H2_arg, specific_heat_H2_arg, PH2_storage_V_arg,
    numbers_of_PH2_storage_arg, PH2_pressure_fnc_helper, multistage_compress_helper,
    multistage_eff_arg, end_port_electricity_price_tuple_arg, CO2e_end_arg,
    end_port_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    if B_fuel_type != 0:
        return 0, 0, 0, 0, 0, A, 0, 0

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

    return opex_money, capex_money, carbon_tax_money, total_energy_consumed, G_emission, A, leak_loss, 0


def PH2_port_B_to_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for transporting H2 from Port B to Site B via pipeline.

    This function models the final delivery leg for the PH2 pathway:
    - Similar to PH2_site_A_to_port_A but at destination
    - Accounts for pressure drop over pipeline distance
    - Calculates energy for maintaining flow
    - Determines final deliverable mass based on pressure constraints

    Only applies when B_fuel_type=0 (hydrogen pathway). For ammonia/methanol pathways,
    this step is skipped (returns pass-through values).

    Args:
        A (float): Mass of hydrogen to transport (kg)
        B_fuel_type (int): Fuel type (only applies when =0 for PH2 pathway)
        process_args_tuple (tuple): Contains PH2_density_fnc_helper, target_pressure_site_B,
            PH2_storage_V, numbers_of_PH2_storage_at_port_B, PH2_pressure_fnc_helper,
            coordinates (port lat/lng, end lat/lng), straight_line_dis_helper,
            kinematic_viscosity, velocity, pipeline params, energy helper,
            electricity price, CO2e, country, tax dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, ener_consumed,
                G_emission, A_final, trans_loss, insurance_cost=0)
    """
    (PH2_density_fnc_helper, target_pressure_site_B_arg, PH2_storage_V_arg,
    numbers_of_PH2_storage_at_port_B_arg, PH2_pressure_fnc_helper,
    end_port_lat_arg, end_port_lng_arg, coor_end_lat_arg, coor_end_lng_arg,
    straight_line_dis_helper, kinematic_viscosity_PH2_helper, compressor_velocity_arg,
    pipeline_diameter_arg, solve_colebrook_helper, epsilon_arg, PH2_transport_energy_helper,
    end_port_electricity_price_tuple_arg, CO2e_end_arg, end_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    if B_fuel_type != 0:
        return 0, 0, 0, 0, 0, A, 0, 0

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

    return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A_final, trans_loss, 0


def PH2_storage_at_site_B(A, B_fuel_type, C_recirculation_BOG, D_truck_apply, E_storage_apply, F_maritime_apply, process_args_tuple):
    """
    Calculate costs and emissions for storing pressurized H2 at destination Site B.

    This function handles final storage for the PH2 pathway:
    - Calculates storage pressure based on mass and vessel volume
    - Minimal energy consumption (pressurized gas storage is passive)
    - No BOG losses (compressed gas doesn't boil off like cryogenic liquids)
    - Only applies when B_fuel_type=0 (hydrogen pathway)

    This is primarily a bookkeeping step to track the final state of hydrogen
    in the supply chain.

    Args:
        A (float): Mass of hydrogen to store (kg)
        B_fuel_type (int): Fuel type (only applies when =0 for PH2 pathway)
        process_args_tuple (tuple): Contains PH2_storage_V_at_site_B,
            numbers_of_PH2_storage_at_site_B, PH2_pressure_fnc_helper,
            end_country_name, carbon_tax_per_ton_co2_dict

    Returns:
        tuple: (opex_money, capex_money, carbon_tax_money, ener_consumed,
                G_emission, A, BOG_loss, insurance_cost=0)
    """
    (PH2_storage_V_at_site_B_arg, numbers_of_PH2_storage_at_site_B_arg, PH2_pressure_fnc_helper,
    end_country_name_arg, carbon_tax_per_ton_co2_dict_arg) = process_args_tuple

    opex_money = 0
    capex_money = 0
    carbon_tax_money = 0

    if B_fuel_type != 0:
        return 0, 0, 0, 0, 0, A, 0, 0

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

    return opex_money, capex_money, carbon_tax_money, ener_consumed, G_emission, A, BOG_loss, 0
