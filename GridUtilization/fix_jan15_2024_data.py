"""
Fix January 15, 2024 data by combining:
- CAISO-renewables-20240115.csv (Solar, Wind, Geothermal, Biomass, Biogas, Small hydro)
- CAISO-supply-20240115.csv (Natural gas, Large hydro, Nuclear, Coal, Other, Imports, Batteries)

Output: caiso_supply/20240115_fuelsource.csv with correct data
"""
import csv
import os

print("Fixing January 15, 2024 data...")

# Read renewables file
renewables_file = "CAISO-renewables-20240115.csv"
supply_file = "CAISO-supply-20240115.csv"
output_file = "caiso_supply/20240115_fuelsource.csv"

print(f"\n1. Reading {renewables_file}...")
with open(renewables_file, 'r') as f:
    lines = f.readlines()

# Parse header to get time intervals
time_intervals = lines[0].strip().split(',')[1:]  # Skip first column
time_intervals = [t.strip() for t in time_intervals if t.strip()]
print(f"   Found {len(time_intervals)} time intervals")

# Parse renewable data by source
renewables_data = {}
for line in lines[1:]:
    if line.strip() and not line.startswith('Demand'):
        parts = line.strip().split(',')
        source_name = parts[0]
        values = [v.strip() if v.strip() else '0' for v in parts[1:]]

        # Pad or trim to match time intervals
        if len(values) < len(time_intervals):
            values.extend(['0'] * (len(time_intervals) - len(values)))
        elif len(values) > len(time_intervals):
            values = values[:len(time_intervals)]

        renewables_data[source_name] = values
        print(f"   Loaded {source_name}: {len(values)} values")

# Read supply file
print(f"\n2. Reading {supply_file}...")
with open(supply_file, 'r') as f:
    lines = f.readlines()

# Parse supply data
supply_data = {}
for line in lines[1:]:
    if line.strip():
        parts = line.strip().split(',')
        source_name = parts[0]
        values = [v.strip() if v.strip() else '0' for v in parts[1:]]

        # Pad or trim to match time intervals
        if len(values) < len(time_intervals):
            values.extend(['0'] * (len(time_intervals) - len(values)))
        elif len(values) > len(time_intervals):
            values = values[:len(time_intervals)]

        supply_data[source_name] = values
        print(f"   Loaded {source_name}: {len(values)} values")

# Build output rows
print(f"\n3. Building output data...")
output_rows = []

column_order = ['Time', 'Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro',
                'Coal', 'Nuclear', 'Natural Gas', 'Large Hydro', 'Batteries', 'Imports', 'Other']

# Map source names to column names
source_map = {
    'Solar': 'Solar',
    'Wind': 'Wind',
    'Geothermal': 'Geothermal',
    'Biomass': 'Biomass',
    'Biogas': 'Biogas',
    'Small hydro': 'Small hydro',
    'Coal': 'Coal',
    'Nuclear': 'Nuclear',
    'Natural gas': 'Natural Gas',
    'Large hydro': 'Large Hydro',
    'Batteries': 'Batteries',
    'Imports': 'Imports',
    'Other': 'Other'
}

for i, time_str in enumerate(time_intervals):
    row = {'Time': time_str}

    # Add renewable sources
    for source in ['Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro']:
        if source in renewables_data:
            row[source] = renewables_data[source][i]
        else:
            row[source] = '0'

    # Add supply sources
    for source_key, col_name in source_map.items():
        if source_key not in ['Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro']:
            if source_key in supply_data:
                row[col_name] = supply_data[source_key][i]
            else:
                row[col_name] = '0'

    output_rows.append(row)

print(f"   Created {len(output_rows)} rows")

# Write output file
print(f"\n4. Writing to {output_file}...")
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=column_order)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\n✓ Successfully fixed January 15, 2024 data")
print(f"  Output: {output_file}")
print(f"  Rows: {len(output_rows)}")

# Verify a sample row
if output_rows:
    print(f"\n5. Sample data (Hour 13:00):")
    for row in output_rows:
        if row['Time'] == '13:00':
            print(f"   Time: {row['Time']}")
            print(f"   Solar: {row['Solar']} MW")
            print(f"   Wind: {row['Wind']} MW")
            print(f"   Nuclear: {row['Nuclear']} MW")
            print(f"   Large Hydro: {row['Large Hydro']} MW")
            print(f"   Natural Gas: {row['Natural Gas']} MW")
            print(f"   Batteries: {row['Batteries']} MW")
            break
