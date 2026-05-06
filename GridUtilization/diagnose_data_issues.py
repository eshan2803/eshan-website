"""
Comprehensive data quality check for all CAISO fuelsource CSV files.

Identifies days with suspicious data patterns:
1. Zero or near-zero Large hydro (should be baseline ~2000 MW)
2. Zero or very low Natural gas (suspicious during most hours)
3. Abnormally low total demand
4. Extreme clean energy penetration (>150%) that might indicate bad data
"""
import os
import csv
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = "caiso_supply"

# Thresholds for suspicious values
SUSPICIOUS_LARGE_HYDRO_THRESHOLD = 100  # MW
SUSPICIOUS_GAS_THRESHOLD = 1000  # MW (should rarely be this low)
SUSPICIOUS_LOW_DEMAND = 15000  # MW (California rarely below this)
SUSPICIOUS_HIGH_CLEAN_PCT = 150  # % (might indicate bad data if consistently this high)

print("Scanning all CAISO fuelsource CSV files for data quality issues...")
print("=" * 80)

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Found {len(files)} files to analyze\n")

issues_by_date = defaultdict(list)
clean_cols = ['Solar', 'Wind', 'Geothermal', 'Biomass', 'Biogas', 'Small hydro', 'Nuclear', 'Large Hydro']

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]

    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    date_str = dt.strftime("%Y-%m-%d")

    # Analyze this day's data
    zero_large_hydro_count = 0
    low_gas_count = 0
    low_demand_count = 0
    high_clean_pct_count = 0

    total_rows = 0
    avg_large_hydro = 0
    avg_gas = 0
    avg_demand = 0
    max_clean_pct = 0

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_rows += 1

                # Check Large hydro
                try:
                    large_hydro = float(row.get("Large Hydro", 0) or 0)
                    avg_large_hydro += large_hydro
                    if large_hydro < SUSPICIOUS_LARGE_HYDRO_THRESHOLD:
                        zero_large_hydro_count += 1
                except (ValueError, TypeError):
                    pass

                # Check Natural gas
                try:
                    gas = float(row.get("Natural Gas", 0) or 0)
                    avg_gas += gas
                    if gas < SUSPICIOUS_GAS_THRESHOLD:
                        low_gas_count += 1
                except (ValueError, TypeError):
                    pass

                # Calculate total demand
                try:
                    demand = sum(float(row.get(col, 0) or 0) for col in [
                        "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
                        "Coal", "Nuclear", "Natural Gas", "Large Hydro", "Batteries",
                        "Imports", "Other"
                    ])
                    avg_demand += demand
                    if demand < SUSPICIOUS_LOW_DEMAND:
                        low_demand_count += 1
                except:
                    pass

                # Calculate clean energy percentage
                try:
                    clean_mw = sum(float(row.get(col, 0) or 0) for col in clean_cols)
                    battery = float(row.get("Batteries", 0) or 0)
                    if battery > 0:
                        clean_mw += battery

                    if demand > 0:
                        clean_pct = (clean_mw / demand) * 100
                        max_clean_pct = max(max_clean_pct, clean_pct)
                        if clean_pct > SUSPICIOUS_HIGH_CLEAN_PCT:
                            high_clean_pct_count += 1
                except:
                    pass

        # Calculate averages
        if total_rows > 0:
            avg_large_hydro /= total_rows
            avg_gas /= total_rows
            avg_demand /= total_rows

        # Flag suspicious days
        has_issues = False

        if zero_large_hydro_count > total_rows * 0.5:  # More than 50% of intervals have low hydro
            issues_by_date[date_str].append(f"Large hydro near-zero for {zero_large_hydro_count}/{total_rows} intervals (avg: {avg_large_hydro:.0f} MW)")
            has_issues = True

        if low_gas_count > total_rows * 0.5:  # More than 50% of intervals have low gas
            issues_by_date[date_str].append(f"Natural gas very low for {low_gas_count}/{total_rows} intervals (avg: {avg_gas:.0f} MW)")
            has_issues = True

        if low_demand_count > total_rows * 0.5:  # More than 50% of intervals have low demand
            issues_by_date[date_str].append(f"Total demand suspiciously low for {low_demand_count}/{total_rows} intervals (avg: {avg_demand:.0f} MW)")
            has_issues = True

        if high_clean_pct_count > 5:  # More than 5 intervals with >150% clean
            issues_by_date[date_str].append(f"Clean energy >150% for {high_clean_pct_count} intervals (max: {max_clean_pct:.1f}%)")
            has_issues = True

    except Exception as e:
        issues_by_date[date_str].append(f"ERROR reading file: {e}")

    if (i + 1) % 500 == 0:
        print(f"  Analyzed {i+1}/{len(files)} files...")

print(f"\nAnalysis complete. Found issues in {len(issues_by_date)} days.\n")
print("=" * 80)

if issues_by_date:
    print("\nDAYS WITH DATA QUALITY ISSUES:")
    print("=" * 80)

    # Group by year and month
    by_year_month = defaultdict(list)
    for date_str in sorted(issues_by_date.keys()):
        year_month = date_str[:7]  # YYYY-MM
        by_year_month[year_month].append(date_str)

    for year_month in sorted(by_year_month.keys()):
        print(f"\n{year_month}:")
        print("-" * 80)
        for date_str in by_year_month[year_month]:
            print(f"\n  {date_str}:")
            for issue in issues_by_date[date_str]:
                print(f"    - {issue}")

    # Summary by issue type
    print("\n" + "=" * 80)
    print("\nSUMMARY BY ISSUE TYPE:")
    print("=" * 80)

    large_hydro_issues = sum(1 for issues in issues_by_date.values() if any('Large hydro' in i for i in issues))
    gas_issues = sum(1 for issues in issues_by_date.values() if any('Natural gas' in i for i in issues))
    demand_issues = sum(1 for issues in issues_by_date.values() if any('demand' in i.lower() for i in issues))
    clean_pct_issues = sum(1 for issues in issues_by_date.values() if any('Clean energy' in i for i in issues))

    print(f"  Days with Large hydro issues: {large_hydro_issues}")
    print(f"  Days with Natural gas issues: {gas_issues}")
    print(f"  Days with Low demand issues: {demand_issues}")
    print(f"  Days with High clean % issues: {clean_pct_issues}")
    print(f"\n  Total days with issues: {len(issues_by_date)}")
else:
    print("\nNo data quality issues found!")

print("\n" + "=" * 80)
