"""
models/capex_calculations.py
Capital expenditure (CAPEX) and operational expenditure (OPEX) calculations
for fuel infrastructure including liquefaction, storage, and loading/unloading.
Extracted from app.py for better organization and reusability.
"""

from constants import (
    LOADING_UNLOADING_CAPEX_PARAMS,
    REFERENCE_ANNUAL_THROUGHPUT_TONS,
    VOYAGE_OVERHEADS_DATA
)


def calculate_liquefaction_capex(fuel_type, capacity_tpd, cargo_mass_kg=None):
    """
    Estimates the amortized capital cost per kg for liquefaction of hydrogen, ammonia, or methanol.

    Source: Based on industry data for hydrogen and ammonia liquefaction costs; methanol assumed zero.

    For ammonia (fuel_type=1), uses cycle-based throughput calculation when cargo_mass_kg is provided,
    since ammonia liquefaction is just simple refrigeration at -33°C (not exotic cryogenics like LH2).

    Args:
        fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol
        capacity_tpd: Daily throughput in tons (used for LH2 only)
        cargo_mass_kg: Optional cargo mass for cycle-based calculation (used for ammonia)

    Returns:
        tuple: (capex_per_kg, om_cost_per_kg) - Both in USD/kg
    """
    cost_models = {
        0: {
            "small_scale": {"base_capex_M_usd": 138.6, "base_capacity": 27, "power_law_exp": 0.66},
            "large_scale": {"base_capex_M_usd": 762.67, "base_capacity": 800, "power_law_exp": 0.62}
        },
        1: {
            # Ammonia refrigeration (not cryogenics): -33°C vs -253°C for LH2
            # Base cost: $5M for 1000 TPD (330k tonnes/year = 330M kg/year) industrial refrigeration plant
            # This is ~27x cheaper per TPD than LH2 cryogenic systems, reflecting simpler technology
            "default": {"base_capex_M_usd": 5.0, "base_capacity_kg_per_year": 330_000_000, "power_law_exp": 0.7}
        },
        2: {
            "default": {"base_capex_M_usd": 0, "base_capacity": 1, "power_law_exp": 0}
        }
    }

    if fuel_type not in cost_models:
        return 0, 0

    # Select appropriate cost model
    if fuel_type == 0:  # Hydrogen has scale-dependent models
        model = cost_models[0]["large_scale"] if capacity_tpd > 100 else cost_models[0]["small_scale"]

        # Calculate total CAPEX using power law scaling
        total_capex_usd = (model['base_capex_M_usd'] * 1_000_000) * \
                          (capacity_tpd / model['base_capacity']) ** model['power_law_exp']

        # Calculate annual throughput (330 working days/year)
        annual_throughput_kg = capacity_tpd * 1000 * 330

    elif fuel_type == 1 and cargo_mass_kg is not None:  # Ammonia with cargo-based calculation
        model = cost_models[1]["default"]

        # Use cycle-based throughput (12 cargos per year)
        cargos_per_year = 12
        annual_throughput_kg = cargo_mass_kg * cargos_per_year

        # Calculate total CAPEX using power law scaling based on annual throughput
        total_capex_usd = (model['base_capex_M_usd'] * 1_000_000) * \
                          (annual_throughput_kg / model['base_capacity_kg_per_year']) ** model['power_law_exp']
    else:
        # Methanol or fallback
        model = cost_models[fuel_type]["default"]
        total_capex_usd = 0
        annual_throughput_kg = 1

    # Calculate annual O&M cost (4% of total CAPEX)
    annual_om_cost = total_capex_usd * 0.04

    # Annualize CAPEX (9% annualization factor)
    annualized_capex = total_capex_usd * 0.09

    if annual_throughput_kg == 0:
        return 0, 0

    # Calculate per-kg costs
    capex_per_kg = annualized_capex / annual_throughput_kg
    om_cost_per_kg = annual_om_cost / annual_throughput_kg

    return capex_per_kg, om_cost_per_kg


