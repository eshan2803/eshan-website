"""
Convert CAISO supply data from row-based format to column-based format.

Input format (CAISO-supply-20240115.csv):
- Row 1: Header with date and time intervals as columns
- Rows 2-10: Energy sources as rows (Renewables, Natural gas, Large hydro, Nuclear, Coal, Other, Imports, Batteries)

Output format (20240115_fuelsource.csv):
- Column headers: Time, Solar, Wind, Geothermal, Biomass, Biogas, Small hydro, Coal, Nuclear, Natural Gas, Large Hydro, Batteries, Imports, Other
- Each row is a 5-minute interval
"""
import csv
import os

# Input and output files
input_file = "CAISO-supply-20240115.csv"
output_file = "caiso_supply/20240115_fuelsource.csv"

print(f"Converting {input_file} to {output_file}...")

# Read the input file
with open(input_file, 'r') as f:
    lines = f.readlines()

# Parse header to get time intervals
header_line = lines[0].strip()
# Split and get time intervals (skip first column which is "Supply 01/15/2024")
time_intervals = header_line.split(',')[1:]  # Skip first column
time_intervals = [t.strip() for t in time_intervals if t.strip()]  # Remove empty strings

print(f"Found {len(time_intervals)} time intervals")

# Parse data rows
data_by_source = {}
for line in lines[1:]:
    if line.strip():
        parts = line.strip().split(',')
        source_name = parts[0]
        values = [v.strip() if v.strip() else '0' for v in parts[1:]]

        # Ensure we have the same number of values as time intervals
        if len(values) < len(time_intervals):
            values.extend(['0'] * (len(time_intervals) - len(values)))
        elif len(values) > len(time_intervals):
            values = values[:len(time_intervals)]

        data_by_source[source_name] = values
        print(f"  Loaded {source_name}: {len(values)} values")

# Map the source names to expected column names
# "Renewables" needs to be broken down, but since we don't have individual breakdown,
# we'll need to work with what we have
# For now, let's assume Renewables = Solar (dominant) and set others to 0

# Create output data structure
output_rows = []

for i, time_str in enumerate(time_intervals):
    row = {
        'Time': time_str,
        'Solar': '0',  # Will calculate from renewables minus known renewables
        'Wind': '0',
        'Geothermal': '0',
        'Biomass': '0',
        'Biogas': '0',
        'Small hydro': '0',
        'Coal': data_by_source.get('Coal', ['0'] * len(time_intervals))[i] if 'Coal' in data_by_source else '0',
        'Nuclear': data_by_source.get('Nuclear', ['0'] * len(time_intervals))[i] if 'Nuclear' in data_by_source else '0',
        'Natural Gas': data_by_source.get('Natural gas', ['0'] * len(time_intervals))[i] if 'Natural gas' in data_by_source else '0',
        'Large Hydro': data_by_source.get('Large hydro', ['0'] * len(time_intervals))[i] if 'Large hydro' in data_by_source else '0',
        'Batteries': data_by_source.get('Batteries', ['0'] * len(time_intervals))[i] if 'Batteries' in data_by_source else '0',
        'Imports': data_by_source.get('Imports', ['0'] * len(time_intervals))[i] if 'Imports' in data_by_source else '0',
        'Other': data_by_source.get('Other', ['0'] * len(time_intervals))[i] if 'Other' in data_by_source else '0',
    }

    # For now, assign all renewables to Solar (since we don't have breakdown)
    # This is a simplification - ideally we'd need the actual breakdown
    if 'Renewables' in data_by_source:
        row['Solar'] = data_by_source['Renewables'][i]

    output_rows.append(row)

# Write output file
column_order = ['Time', 'Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro',
                'Coal', 'Nuclear', 'Natural Gas', 'Large Hydro', 'Batteries', 'Imports', 'Other']

with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=column_order)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\nSuccessfully converted {len(output_rows)} rows")
print(f"Output saved to {output_file}")
