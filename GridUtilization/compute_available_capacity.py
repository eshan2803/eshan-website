"""
Compute hourly actual available capacity for California by resource type.
Combines:
  - Installed capacity by resource (from EIA via capacity_by_resource.json)
  - Solar hourly capacity factors (12 months x 24 hours)
  - Wind hourly capacity factors (12 months x 24 hours)
  - Hydro monthly capacity factors (varies by year based on wet/dry classification)
  - Fixed capacity factors for nuclear, geothermal, natural gas, biomass, etc.

Output: available_capacity.json
"""

import json
import os

# ─── Solar Capacity Factors (12 months x 24 hours) ───────────────────────────
# Source: Derived from EIA-930 actual hourly generation (2020-2025) for CAL respondent.
# Method: p99 of (actual generation / installed capacity) per hour per month,
# capped at 1.0. This represents the maximum available output envelope.
# Values < 0.01 (measurement noise / auxiliary loads) are zeroed.
SOLAR_CF = [
    # Jan
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.033, 0.399, 0.722, 0.787, 0.778, 0.771, 0.781, 0.79, 0.712, 0.661, 0.491, 0.175, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Feb
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.172, 0.644, 0.842, 0.906, 0.903, 0.904, 0.892, 0.882, 0.856, 0.652, 0.578, 0.381, 0.051, 0.0, 0.0, 0.0, 0.0],
    # Mar
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.333, 0.732, 0.873, 0.922, 0.932, 0.939, 0.932, 0.95, 0.967, 0.902, 0.788, 0.703, 0.509, 0.141, 0.011, 0.0, 0.0],
    # Apr
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.284, 0.698, 0.868, 0.945, 0.98, 0.986, 0.983, 0.98, 0.962, 0.917, 0.827, 0.765, 0.638, 0.308, 0.028, 0.0, 0.0],
    # May
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.421, 0.759, 0.879, 0.944, 0.974, 0.98, 0.977, 0.974, 0.963, 0.929, 0.868, 0.806, 0.705, 0.404, 0.08, 0.0, 0.0],
    # Jun
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.089, 0.449, 0.767, 0.888, 0.951, 0.991, 1.0, 1.0, 0.994, 0.972, 0.938, 0.893, 0.846, 0.724, 0.462, 0.116, 0.0, 0.0],
    # Jul
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.026, 0.343, 0.702, 0.862, 0.936, 0.975, 0.994, 0.997, 0.989, 0.972, 0.941, 0.904, 0.845, 0.726, 0.461, 0.11, 0.0, 0.0],
    # Aug
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.235, 0.639, 0.848, 0.933, 0.977, 0.992, 0.994, 0.988, 0.966, 0.929, 0.905, 0.845, 0.707, 0.392, 0.062, 0.0, 0.0],
    # Sep
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.116, 0.559, 0.818, 0.905, 0.941, 0.949, 0.951, 0.947, 0.936, 0.905, 0.859, 0.796, 0.558, 0.162, 0.0, 0.0, 0.0],
    # Oct
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.039, 0.397, 0.74, 0.882, 0.884, 0.88, 0.89, 0.885, 0.876, 0.833, 0.792, 0.67, 0.307, 0.027, 0.0, 0.0, 0.0],
    # Nov
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.184, 0.604, 0.79, 0.832, 0.833, 0.832, 0.828, 0.822, 0.802, 0.799, 0.735, 0.484, 0.101, 0.013, 0.0, 0.0, 0.0],
    # Dec
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.065, 0.435, 0.712, 0.763, 0.753, 0.753, 0.758, 0.735, 0.717, 0.669, 0.471, 0.057, 0.012, 0.0, 0.0, 0.0, 0.0],
]

