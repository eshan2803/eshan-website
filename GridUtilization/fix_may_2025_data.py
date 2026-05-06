"""
Fix May 2025 data issues:
1. Re-download demand files with correct dates
2. Regenerate comprehensive CSV (fixes Natural Gas/Large Hydro = 0 bug)
3. Recalculate renewable penetration (fixes inflated % values)
4. Regenerate all charts

Run this after the scripts have been fixed.
"""
import os
import subprocess
import json
from datetime import date, timedelta
from pathlib import Path

# Color codes
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(msg, color=Colors.OKBLUE):
    print(f"{color}{msg}{Colors.ENDC}")

def log_header(msg):
    print(f"\n{'='*70}")
    log(msg, Colors.HEADER + Colors.BOLD)
    print('='*70)

def log_success(msg):
    log(f"[OK] {msg}", Colors.OKGREEN)

def log_error(msg):
    log(f"[ERROR] {msg}", Colors.FAIL)

def log_warning(msg):
    log(f"[WARNING] {msg}", Colors.WARNING)

def run_command(cmd, description):
    """Run a command and return success status"""
    log(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1800  # 30 minutes max
        )
        if result.returncode == 0:
            log_success(f"{description} completed")
            return True
        else:
            log_error(f"{description} failed")
            if result.stderr:
                print(f"  Error: {result.stderr[:500]}")
            return False
    except Exception as e:
        log_error(f"{description} error: {e}")
        return False

# Step 1: Identify and delete wrong demand files
log_header("STEP 1: Delete Wrong Demand Files for May 2025")

demand_dir = Path("caiso_demand_downloads")
may_2025_files = list(demand_dir.glob("202505*_demand.csv"))

log(f"Found {len(may_2025_files)} May 2025 demand files")

deleted = 0
for file in may_2025_files:
    try:
        # Check if file has wrong date
        with open(file, 'r') as f:
            first_line = f.readline()
            # Should contain "05/.../2025" but many have 2021, 2023, etc.
            if "2025" not in first_line or "Demand" not in first_line:
                log_warning(f"Deleting {file.name} (contains: {first_line[:50]})")
                file.unlink()
                deleted += 1
            elif "2021" in first_line or "2023" in first_line or "2024" in first_line or "2020" in first_line:
                # Definitely wrong year
                log_warning(f"Deleting {file.name} (wrong year in: {first_line[:50]})")
                file.unlink()
                deleted += 1
    except Exception as e:
        log_error(f"Could not check {file.name}: {e}")

log_success(f"Deleted {deleted} incorrect demand files")

# Step 2: Create list of dates to re-download (May 1-31, 2025)
log_header("STEP 2: Create List of Dates to Re-Download")

dates_to_download = []
start_date = date(2025, 5, 1)
end_date = date(2025, 5, 31)

current = start_date
while current <= end_date:
    demand_file = demand_dir / f"{current.strftime('%Y%m%d')}_demand.csv"
    if not demand_file.exists():
        dates_to_download.append(current)
    current += timedelta(days=1)

log(f"Need to download {len(dates_to_download)} dates")

if dates_to_download:
    # Write to temp file for download script
    with open("temp_missing_dates.txt", "w") as f:
        for d in dates_to_download:
            f.write(d.strftime("%Y-%m-%d") + "\n")

    log_success(f"Created temp_missing_dates.txt with {len(dates_to_download)} dates")

    # Step 3: Re-download demand files
    log_header("STEP 3: Re-Download Demand Files")

    success = run_command(
        "python download_missing_dates.py",
        f"Downloading {len(dates_to_download)} demand files"
    )

    # Clean up temp file
    if os.path.exists("temp_missing_dates.txt"):
        os.remove("temp_missing_dates.txt")

    if not success:
        log_error("Demand download failed - stopping here")
        exit(1)
else:
    log_success("All May 2025 demand files already correct")

# Step 4: Regenerate comprehensive CSV
log_header("STEP 4: Regenerate Comprehensive CSV")

log("This will take 5-10 minutes...")
success = run_command(
    "python create_comprehensive_csv.py",
    "Regenerating comprehensive CSV with fixed extraction logic"
)

if not success:
    log_error("CSV regeneration failed")
    exit(1)

# Step 5: Recalculate renewable penetration
log_header("STEP 5: Recalculate Renewable Penetration")

success1 = run_command(
    "python process_renewable_penetration_with_demand_csv_v3.py",
    "Daily renewable penetration"
)

success2 = run_command(
    "python process_renewable_penetration_hourly_corrected.py",
    "Hourly renewable penetration"
)

if not (success1 and success2):
    log_error("Penetration calculation failed")
    exit(1)

# Step 6: Regenerate charts
log_header("STEP 6: Regenerate Charts")

charts = [
    ("plot_renewable_penetration_improved_v3.py", "Main renewable penetration chart"),
    ("plot_daily_metrics_4panel.py", "4-panel daily metrics dashboard"),
    ("plot_natural_gas_generation.py", "Natural gas generation chart"),
    ("plot_energy_breakdown.py", "Energy breakdown chart"),
    ("plot_energy_breakdown_v2.py", "Energy breakdown V2 chart"),
    ("plot_lmp_vs_battery_by_year.py", "LMP vs battery by year chart"),
    ("plot_as_vs_lmp_by_year.py", "A/S vs LMP by year charts"),
    ("plot_as_vs_load_by_year.py", "A/S vs load by year charts"),
]

chart_success = 0
for script, description in charts:
    if os.path.exists(script):
        if run_command(f"python {script}", description):
            chart_success += 1

log_success(f"Regenerated {chart_success}/{len(charts)} charts")

# Step 7: Verify fixes
log_header("STEP 7: Verify Fixes")

log("Checking May 23, 2025 data...")
try:
    # Check renewable penetration
    with open("renewable_penetration_daily_corrected_full.json") as f:
        data = json.load(f)
        may23_data = data.get("2025-05-23", {})
        penetration = may23_data.get("avg_penetration", 0)

        if 85 <= penetration <= 90:
            log_success(f"May 23, 2025 penetration: {penetration}% (CORRECT - was 97.5%)")
        else:
            log_warning(f"May 23, 2025 penetration: {penetration}% (expected 85-90%)")

    # Check comprehensive CSV
    import csv
    with open("caiso_comprehensive_data.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['timestamp'] == '2025-05-23 00:00':
                nat_gas = float(row['natural_gas_mw'])
                large_hydro = float(row['large_hydro_mw'])

                if nat_gas > 5000 and large_hydro > 4000:
                    log_success(f"Natural Gas: {nat_gas} MW, Large Hydro: {large_hydro} MW (CORRECT - was 0.0)")
                else:
                    log_warning(f"Natural Gas: {nat_gas} MW, Large Hydro: {large_hydro} MW (expected ~5141, ~4486)")
                break

except Exception as e:
    log_error(f"Verification failed: {e}")

log_header("DATA FIX COMPLETE")

print("""
Next steps:
1. Review the corrected penetration values (should be ~10% lower than before)
2. Update any analysis or reports based on the old incorrect data
3. Push updated charts to GitHub with: git add *.png && git commit -m "Fix May 2025 data" && git push origin simbooni
""")
