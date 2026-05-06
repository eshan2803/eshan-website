"""
Analyze demand file conflicts and determine recovery strategy.
"""
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict

DEMAND_DIR = "caiso_demand_downloads"

demand_files = sorted(glob.glob(os.path.join(DEMAND_DIR, "*_demand.csv")))

print(f"Analyzing {len(demand_files)} demand files...")
print("="*80)

# Map: actual_date -> list of filenames claiming to have that date's data
date_to_files = defaultdict(list)
filename_to_actual = {}

for fpath in demand_files:
    basename = os.path.basename(fpath)
    filename_date = basename.split('_')[0]

    try:
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline().strip()
            if 'Demand' in first_line:
                parts = first_line.replace(',', ' ').split()
                if len(parts) >= 2:
                    actual_date_str = parts[1]
                    actual_dt = datetime.strptime(actual_date_str, '%m/%d/%Y')
                    actual_date = actual_dt.strftime('%Y%m%d')

                    date_to_files[actual_date].append(basename)
                    filename_to_actual[basename] = actual_date
    except Exception as e:
        pass

# Find dates with multiple files
print("\nDates with multiple files claiming same data:")
print("-"*80)
duplicates = {k: v for k, v in date_to_files.items() if len(v) > 1}
print(f"Found {len(duplicates)} dates with duplicate data")

for date, files in list(duplicates.items())[:10]:
    print(f"{date}: {files}")

# Find what dates we actually have (unique dates with data)
actual_dates_covered = set(date_to_files.keys())
print(f"\nUnique dates with data files: {len(actual_dates_covered)}")

# Find what dates are expected (all dates from 2020-01-01 to 2026-04-01)
start_date = datetime(2020, 1, 1)
end_date = datetime(2026, 4, 1)
expected_dates = set()
current = start_date
while current <= end_date:
    expected_dates.add(current.strftime('%Y%m%d'))
    current += timedelta(days=1)

print(f"Expected dates (2020-01-01 to 2026-04-01): {len(expected_dates)}")

# Find missing dates
missing_dates = expected_dates - actual_dates_covered
print(f"Missing dates: {len(missing_dates)}")

if missing_dates:
    missing_sorted = sorted(list(missing_dates))
    print(f"\nFirst 20 missing dates:")
    for d in missing_sorted[:20]:
        print(f"  {d}")

# Strategy
print(f"\n{'='*80}")
print("RECOVERY STRATEGY:")
print("="*80)
print(f"1. Keep one file for each of the {len(actual_dates_covered)} dates with data")
print(f"2. Delete {len(demand_files) - len(actual_dates_covered)} duplicate/mislabeled files")
print(f"3. Download {len(missing_dates)} missing demand files")
print(f"\nTotal after recovery: {len(actual_dates_covered) + len(missing_dates)} files")
print(f"Expected: {len(expected_dates)} files")
if len(actual_dates_covered) + len(missing_dates) == len(expected_dates):
    print("Status: Complete coverage possible")
else:
    print(f"Status: Will be short {len(expected_dates) - len(actual_dates_covered) - len(missing_dates)} files")

# Save missing dates to file for download
with open('missing_demand_dates.txt', 'w') as f:
    for d in sorted(missing_dates):
        f.write(f"{d}\n")

print(f"\nSaved {len(missing_dates)} missing dates to missing_demand_dates.txt")