# ─── Wind Capacity Factors (12 months x 24 hours) ────────────────────────────
# Source: Derived from EIA-930 actual hourly generation (2020-2025) for CAL respondent.
# Method: p99 of (actual generation / installed capacity) per hour per month,
# capped at 1.0. This represents the maximum available output envelope.
# Wind in CA peaks in late afternoon/evening (Tehachapi, Altamont Pass thermal winds)
# and is generally higher at night than midday.
WIND_CF = [
    # Jan
    [0.694, 0.686, 0.678, 0.688, 0.679, 0.663, 0.646, 0.658, 0.597, 0.622, 0.627, 0.655, 0.669, 0.67, 0.694, 0.711, 0.674, 0.677, 0.65, 0.652, 0.675, 0.72, 0.708, 0.694],
    # Feb
    [0.717, 0.72, 0.714, 0.675, 0.694, 0.677, 0.701, 0.685, 0.673, 0.729, 0.723, 0.735, 0.739, 0.736, 0.755, 0.759, 0.766, 0.76, 0.777, 0.802, 0.78, 0.741, 0.727, 0.724],
    # Mar
    [0.803, 0.767, 0.79, 0.791, 0.804, 0.793, 0.762, 0.757, 0.729, 0.733, 0.797, 0.781, 0.798, 0.805, 0.804, 0.804, 0.826, 0.816, 0.851, 0.885, 0.852, 0.849, 0.807, 0.817],
    # Apr
    [0.893, 0.883, 0.873, 0.856, 0.826, 0.825, 0.815, 0.781, 0.764, 0.766, 0.767, 0.806, 0.809, 0.828, 0.848, 0.84, 0.854, 0.865, 0.865, 0.861, 0.849, 0.858, 0.833, 0.861],
    # May
    [0.923, 0.907, 0.879, 0.857, 0.866, 0.851, 0.831, 0.802, 0.783, 0.769, 0.801, 0.835, 0.853, 0.842, 0.87, 0.911, 0.905, 0.933, 0.903, 0.896, 0.891, 0.902, 0.893, 0.912],
    # Jun
    [0.878, 0.855, 0.834, 0.82, 0.806, 0.804, 0.807, 0.761, 0.732, 0.731, 0.731, 0.753, 0.752, 0.771, 0.791, 0.805, 0.85, 0.874, 0.887, 0.91, 0.902, 0.894, 0.89, 0.9],
    # Jul
    [0.838, 0.816, 0.805, 0.816, 0.796, 0.787, 0.758, 0.719, 0.69, 0.648, 0.614, 0.587, 0.573, 0.611, 0.659, 0.724, 0.769, 0.793, 0.833, 0.839, 0.817, 0.824, 0.827, 0.855],
    # Aug
    [0.853, 0.873, 0.853, 0.833, 0.836, 0.811, 0.766, 0.768, 0.714, 0.671, 0.621, 0.603, 0.58, 0.587, 0.633, 0.694, 0.73, 0.759, 0.791, 0.807, 0.831, 0.84, 0.868, 0.854],
    # Sep
    [0.776, 0.788, 0.783, 0.737, 0.7, 0.732, 0.734, 0.728, 0.624, 0.635, 0.641, 0.654, 0.691, 0.753, 0.76, 0.778, 0.787, 0.805, 0.82, 0.858, 0.824, 0.818, 0.806, 0.808],
    # Oct
    [0.753, 0.732, 0.747, 0.713, 0.713, 0.715, 0.735, 0.713, 0.696, 0.709, 0.679, 0.658, 0.718, 0.72, 0.738, 0.735, 0.76, 0.744, 0.779, 0.779, 0.788, 0.793, 0.767, 0.744],
    # Nov
    [0.677, 0.689, 0.691, 0.676, 0.658, 0.639, 0.617, 0.611, 0.625, 0.649, 0.659, 0.686, 0.713, 0.72, 0.709, 0.681, 0.718, 0.683, 0.678, 0.672, 0.668, 0.704, 0.708, 0.7],
    # Dec
    [0.62, 0.652, 0.653, 0.634, 0.625, 0.604, 0.594, 0.603, 0.607, 0.567, 0.584, 0.596, 0.622, 0.649, 0.659, 0.69, 0.701, 0.683, 0.686, 0.676, 0.668, 0.678, 0.686, 0.658],
]

# ─── Hydro Monthly Capacity Factors by Year ──────────────────────────────────
# Source: Derived from CA DWR water year classifications and EIA generation data
# Water Year Types:
#   2020: Dry/Dry         → annual CF ~17%
#   2021: Critical/Critical → annual CF ~12%
#   2022: Critical/Critical → annual CF ~14%
#   2023: Wet/Wet          → annual CF ~26%
#   2024: Above Normal/AN  → annual CF ~24%
#   2025: Above Normal/BN  → annual CF ~21%
# Widened spread: Critical years have much lower winter/spring, wet years have dramatic spring peaks
HYDRO_CF = {
    # [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
    "2020": [0.09, 0.11, 0.15, 0.19, 0.23, 0.26, 0.25, 0.22, 0.18, 0.13, 0.09, 0.08],
    "2021": [0.06, 0.07, 0.08, 0.10, 0.11, 0.13, 0.16, 0.15, 0.14, 0.11, 0.07, 0.06],
    "2022": [0.07, 0.08, 0.10, 0.13, 0.15, 0.17, 0.19, 0.17, 0.15, 0.12, 0.08, 0.07],
    "2023": [0.16, 0.22, 0.38, 0.45, 0.44, 0.42, 0.37, 0.31, 0.24, 0.18, 0.14, 0.16],
    "2024": [0.14, 0.18, 0.31, 0.37, 0.38, 0.37, 0.33, 0.28, 0.22, 0.16, 0.13, 0.14],
    "2025": [0.12, 0.15, 0.24, 0.30, 0.31, 0.30, 0.27, 0.24, 0.19, 0.15, 0.11, 0.12],
}

