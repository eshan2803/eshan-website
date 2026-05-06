"""
Fix mislabeled demand files by renaming them to match the actual date in cell A1.
"""
import os
import glob
import shutil
from datetime import datetime

DEMAND_DIR = "caiso_demand_downloads"

demand_files = sorted(glob.glob(os.path.join(DEMAND_DIR, "*_demand.csv")))

print(f"Found {len(demand_files)} demand files")
print("="*80)

# First pass: identify all files and their correct names
file_mapping = {}
mismatches = []
correct = 0

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

                    correct_filename = f"{actual_date}_demand.csv"
                    correct_path = os.path.join(DEMAND_DIR, correct_filename)

                    if filename_date != actual_date:
                        mismatches.append({
                            'old_path': fpath,
                            'new_path': correct_path,
                            'old_name': basename,
                            'new_name': correct_filename,
                            'date': actual_date
                        })
                    else:
                        correct += 1

                    file_mapping[fpath] = correct_path
    except Exception as e:
        print(f"ERROR reading {basename}: {e}")

print(f"Analysis:")
print(f"  Correct: {correct}")
print(f"  Need renaming: {len(mismatches)}")

# Check for conflicts (multiple files trying to rename to same name)
from collections import defaultdict
target_names = defaultdict(list)
for m in mismatches:
    target_names[m['new_name']].append(m['old_name'])

conflicts = {k: v for k, v in target_names.items() if len(v) > 1}
if conflicts:
    print(f"\n{'='*80}")
    print(f"WARNING: {len(conflicts)} naming conflicts detected!")
    print(f"{'='*80}")
    for new_name, old_names in list(conflicts.items())[:10]:
        print(f"{new_name} <- {old_names}")
    print(f"\nCannot proceed with renaming due to conflicts.")
    print(f"Manual intervention required.")
else:
    print(f"\nNo conflicts detected. Safe to rename.")

    # Rename in two passes to avoid overwriting
    # Pass 1: Rename to temporary names
    print(f"\nPass 1: Renaming to temporary names...")
    temp_mapping = {}
    for m in mismatches:
        temp_name = m['old_path'] + '.tmp'
        shutil.move(m['old_path'], temp_name)
        temp_mapping[temp_name] = m['new_path']

    print(f"Pass 2: Renaming to final names...")
    for temp_path, final_path in temp_mapping.items():
        shutil.move(temp_path, final_path)

    print(f"\n{'='*80}")
    print(f"SUCCESS: Renamed {len(mismatches)} files")
    print(f"{'='*80}")

# Verify
print(f"\nVerifying renamed files...")
renamed_files = sorted(glob.glob(os.path.join(DEMAND_DIR, "*_demand.csv")))
verify_correct = 0
verify_mismatch = 0

for fpath in renamed_files:
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

                    if filename_date == actual_date:
                        verify_correct += 1
                    else:
                        verify_mismatch += 1
    except:
        pass

print(f"After renaming: {verify_correct} correct, {verify_mismatch} mismatched")
