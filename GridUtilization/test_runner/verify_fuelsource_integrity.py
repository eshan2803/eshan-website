"""
Verify fuelsource file structural integrity.
Since fuelsource files don't contain dates, we can only check:
1. Each file has 288 rows (24 hours * 12 intervals)
2. Time progression is correct (00:00, 00:05, ..., 23:55)
3. No corrupt/incomplete files
"""
import os
import csv
import glob
from datetime import datetime

print("="*80)
print("VERIFYING FUELSOURCE FILE INTEGRITY")
print("="*80)

fuelsource_files = sorted(glob.glob("caiso_supply/*_fuelsource.csv"))
print(f"\nTotal fuelsource files: {len(fuelsource_files)}")

correct_count = 0
incorrect_rows = []
time_sequence_errors = []
corrupt_files = []

expected_times = [f"{h}:{m:02d}" for h in range(24) for m in range(0, 60, 5)]
expected_row_count = 288  # 24 hours * 12 five-minute intervals

for i, fpath in enumerate(fuelsource_files):
    basename = os.path.basename(fpath)

    try:
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Check row count
            if len(rows) != expected_row_count:
                incorrect_rows.append({
                    'file': basename,
                    'expected': expected_row_count,
                    'actual': len(rows)
                })
                continue

            # Check time sequence
            times = [row.get('Time', '') for row in rows]
            if times != expected_times:
                # Check if just off by one or completely wrong
                first_time = times[0] if times else 'N/A'
                last_time = times[-1] if times else 'N/A'
                time_sequence_errors.append({
                    'file': basename,
                    'first': first_time,
                    'last': last_time,
                    'count': len(times)
                })
                continue

            correct_count += 1

    except Exception as e:
        corrupt_files.append({
            'file': basename,
            'error': str(e)
        })

    if (i + 1) % 500 == 0:
        print(f"  Checked {i+1}/{len(fuelsource_files)}...")

print(f"\nResults:")
print(f"  Correct structure: {correct_count} ({correct_count/len(fuelsource_files)*100:.1f}%)")
print(f"  Incorrect row count: {len(incorrect_rows)}")
print(f"  Time sequence errors: {len(time_sequence_errors)}")
print(f"  Corrupt/unreadable: {len(corrupt_files)}")

if incorrect_rows:
    print(f"\nIncorrect row count (first 10):")
    for item in incorrect_rows[:10]:
        print(f"  {item['file']}: {item['actual']} rows (expected {item['expected']})")

if time_sequence_errors:
    print(f"\nTime sequence errors (first 10):")
    for item in time_sequence_errors[:10]:
        print(f"  {item['file']}: {item['first']} to {item['last']} ({item['count']} rows)")

if corrupt_files:
    print(f"\nCorrupt files (first 10):")
    for item in corrupt_files[:10]:
        print(f"  {item['file']}: {item['error']}")

print(f"\n{'='*80}")
print("CONCLUSION:")
print("="*80)

if correct_count == len(fuelsource_files):
    print("*** ALL FUELSOURCE FILES HAVE CORRECT STRUCTURE ***")
    print("(Note: Cannot verify dates since files don't contain date information)")
else:
    print(f"*** {len(fuelsource_files) - correct_count} FILES HAVE ISSUES ***")
    print(f"These files may need to be re-downloaded or fixed.")

print(f"\nNote: Fuelsource files only contain time columns (00:00-23:55).")
print(f"Date verification is impossible without external metadata.")
print(f"If supply CSVs have date issues like demand CSVs did, fuelsource may too.")