# ─── Fixed Capacity Factors for Other Resources ──────────────────────────────
# Nuclear: Diablo Canyon baseload, ~92% availability
NUCLEAR_CF = 0.92
# Geothermal: Baseload, ~90% availability
GEOTHERMAL_CF = 0.90
# Natural Gas subcategories:
GAS_CCGT_CF = 0.90      # Combined cycle: efficient, baseload/intermediate
GAS_PEAKER_CF = 0.90    # Combustion turbine: peakers, available when needed
GAS_STEAM_CF = 0.85     # Steam turbine: older units, more maintenance
GAS_ICE_CF = 0.85       # ICE + Other: small, older units
# Biomass/biogas: Baseload-ish, ~80% availability
BIOMASS_CF = 0.80
# Battery storage: Not a generation source; represents discharge availability
# We'll include at 0 for generation capacity (it shifts load, doesn't generate)
BATTERY_CF = 0.0
# Other thermal (waste heat, petroleum coke, jet fuel, etc.): ~75% availability
OTHER_THERMAL_CF = 0.75

# ─── Resource Category Mapping ────────────────────────────────────────────────
# Maps EIA resource names to our simplified categories
RESOURCE_MAP = {
    "Solar": "Solar",
    "Wind": "Wind",
    "Water": "Hydro",
    "Nuclear": "Nuclear",
    "Geothermal": "Geothermal",
    "Natural Gas - CCGT": "Gas CCGT",
    "Natural Gas - Peaker": "Gas Peaker",
    "Natural Gas - Steam": "Gas Steam",
    "Natural Gas - ICE": "Gas ICE",
    "Electricity used for energy storage": "Battery Storage",
    # Biomass category
    "Wood Waste Solids": "Biomass",
    "Landfill Gas": "Biomass",
    "Other Biomass Gases ": "Biomass",
    "Agriculture Byproducts": "Biomass",
    "Municipal Solid Waste (All)": "Biomass",
    # Other thermal / fossil
    "Other Gas": "Other Thermal",
    "Jet Fuel": "Other Thermal",
    "Disillate Fuel Oil": "Other Thermal",
    "Waste Heat": "Other Thermal",
    "Refined Coal": "Other Thermal",
    "Bituminous Coal": "Other Thermal",
    "Petroleum Coke": "Other Thermal",
    "Purchased Steam": "Other Thermal",
    "Gaseous Propane": "Other Thermal",
    "Other": "Other Thermal",
}

# Category to capacity factor mapping (for non-variable resources)
CATEGORY_CF = {
    "Nuclear": NUCLEAR_CF,
    "Geothermal": GEOTHERMAL_CF,
    "Gas CCGT": GAS_CCGT_CF,
    "Gas Peaker": GAS_PEAKER_CF,
    "Gas Steam": GAS_STEAM_CF,
    "Gas ICE": GAS_ICE_CF,
    "Biomass": BIOMASS_CF,
    "Battery Storage": BATTERY_CF,
    "Other Thermal": OTHER_THERMAL_CF,
}

# Categories in display order
CATEGORIES = [
    "Solar", "Wind", "Hydro", "Nuclear",
    "Gas CCGT", "Gas Peaker", "Gas Steam", "Gas ICE",
    "Geothermal", "Biomass", "Battery Storage", "Other Thermal"
]


def load_installed_capacity(path="capacity_by_resource.json"):
    """Load installed capacity and aggregate by category."""
    with open(path, "r") as f:
        raw = json.load(f)

    aggregated = {}
    for year_str, resources in raw.items():
        cat_capacity = {}
        for resource, mw in resources.items():
            cat = RESOURCE_MAP.get(resource, "Other Thermal")
            cat_capacity[cat] = cat_capacity.get(cat, 0) + mw
        aggregated[year_str] = cat_capacity

    return aggregated


