"""
models/insurance_model.py
Insurance cost calculations for cargo shipments.
Extracted from app.py for better organization.
"""

from constants import (
    INSURANCE_PERCENTAGE_OF_CARGO_VALUE,
    BASE_PER_TRANSIT_INSURANCE_PERCENTAGE,
    MINIMUM_INSURANCE_PREMIUM_USD,
    COMMODITY_RISK_FACTORS,
    BROKERAGE_AND_AGENT_FEE_USD,
    ROUTE_RISK_ZONES
)
from utils.helpers import calculate_route_risk_multiplier


def calculate_insurance_cost(cargo_value_usd, commodity_type, route_risk_multiplier=1.0):
    """
    Calculate insurance cost for a shipment.

    Args:
        cargo_value_usd: Total value of cargo in USD
        commodity_type: Type of commodity (e.g., "Liquid Hydrogen", "Strawberry")
        route_risk_multiplier: Risk multiplier based on route (from route risk zones)

    Returns:
        dict: Dictionary with insurance cost breakdown
    """
    # Get commodity risk factor
    commodity_risk = COMMODITY_RISK_FACTORS.get(commodity_type, 1.0)

    # Calculate base insurance rate
    base_rate = BASE_PER_TRANSIT_INSURANCE_PERCENTAGE / 100.0  # Convert to decimal

    # Apply risk multipliers
    adjusted_rate = base_rate * commodity_risk * route_risk_multiplier

    # Calculate premium
    insurance_premium = cargo_value_usd * adjusted_rate

    # Apply minimum premium
    if insurance_premium < MINIMUM_INSURANCE_PREMIUM_USD:
        insurance_premium = MINIMUM_INSURANCE_PREMIUM_USD

    return {
        'base_rate_pct': BASE_PER_TRANSIT_INSURANCE_PERCENTAGE,
        'commodity_risk_factor': commodity_risk,
        'route_risk_multiplier': route_risk_multiplier,
        'adjusted_rate_pct': adjusted_rate * 100,
        'insurance_premium_usd': insurance_premium,
        'minimum_premium_applied': insurance_premium == MINIMUM_INSURANCE_PREMIUM_USD
    }


def calculate_brokerage_fees(num_shipments=1):
    """
    Calculate brokerage and agent fees.

    Args:
        num_shipments: Number of shipments

    Returns:
        float: Total brokerage fees in USD
    """
    return BROKERAGE_AND_AGENT_FEE_USD * num_shipments


def calculate_total_insurance_and_fees(cargo_value_usd, commodity_type,
                                       route_risk_multiplier=1.0, num_shipments=1):
    """
    Calculate total insurance and associated fees.

    Args:
        cargo_value_usd: Total value of cargo in USD
        commodity_type: Type of commodity
        route_risk_multiplier: Risk multiplier based on route
        num_shipments: Number of shipments

    Returns:
        dict: Complete breakdown of insurance and fees
    """
    insurance_details = calculate_insurance_cost(cargo_value_usd, commodity_type, route_risk_multiplier)
    brokerage = calculate_brokerage_fees(num_shipments)

    total_cost = insurance_details['insurance_premium_usd'] + brokerage

    return {
        'insurance_premium_usd': insurance_details['insurance_premium_usd'],
        'brokerage_fees_usd': brokerage,
        'total_insurance_and_fees_usd': total_cost,
        'insurance_details': insurance_details
    }


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
