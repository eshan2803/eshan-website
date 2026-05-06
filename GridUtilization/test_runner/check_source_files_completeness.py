"""
Check completeness of source files (fuelsource CSVs, demand CSVs, LMP, A/S)
"""
import os
import json
import glob
from datetime import datetime, timedelta
from collections import defaultdict

print("="*80)
print("CHECKING SOURCE FILES COMPLETENESS")
print("="*80)

# Check fuelsource CSVs
print("\n1. FUELSOURCE CSVs")
print("-"*80)
fuelsource_files = sorted(glob.glob("caiso_supply/*_fuelsource.csv"))
print(f"Total files: {len(fuelsource_files)}")

incomplete_fuelsource = []
for fpath in fuelsource_files:
    basename = os.path.basename(fpath)
    date_str = basename.split("_")[0]

    # Count lines
    with open(fpath) as f:
        lines = f.readlines()
        data_lines = len(lines) - 1  # Subtract header

        # Expected: 288 lines (24 hours * 12 intervals per hour)
        # But DST days have different counts
        if data_lines < 270:  # Allow some tolerance
            incomplete_fuelsource.append((date_str, data_lines))

if incomplete_fuelsource:
    print(f"\nIncomplete fuelsource files ({len(incomplete_fuelsource)}):")
    for date, lines in incomplete_fuelsource[:20]:
        expected_intervals = lines * 5 / 60  # Convert to hours
        print(f"  {date}: {lines} intervals (~{expected_intervals:.1f} hours of data)")
else:
    print("All fuelsource files are complete")

# Check demand CSVs
print("\n2. DEMAND CSVs")
print("-"*80)
demand_files = sorted(glob.glob("caiso_demand_downloads/*_demand.csv"))
print(f"Total files: {len(demand_files)}")

# Check for missing dates
fuelsource_dates = set()
for fpath in fuelsource_files:
    basename = os.path.basename(fpath)
    date_str = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        fuelsource_dates.add(dt.strftime("%Y-%m-%d"))
    except:
        pass

demand_dates = set()
for fpath in demand_files:
    basename = os.path.basename(fpath)
    date_str = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        demand_dates.add(dt.strftime("%Y-%m-%d"))
    except:
        pass

missing_demand = fuelsource_dates - demand_dates
if missing_demand:
    print(f"\nDates with fuelsource but NO demand CSV ({len(missing_demand)}):")
    for date in sorted(missing_demand)[:20]:
        print(f"  {date}")
else:
    print("All fuelsource dates have corresponding demand CSVs")

# Check LMP data
print("\n3. LMP PRICE DATA")
print("-"*80)
with open("caiso_prices.json") as f:
    lmp_data = json.load(f)

print(f"Total dates: {len(lmp_data)}")
print(f"Date range: {min(lmp_data.keys())} to {max(lmp_data.keys())}")

# Check for missing dates in LMP
lmp_dates = set(lmp_data.keys())
missing_lmp = fuelsource_dates - lmp_dates

if missing_lmp:
    print(f"\nDates with generation but NO LMP data ({len(missing_lmp)}):")

    # Group into consecutive ranges
    missing_sorted = sorted(missing_lmp)
    ranges = []
    start = missing_sorted[0]
    end = start

    for i in range(1, len(missing_sorted)):
        curr = missing_sorted[i]
        prev = missing_sorted[i-1]

        curr_dt = datetime.strptime(curr, "%Y-%m-%d")
        prev_dt = datetime.strptime(prev, "%Y-%m-%d")

        if (curr_dt - prev_dt).days == 1:
            end = curr
        else:
            ranges.append((start, end))
            start = curr
            end = curr

    ranges.append((start, end))

    for start, end in ranges[:30]:
        if start == end:
            print(f"  {start}")
        else:
            days = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days + 1
            print(f"  {start} to {end} ({days} days)")
else:
    print("All generation dates have LMP data")

# Check LMP data completeness (hourly values)
print("\nChecking LMP hourly completeness...")
incomplete_lmp_days = []
for date, hours in lmp_data.items():
    # Check if all hours have required fields
    missing_hours = []
    for hour in range(1, 25):
        hour_str = str(hour)
        if hour_str not in hours:
            missing_hours.append(hour)
        else:
            # Check if has breakdown
            h_data = hours[hour_str]
            if 'MCC' not in h_data or 'MEC' not in h_data:
                missing_hours.append(hour)

    if missing_hours and len(missing_hours) < 24:  # Partial data
        incomplete_lmp_days.append((date, missing_hours))

if incomplete_lmp_days:
    print(f"Days with incomplete LMP hours ({len(incomplete_lmp_days)}):")
    for date, hours in incomplete_lmp_days[:20]:
        print(f"  {date}: missing hours {hours[:5]}" + ("..." if len(hours) > 5 else ""))
else:
    print("All LMP days have complete hourly data")

# Check A/S data
print("\n4. ANCILLARY SERVICES DATA")
print("-"*80)
with open("ancillary_services.json") as f:
    as_data = json.load(f)

print(f"Total dates: {len(as_data)}")
print(f"Date range: {min(as_data.keys())} to {max(as_data.keys())}")

# Check for missing dates in A/S
as_dates = set(as_data.keys())
missing_as = fuelsource_dates - as_dates

if missing_as:
    print(f"\nDates with generation but NO A/S data ({len(missing_as)}):")
    missing_sorted = sorted(missing_as)
    for date in missing_sorted[:30]:
        print(f"  {date}")
    if len(missing_sorted) > 30:
        print(f"  ... and {len(missing_sorted) - 30} more dates")
else:
    print("All generation dates have A/S data")

# Check A/S data completeness
print("\nChecking A/S hourly completeness...")
incomplete_as_days = []
for date, hours in as_data.items():
    missing_hours = []
    for hour in range(1, 25):
        hour_str = str(hour)
        if hour_str not in hours:
            missing_hours.append(hour)
        else:
            # Check if has all fields
            h_data = hours[hour_str]
            if 'NR' not in h_data or 'RU' not in h_data:
                missing_hours.append(hour)

    if missing_hours and len(missing_hours) < 24:
        incomplete_as_days.append((date, missing_hours))

if incomplete_as_days:
    print(f"Days with incomplete A/S hours ({len(incomplete_as_days)}):")
    for date, hours in incomplete_as_days[:20]:
        print(f"  {date}: missing hours {hours[:5]}" + ("..." if len(hours) > 5 else ""))
    if len(incomplete_as_days) > 20:
        print(f"  ... and {len(incomplete_as_days) - 20} more days")
else:
    print("All A/S days have complete hourly data")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Fuelsource CSVs: {len(fuelsource_files)} files")
print(f"  Incomplete: {len(incomplete_fuelsource)} files")
print(f"Demand CSVs: {len(demand_files)} files")
print(f"  Missing: {len(missing_demand)} dates")
print(f"LMP data: {len(lmp_data)} dates")
print(f"  Missing: {len(missing_lmp)} dates")
print(f"  Incomplete hours: {len(incomplete_lmp_days)} dates")
print(f"A/S data: {len(as_data)} dates")
print(f"  Missing: {len(missing_as)} dates")
print(f"  Incomplete hours: {len(incomplete_as_days)} dates")