def calculate_storage_capex(fuel_type, capacity_tpd, storage_mass_kg, storage_days):
    """
    Estimates the amortized capital cost per kg for large-scale storage of hydrogen, ammonia, or methanol.

    Source: Based on industry data for cryogenic and chemical storage costs.

    Args:
        fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol
        capacity_tpd: Daily throughput in tons
        storage_mass_kg: Storage capacity in kg
        storage_days: Average storage duration in days

    Returns:
        tuple: (capex_per_kg, om_cost_per_kg) - Both in USD/kg
    """
    cost_models = {
        0: {  # Hydrogen (cryogenic storage)
            "base_capex_M_usd": 35,
            "base_capacity": 335000,
            "power_law_exp": 0.7
        },
        1: {  # Ammonia (pressurized/refrigerated storage)
            "base_capex_M_usd": 15,
            "base_capacity": 6650000,
            "power_law_exp": 0.7
        },
        2: {  # Methanol (atmospheric storage)
            "base_capex_M_usd": 1.5,
            "base_capacity": 5000000,
            "power_law_exp": 0.6
        }
    }

    if fuel_type not in cost_models:
        return 0, 0

    model = cost_models[fuel_type]

    # Calculate total CAPEX using power law scaling
    total_capex_usd = (model['base_capex_M_usd'] * 1_000_000) * \
                      (storage_mass_kg / model['base_capacity']) ** model['power_law_exp']

    # Calculate annual O&M cost (4% of total CAPEX)
    annual_om_cost = total_capex_usd * 0.04

    # Annualize CAPEX (9% annualization factor)
    annualized_capex = total_capex_usd * 0.09

    # Calculate annual throughput based on actual cargo cycles
    if storage_days == 0:
        return 0, 0
    cycles_per_year = 330 / storage_days
    annual_throughput_kg = storage_mass_kg * cycles_per_year

    if annual_throughput_kg == 0:
        return 0, 0

    # Calculate per-kg costs
    capex_per_kg = annualized_capex / annual_throughput_kg
    om_cost_per_kg = annual_om_cost / annual_throughput_kg

    return capex_per_kg, om_cost_per_kg


def calculate_loading_unloading_capex(fuel_type):
    """
    Estimates the amortized capital cost per kg for loading/unloading infrastructure (arms, jetties).

    Prorated based on assumed annual throughput of a typical terminal.

    Args:
        fuel_type: 0 for hydrogen, 1 for ammonia, 2 for methanol

    Returns:
        tuple: (capex_per_kg, om_cost_per_kg) - Both in USD/kg of throughput
    """
    capex_model = LOADING_UNLOADING_CAPEX_PARAMS.get(fuel_type)
    ref_throughput_tons_per_year = REFERENCE_ANNUAL_THROUGHPUT_TONS.get(fuel_type)

    if not capex_model or ref_throughput_tons_per_year == 0:
        return 0, 0

    # Calculate total facility CAPEX
    total_facility_capex_usd = capex_model['total_capex_M_usd'] * 1_000_000

    # Annualize CAPEX
    annualized_capex = total_facility_capex_usd * capex_model['annualization_factor']

    # Calculate annual O&M cost (4% of total CAPEX)
    annual_om_cost = total_facility_capex_usd * 0.04

    # Annual throughput in kg
    annual_throughput_kg = ref_throughput_tons_per_year * 1000

    # Calculate per-kg costs
    capex_per_kg_throughput = annualized_capex / annual_throughput_kg if annual_throughput_kg > 0 else 0
    om_cost_per_kg_throughput = annual_om_cost / annual_throughput_kg if annual_throughput_kg > 0 else 0

    return capex_per_kg_throughput, om_cost_per_kg_throughput