def compute_hourly_available(installed, year_str, month_idx):
    """
    Compute 24-hour available capacity (MW) for each category.
    month_idx: 0=Jan, 11=Dec
    Returns dict of {category: [24 hourly MW values]}
    """
    result = {}
    for cat in CATEGORIES:
        cap_mw = installed.get(cat, 0)
        hourly = [0.0] * 24

        if cat == "Solar":
            for h in range(24):
                hourly[h] = round(cap_mw * SOLAR_CF[month_idx][h], 1)
        elif cat == "Wind":
            for h in range(24):
                hourly[h] = round(cap_mw * WIND_CF[month_idx][h], 1)
        elif cat == "Hydro":
            cf = HYDRO_CF.get(year_str, HYDRO_CF["2025"])[month_idx]
            hourly = [round(cap_mw * cf, 1)] * 24
        else:
            cf = CATEGORY_CF.get(cat, 0.75)
            hourly = [round(cap_mw * cf, 1)] * 24

        result[cat] = hourly

    # Compute total
    total = [0.0] * 24
    for h in range(24):
        total[h] = round(sum(result[cat][h] for cat in CATEGORIES), 1)
    result["Total"] = total

    return result


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cap_path = os.path.join(script_dir, "capacity_by_resource.json")

    print("==============================================")
    print("California Hourly Available Capacity by Resource")
    print("Years: 2020-2025, 12 months x 24 hours")
    print("==============================================")

    installed = load_installed_capacity(cap_path)

    output = {}
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for year_str in sorted(installed.keys()):
        year_data = {}
        cap = installed[year_str]

        print(f"\n--- {year_str} ---")
        gas_total = sum(cap.get(g, 0) for g in ['Gas CCGT', 'Gas Peaker', 'Gas Steam', 'Gas ICE'])
        print(f"  Installed: Solar={cap.get('Solar',0):,.0f} MW, "
              f"Wind={cap.get('Wind',0):,.0f} MW, "
              f"Hydro={cap.get('Hydro',0):,.0f} MW, "
              f"Gas={gas_total:,.0f} MW (CCGT={cap.get('Gas CCGT',0):,.0f}, "
              f"Peaker={cap.get('Gas Peaker',0):,.0f}, "
              f"Steam={cap.get('Gas Steam',0):,.0f}, "
              f"ICE={cap.get('Gas ICE',0):,.0f}), "
              f"Nuclear={cap.get('Nuclear',0):,.0f} MW")

        hydro_type = {
            "2020": "Dry", "2021": "Critical", "2022": "Critical",
            "2023": "Wet", "2024": "Above Normal", "2025": "Above Normal/Below Normal"
        }
        print(f"  Hydro year type: {hydro_type.get(year_str, 'Unknown')}")

        for m in range(12):
            month_key = f"{m+1:02d}"
            hourly = compute_hourly_available(cap, year_str, m)
            year_data[month_key] = hourly

            # Print peak hour summary
            peak_total = max(hourly["Total"])
            peak_solar = max(hourly["Solar"])
            peak_wind = max(hourly["Wind"])
            hydro_val = hourly["Hydro"][0]
            print(f"  {month_names[m]}: Peak Total={peak_total:,.0f} MW "
                  f"(Solar={peak_solar:,.0f}, Wind={peak_wind:,.0f}, Hydro={hydro_val:,.0f})")

        output[year_str] = year_data

    # Save output
    output_path = os.path.join(script_dir, "available_capacity.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {output_path}")

    # Print a sample: June 2023 (wet year, peak solar/wind month)
    print("\n--- Sample: June 2023 (Wet Year) ---")
    print(f"{'Hour':>5}", end="")
    for cat in CATEGORIES:
        print(f"  {cat:>14}", end="")
    print(f"  {'Total':>14}")
    print("-" * (5 + (14 + 2) * (len(CATEGORIES) + 1)))

    june_2023 = output["2023"]["06"]
    for h in range(24):
        print(f"{h:>5}", end="")
        for cat in CATEGORIES:
            print(f"  {june_2023[cat][h]:>14,.1f}", end="")
        print(f"  {june_2023['Total'][h]:>14,.1f}")

    # Also print metadata about assumptions
    print("\n--- Assumptions ---")
    print("Solar/Wind: Hourly profiles from typical CA capacity factor data")
    print("Hydro: Monthly CFs derived from CA DWR water year classifications")
    print("  2020: Dry (Sac Valley + San Joaquin)")
    print("  2021: Critically Dry")
    print("  2022: Critically Dry")
    print("  2023: Wet")
    print("  2024: Above Normal")
    print("  2025: Above Normal (Sacramento) / Below Normal (San Joaquin)")
    print(f"Nuclear: {NUCLEAR_CF*100:.0f}% constant (Diablo Canyon baseload)")
    print(f"Geothermal: {GEOTHERMAL_CF*100:.0f}% constant (baseload)")
    print(f"Gas CCGT: {GAS_CCGT_CF*100:.0f}% availability (combined cycle)")
    print(f"Gas Peaker: {GAS_PEAKER_CF*100:.0f}% availability (combustion turbine)")
    print(f"Gas Steam: {GAS_STEAM_CF*100:.0f}% availability (steam turbine)")
    print(f"Gas ICE: {GAS_ICE_CF*100:.0f}% availability (reciprocating engine + other)")
    print(f"Biomass: {BIOMASS_CF*100:.0f}% constant")
    print(f"Battery Storage: Excluded from generation (load-shifting resource)")
    print(f"Other Thermal: {OTHER_THERMAL_CF*100:.0f}% availability")


if __name__ == "__main__":
    main()
