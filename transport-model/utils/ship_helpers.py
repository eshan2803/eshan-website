"""
utils/ship_helpers.py
Ship-related helper calculations.
Extracted from app.py for better organization.
"""

import numpy as np


def calculate_ship_power_kw(ship_volume_m3):
    """
    Estimate ship propulsion power based on cargo volume.
    Uses interpolation from typical ship data.

    Args:
        ship_volume_m3: Ship cargo volume in cubic meters

    Returns:
        float: Estimated propulsion power in kW
    """
    # Reference data: (volume_m3, power_kw)
    power_scaling_data = [
        (20000, 7000),
        (90000, 15000),
        (174000, 19900),
        (210000, 25000),
        (266000, 43540)
    ]

    volumes_m3 = [p[0] for p in power_scaling_data]
    powers_kw = [p[1] for p in power_scaling_data]

    # Interpolate
    power_kw = np.interp(ship_volume_m3, volumes_m3, powers_kw)

    return power_kw
