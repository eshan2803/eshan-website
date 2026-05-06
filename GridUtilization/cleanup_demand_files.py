"""
Clean up demand files - keep one correctly named file per date, delete duplicates.
"""
import os
import glob
from datetime import datetime
from collections import defaultdict

DEMAND_DIR = "caiso_demand_downloads"
BACKUP_DIR = "caiso_demand_downloads_backup"

# Create backup directory
os.makedirs(BACKUP_DIR, exist_ok=True)

demand_files = sorted(glob.glob(os.path.join(DEMAND_DIR, "*_demand.csv")))

print(f"Processing {len(demand_files)} demand files...")
print("="*80)

# Map: actual_date -> list of (filepath, filename, is_correct_name)
date_to_files = defaultdict(list)

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

                    is_correct = (filename_date == actual_date)
                    date_to_files[actual_date].append((fpath, basename, is_correct))
    except Exception as e:
        print(f"ERROR reading {basename}: {e}")

print(f"Found data for {len(date_to_files)} unique dates")

# For each date, keep one file (prefer correctly named, then earliest filename)
files_to_keep = []
files_to_delete = []

for actual_date, file_list in date_to_files.items():
    # Sort: correctly named first, then by filename
    file_list_sorted = sorted(file_list, key=lambda x: (not x[2], x[1]))

    # Keep the first one
    to_keep = file_list_sorted[0]
    files_to_keep.append(to_keep)

    # Delete the rest
    for f in file_list_sorted[1:]:
        files_to_delete.append(f)

    # If kept file is not correctly named, rename it
    if not to_keep[2]:
        old_path = to_keep[0]
        correct_name = f"{actual_date}_demand.csv"
        new_path = os.path.join(DEMAND_DIR, correct_name)

        # Check if target already exists
        if os.path.exists(new_path):
            # This should not happen since we're processing one date at a time
            print(f"WARNING: Target {correct_name} already exists when trying to rename {to_keep[1]}")
        else:
            files_to_keep.append((new_path, correct_name, True))  # Update record
            # Will rename after deletions

print(f"\n{'='*80}")
print(f"Plan:")
print(f"  Keep: {len(files_to_keep)} files")
print(f"  Delete: {len(files_to_delete)} files")

# Execute deletions
print(f"\nDeleting {len(files_to_delete)} duplicate files...")
deleted_count = 0
for fpath, basename, _ in files_to_delete:
    try:
        os.remove(fpath)
        deleted_count += 1
    except Exception as e:
        print(f"ERROR deleting {basename}: {e}")

print(f"Deleted {deleted_count} files")

# Rename incorrectly named files
print(f"\nRenaming incorrectly named files...")
renamed_count = 0

# Re-scan to handle renames
for actual_date, file_list in date_to_files.items():
    # Check if the correct filename exists
    correct_filename = f"{actual_date}_demand.csv"
    correct_path = os.path.join(DEMAND_DIR, correct_filename)

    if not os.path.exists(correct_path):
        # Find which file should be renamed
        remaining_files = [f for f in file_list if os.path.exists(f[0])]
        if remaining_files:
            old_path = remaining_files[0][0]
            try:
                os.rename(old_path, correct_path)
                renamed_count += 1
            except Exception as e:
                print(f"ERROR renaming {remaining_files[0][1]} to {correct_filename}: {e}")

print(f"Renamed {renamed_count} files")

# Verify
print(f"\n{'='*80}")
print("Verifying...")
final_files = sorted(glob.glob(os.path.join(DEMAND_DIR, "*_demand.csv")))
verify_correct = 0
verify_incorrect = 0

for fpath in final_files:
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
                        verify_incorrect += 1
                        print(f"STILL INCORRECT: {basename} has data for {actual_date}")
    except:
        pass

print(f"\n{'='*80}")
print(f"FINAL RESULTS:")
print(f"  Total files: {len(final_files)}")
print(f"  Correct: {verify_correct}")
print(f"  Incorrect: {verify_incorrect}")
print("="*80)
