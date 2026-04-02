"""
Process CAISO fuel-source CSVs to calculate daily energy totals (MWh) with import breakdown.

Uses import dispatch data from curtailmentdata folder to classify imports as clean vs. fossil.

Categories:
  - Fossil (Natural Gas from CAISO + fossil imports)
  - Clean Energy (renewables + nuclear + hydro + batteries + clean imports)

Outputs:
  - daily_energy_with_import_breakdown.json: Daily MWh by category and clean %
"""
import os
import csv
import json
import glob
import pandas as pd
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
IMPORT_DISPATCH_FILE = r"c:\Users\eshan\OneDrive\Desktop\eshan-website\curtailmentdata\EIA_Import_Dispatch_and_CI_2019_2024.csv"
OUT_FILE = os.path.join(os.path.dirname(__file__), "daily_energy_with_import_breakdown.json")

# Clean energy sources in CAISO data
CLEAN_SOURCES = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Nuclear", "Large Hydro", "Large hydro"
]

# Import sources classification
IMPORT_CLEAN_SOURCES = ["Nuclear", "Geothermal", "Large Hydro", "Small Hydro", "Solar", "Wind", "Biomass"]
IMPORT_FOSSIL_SOURCES = ["Coal", "Natural Gas", "Oil"]
# "Unspecified" and "Other" will be kept separate as unknown

print("Loading import dispatch data...")
import_df = pd.read_csv(IMPORT_DISPATCH_FILE)

# Convert Date to datetime and create a lookup key
import_df['Date_dt'] = pd.to_datetime(import_df['Date'])
import_df['Date_key'] = import_df['Date_dt'].dt.strftime('%Y-%m-%d')
import_df['Hour_key'] = import_df['Hour'].astype(int)

# Create lookup dictionary: (date, hour) -> import breakdown
import_lookup = {}
for _, row in import_df.iterrows():
    key = (row['Date_key'], row['Hour_key'])

    # Calculate clean vs fossil imports
    clean_import_mwh = 0.0
    fossil_import_mwh = 0.0
    unknown_import_mwh = 0.0

    for source in IMPORT_CLEAN_SOURCES:
        clean_import_mwh += row.get(f'NW_{source}_MWh', 0) or 0
        clean_import_mwh += row.get(f'SW_{source}_MWh', 0) or 0

    for source in IMPORT_FOSSIL_SOURCES:
        fossil_import_mwh += row.get(f'NW_{source}_MWh', 0) or 0
        fossil_import_mwh += row.get(f'SW_{source}_MWh', 0) or 0

    # Unknown = Unspecified + Other
    unknown_import_mwh += row.get('NW_Unspecified_MWh', 0) or 0
    unknown_import_mwh += row.get('NW_Other_MWh', 0) or 0
    unknown_import_mwh += row.get('SW_Unspecified_MWh', 0) or 0
    unknown_import_mwh += row.get('SW_Other_MWh', 0) or 0

    import_lookup[key] = {
        'clean': clean_import_mwh,
        'fossil': fossil_import_mwh,
        'unknown': unknown_import_mwh
    }

print(f"Loaded import data for {len(import_lookup)} hour entries")

# Calculate 2024 average ratios for use with 2025 data
print("Calculating 2024 average import ratios...")
import_2024 = import_df[import_df['Date_dt'].dt.year == 2024]

total_2024_clean = 0.0
total_2024_fossil = 0.0
total_2024_unknown = 0.0

for _, row in import_2024.iterrows():
    for source in IMPORT_CLEAN_SOURCES:
        total_2024_clean += row.get(f'NW_{source}_MWh', 0) or 0
        total_2024_clean += row.get(f'SW_{source}_MWh', 0) or 0

    for source in IMPORT_FOSSIL_SOURCES:
        total_2024_fossil += row.get(f'NW_{source}_MWh', 0) or 0
        total_2024_fossil += row.get(f'SW_{source}_MWh', 0) or 0

    total_2024_unknown += row.get('NW_Unspecified_MWh', 0) or 0
    total_2024_unknown += row.get('NW_Other_MWh', 0) or 0
    total_2024_unknown += row.get('SW_Unspecified_MWh', 0) or 0
    total_2024_unknown += row.get('SW_Other_MWh', 0) or 0

total_2024 = total_2024_clean + total_2024_fossil + total_2024_unknown
if total_2024 > 0:
    ratio_2024_clean = total_2024_clean / total_2024
    ratio_2024_fossil = total_2024_fossil / total_2024
    ratio_2024_unknown = total_2024_unknown / total_2024
else:
    ratio_2024_clean = 0.5
    ratio_2024_fossil = 0.3
    ratio_2024_unknown = 0.2

print(f"2024 import ratios: Clean={ratio_2024_clean*100:.1f}%, Fossil={ratio_2024_fossil*100:.1f}%, Unknown={ratio_2024_unknown*100:.1f}%")

