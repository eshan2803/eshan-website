"""
Check comprehensive CSV for missing data and gaps.
Reports:
1. Missing timestamps (gaps in 5-minute intervals)
2. Missing demand data
3. Missing LMP data
4. Missing A/S data
"""
import csv
from datetime import datetime, timedelta
from collections import defaultdict

print("Analyzing comprehensive CSV for completeness...\n")

# Track issues
missing_timestamps = []
rows_no_demand = []
rows_no_lmp = defaultdict(int)  # Count by date
rows_no_as = defaultdict(int)
all_timestamps = []
dates_seen = set()

with open('caiso_comprehensive_data.csv') as f:
    reader = csv.DictReader(f)

    prev_timestamp = None

    for row in reader:
        timestamp_str = row['timestamp']
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        all_timestamps.append(timestamp)
        date_key = timestamp.strftime("%Y-%m-%d")
        dates_seen.add(date_key)

        # Check for gaps in timestamps (should be 5 minutes apart)
        if prev_timestamp:
            expected_next = prev_timestamp + timedelta(minutes=5)
            if timestamp != expected_next:
                # Gap detected
                missing_timestamps.append({
                    'after': prev_timestamp,
                    'before': timestamp,
                    'gap_minutes': (timestamp - prev_timestamp).total_seconds() / 60
                })

        prev_timestamp = timestamp

        # Check for missing demand
        if not row['demand_mw']:
            rows_no_demand.append(timestamp_str)

        # Check for missing LMP (only count at :00 when it should exist)
        if timestamp.minute == 0:
            if not row['lmp']:
                rows_no_lmp[date_key] += 1

        # Check for missing A/S (only count at :00 when it should exist)
        if timestamp.minute == 0:
            if not row['nr']:
                rows_no_as[date_key] += 1

# Report
print("="*80)
print("TIMESTAMP GAPS (missing 5-minute intervals)")
print("="*80)
if missing_timestamps:
    print(f"Found {len(missing_timestamps)} gaps:\n")
    for gap in missing_timestamps[:20]:  # Show first 20
        print(f"  Gap after {gap['after']} (missing {int(gap['gap_minutes'])} minutes)")
        print(f"    -> Next timestamp: {gap['before']}")
    if len(missing_timestamps) > 20:
        print(f"\n  ... and {len(missing_timestamps) - 20} more gaps")
else:
    print("[OK] No timestamp gaps found")

print("\n" + "="*80)
print("MISSING DEMAND DATA (rows with empty demand_mw)")
print("="*80)
if rows_no_demand:
    print(f"Found {len(rows_no_demand)} rows with missing demand:\n")
    # Group by date
    demand_by_date = defaultdict(list)
    for ts in rows_no_demand[:100]:  # Limit to first 100
        date = ts.split()[0]
        time = ts.split()[1]
        demand_by_date[date].append(time)

    for date in sorted(demand_by_date.keys())[:20]:
        times = demand_by_date[date]
        if len(times) <= 5:
            print(f"  {date}: {', '.join(times)}")
        else:
            print(f"  {date}: {times[0]} to {times[-1]} ({len(times)} intervals)")

    if len(demand_by_date) > 20:
        print(f"\n  ... and {len(demand_by_date) - 20} more dates with missing demand")
else:
    print("[OK] No missing demand data")

print("\n" + "="*80)
print("MISSING LMP DATA (dates with missing hourly LMP at :00)")
print("="*80)
if rows_no_lmp:
    dates_missing_lmp = [(date, count) for date, count in rows_no_lmp.items() if count > 0]
    dates_missing_lmp.sort()

    if dates_missing_lmp:
        print(f"Found {len(dates_missing_lmp)} dates with missing LMP data:\n")

        # Group consecutive dates
        ranges = []
        start_date = dates_missing_lmp[0][0]
        end_date = start_date

        for i in range(1, len(dates_missing_lmp)):
            curr_date = dates_missing_lmp[i][0]
            prev_date = dates_missing_lmp[i-1][0]

            curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
            prev_dt = datetime.strptime(prev_date, "%Y-%m-%d")

            if (curr_dt - prev_dt).days == 1:
                end_date = curr_date
            else:
                ranges.append((start_date, end_date))
                start_date = curr_date
                end_date = curr_date

        ranges.append((start_date, end_date))

        for start, end in ranges[:20]:
            if start == end:
                hours_missing = rows_no_lmp[start]
                print(f"  {start}: {hours_missing}/24 hours missing")
            else:
                print(f"  {start} to {end}: Multiple days")

        if len(ranges) > 20:
            print(f"\n  ... and {len(ranges) - 20} more date ranges")
    else:
        print("[OK] All dates have complete LMP data")
else:
    print("[OK] No missing LMP data")

print("\n" + "="*80)
print("MISSING A/S DATA (dates with missing hourly A/S at :00)")
print("="*80)
if rows_no_as:
    dates_missing_as = [(date, count) for date, count in rows_no_as.items() if count > 0]
    dates_missing_as.sort()

    if dates_missing_as:
        print(f"Found {len(dates_missing_as)} dates with missing A/S data:\n")

        # Show first 20
        for date, count in dates_missing_as[:20]:
            print(f"  {date}: {count}/24 hours missing")

        if len(dates_missing_as) > 20:
            print(f"\n  ... and {len(dates_missing_as) - 20} more dates")
    else:
        print("[OK] All dates have complete A/S data")
else:
    print("[OK] No missing A/S data")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total timestamps: {len(all_timestamps):,}")
print(f"Date range: {min(dates_seen)} to {max(dates_seen)}")
print(f"Days covered: {len(dates_seen)}")
print(f"Timestamp gaps: {len(missing_timestamps)}")
print(f"Rows with missing demand: {len(rows_no_demand)}")
print(f"Dates with missing LMP: {len([d for d in rows_no_lmp.values() if d > 0])}")
print(f"Dates with missing A/S: {len([d for d in rows_no_as.values() if d > 0])}")
