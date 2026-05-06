"""
Process browser-downloaded CAISO files and merge into correct format.

Takes the raw supply and renewables CSV files downloaded from the browser
and combines them into the standard fuelsource.csv format used by the analysis.

Input files (from download_caiso_browser.py):
- {YYYYMMDD}_supply_raw.csv (Natural gas, Large hydro, Nuclear, Coal, Other, Imports, Batteries)
- {YYYYMMDD}_renewables_raw.csv (Solar, Wind, Geothermal, Biomass, Biogas, Small hydro)

Output file:
- caiso_supply/{YYYYMMDD}_fuelsource.csv (standard format with all columns)
"""
import csv
import os
import glob
from pathlib import Path
from collections import defaultdict

DOWNLOAD_DIR = Path(__file__).parent / "caiso_downloads"
OUTPUT_DIR = Path(__file__).parent / "caiso_supply"
OUTPUT_DIR.mkdir(exist_ok=True)

# Standard column order for fuelsource.csv
COLUMN_ORDER = ['Time', 'Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro',
                'Coal', 'Nuclear', 'Natural Gas', 'Large Hydro', 'Batteries', 'Imports', 'Other']


def parse_caiso_csv(file_path):
    """
    Parse CAISO CSV format where rows are energy sources and columns are time intervals.

    Returns:
        time_intervals: list of time strings (e.g., ['00:00', '00:05', ...])
        data_by_source: dict mapping source name to list of values
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # First line has header with time intervals
    header_line = lines[0].strip()
    parts = header_line.split(',')

    # Skip first column (usually date/label), rest are time intervals
    time_intervals = [t.strip() for t in parts[1:] if t.strip()]

    # Parse data rows
    data_by_source = {}
    for line in lines[1:]:
        if not line.strip():
            continue

        parts = line.strip().split(',')
        source_name = parts[0].strip()

        # Get values, padding if needed
        values = [v.strip() if v.strip() else '0' for v in parts[1:]]

        # Ensure same length as time intervals
        if len(values) < len(time_intervals):
            values.extend(['0'] * (len(time_intervals) - len(values)))
        elif len(values) > len(time_intervals):
            values = values[:len(time_intervals)]

        data_by_source[source_name] = values

    return time_intervals, data_by_source


def merge_files(date_str):
    """
    Merge supply and renewables files for a given date.

    Args:
        date_str: Date in YYYYMMDD format

    Returns:
        True if successful, False otherwise
    """
    supply_file = DOWNLOAD_DIR / f"{date_str}_supply_raw.csv"
    renewables_file = DOWNLOAD_DIR / f"{date_str}_renewables_raw.csv"
    output_file = OUTPUT_DIR / f"{date_str}_fuelsource.csv"

    if not supply_file.exists() or not renewables_file.exists():
        return False

    # Parse both files
    try:
        time_intervals_r, renewables_data = parse_caiso_csv(renewables_file)
        time_intervals_s, supply_data = parse_caiso_csv(supply_file)

        # Use renewables time intervals (should be the same)
        time_intervals = time_intervals_r

        # Map source names to standard column names
        source_map = {
            # Renewables
            'Solar': 'Solar',
            'Wind': 'Wind',
            'Geothermal': 'Geothermal',
            'Biomass': 'Biomass',
            'Biogas': 'Biogas',
            'Small hydro': 'Small hydro',
            # Supply
            'Coal': 'Coal',
            'Nuclear': 'Nuclear',
            'Natural gas': 'Natural Gas',
            'Large hydro': 'Large Hydro',
            'Batteries': 'Batteries',
            'Imports': 'Imports',
            'Other': 'Other',
            # Alternative names (CAISO sometimes varies)
            'Natural Gas': 'Natural Gas',
            'Large Hydro': 'Large Hydro',
        }

        # Build output rows
        output_rows = []
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
                if col_name not in ['Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro']:
                    if source_key in supply_data:
                        row[col_name] = supply_data[source_key][i]
                    elif col_name not in row:
                        row[col_name] = '0'

            output_rows.append(row)

        # Write output file
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=COLUMN_ORDER)
            writer.writeheader()
            writer.writerows(output_rows)

        return True

    except Exception as e:
        print(f"    ERROR processing {date_str}: {str(e)[:80]}")
        return False


def main():
    print("=" * 80)
    print("Processing browser-downloaded CAISO files")
    print("=" * 80)
    print(f"Input directory: {DOWNLOAD_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Find all supply_raw files
    supply_files = sorted(DOWNLOAD_DIR.glob("*_supply_raw.csv"))
    print(f"Found {len(supply_files)} supply files to process\n")

    success_count = 0
    error_count = 0
    skipped_count = 0

    for supply_file in supply_files:
        # Extract date from filename
        date_str = supply_file.stem.split('_')[0]  # YYYYMMDD

        # Check if output already exists
        output_file = OUTPUT_DIR / f"{date_str}_fuelsource.csv"
        if output_file.exists():
            skipped_count += 1
            continue

        print(f"Processing {date_str}...")

        if merge_files(date_str):
            success_count += 1
            print(f"  OK Created {output_file.name}")
        else:
            error_count += 1

    # Summary
    print("\n" + "=" * 80)
    print("Processing complete!")
    print(f"  Success: {success_count} files")
    print(f"  Errors: {error_count} files")
    print(f"  Skipped (already exist): {skipped_count} files")

    total_fuelsource = len(list(OUTPUT_DIR.glob("*_fuelsource.csv")))
    print(f"\n  Total fuelsource.csv files in {OUTPUT_DIR}: {total_fuelsource}")


if __name__ == "__main__":
    main()
