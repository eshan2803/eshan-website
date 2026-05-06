"""
Calculate renewable penetration for a specific date using TWO methodologies:

Method 1: Conservative (Imports NOT Classified)
  - Treats all imports as non-clean
  - Clean = CA renewables + nuclear + hydro + battery discharge

Method 2: Import Classification
  - Splits imports based on CA's internal generation mix
  - If CA is generating 80% clean internally, assumes 80% of imports are clean
  - More realistic for regions with high renewable penetration

Usage:
  python calculate_penetration_two_methods.py 2025-05-23
"""
import sys
import csv
import os
from datetime import datetime
from collections import defaultdict

def calculate_for_date(date_str):
    """Calculate penetration using both methods for a specific date"""

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_str_raw = date_obj.strftime("%Y%m%d")

    # Load demand from demand CSV
    demand_file = f"caiso_demand_downloads/{date_str_raw}_demand.csv"
    if not os.path.exists(demand_file):
        print(f"ERROR: Demand file not found: {demand_file}")
        return None

    demand_hourly = {}
    try:
        with open(demand_file, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                demand_line = lines[1].strip().split(",")
                demand_values = [float(x) if x.strip() else None for x in demand_line[1:25]]
                if len(demand_values) >= 24:
                    for hour in range(24):
                        demand_hourly[hour] = demand_values[hour]
    except Exception as e:
        print(f"ERROR reading demand file: {e}")
        return None

    # Load fuelsource CSV
    fuelsource_file = f"caiso_supply/{date_str_raw}_fuelsource.csv"
    if not os.path.exists(fuelsource_file):
        print(f"ERROR: Fuelsource file not found: {fuelsource_file}")
        return None

    # Process 5-minute data
    method1_clean_mwh = 0.0
    method1_load_mwh = 0.0

    method2_clean_mwh = 0.0
    method2_load_mwh = 0.0

    CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro", "Large hydro"]

    try:
        with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                except (ValueError, IndexError):
                    continue

                # Get demand for this hour
                if hour >= len(demand_hourly) or hour not in demand_hourly:
                    continue

                demand_mw = demand_hourly[hour]
                if demand_mw <= 0:
                    continue

                # Parse all generation sources
                clean_mw = 0.0
                for col in CLEAN_COLS:
                    try:
                        clean_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                battery_mw = 0.0
                try:
                    battery_mw = float(row.get("Batteries", 0) or 0)
                except (ValueError, TypeError):
                    pass

                imports_mw = 0.0
                try:
                    imports_mw = float(row.get("Imports", 0) or 0)
                except (ValueError, TypeError):
                    pass

                nat_gas_mw = 0.0
                try:
                    nat_gas_mw = float(row.get("Natural Gas", 0) or 0)
                except (ValueError, TypeError):
                    pass

                coal_mw = 0.0
                try:
                    coal_mw = float(row.get("Coal", 0) or 0)
                except (ValueError, TypeError):
                    pass

                # Calculate load (same for both methods)
                total_load = demand_mw + abs(min(battery_mw, 0))

                # METHOD 1: Conservative (Imports NOT Classified)
                method1_clean = clean_mw
                if battery_mw > 0:
                    method1_clean += battery_mw

                method1_clean_mwh += method1_clean
                method1_load_mwh += total_load

                # METHOD 2: Import Classification
                # Calculate CA's internal clean ratio (excluding imports)
                internal_generation = clean_mw + nat_gas_mw + coal_mw
                if battery_mw > 0:
                    internal_generation += battery_mw
                elif battery_mw < 0:
                    # Battery charging doesn't count as generation
                    pass

                if internal_generation > 0:
                    ca_clean_ratio = clean_mw / internal_generation
                    if battery_mw > 0:
                        ca_clean_ratio = (clean_mw + battery_mw) / internal_generation
                else:
                    ca_clean_ratio = 0.0

                # Apply ratio to imports
                clean_imports = max(0, imports_mw) * ca_clean_ratio

                method2_clean = method1_clean + clean_imports
                method2_clean_mwh += method2_clean
                method2_load_mwh += total_load

    except Exception as e:
        print(f"ERROR processing fuelsource: {e}")
        return None

    # Calculate percentages
    if method1_load_mwh > 0:
        method1_pct = (method1_clean_mwh / method1_load_mwh) * 100.0
    else:
        method1_pct = 0.0

    if method2_load_mwh > 0:
        method2_pct = (method2_clean_mwh / method2_load_mwh) * 100.0
    else:
        method2_pct = 0.0

    return {
        'date': date_str,
        'method1': {
            'name': 'Conservative (Imports NOT Classified)',
            'clean_mwh': method1_clean_mwh,
            'load_mwh': method1_load_mwh,
            'penetration': method1_pct
        },
        'method2': {
            'name': 'Import Classification',
            'clean_mwh': method2_clean_mwh,
            'load_mwh': method2_load_mwh,
            'penetration': method2_pct
        }
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calculate_penetration_two_methods.py YYYY-MM-DD")
        print("Example: python calculate_penetration_two_methods.py 2025-05-23")
        sys.exit(1)

    date_str = sys.argv[1]

    print("="*70)
    print(f"Calculating Renewable Penetration for {date_str}")
    print("="*70)

    result = calculate_for_date(date_str)

    if result:
        print(f"\nDate: {result['date']}")
        print("\n" + "-"*70)
        print("METHOD 1: Conservative (Imports NOT Classified)")
        print("-"*70)
        print(f"  Clean Energy: {result['method1']['clean_mwh']:,.0f} MWh")
        print(f"  Total Load:   {result['method1']['load_mwh']:,.0f} MWh")
        print(f"  Penetration:  {result['method1']['penetration']:.2f}%")

        print("\n" + "-"*70)
        print("METHOD 2: Import Classification")
        print("-"*70)
        print(f"  Clean Energy: {result['method2']['clean_mwh']:,.0f} MWh")
        print(f"  Total Load:   {result['method2']['load_mwh']:,.0f} MWh")
        print(f"  Penetration:  {result['method2']['penetration']:.2f}%")

        print("\n" + "-"*70)
        print("DIFFERENCE")
        print("-"*70)
        diff = result['method2']['penetration'] - result['method1']['penetration']
        print(f"  Method 2 is {diff:+.2f} percentage points higher")
        print(f"  Additional clean energy from classified imports: {result['method2']['clean_mwh'] - result['method1']['clean_mwh']:,.0f} MWh")

        print("\n" + "="*70)
        print("Notes:")
        print("  - Method 1 treats all imports as non-clean (conservative)")
        print("  - Method 2 assumes imports have same clean % as CA internal generation")
        print("  - Your manual calculation matched Method 1")
        print("="*70)
    else:
        print("\nCalculation failed. Check error messages above.")
        sys.exit(1)
