"""
CAISO Daily Data Update Script

Automatically updates all CAISO data, recalculates metrics, regenerates charts,
and pushes to GitHub. Handles missing dates if script wasn't run for multiple days.

Run this daily to keep website updated with latest data.
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta, date
from pathlib import Path
import time

# Color codes for Windows console
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(message, color=Colors.OKBLUE):
    """Print colored log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.ENDC}")

def log_header(message):
    """Print section header"""
    print(f"\n{'='*70}")
    log(message, Colors.HEADER + Colors.BOLD)
    print('='*70)

def log_success(message):
    """Print success message"""
    log(f"✓ {message}", Colors.OKGREEN)

def log_error(message):
    """Print error message"""
    log(f"✗ {message}", Colors.FAIL)

def log_warning(message):
    """Print warning message"""
    log(f"⚠ {message}", Colors.WARNING)

def run_command(command, description, timeout=600):
    """Run a shell command and capture output"""
    log(f"Running: {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            log_success(f"{description} completed")
            return True, result.stdout
        else:
            log_error(f"{description} failed")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        log_error(f"{description} timed out")
        return False, "Timeout"
    except Exception as e:
        log_error(f"{description} error: {str(e)}")
        return False, str(e)

def get_last_data_date():
    """Find the most recent date in our data files"""
    try:
        # Check renewable penetration daily data
        if os.path.exists("renewable_penetration_daily_corrected_full.json"):
            with open("renewable_penetration_daily_corrected_full.json") as f:
                data = json.load(f)
                dates = sorted(data.keys())
                if dates:
                    last_date = datetime.strptime(dates[-1], "%Y-%m-%d").date()
                    return last_date
    except Exception as e:
        log_warning(f"Could not read existing data: {e}")

    # Default to yesterday if no data found
    return date.today() - timedelta(days=2)

def get_missing_dates(last_date):
    """Get list of dates between last_date and yesterday that need to be downloaded"""
    yesterday = date.today() - timedelta(days=1)

    if last_date >= yesterday:
        log("Data is up to date")
        return []

    missing = []
    current = last_date + timedelta(days=1)
    while current <= yesterday:
        missing.append(current)
        current += timedelta(days=1)

    return missing

def download_missing_demand(missing_dates):
    """Download demand CSV files for missing dates"""
    if not missing_dates:
        return True

    log_header(f"STEP 1: Downloading Demand Data ({len(missing_dates)} days)")

    # Check which demand files are actually missing
    demand_dir = Path("caiso_demand_downloads")
    actually_missing = []

    for d in missing_dates:
        demand_file = demand_dir / f"{d.strftime('%Y%m%d')}_demand.csv"
        if not demand_file.exists():
            actually_missing.append(d)

    if not actually_missing:
        log_success("All demand files already exist")
        return True

    log(f"Need to download {len(actually_missing)} demand CSV files")

    # Create temp file with dates
    with open("temp_missing_dates.txt", "w") as f:
        for d in actually_missing:
            f.write(d.strftime("%Y-%m-%d") + "\n")

    # Run download script (allow ~60 seconds per date for Selenium)
    timeout_seconds = max(60, len(actually_missing) * 60)
    success, _ = run_command(
        "python download_missing_dates.py",
        f"Downloading {len(actually_missing)} demand CSV files",
        timeout=timeout_seconds
    )

    # Clean up temp file
    if os.path.exists("temp_missing_dates.txt"):
        os.remove("temp_missing_dates.txt")

    return success

def download_missing_supply(missing_dates):
    """Download supply/fuelsource CSV files for missing dates"""
    if not missing_dates:
        return True

    log_header(f"STEP 2: Downloading Supply Data ({len(missing_dates)} days)")

    # Check which supply files are missing
    missing_supply = []
    for d in missing_dates:
        supply_file = f"caiso_supply/{d.strftime('%Y%m%d')}_fuelsource.csv"
        if not os.path.exists(supply_file):
            missing_supply.append(d)

    if not missing_supply:
        log_success("All supply files already exist")
        return True

    log(f"Need to download {len(missing_supply)} supply files")

    # For now, use the CAISO downloader (you may need to adapt this)
    # This is a placeholder - you'll need to implement supply download
    log_warning("Supply download not yet automated - manual download may be needed")
    log_warning(f"Missing dates: {[d.strftime('%Y-%m-%d') for d in missing_supply[:5]]}")

    return True  # Don't fail the whole process

def update_lmp_prices():
    """Update LMP prices for new dates"""
    log_header("STEP 3: Updating LMP Prices")

    success, _ = run_command(
        "python fetch_prices_historical.py",
        "Fetching latest LMP prices",
        timeout=300
    )

    return success

def update_as_prices():
    """Update Ancillary Services prices for new dates"""
    log_header("STEP 4: Updating Ancillary Services Prices")

    success, _ = run_command(
        "python fetch_as_prices.py",
        "Fetching latest A/S prices",
        timeout=300
    )

    return success

def recalculate_penetration():
    """Recalculate renewable penetration with corrected methodology"""
    log_header("STEP 5: Recalculating Renewable Penetration")

    # Recalculate daily penetration
    log("Processing daily penetration data...")
    success1, _ = run_command(
        "python process_renewable_penetration_with_demand_csv_v3.py",
        "Daily penetration (energy-weighted)",
        timeout=600
    )

    # Recalculate hourly penetration
    log("Processing hourly penetration data...")
    success2, _ = run_command(
        "python process_renewable_penetration_hourly_corrected.py",
        "Hourly penetration (5-min aggregated)",
        timeout=600
    )

    # Process 2026 Q1 if needed
    log("Processing 2026 Q1 data...")
    success3, _ = run_command(
        "python process_2026_hourly_corrected.py",
        "2026 Q1 hourly data",
        timeout=300
    )

    # Merge datasets
    if success1 and success2:
        try:
            log("Merging 2026 Q1 data with main dataset...")
            with open('renewable_penetration_daily_corrected_full.json') as f:
                data_main = json.load(f)

            if os.path.exists('renewable_penetration_daily_v5.json'):
                with open('renewable_penetration_daily_v5.json') as f:
                    data_2026 = json.load(f)

                merged = {**data_main, **data_2026}
                sorted_data = dict(sorted(merged.items()))

                with open('renewable_penetration_daily_corrected_full.json', 'w') as f:
                    json.dump(sorted_data, f, indent=2)

                log_success("Merged 2026 Q1 data")

            # Merge hourly
            with open('renewable_penetration_hourly_corrected.json') as f:
                hourly_main = json.load(f)

            if os.path.exists('renewable_penetration_hourly_2026q1_corrected.json'):
                with open('renewable_penetration_hourly_2026q1_corrected.json') as f:
                    hourly_2026 = json.load(f)

                merged_hourly = {**hourly_main, **hourly_2026}
                sorted_hourly = dict(sorted(merged_hourly.items()))

                with open('renewable_penetration_hourly_corrected.json', 'w') as f:
                    json.dump(sorted_hourly, f, indent=2)

                log_success("Merged hourly 2026 Q1 data")

        except Exception as e:
            log_warning(f"Merge error: {e}")

    return success1 and success2

def update_supporting_data():
    """Update supporting data files (natural gas, energy breakdown)"""
    log_header("STEP 6: Updating Supporting Data")

    # Natural gas data
    log("Processing natural gas data...")
    success1, _ = run_command(
        "python process_natural_gas_data.py",
        "Natural gas generation statistics",
        timeout=300
    )

    # Daily energy breakdown
    log("Processing daily energy breakdown...")
    success2, _ = run_command(
        "python process_daily_energy.py",
        "Daily energy breakdown",
        timeout=300
    )

    return success1 and success2

def regenerate_charts():
    """Regenerate all charts for the website"""
    log_header("STEP 7: Regenerating Charts")

    charts = [
        ("plot_renewable_penetration_improved_v3.py", "Main renewable penetration chart"),
        ("plot_daily_metrics_4panel.py", "4-panel daily metrics dashboard"),
        ("plot_natural_gas_generation.py", "Natural gas generation chart"),
        ("plot_energy_breakdown.py", "Energy breakdown chart"),
        ("plot_energy_breakdown_v2.py", "Energy breakdown V2 chart"),
        ("plot_capacity_factor_seasonal_with_avg.py", "Capacity factor seasonal chart"),
        ("plot_cf_lmp.py", "Capacity factor vs LMP chart"),
        ("plot_ramp_rate_seasonal.py", "Ramp rate seasonal chart"),
        ("plot_ramp_lmp.py", "Ramp rate vs LMP chart"),
        ("plot_battery_gw_vs_lmp.py", "Battery capacity vs LMP chart"),
        ("plot_lmp_vs_battery_by_year.py", "LMP vs battery by year chart"),
    ]

    all_success = True
    for script, description in charts:
        if os.path.exists(script):
            success, _ = run_command(
                f"python {script}",
                description,
                timeout=120
            )
            if not success:
                all_success = False
                log_warning(f"Chart generation failed: {description}")
        else:
            log_warning(f"Chart script not found: {script}")

    return all_success

def update_comprehensive_csv(use_incremental=True):
    """Update the comprehensive CSV file"""
    log_header("STEP 8: Updating Comprehensive CSV")

    if use_incremental and os.path.exists("caiso_comprehensive_data.csv"):
        # Fast incremental update - only append new dates
        log("Using incremental update (appending new dates only)")
        success, _ = run_command(
            "python append_to_comprehensive_csv.py",
            "Incremental CSV update (fast)",
            timeout=300
        )
    else:
        # Full regeneration
        log("Using full regeneration (processing all dates)")
        success, _ = run_command(
            "python create_comprehensive_csv.py",
            "Full CSV regeneration (may take several minutes)",
            timeout=1800
        )

    return success

def git_commit_and_push():
    """Commit changes and push to GitHub"""
    log_header("STEP 9: Pushing to GitHub")

    # Check if there are changes
    result = subprocess.run("git status --short", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        log("No changes to commit")
        return True

    # Add files
    log("Staging updated files...")
    files_to_add = [
        "renewable_penetration_improved_v3.png",
        "daily_metrics_4panel.png",
        "renewable_penetration_daily_corrected_full.json",
        "renewable_penetration_hourly_corrected.json",
        "caiso_prices.json",
        "ancillary_services.json",
        "natural_gas_daily.json",
        "daily_energy_breakdown.json",
        "*.png",  # All chart images
    ]

    for file_pattern in files_to_add:
        subprocess.run(f"git add {file_pattern}", shell=True, capture_output=True)

    # Create commit message
    today = date.today()
    commit_msg = f"Auto-update CAISO data for {today.strftime('%a %m/%d/%Y')}"

    # Commit
    log("Creating commit...")
    success1, _ = run_command(
        f'git commit -m "{commit_msg}"',
        "Git commit",
        timeout=30
    )

    if not success1:
        log_warning("No changes to commit or commit failed")
        return True  # Don't fail if nothing to commit

    # Push
    log("Pushing to GitHub...")
    success2, _ = run_command(
        "git push origin main",
        "Git push",
        timeout=60
    )

    return success2

def main():
    """Main execution function"""
    start_time = time.time()

    print("\n" + "="*70)
    print(f"{Colors.HEADER}{Colors.BOLD}CAISO DAILY DATA UPDATE{Colors.ENDC}")
    print(f"{Colors.HEADER}Automated update script for eshan-website{Colors.ENDC}")
    print("="*70 + "\n")

    log(f"Starting update process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 0: Check for missing dates
    log_header("STEP 0: Checking for Missing Dates")
    last_date = get_last_data_date()
    log(f"Last data date: {last_date.strftime('%Y-%m-%d')}")

    missing_dates = get_missing_dates(last_date)
    if missing_dates:
        log_warning(f"Found {len(missing_dates)} missing dates:")
        for d in missing_dates[:5]:
            log(f"  - {d.strftime('%Y-%m-%d')}")
        if len(missing_dates) > 5:
            log(f"  ... and {len(missing_dates) - 5} more")
    else:
        log_success("No missing dates - data is up to date!")

        # Ask if user wants to continue anyway
        if len(sys.argv) > 1 and sys.argv[1] == "--force":
            log("Force mode enabled, continuing anyway")
        else:
            log("Run with --force flag to update anyway")
            return 0

    # Execute update steps
    steps_success = []

    # Download data
    steps_success.append(download_missing_demand(missing_dates))
    steps_success.append(download_missing_supply(missing_dates))
    steps_success.append(update_lmp_prices())
    steps_success.append(update_as_prices())

    # Process data
    steps_success.append(recalculate_penetration())
    steps_success.append(update_supporting_data())

    # Generate outputs
    steps_success.append(regenerate_charts())

    # Update comprehensive CSV (always, unless --skip-csv flag)
    if "--skip-csv" in sys.argv:
        log_warning("Skipping comprehensive CSV update (--skip-csv flag)")
        steps_success.append(True)
    else:
        # Use full regeneration if --full-csv flag is set
        use_incremental = "--full-csv" not in sys.argv
        steps_success.append(update_comprehensive_csv(use_incremental=use_incremental))

    # Push to GitHub
    steps_success.append(git_commit_and_push())

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "="*70)
    log_header("UPDATE SUMMARY")

    total_steps = len(steps_success)
    successful_steps = sum(steps_success)

    if successful_steps == total_steps:
        log_success(f"All {total_steps} steps completed successfully!")
    else:
        failed_steps = total_steps - successful_steps
        log_warning(f"{successful_steps}/{total_steps} steps completed ({failed_steps} failed)")

    log(f"Total time: {elapsed/60:.1f} minutes")

    if missing_dates:
        log(f"Updated data through: {missing_dates[-1].strftime('%Y-%m-%d')}")

    print("="*70 + "\n")

    return 0 if successful_steps == total_steps else 1

if __name__ == "__main__":
    exit_code = main()

    # Keep window open if run by double-clicking
    if len(sys.argv) == 1:
        input("\nPress Enter to close...")

    sys.exit(exit_code)
