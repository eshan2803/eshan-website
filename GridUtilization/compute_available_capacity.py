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
# Source: User-provided typical California solar profiles
SOLAR_CF = [
    # Jan
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.208, 0.486, 0.578, 0.486, 0.208, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Feb
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.126, 0.508, 0.699, 0.699, 0.508, 0.126, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Mar
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.34, 0.656, 0.813, 0.813, 0.656, 0.34, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Apr
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.242, 0.613, 0.837, 0.911, 0.837, 0.613, 0.242, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # May
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.428, 0.733, 0.917, 0.978, 0.917, 0.733, 0.428, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Jun
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.438, 0.75, 0.938, 1.0, 0.938, 0.75, 0.438, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Jul
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.126, 0.543, 0.821, 0.96, 0.96, 0.821, 0.543, 0.126, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Aug
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.242, 0.613, 0.837, 0.911, 0.837, 0.613, 0.242, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Sep
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.463, 0.741, 0.833, 0.741, 0.463, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Oct
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.126, 0.508, 0.699, 0.699, 0.508, 0.126, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Nov
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.467, 0.556, 0.467, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # Dec
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.278, 0.476, 0.476, 0.278, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
]

# ─── Wind Capacity Factors (12 months x 24 hours) ────────────────────────────
# Source: User-provided typical California wind profiles
WIND_CF = [
    # Jan
    [0.114, 0.104, 0.095, 0.095, 0.095, 0.095, 0.104, 0.114, 0.133, 0.152, 0.171, 0.19, 0.208, 0.228, 0.247, 0.284, 0.303, 0.284, 0.266, 0.266, 0.228, 0.19, 0.152, 0.133],
    # Feb
    [0.147, 0.135, 0.123, 0.123, 0.123, 0.123, 0.135, 0.147, 0.172, 0.197, 0.221, 0.246, 0.27, 0.295, 0.319, 0.369, 0.393, 0.369, 0.344, 0.344, 0.295, 0.246, 0.197, 0.172],
    # Mar
    [0.215, 0.197, 0.178, 0.178, 0.178, 0.178, 0.197, 0.215, 0.25, 0.285, 0.322, 0.357, 0.393, 0.428, 0.465, 0.535, 0.572, 0.535, 0.5, 0.5, 0.428, 0.357, 0.285, 0.25],
    # Apr
    [0.295, 0.27, 0.246, 0.246, 0.246, 0.246, 0.27, 0.295, 0.344, 0.393, 0.442, 0.491, 0.541, 0.59, 0.639, 0.736, 0.785, 0.736, 0.688, 0.688, 0.59, 0.491, 0.393, 0.344],
    # May
    [0.342, 0.314, 0.284, 0.284, 0.284, 0.284, 0.314, 0.342, 0.399, 0.455, 0.513, 0.569, 0.626, 0.683, 0.74, 0.854, 0.91, 0.854, 0.797, 0.797, 0.683, 0.569, 0.455, 0.399],
    # Jun
    [0.375, 0.344, 0.312, 0.312, 0.312, 0.312, 0.344, 0.375, 0.438, 0.5, 0.563, 0.625, 0.688, 0.75, 0.813, 0.938, 1.0, 0.938, 0.875, 0.875, 0.75, 0.625, 0.5, 0.438],
    # Jul
    [0.295, 0.27, 0.246, 0.246, 0.246, 0.246, 0.27, 0.295, 0.344, 0.393, 0.442, 0.491, 0.541, 0.59, 0.639, 0.736, 0.785, 0.736, 0.688, 0.688, 0.59, 0.491, 0.393, 0.344],
    # Aug
    [0.248, 0.227, 0.206, 0.206, 0.206, 0.206, 0.227, 0.248, 0.29, 0.33, 0.372, 0.413, 0.454, 0.496, 0.536, 0.62, 0.66, 0.62, 0.578, 0.578, 0.496, 0.413, 0.33, 0.29],
    # Sep
    [0.234, 0.215, 0.196, 0.196, 0.196, 0.196, 0.215, 0.234, 0.273, 0.312, 0.352, 0.391, 0.43, 0.469, 0.508, 0.585, 0.625, 0.585, 0.547, 0.547, 0.469, 0.391, 0.312, 0.273],
    # Oct
    [0.147, 0.135, 0.123, 0.123, 0.123, 0.123, 0.135, 0.147, 0.172, 0.197, 0.221, 0.246, 0.27, 0.295, 0.319, 0.369, 0.393, 0.369, 0.344, 0.344, 0.295, 0.246, 0.197, 0.172],
    # Nov
    [0.114, 0.104, 0.095, 0.095, 0.095, 0.095, 0.104, 0.114, 0.133, 0.152, 0.171, 0.19, 0.208, 0.228, 0.247, 0.284, 0.303, 0.284, 0.266, 0.266, 0.228, 0.19, 0.152, 0.133],
    # Dec
    [0.107, 0.098, 0.09, 0.09, 0.09, 0.09, 0.098, 0.107, 0.125, 0.143, 0.16, 0.178, 0.197, 0.215, 0.232, 0.268, 0.285, 0.268, 0.25, 0.25, 0.215, 0.178, 0.143, 0.125],
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
# Natural Gas: Dispatchable, available at ~90% of nameplate (maintenance/outages)
NATURAL_GAS_CF = 0.90
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
    "Natural Gas": "Natural Gas",
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
    "Natural Gas": NATURAL_GAS_CF,
    "Biomass": BIOMASS_CF,
    "Battery Storage": BATTERY_CF,
    "Other Thermal": OTHER_THERMAL_CF,
}

# Categories in display order
CATEGORIES = [
    "Solar", "Wind", "Hydro", "Nuclear", "Natural Gas",
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
        print(f"  Installed: Solar={cap.get('Solar',0):,.0f} MW, "
              f"Wind={cap.get('Wind',0):,.0f} MW, "
              f"Hydro={cap.get('Hydro',0):,.0f} MW, "
              f"Gas={cap.get('Natural Gas',0):,.0f} MW, "
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
    print(f"Natural Gas: {NATURAL_GAS_CF*100:.0f}% availability (dispatchable)")
    print(f"Biomass: {BIOMASS_CF*100:.0f}% constant")
    print(f"Battery Storage: Excluded from generation (load-shifting resource)")
    print(f"Other Thermal: {OTHER_THERMAL_CF*100:.0f}% availability")


if __name__ == "__main__":
    main()
