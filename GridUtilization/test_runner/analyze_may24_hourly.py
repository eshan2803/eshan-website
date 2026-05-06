"""
Walk through May 24, 2025 hour by hour to understand the difference between:
- Method 1 (Homepage/v5): No import classification, penetration = clean/(demand+charging)
- Method 2 (Import breakdown): Classify imports, penetration = clean/(clean+fossil)
"""
import csv
import json

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

# Load import ratios from the hourly 2024 data
# Simplified version - load from the process_daily_energy_with_import_breakdown.py output
with open("daily_energy_with_import_breakdown.json", "r") as f:
    import_breakdown = json.load(f)

# For simplicity, use approximate 2024 annual ratios
# From the HTML report: 70.5% clean, 22.9% fossil, 6.6% unknown
IMPORT_CLEAN_RATIO = 0.705
IMPORT_FOSSIL_RATIO = 0.229
IMPORT_UNKNOWN_RATIO = 0.066

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

# Calculate hourly averages and both methods
print("="*120)
print(f"May 24, 2025 - Hour-by-Hour Analysis")
print("="*120)
print(f"{'Hour':>4} | {'Demand':>7} | {'Clean':>7} | {'Gas':>7} | {'Batt':>7} | {'Import':>7} || {'Method1':>8} | {'Method2':>8} | {'Diff':>7}")
print(f"{'':>4} | {'(MW)':>7} | {'(MW)':>7} | {'(MW)':>7} | {'(MW)':>7} | {'(MW)':>7} || {'(%)':>8} | {'(%)':>8} | {'(pp)':>7}")
print("-"*120)

method1_clean_total = 0
method1_load_total = 0
method2_clean_total = 0
method2_supply_total = 0

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

    # METHOD 1 (Homepage/v5): No import classification
    # Clean = CA clean + battery discharge (if positive)
    # Load = Demand + battery charging (if negative)
    method1_clean = clean_mw
    if battery_mw > 0:
        method1_clean += battery_mw

    method1_load = demand_mw + abs(min(battery_mw, 0))

    method1_penetration = (method1_clean / method1_load * 100) if method1_load > 0 else 0

    # METHOD 2 (Import breakdown): Classify imports
    # Clean = CA clean + battery discharge + clean imports
    # Fossil = CA gas + fossil imports + unknown imports
    # Penetration = Clean / (Clean + Fossil)

    clean_imports = imports_mw * IMPORT_CLEAN_RATIO
    fossil_imports = imports_mw * (IMPORT_FOSSIL_RATIO + IMPORT_UNKNOWN_RATIO)

    method2_clean = clean_mw
    if battery_mw > 0:
        method2_clean += battery_mw
    method2_clean += clean_imports

    method2_fossil = gas_mw + fossil_imports
    method2_supply = method2_clean + method2_fossil

    method2_penetration = (method2_clean / method2_supply * 100) if method2_supply > 0 else 0

    diff = method2_penetration - method1_penetration

    # Accumulate totals (MWh = MW * 1 hour)
    method1_clean_total += method1_clean
    method1_load_total += method1_load
    method2_clean_total += method2_clean
    method2_supply_total += method2_supply

    print(f"{h:4d} | {demand_mw:7.0f} | {clean_mw:7.0f} | {gas_mw:7.0f} | {battery_mw:7.0f} | {imports_mw:7.0f} || {method1_penetration:8.2f} | {method2_penetration:8.2f} | {diff:7.2f}")

# Daily totals
method1_daily = (method1_clean_total / method1_load_total * 100) if method1_load_total > 0 else 0
method2_daily = (method2_clean_total / method2_supply_total * 100) if method2_supply_total > 0 else 0
daily_diff = method2_daily - method1_daily

print("-"*120)
print(f"{'DAILY':>4} | {'-':>7} | {'-':>7} | {'-':>7} | {'-':>7} | {'-':>7} || {method1_daily:8.2f} | {method2_daily:8.2f} | {daily_diff:7.2f}")
print("="*120)

print("\nKey Insights:")
print(f"1. Method 1 (Homepage): {method1_daily:.2f}% - Treats imports as unknown, divides by gross demand")
print(f"2. Method 2 (Import breakdown): {method2_daily:.2f}% - Classifies imports (~70.5% clean), divides by total supply")
print(f"3. The difference ({daily_diff:+.2f} pp) comes from:")
print(f"   - Adding fossil imports (~30% of imports) to the denominator")
print(f"   - This increases total supply more than it increases clean energy")
print(f"   - When imports are high but partly fossil, Method 2 shows lower penetration")
