"""Verify comprehensive CSV has all expected data"""
import csv

rows_with_demand = 0
rows_with_lmp = 0
rows_with_as = 0
rows_with_lmp_breakdown = 0
total_rows = 0

print("Verifying comprehensive CSV...")

with open('caiso_comprehensive_data.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1

        if row['demand_mw']:
            rows_with_demand += 1

        if row['lmp']:
            rows_with_lmp += 1

        if row['nr']:
            rows_with_as += 1

        if row['mcc'] or row['mec'] or row['ghg'] or row['loss']:
            rows_with_lmp_breakdown += 1

        if total_rows >= 20000:
            break

print(f"\nFirst {total_rows:,} rows:")
print(f"  Rows with demand: {rows_with_demand:,} ({rows_with_demand/total_rows*100:.1f}%)")
print(f"  Rows with LMP: {rows_with_lmp:,} ({rows_with_lmp/total_rows*100:.1f}%)")
print(f"  Rows with LMP breakdown: {rows_with_lmp_breakdown:,} ({rows_with_lmp_breakdown/total_rows*100:.1f}%)")
print(f"  Rows with A/S prices: {rows_with_as:,} ({rows_with_as/total_rows*100:.1f}%)")
print(f"\nExpected:")
print(f"  Demand: ~100% (5-minute intervals)")
print(f"  LMP/A/S: ~8.3% (hourly at :00, so 1/12 of 5-min rows)")
