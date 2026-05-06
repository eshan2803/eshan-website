"""
Quick test to verify that the FUEL_COLS fix works correctly.
Tests that Natural Gas and Large Hydro are extracted properly.
"""
import csv

# New fixed version - list of tuples
FUEL_COLS_FIXED = [
    ("Solar", "solar_mw"),
    ("Wind", "wind_mw"),
    ("Natural Gas", "natural_gas_mw"),
    ("Nuclear", "nuclear_mw"),
    ("Large Hydro", "large_hydro_mw"),
    ("Small hydro", "small_hydro_mw"),
    ("Geothermal", "geothermal_mw"),
    ("Biomass", "biomass_mw"),
    ("Biogas", "biogas_mw"),
    ("Batteries", "batteries_mw"),
    ("Imports", "imports_mw"),
    ("Other", "other_mw"),
    ("Coal", "coal_mw")
]

print("Testing comprehensive CSV extraction logic...")
print("=" * 70)

# Test with May 23, 2025 data
fpath = "caiso_supply/20250523_fuelsource.csv"

try:
    with open(fpath, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        row = next(reader)

        print("\nInput CSV columns:")
        print(f"  Available: {list(row.keys())}")

        print("\nTesting FIXED extraction logic (list of tuples):")
        row_data = {}
        for fuel_col, csv_col in FUEL_COLS_FIXED:
            try:
                val = float(row.get(fuel_col) or 0)
                row_data[csv_col] = round(val, 2)
            except (ValueError, TypeError):
                row_data[csv_col] = ""

        print(f"  Natural Gas: {row_data['natural_gas_mw']} MW (expected: 5141)")
        print(f"  Large Hydro: {row_data['large_hydro_mw']} MW (expected: 4486)")
        print(f"  Solar: {row_data['solar_mw']} MW (expected: -29)")
        print(f"  Wind: {row_data['wind_mw']} MW (expected: 4930)")

        # Verify
        success = True
        if row_data['natural_gas_mw'] != 5141.0:
            print(f"\n[FAIL] Natural Gas is {row_data['natural_gas_mw']}, expected 5141.0")
            success = False
        if row_data['large_hydro_mw'] != 4486.0:
            print(f"\n[FAIL] Large Hydro is {row_data['large_hydro_mw']}, expected 4486.0")
            success = False

        if success:
            print("\n[SUCCESS] All values extracted correctly!")
            print("\nThe fix works. Now run: python fix_may_2025_data.py")
        else:
            print("\n[FAILED] Extraction still broken")

except FileNotFoundError:
    print(f"\n[ERROR] File not found: {fpath}")
except Exception as e:
    print(f"\n[ERROR] {e}")

print("=" * 70)
