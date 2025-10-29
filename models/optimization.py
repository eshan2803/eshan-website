"""
models/optimization.py
Optimization functions for weight calculations and other optimization problems.
Extracted from app.py for better organization.
"""

from scipy.optimize import minimize
import numpy as np


def optimize_truck_weight_distribution(total_cargo_kg, num_trucks, max_weight_per_truck_kg=40000):
    """
    Optimize distribution of cargo weight across multiple trucks.

    Args:
        total_cargo_kg: Total cargo mass in kg
        num_trucks: Number of trucks available
        max_weight_per_truck_kg: Maximum weight per truck in kg (default: 40,000 kg)

    Returns:
        list: Optimized weight distribution (kg per truck)
    """
    # Simple equal distribution with capacity check
    weight_per_truck = total_cargo_kg / num_trucks

    if weight_per_truck > max_weight_per_truck_kg:
        # Need more trucks
        required_trucks = int(np.ceil(total_cargo_kg / max_weight_per_truck_kg))
        weight_per_truck = total_cargo_kg / required_trucks
        distribution = [weight_per_truck] * required_trucks
    else:
        distribution = [weight_per_truck] * num_trucks

    return distribution


def optimize_ship_loading(cargo_mass_kg, cargo_volume_m3, ship_capacity_m3,
                          max_payload_kg=None):
    """
    Optimize ship loading considering both mass and volume constraints.

    Args:
        cargo_mass_kg: Total cargo mass in kg
        cargo_volume_m3: Total cargo volume in cubic meters
        ship_capacity_m3: Ship capacity in cubic meters
        max_payload_kg: Maximum payload in kg (optional)

    Returns:
        dict: Loading optimization results
    """
    # Check volume constraint
    if cargo_volume_m3 > ship_capacity_m3:
        volume_utilization = 1.0
        actual_cargo_volume = ship_capacity_m3
        volume_limited = True
        # Scale down mass proportionally
        actual_cargo_mass = cargo_mass_kg * (ship_capacity_m3 / cargo_volume_m3)
    else:
        volume_utilization = cargo_volume_m3 / ship_capacity_m3
        actual_cargo_volume = cargo_volume_m3
        actual_cargo_mass = cargo_mass_kg
        volume_limited = False

    # Check mass constraint if provided
    mass_limited = False
    if max_payload_kg and actual_cargo_mass > max_payload_kg:
        mass_limited = True
        actual_cargo_mass = max_payload_kg
        # Scale down volume proportionally
        actual_cargo_volume = cargo_volume_m3 * (max_payload_kg / cargo_mass_kg)
        volume_utilization = actual_cargo_volume / ship_capacity_m3

    num_shipments_needed = np.ceil(cargo_mass_kg / actual_cargo_mass)

    return {
        'actual_cargo_mass_kg': actual_cargo_mass,
        'actual_cargo_volume_m3': actual_cargo_volume,
        'volume_utilization': volume_utilization,
        'volume_limited': volume_limited,
        'mass_limited': mass_limited,
        'num_shipments_needed': int(num_shipments_needed)
    }


def optimize_refrigeration_temperature(ambient_temp_c, target_temp_c, transit_time_days,
                                       food_type="generic"):
    """
    Optimize refrigeration temperature and power settings for food transport.

    Args:
        ambient_temp_c: Ambient temperature in Celsius
        target_temp_c: Target refrigeration temperature in Celsius
        transit_time_days: Transit time in days
        food_type: Type of food product

    Returns:
        dict: Optimized refrigeration settings
    """
    # Temperature safety margins by food type
    safety_margins = {
        "strawberry": 0.5,   # Very sensitive
        "hass_avocado": 1.0,
        "banana": 1.5,
        "generic": 1.0
    }

    safety_margin = safety_margins.get(food_type, 1.0)

    # Optimal setpoint slightly below target for safety
    optimal_setpoint = target_temp_c - safety_margin

    # Temperature differential
    temp_differential = ambient_temp_c - optimal_setpoint

    # Estimated COP (coefficient of performance)
    # Using simplified Carnot efficiency
    carnot_cop = (optimal_setpoint + 273.15) / temp_differential
    actual_cop = carnot_cop * 0.4  # Real systems achieve ~40% of Carnot

    # Bound COP to realistic values
    actual_cop = max(0.5, min(actual_cop, 4.0))

    return {
        'optimal_setpoint_c': optimal_setpoint,
        'temp_differential_c': temp_differential,
        'estimated_cop': actual_cop,
        'safety_margin_c': safety_margin
    }


def optimize_storage_pressure(storage_mass_kg, storage_volume_m3, fuel_type="hydrogen"):
    """
    Optimize storage pressure for fuel transport.

    Args:
        storage_mass_kg: Mass to be stored in kg
        storage_volume_m3: Available storage volume in cubic meters
        fuel_type: Type of fuel ("hydrogen", "ammonia", "methanol")

    Returns:
        dict: Optimized storage parameters
    """
    required_density = storage_mass_kg / storage_volume_m3  # kg/m³

    if fuel_type == "hydrogen":
        # For compressed hydrogen, pressure is related to density
        # Using simplified relationship: P ≈ 0.027 * density + 2 (bar)
        from utils.conversions import PH2_pressure_fnc

        optimal_pressure = PH2_pressure_fnc(required_density)

        # Typical compressed H2 storage: 350-700 bar
        if optimal_pressure < 350:
            optimal_pressure = 350
            actual_density = (optimal_pressure - 2) / 0.027
        elif optimal_pressure > 700:
            optimal_pressure = 700
            actual_density = (optimal_pressure - 2) / 0.027
        else:
            actual_density = required_density

        return {
            'optimal_pressure_bar': optimal_pressure,
            'actual_density_kg_m3': actual_density,
            'required_volume_m3': storage_mass_kg / actual_density,
            'storage_type': 'compressed'
        }

    elif fuel_type == "ammonia":
        # Ammonia typically stored at moderate pressure (10-20 bar) or refrigerated
        optimal_pressure = 15.0  # bar
        actual_density = 600.0  # kg/m³ (liquid ammonia)

        return {
            'optimal_pressure_bar': optimal_pressure,
            'actual_density_kg_m3': actual_density,
            'required_volume_m3': storage_mass_kg / actual_density,
            'storage_type': 'pressurized_liquid'
        }

    elif fuel_type == "methanol":
        # Methanol stored as liquid at atmospheric pressure
        optimal_pressure = 1.0  # bar (atmospheric)
        actual_density = 792.0  # kg/m³

        return {
            'optimal_pressure_bar': optimal_pressure,
            'actual_density_kg_m3': actual_density,
            'required_volume_m3': storage_mass_kg / actual_density,
            'storage_type': 'liquid_atmospheric'
        }

    else:
        raise ValueError(f"Unknown fuel type: {fuel_type}")


def minimize_total_cost(cost_function, initial_guess, constraints=None, bounds=None):
    """
    Generic optimization function to minimize total cost.

    Args:
        cost_function: Function to minimize (takes array of variables)
        initial_guess: Initial guess for variables
        constraints: Optional constraints (scipy format)
        bounds: Optional bounds for variables (list of tuples)

    Returns:
        dict: Optimization result
    """
    result = minimize(
        cost_function,
        initial_guess,
        method='SLSQP',
        constraints=constraints,
        bounds=bounds,
        options={'maxiter': 1000, 'ftol': 1e-6}
    )

    return {
        'success': result.success,
        'optimal_values': result.x,
        'optimal_cost': result.fun,
        'message': result.message,
        'iterations': result.nit
    }