daily_data = {}

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"\nProcessing {len(files)} fuelsource CSV files...")

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    date_key = dt.strftime("%Y-%m-%d")

    # Accumulate MWh for each category (5-min intervals = 1/12 hour)
    caiso_fossil_mwh = 0.0  # Natural gas from CAISO
    caiso_clean_mwh = 0.0   # Clean sources from CAISO
    import_clean_mwh = 0.0   # Clean imports
    import_fossil_mwh = 0.0  # Fossil imports
    import_unknown_mwh = 0.0 # Unknown imports
    gross_demand_mwh = 0.0

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Get hour (1-24 format)
                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                    if hour == 0:  # Handle midnight as hour 24
                        hour = 24
                except (ValueError, IndexError):
                    continue

                # Get natural gas from CAISO (handle both capitalizations)
                try:
                    gas_mw = float(row.get("Natural Gas") or row.get("Natural gas") or 0)
                except (ValueError, TypeError):
                    gas_mw = 0.0

                # Get clean energy sources from CAISO
                clean_mw = 0.0
                for col in CLEAN_SOURCES:
                    try:
                        val = float(row.get(col) or 0)
                        clean_mw += val
                    except (ValueError, TypeError):
                        pass

                # Get battery discharge (positive battery = discharge = supply)
                try:
                    battery_mw = float(row.get("Batteries") or 0)
                    if battery_mw > 0:  # Only count discharge as clean supply
                        clean_mw += battery_mw
                except (ValueError, TypeError):
                    pass

                # Get CAISO total imports
                try:
                    total_import_mw = float(row.get("Imports") or 0)
                except (ValueError, TypeError):
                    total_import_mw = 0.0

                interval_hours = 1.0 / 12.0
                total_import_mwh = total_import_mw * interval_hours

                # Get classification ratios from dispatch model
                import_key = (date_key, hour)
                if import_key in import_lookup and total_import_mwh > 0:
                    import_data = import_lookup[import_key]
                    # Calculate total from dispatch model
                    dispatch_total = import_data['clean'] + import_data['fossil'] + import_data['unknown']

                    if dispatch_total > 0:
                        # Use dispatch model RATIOS but apply to CAISO total
                        ratio_clean = import_data['clean'] / dispatch_total
                        ratio_fossil = import_data['fossil'] / dispatch_total
                        ratio_unknown = import_data['unknown'] / dispatch_total

                        import_clean_interval = total_import_mwh * ratio_clean
                        import_fossil_interval = total_import_mwh * ratio_fossil
                        import_unknown_interval = total_import_mwh * ratio_unknown
                    else:
                        # Fallback to 2024 ratios
                        import_clean_interval = total_import_mwh * ratio_2024_clean
                        import_fossil_interval = total_import_mwh * ratio_2024_fossil
                        import_unknown_interval = total_import_mwh * ratio_2024_unknown
                else:
                    # No dispatch data - use 2024 ratios
                    import_clean_interval = total_import_mwh * ratio_2024_clean
                    import_fossil_interval = total_import_mwh * ratio_2024_fossil
                    import_unknown_interval = total_import_mwh * ratio_2024_unknown

                # Calculate gross demand (same as V1 - all CAISO sources)
                net_demand_mw = 0.0
                for col in ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
                           "Coal", "Nuclear", "Large Hydro", "Large hydro", "Natural Gas",
                           "Natural gas", "Batteries", "Imports", "Other"]:
                    try:
                        val = float(row.get(col) or 0)
                        net_demand_mw += val
                    except (ValueError, TypeError):
                        pass

                # Gross demand excludes battery charging
                try:
                    battery_mw_all = float(row.get("Batteries") or 0)
                    gross_demand_mw_interval = net_demand_mw - min(battery_mw_all, 0)
                except (ValueError, TypeError):
                    gross_demand_mw_interval = net_demand_mw

                # Accumulate MWh (5-min interval = 1/12 hour)
                interval_hours = 1.0 / 12.0
                caiso_fossil_mwh += gas_mw * interval_hours
                caiso_clean_mwh += clean_mw * interval_hours
                import_clean_mwh += import_clean_interval
                import_fossil_mwh += import_fossil_interval
                import_unknown_mwh += import_unknown_interval
                gross_demand_mwh += gross_demand_mw_interval * interval_hours

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Calculate totals (treat unknown as fossil)
    total_fossil_mwh = caiso_fossil_mwh + import_fossil_mwh + import_unknown_mwh
    total_clean_mwh = caiso_clean_mwh + import_clean_mwh

    # Calculate clean % (using total supply, not gross demand which may have rounding differences)
    total_supply = total_fossil_mwh + total_clean_mwh
    if total_supply > 0:
        clean_pct = (total_clean_mwh / total_supply) * 100.0
    else:
        clean_pct = 0.0

    daily_data[date_key] = {
        "fossil_mwh": round(total_fossil_mwh, 2),
        "clean_mwh": round(total_clean_mwh, 2),
        "gross_demand_mwh": round(gross_demand_mwh, 2),
        "clean_pct": round(clean_pct, 2)
    }

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Sort and save
sorted_daily = dict(sorted(daily_data.items()))
with open(OUT_FILE, "w") as f:
    json.dump(sorted_daily, f, indent=2)

print(f"\nSaved daily energy breakdown to {OUT_FILE}")
print(f"Processed {len(sorted_daily)} days from {list(sorted_daily.keys())[0]} to {list(sorted_daily.keys())[-1]}")

# Print summary statistics
all_fossil = [d["fossil_mwh"] for d in sorted_daily.values()]
all_clean = [d["clean_mwh"] for d in sorted_daily.values()]
all_demand = [d["gross_demand_mwh"] for d in sorted_daily.values()]
all_clean_pct = [d["clean_pct"] for d in sorted_daily.values()]

print(f"\nSummary:")
print(f"  Average daily fossil energy (incl. unknown imports): {sum(all_fossil)/len(all_fossil):,.0f} MWh")
print(f"  Average daily clean energy: {sum(all_clean)/len(all_clean):,.0f} MWh")
print(f"  Average daily gross demand: {sum(all_demand)/len(all_demand):,.0f} MWh")
print(f"  Average clean %: {sum(all_clean_pct)/len(all_clean_pct):.1f}%")
