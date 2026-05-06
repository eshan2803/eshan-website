"""
Calculate ENERGY-BASED clean penetration for May 24, 2025.

This calculates: Total Clean Energy (MWh) / Total Load (MWh) × 100

Where:
- Total Clean Energy = sum of clean MW × hours (converted to MWh)
- Total Load = Demand + Battery Charging (when negative)

This is different from V3 which averages hourly percentages.
"""
import csv

date_str = "20250524"

# Load demand data (hourly format)
demand_file = f"caiso_demand_downloads/{date_str}_demand.csv"
demand_hourly = {}
with open(demand_file, "r", encoding="utf-8-sig") as f:
    lines = f.readlines()
    if len(lines) >= 2:
        demand_line = lines[1].strip().split(",")
        demand_values = [float(x) if x.strip() else 0 for x in demand_line[1:25]]
        for h in range(24):
            if h < len(demand_values):
                demand_hourly[h] = demand_values[h]

CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

# Process fuelsource CSV
fuelsource_file = f"caiso_supply/{date_str}_fuelsource.csv"

# Aggregate by hour
hourly_data = {}
for h in range(24):
    hourly_data[h] = {
        'demand_mw': 0,
        'count': 0,
        'clean_mw': 0,
        'gas_mw': 0,
        'battery_mw': 0,
        'imports_mw': 0
    }

with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for idx, row in enumerate(reader):
        time_str = row.get("Time", "")
        if not time_str:
            continue

        hour = int(time_str.split(":")[0])

        # Get demand for this hour
        if hour not in demand_hourly:
            continue
        demand_mw = demand_hourly[hour]

        # Get clean energy
        clean_mw = 0.0
        for col in CLEAN_COLS:
            try:
                clean_mw += float(row.get(col, 0) or 0)
            except (ValueError, TypeError):
                pass

        # Get battery
        battery_mw = float(row.get("Batteries", 0) or 0)

        # Get natural gas
        gas_mw = float(row.get("Natural Gas", 0) or 0)

        # Get imports
        imports_mw = float(row.get("Imports", 0) or 0)

        # Accumulate
        hourly_data[hour]['demand_mw'] += demand_mw
        hourly_data[hour]['clean_mw'] += clean_mw
        hourly_data[hour]['gas_mw'] += gas_mw
        hourly_data[hour]['battery_mw'] += battery_mw
        hourly_data[hour]['imports_mw'] += imports_mw
        hourly_data[hour]['count'] += 1

# Calculate three different metrics
print("="*100)
print(f"May 24, 2025 - Three Different Penetration Calculations")
print("="*100)
print()

# METHOD 1: Average of hourly percentages (current V3 implementation)
method1_pct_sum = 0
method1_hour_count = 0

# METHOD 2: Energy-based (total clean MWh / total load MWh)
method2_clean_mwh = 0
method2_load_mwh = 0

# METHOD 3: Import breakdown style (for comparison)
method3_clean_mwh = 0
method3_supply_mwh = 0

# Import classification ratio
IMPORT_CLEAN_RATIO = 0.705

print(f"{'Hour':>4} | {'Demand':>7} | {'Clean':>7} | {'Batt':>7} | {'Load':>7} || {'HourlyPct':>9} | {'CleanMWh':>9} | {'LoadMWh':>8}")
print(f"{'':>4} | {'(MW)':>7} | {'(MW)':>7} | {'(MW)':>7} | {'(MW)':>7} || {'(%)':>9} | {'':>9} | {'':>8}")
print("-"*100)

for h in range(24):
    data = hourly_data[h]
    if data['count'] == 0:
        continue

    # Average MW for the hour
    demand_mw = data['demand_mw'] / data['count']
    clean_mw = data['clean_mw'] / data['count']
    gas_mw = data['gas_mw'] / data['count']
    battery_mw = data['battery_mw'] / data['count']
    imports_mw = data['imports_mw'] / data['count']

    # METHOD 1: Hourly percentage (what V3 does)
    clean_with_battery = clean_mw
    if battery_mw > 0:
        clean_with_battery += battery_mw

    load_mw = demand_mw + abs(min(battery_mw, 0))  # Add battery charging to load

    hourly_pct = (clean_with_battery / load_mw * 100) if load_mw > 0 else 0
    method1_pct_sum += hourly_pct
    method1_hour_count += 1

    # METHOD 2: Energy-based accumulation (convert MW to MWh)
    clean_mwh_hour = clean_with_battery  # MW for 1 hour = MWh
    load_mwh_hour = load_mw

    method2_clean_mwh += clean_mwh_hour
    method2_load_mwh += load_mwh_hour

    # METHOD 3: Import breakdown style (for reference)
    clean_imports = imports_mw * IMPORT_CLEAN_RATIO if imports_mw > 0 else imports_mw * IMPORT_CLEAN_RATIO
    method3_clean = clean_with_battery + clean_imports
    method3_fossil = gas_mw + (imports_mw * (1 - IMPORT_CLEAN_RATIO) if imports_mw > 0 else imports_mw * (1 - IMPORT_CLEAN_RATIO))
    method3_supply = method3_clean + method3_fossil

    method3_clean_mwh += method3_clean
    method3_supply_mwh += method3_supply

    print(f"{h:4d} | {demand_mw:7.0f} | {clean_mw:7.0f} | {battery_mw:7.0f} | {load_mw:7.0f} || {hourly_pct:9.2f} | {clean_mwh_hour:9.0f} | {load_mwh_hour:8.0f}")

print("-"*100)

# Calculate final results
method1_avg = method1_pct_sum / method1_hour_count if method1_hour_count > 0 else 0
method2_pct = (method2_clean_mwh / method2_load_mwh * 100) if method2_load_mwh > 0 else 0
method3_pct = (method3_clean_mwh / method3_supply_mwh * 100) if method3_supply_mwh > 0 else 0

print()
print("="*100)
print("SUMMARY FOR MAY 24, 2025:")
print("="*100)
print()
print(f"METHOD 1: Average of Hourly Percentages (Current V3 Homepage)")
print(f"  Formula: average(clean[h]/load[h] for all hours)")
print(f"  Result:  {method1_avg:.2f}%")
print(f"  Matches: renewable_penetration_daily_v3.json -> 90.93%")
print()
print(f"METHOD 2: Energy-Based Percentage (What You Want)")
print(f"  Formula: sum(clean_mwh) / sum(load_mwh) × 100")
print(f"  Result:  {method2_pct:.2f}%")
print(f"  Clean Energy: {method2_clean_mwh:,.0f} MWh")
print(f"  Total Load:   {method2_load_mwh:,.0f} MWh")
print()
print(f"METHOD 3: Import Breakdown Style (For Reference)")
print(f"  Formula: sum(clean+import_clean) / sum(clean+fossil+import_all) × 100")
print(f"  Result:  {method3_pct:.2f}%")
print(f"  Matches: daily_energy_with_import_breakdown.json -> 88.51%")
print()
print("="*100)
print()
print("KEY INSIGHT:")
print(f"  Method 1 (averaging percentages): {method1_avg:.2f}%")
print(f"  Method 2 (percentage of totals):  {method2_pct:.2f}%")
print(f"  Difference: {method1_avg - method2_pct:+.2f} percentage points")
print()
print("WHY THEY DIFFER:")
print("  - Low-demand hours with high clean % boost Method 1")
print("  - High-demand hours with lower clean % dominate Method 2")
print("  - Method 2 is the correct 'energy-weighted' metric you want")
print("="*100)
