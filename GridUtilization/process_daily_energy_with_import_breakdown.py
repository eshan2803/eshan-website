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
# Fallback to local path or relative path
IMPORT_DISPATCH_FILE = os.environ.get("EIA_IMPORT_FILE", r"c:\Users\eshan\OneDrive\Desktop\eshan-website\curtailmentdata\EIA_Import_Dispatch_and_CI_2019_2024.csv")
if not os.path.exists(IMPORT_DISPATCH_FILE):
    IMPORT_DISPATCH_FILE = os.path.join(os.path.dirname(__file__), "..", "curtailmentdata", "EIA_Import_Dispatch_and_CI_2019_2024.csv")
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
if os.path.exists(IMPORT_DISPATCH_FILE):
    import_df = pd.read_csv(IMPORT_DISPATCH_FILE)
    import_df['Date_dt'] = pd.to_datetime(import_df['Date'])
    import_df['Date_key'] = import_df['Date_dt'].dt.strftime('%Y-%m-%d')
    import_df['Hour_key'] = import_df['Hour'].astype(int)
else:
    print(f"Warning: Import dispatch file not found at {IMPORT_DISPATCH_FILE}. Using fallback ratios.")
    import_df = pd.DataFrame(columns=['Date', 'Hour', 'Date_dt', 'Date_key', 'Hour_key'])

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

# Build hourly 2024 ratios for fallback (hour-of-day specific, not annual average)
# This captures the merit-order dispatch pattern: mid-day is mostly clean, nighttime is more fossil
print("Calculating 2024 hourly import ratios (by hour of day)...")
import_2024 = import_df[import_df['Date_dt'].dt.year == 2024]

hourly_2024_totals = {}  # hour -> {clean, fossil, unknown}
for h in range(1, 25):
    hourly_2024_totals[h] = {'clean': 0.0, 'fossil': 0.0, 'unknown': 0.0}

for _, row in import_2024.iterrows():
    h = int(row['Hour_key'])
    if h not in hourly_2024_totals:
        continue

    for source in IMPORT_CLEAN_SOURCES:
        hourly_2024_totals[h]['clean'] += row.get(f'NW_{source}_MWh', 0) or 0
        hourly_2024_totals[h]['clean'] += row.get(f'SW_{source}_MWh', 0) or 0

    for source in IMPORT_FOSSIL_SOURCES:
        hourly_2024_totals[h]['fossil'] += row.get(f'NW_{source}_MWh', 0) or 0
        hourly_2024_totals[h]['fossil'] += row.get(f'SW_{source}_MWh', 0) or 0

    hourly_2024_totals[h]['unknown'] += row.get('NW_Unspecified_MWh', 0) or 0
    hourly_2024_totals[h]['unknown'] += row.get('NW_Other_MWh', 0) or 0
    hourly_2024_totals[h]['unknown'] += row.get('SW_Unspecified_MWh', 0) or 0
    hourly_2024_totals[h]['unknown'] += row.get('SW_Other_MWh', 0) or 0

# Convert to ratios
hourly_2024_ratios = {}
for h in range(1, 25):
    t = hourly_2024_totals[h]
    total = t['clean'] + t['fossil'] + t['unknown']
    if total > 0:
        hourly_2024_ratios[h] = {
            'clean': t['clean'] / total,
            'fossil': t['fossil'] / total,
            'unknown': t['unknown'] / total,
        }
    else:
        hourly_2024_ratios[h] = {'clean': 0.5, 'fossil': 0.3, 'unknown': 0.2}

# Print sample to show hourly variation
for h in [1, 6, 10, 12, 16, 20, 24]:
    r = hourly_2024_ratios[h]
    print(f"  Hour {h:2d}: Clean={r['clean']*100:5.1f}%  Fossil={r['fossil']*100:5.1f}%  Unknown={r['unknown']*100:5.1f}%")

# Also load EIA interchange data for NW/SW splits (2025+ if available)
EIA_INTERCHANGE_FILE = os.path.join(os.path.dirname(__file__), "..", "curtailmentdata", "EIA_Interchange_2019_2024.csv")
interchange_lookup = {}  # (date_key, hour) -> {nw: MWh, sw: MWh}
if os.path.exists(EIA_INTERCHANGE_FILE):
    interchange_df = pd.read_csv(EIA_INTERCHANGE_FILE)
    interchange_df['Date_dt'] = pd.to_datetime(interchange_df['Date'])
    interchange_df['Date_key'] = interchange_df['Date_dt'].dt.strftime('%Y-%m-%d')
    for _, row in interchange_df.iterrows():
        key = (row['Date_key'], int(row['Hour']))
        interchange_lookup[key] = {
            'nw': row.get('NW Import', 0) or 0,
            'sw': row.get('SW Import', 0) or 0,
        }
    print(f"Loaded EIA interchange data: {len(interchange_lookup)} hour entries")

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
                # Hour mapping: CAISO fuelsource uses 0-23, dispatch uses 1-24
                dispatch_hour = hour if hour > 0 else 24
                import_key = (date_key, dispatch_hour)

                if import_key in import_lookup and total_import_mwh > 0:
                    # Full dispatch data available for this date+hour
                    import_data = import_lookup[import_key]
                    dispatch_total = import_data['clean'] + import_data['fossil'] + import_data['unknown']

                    if dispatch_total > 0:
                        ratio_clean = import_data['clean'] / dispatch_total
                        ratio_fossil = import_data['fossil'] / dispatch_total
                        ratio_unknown = import_data['unknown'] / dispatch_total

                        import_clean_interval = total_import_mwh * ratio_clean
                        import_fossil_interval = total_import_mwh * ratio_fossil
                        import_unknown_interval = total_import_mwh * ratio_unknown
                    else:
                        # Dispatch total is zero — use hourly 2024 ratios
                        r = hourly_2024_ratios.get(dispatch_hour, hourly_2024_ratios[12])
                        import_clean_interval = total_import_mwh * r['clean']
                        import_fossil_interval = total_import_mwh * r['fossil']
                        import_unknown_interval = total_import_mwh * r['unknown']
                else:
                    # No dispatch data for this date — use hourly 2024 ratios
                    # This preserves the hour-of-day merit order pattern
                    r = hourly_2024_ratios.get(dispatch_hour, hourly_2024_ratios[12])
                    import_clean_interval = total_import_mwh * r['clean']
                    import_fossil_interval = total_import_mwh * r['fossil']
                    import_unknown_interval = total_import_mwh * r['unknown']

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