def calculate_voyage_overheads(voyage_duration_days, ship_params, canal_transits, port_regions=None):
    """
    Calculate voyage overhead costs including daily operating costs, port fees, canal tolls, and maintenance.

    Args:
        voyage_duration_days: Duration of voyage in days
        ship_params: Dictionary with ship parameters including 'gross_tonnage' and 'key' (ship type)
        canal_transits: Dictionary with 'suez' and 'panama' boolean flags
        port_regions: Optional dictionary with port region information (currently unused)

    Returns:
        tuple: (opex_overheads, capex_overheads) - Both in USD
    """
    ship_gt = ship_params['gross_tonnage']
    ship_key = ship_params.get('key', 'standard')

    # Get overhead parameters for this ship type
    overheads = VOYAGE_OVERHEADS_DATA.get(ship_key, VOYAGE_OVERHEADS_DATA['standard'])

    # 1. Calculate Daily Operating Costs (OPEX)
    daily_opex = overheads['daily_operating_cost_usd'] * voyage_duration_days

    # 2. Port Fees (charged at both origin and destination)
    port_fees_cost = overheads['port_fee_usd'] * 2

    # 3. Maintenance Costs
    maintenance_cost = overheads.get('daily_maintenance_cost_usd', 3000) * voyage_duration_days

    # 4. Canal Fees (based on gross tonnage)
    canal_fees_cost = 0
    if canal_transits.get("suez"):
        canal_fees_cost = ship_gt * overheads['suez_toll_per_gt_usd']
    elif canal_transits.get("panama"):
        canal_fees_cost = ship_gt * overheads['panama_toll_per_gt_usd']

    # Sum all operational overheads
    opex_overheads = daily_opex + port_fees_cost + canal_fees_cost + maintenance_cost

    # 5. Daily Capital Cost (CAPEX) - ship financing/depreciation
    capex_overheads = overheads['daily_capital_cost_usd'] * voyage_duration_days

    return opex_overheads, capex_overheads


def calculate_food_infra_capex(process_name, capacity_tons_per_day, throughput_kg, storage_days=0):
    """
    Calculate CAPEX for food processing infrastructure (freezing, precooling, cold storage).

    Args:
        process_name: Type of process ("freezing", "precool", "cold_storage")
        capacity_tons_per_day: Facility capacity in tons per day
        throughput_kg: Mass of product processed in kg
        storage_days: Storage duration in days (for cold_storage only)

    Returns:
        float: Amortized CAPEX per kg in USD/kg
    """
    # Base CAPEX models for different food processes (in millions USD)
    capex_models = {
        "freezing": {
            "base_capex_M_usd": 5.0,
            "base_capacity_tpd": 50,
            "power_law_exp": 0.65,
            "annualization_factor": 0.10
        },
        "precool": {
            "base_capex_M_usd": 2.0,
            "base_capacity_tpd": 100,
            "power_law_exp": 0.60,
            "annualization_factor": 0.10
        },
        "cold_storage": {
            "base_capex_M_usd": 10.0,
            "base_capacity_tpd": 200,
            "power_law_exp": 0.70,
            "annualization_factor": 0.09
        }
    }

    if process_name not in capex_models:
        return 0.0

    model = capex_models[process_name]

    # Calculate total CAPEX using power law scaling
    total_capex_usd = (model['base_capex_M_usd'] * 1_000_000) * \
                      (capacity_tons_per_day / model['base_capacity_tpd']) ** model['power_law_exp']

    # Annualize CAPEX
    annualized_capex = total_capex_usd * model['annualization_factor']

    # Calculate annual throughput
    if process_name == "cold_storage" and storage_days > 0:
        # For storage, calculate based on cycles per year
        cycles_per_year = 330 / storage_days
        annual_throughput_kg = throughput_kg * cycles_per_year
    else:
        # For processing, calculate based on daily capacity
        annual_throughput_kg = capacity_tons_per_day * 1000 * 330

    if annual_throughput_kg == 0:
        return 0.0

    # Calculate per-kg CAPEX
    capex_per_kg = annualized_capex / annual_throughput_kg

    return capex_per_kg
