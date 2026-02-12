"""
models/ship_calculations.py
Ship-related calculations including speed, fuel consumption, and voyage costs.
Extracted from app.py for better organization.
"""

from constants import VOYAGE_OVERHEADS_DATA


def calculate_ship_speed(ship_type):
    """
    Get typical speed for different ship types.

    Args:
        ship_type: Ship type identifier (string)

    Returns:
        float: Ship speed in knots
    """
    speed_map = {
        'small': 15.0,
        'midsized': 18.0,
        'standard': 20.0,
        'q-flex': 19.5,
        'q-max': 19.0
    }
    return speed_map.get(ship_type, 18.0)


def calculate_voyage_time_days(distance_km, ship_type):
    """
    Calculate voyage time in days based on distance and ship type.

    Args:
        distance_km: Distance in kilometers
        ship_type: Ship type identifier

    Returns:
        float: Voyage time in days
    """
    speed_knots = calculate_ship_speed(ship_type)
    distance_nm = distance_km / 1.852  # Convert km to nautical miles
    voyage_time_hours = distance_nm / speed_knots
    voyage_time_days = voyage_time_hours / 24.0
    return voyage_time_days


def calculate_ship_fuel_consumption(ship_type, voyage_time_days):
    """
    Calculate ship fuel consumption based on ship type and voyage duration.

    Args:
        ship_type: Ship type identifier
        voyage_time_days: Voyage duration in days

    Returns:
        float: Fuel consumption in metric tons
    """
    # Daily fuel consumption rates (metric tons/day) by ship type
    fuel_consumption_map = {
        'small': 25.0,
        'midsized': 40.0,
        'standard': 60.0,
        'q-flex': 150.0,
        'q-max': 180.0
    }

    daily_consumption = fuel_consumption_map.get(ship_type, 50.0)
    total_fuel = daily_consumption * voyage_time_days

    return total_fuel


def calculate_voyage_overhead_costs(ship_type, voyage_time_days, cargo_mass_kg,
                                    suez_transit=False, panama_transit=False):
    """
    Calculate all voyage overhead costs including operating, capital, port fees, and canal tolls.

    Args:
        ship_type: Ship type identifier
        voyage_time_days: Voyage duration in days
        cargo_mass_kg: Total cargo mass in kg
        suez_transit: Boolean indicating if route passes through Suez canal
        panama_transit: Boolean indicating if route passes through Panama canal

    Returns:
        dict: Dictionary with breakdown of all overhead costs in USD
    """
    if ship_type not in VOYAGE_OVERHEADS_DATA:
        ship_type = 'standard'  # Default fallback

    overheads = VOYAGE_OVERHEADS_DATA[ship_type]

    # Daily costs
    operating_cost = overheads['daily_operating_cost_usd'] * voyage_time_days
    capital_cost = overheads['daily_capital_cost_usd'] * voyage_time_days
    maintenance_cost = overheads['daily_maintenance_cost_usd'] * voyage_time_days

    # Port fees (charged at both origin and destination)
    port_fees = overheads['port_fee_usd'] * 2

    # Canal tolls (based on gross tonnage estimate)
    # Estimate GT from cargo mass (very rough approximation)
    estimated_gt = cargo_mass_kg / 1000.0  # Simplified: 1 ton cargo ≈ 1 GT

    suez_toll = 0.0
    if suez_transit:
        suez_toll = estimated_gt * overheads['suez_toll_per_gt_usd']

    panama_toll = 0.0
    if panama_transit:
        panama_toll = estimated_gt * overheads['panama_toll_per_gt_usd']

    total_overhead = (operating_cost + capital_cost + maintenance_cost +
                     port_fees + suez_toll + panama_toll)

    return {
        'operating_cost_usd': operating_cost,
        'capital_cost_usd': capital_cost,
        'maintenance_cost_usd': maintenance_cost,
        'port_fees_usd': port_fees,
        'suez_toll_usd': suez_toll,
        'panama_toll_usd': panama_toll,
        'total_overhead_usd': total_overhead
    }


def calculate_bunker_fuel_cost(fuel_tons, bunker_price_per_ton=650.0):
    """
    Calculate bunker fuel cost for ship.

    Args:
        fuel_tons: Fuel consumption in metric tons
        bunker_price_per_ton: Bunker fuel price in USD per metric ton (default: $650)

    Returns:
        float: Total bunker fuel cost in USD
    """
    return fuel_tons * bunker_price_per_ton


def calculate_ship_emissions(fuel_tons, emission_factor=3.114):
    """
    Calculate CO2 emissions from ship bunker fuel.

    Args:
        fuel_tons: Fuel consumption in metric tons
        emission_factor: Emission factor in tons CO2 per ton fuel (default: 3.114 for HFO)

    Returns:
        float: CO2 emissions in metric tons
    """
    return fuel_tons * emission_factor


def get_ship_capacity(ship_type):
    """
    Get typical cargo capacity for different ship types.

    Args:
        ship_type: Ship type identifier

    Returns:
        float: Cargo capacity in cubic meters
    """
    capacity_map = {
        'small': 25000,      # m³
        'midsized': 50000,   # m³
        'standard': 125000,  # m³
        'q-flex': 210000,    # m³
        'q-max': 266000      # m³
    }
    return capacity_map.get(ship_type, 125000)


def estimate_ship_gross_tonnage(ship_type):
    """
    Estimate gross tonnage for different ship types.

    Args:
        ship_type: Ship type identifier

    Returns:
        float: Gross tonnage (GT)
    """
    gt_map = {
        'small': 15000,
        'midsized': 35000,
        'standard': 75000,
        'q-flex': 130000,
        'q-max': 160000
    }
    return gt_map.get(ship_type, 75000)
