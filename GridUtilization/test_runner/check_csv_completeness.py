"""
Check comprehensive CSV for missing dates/hours/timestamps.
Reports any gaps in the data.
"""
import csv
from datetime import datetime, timedelta
from collections import defaultdict

CSV_FILE = "caiso_comprehensive_data.csv"

def check_completeness():
    print("=" * 80)
    print("COMPREHENSIVE CSV COMPLETENESS CHECK")
    print("=" * 80)

    # Read all timestamps from CSV
    timestamps = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M")
                timestamps.append(ts)
            except:
                pass

    if not timestamps:
        print("ERROR: No valid timestamps found in CSV")
        return

    timestamps.sort()
    first_ts = timestamps[0]
    last_ts = timestamps[-1]

    print(f"\nFirst timestamp: {first_ts}")
    print(f"Last timestamp:  {last_ts}")
    print(f"Total rows: {len(timestamps):,}")

    # Expected: 288 timestamps per day (5-minute intervals)
    first_date = first_ts.date()
    last_date = last_ts.date()
    total_days = (last_date - first_date).days + 1
    expected_rows = total_days * 288

    print(f"\nDate range: {first_date} to {last_date}")
    print(f"Total days: {total_days:,}")
    print(f"Expected rows: {expected_rows:,} (288 per day)")
    print(f"Actual rows: {len(timestamps):,}")

    if len(timestamps) < expected_rows:
        missing = expected_rows - len(timestamps)
        print(f"\n[WARNING] MISSING {missing:,} rows ({missing/288:.1f} days)")
    else:
        print("\n[OK] Row count matches expected")

    # Check for missing dates
    print("\n" + "-" * 80)
    print("CHECKING FOR MISSING DATES")
    print("-" * 80)

    # Group timestamps by date
    dates_dict = defaultdict(list)
    for ts in timestamps:
        dates_dict[ts.date()].append(ts)

    missing_dates = []
    incomplete_dates = []

    current_date = first_date
    while current_date <= last_date:
        if current_date not in dates_dict:
            missing_dates.append(current_date)
        elif len(dates_dict[current_date]) < 288:
            incomplete_dates.append((current_date, len(dates_dict[current_date])))
        current_date += timedelta(days=1)

    if missing_dates:
        print(f"\n[WARNING] MISSING DATES ({len(missing_dates)}):")
        for d in missing_dates[:20]:
            print(f"  - {d}")
        if len(missing_dates) > 20:
            print(f"  ... and {len(missing_dates) - 20} more")
    else:
        print("\n[OK] No missing dates")

    if incomplete_dates:
        print(f"\n[WARNING] INCOMPLETE DATES ({len(incomplete_dates)}):")
        for d, count in incomplete_dates[:20]:
            print(f"  - {d}: {count}/288 rows (missing {288-count})")
        if len(incomplete_dates) > 20:
            print(f"  ... and {len(incomplete_dates) - 20} more")
    else:
        print("\n[OK] All dates have complete 288 timestamps")

    # Check for gaps in timestamps within each date
    print("\n" + "-" * 80)
    print("CHECKING FOR TIMESTAMP GAPS")
    print("-" * 80)

    dates_with_gaps = []

    for date in sorted(dates_dict.keys()):
        day_timestamps = sorted(dates_dict[date])

        # Expected: 00:00, 00:05, 00:10, ..., 23:55
        expected_ts = []
        for hour in range(24):
            for minute in range(0, 60, 5):
                expected_ts.append(datetime(date.year, date.month, date.day, hour, minute))

        missing_ts = []
        for exp in expected_ts:
            if exp not in day_timestamps:
                missing_ts.append(exp)

        if missing_ts:
            dates_with_gaps.append((date, missing_ts))

    if dates_with_gaps:
        print(f"\n[WARNING] DATES WITH TIMESTAMP GAPS ({len(dates_with_gaps)}):")
        for date, missing in dates_with_gaps[:10]:
            print(f"\n  {date} - missing {len(missing)} timestamps:")
            for ts in missing[:5]:
                print(f"    - {ts.strftime('%H:%M')}")
            if len(missing) > 5:
                print(f"    ... and {len(missing) - 5} more")
        if len(dates_with_gaps) > 10:
            print(f"\n  ... and {len(dates_with_gaps) - 10} more dates with gaps")
    else:
        print("\n[OK] No timestamp gaps found - all 5-minute intervals present")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    issues = []
    if missing_dates:
        issues.append(f"{len(missing_dates)} missing dates")
    if incomplete_dates:
        issues.append(f"{len(incomplete_dates)} incomplete dates")
    if dates_with_gaps:
        issues.append(f"{len(dates_with_gaps)} dates with timestamp gaps")

    if issues:
        print("\n[WARNING] ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n[OK] CSV IS COMPLETE - no gaps found!")

    print("=" * 80)

if __name__ == "__main__":
    check_completeness()
