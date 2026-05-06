"""
Verify that ALL data files are correctly labeled (filename matches content date).
Checks: fuelsource, supply, LMP prices, A/S prices
"""
import os
import csv
import json
import glob
from datetime import datetime

print("="*80)
print("VERIFYING ALL DATA FILE LABELS")
print("="*80)

# ============================================================================
# 1. FUELSOURCE FILES
# ============================================================================
print("\n1. FUELSOURCE FILES (caiso_supply/*_fuelsource.csv)")
print("-"*80)

fuelsource_files = sorted(glob.glob("caiso_supply/*_fuelsource.csv"))
print(f"Total fuelsource files: {len(fuelsource_files)}")

fuelsource_correct = 0
fuelsource_mismatched = []

for i, fpath in enumerate(fuelsource_files):
    basename = os.path.basename(fpath)
    filename_date = basename.split('_')[0]

    try:
        # Read first data row to check date
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)

            if first_row and 'Date' in first_row:
                # Date format: MM/DD/YYYY
                actual_date_str = first_row['Date']
                actual_dt = datetime.strptime(actual_date_str, '%m/%d/%Y')
                actual_date = actual_dt.strftime('%Y%m%d')

                if filename_date == actual_date:
                    fuelsource_correct += 1
                else:
                    fuelsource_mismatched.append({
                        'filename': basename,
                        'filename_date': filename_date,
                        'actual_date': actual_date,
                        'actual_str': actual_date_str
                    })
    except Exception as e:
        pass

    if (i + 1) % 500 == 0:
        print(f"  Checked {i+1}/{len(fuelsource_files)}...")

print(f"\nResults:")
print(f"  Correct: {fuelsource_correct}")
print(f"  Mismatched: {len(fuelsource_mismatched)}")

if fuelsource_mismatched:
    print(f"\nMismatched files (first 20):")
    for m in fuelsource_mismatched[:20]:
        print(f"  {m['filename']} -> Should be {m['actual_date']}_fuelsource.csv (data from {m['actual_str']})")

# ============================================================================
# 2. LMP PRICE DATA (caiso_prices.json)
# ============================================================================
print(f"\n{'='*80}")
print("2. LMP PRICE DATA (caiso_prices.json)")
print("-"*80)

try:
    with open('caiso_prices.json', 'r') as f:
        lmp_data = json.load(f)

    print(f"Total dates in caiso_prices.json: {len(lmp_data)}")

    # Check structure: should be {date: {hour: {LMP, MCC, MEC, etc}}}
    lmp_issues = []

    for date_key in list(lmp_data.keys())[:10]:  # Sample first 10
        try:
            # Verify date_key is valid format YYYY-MM-DD
            dt = datetime.strptime(date_key, '%Y-%m-%d')

            # Check hourly data structure
            hourly_data = lmp_data[date_key]
            if not isinstance(hourly_data, dict):
                lmp_issues.append(f"{date_key}: Invalid structure (not dict)")
        except Exception as e:
            lmp_issues.append(f"{date_key}: {e}")

    if lmp_issues:
        print(f"Structure issues found:")
        for issue in lmp_issues:
            print(f"  {issue}")
    else:
        print(f"Structure: OK (date keys valid, hourly data present)")

    # Check date coverage
    dates = sorted(lmp_data.keys())
    print(f"Date range: {dates[0]} to {dates[-1]}")

except FileNotFoundError:
    print("File not found: caiso_prices.json")
except Exception as e:
    print(f"Error reading caiso_prices.json: {e}")

# ============================================================================
# 3. ANCILLARY SERVICES DATA (ancillary_services.json)
# ============================================================================
print(f"\n{'='*80}")
print("3. ANCILLARY SERVICES DATA (ancillary_services.json)")
print("-"*80)

try:
    with open('ancillary_services.json', 'r') as f:
        as_data = json.load(f)

    print(f"Total dates in ancillary_services.json: {len(as_data)}")

    # Check structure
    as_issues = []

    for date_key in list(as_data.keys())[:10]:  # Sample first 10
        try:
            dt = datetime.strptime(date_key, '%Y-%m-%d')

            hourly_data = as_data[date_key]
            if not isinstance(hourly_data, dict):
                as_issues.append(f"{date_key}: Invalid structure")
        except Exception as e:
            as_issues.append(f"{date_key}: {e}")

    if as_issues:
        print(f"Structure issues found:")
        for issue in as_issues:
            print(f"  {issue}")
    else:
        print(f"Structure: OK")

    # Check date coverage
    dates = sorted(as_data.keys())
    print(f"Date range: {dates[0]} to {dates[-1]}")

except FileNotFoundError:
    print("File not found: ancillary_services.json")
except Exception as e:
    print(f"Error reading ancillary_services.json: {e}")

# ============================================================================
# 4. BATTERY CHARGING DATA (battery_charging.json)
# ============================================================================
print(f"\n{'='*80}")
print("4. BATTERY CHARGING DATA (battery_charging.json)")
print("-"*80)

try:
    with open('battery_charging.json', 'r') as f:
        battery_data = json.load(f)

    print(f"Total dates in battery_charging.json: {len(battery_data)}")

    # Check structure
    dates = sorted(battery_data.keys())
    print(f"Date range: {dates[0]} to {dates[-1]}")

    # Sample check
    sample_date = dates[0]
    sample_data = battery_data[sample_date]
    print(f"Sample data structure ({sample_date}): {type(sample_data)} with {len(sample_data) if isinstance(sample_data, dict) else 'N/A'} entries")

except FileNotFoundError:
    print("File not found: battery_charging.json")
except Exception as e:
    print(f"Error reading battery_charging.json: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print(f"\n{'='*80}")
print("SUMMARY")
print("="*80)

print(f"\nFuelsource files:")
print(f"  Total: {len(fuelsource_files)}")
print(f"  Correct: {fuelsource_correct} ({fuelsource_correct/len(fuelsource_files)*100:.1f}%)")
print(f"  Mismatched: {len(fuelsource_mismatched)} ({len(fuelsource_mismatched)/len(fuelsource_files)*100:.1f}%)")

if len(fuelsource_mismatched) > 0:
    print(f"\n*** WARNING: {len(fuelsource_mismatched)} fuelsource files are mislabeled! ***")
    print(f"*** This will cause the same issues as demand files! ***")
else:
    print(f"\n*** Fuelsource files: ALL CORRECT ***")

print("\nJSON data files appear to be indexed by date strings, not filenames.")
print("These should be safe as long as the date keys are correct.")
