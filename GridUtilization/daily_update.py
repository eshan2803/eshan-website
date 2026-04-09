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
    try:
        print(f"{color}[{timestamp}] {message}{Colors.ENDC}")
    except UnicodeEncodeError:
        # Fallback for terminals that don't support Unicode
        safe = message.encode('ascii', 'replace').decode('ascii')
        print(f"{color}[{timestamp}] {safe}{Colors.ENDC}")

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
    """Get list of dates between last_date and yesterday that need to be downloaded

    Also verifies that source files exist for the last_date itself.
    If demand or supply files are missing for last_date, includes it in missing list.
    """
    yesterday = date.today() - timedelta(days=1)
    missing = []

    # First, verify source files exist for the last_date
    demand_file = Path("caiso_demand_downloads") / f"{last_date.strftime('%Y%m%d')}_demand.csv"
    supply_file = Path("caiso_supply") / f"{last_date.strftime('%Y%m%d')}_fuelsource.csv"

    files_missing = []
    if not demand_file.exists():
        files_missing.append("demand CSV")
    if not supply_file.exists():
        files_missing.append("supply CSV")

    if files_missing:
        log_warning(f"Source files missing for {last_date.strftime('%Y-%m-%d')}: {', '.join(files_missing)}")
        log_warning("Will re-download this date to fix missing files")
        missing.append(last_date)

    # Then check for any dates after last_date
    if last_date < yesterday:
        current = last_date + timedelta(days=1)
        while current <= yesterday:
            missing.append(current)
            current += timedelta(days=1)

    if not missing:
        log_success("Data is up to date and all source files verified")

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

    # Check which supply files are missing (check caiso_supply for processed files)
    missing_supply = []
    for d in missing_dates:
        supply_file = f"caiso_supply/{d.strftime('%Y%m%d')}_fuelsource.csv"
        if not os.path.exists(supply_file):
            missing_supply.append(d)

    if not missing_supply:
        log_success("All supply files already exist")
        return True

    log(f"Need to download {len(missing_supply)} supply files")

    # Create temp file with dates
    with open("temp_supply_dates.txt", "w") as f:
        for d in missing_supply:
            f.write(d.strftime("%Y-%m-%d") + "\n")

    # Run download script (allow ~3 minutes per date for Playwright with retries)
    timeout_seconds = max(180, len(missing_supply) * 180)
    success, _ = run_command(
        "python download_caiso_supply_browser.py",
        f"Downloading {len(missing_supply)} supply CSV files",
        timeout=timeout_seconds
    )

    # Clean up temp file
    if os.path.exists("temp_supply_dates.txt"):
        os.remove("temp_supply_dates.txt")

    # Convert raw browser downloads to fuelsource format
    if success:
        log("Converting raw downloads to fuelsource format...")
        success2, _ = run_command(
            "python process_browser_downloads.py",
            "Converting raw CSVs to fuelsource format",
            timeout=300
        )
        if not success2:
            log_error("Failed to convert browser downloads to fuelsource format")
            return False

    return success

def update_lmp_prices():
    """Update LMP prices for new dates (both hourly and 5-min)"""
    log_header("STEP 3: Updating LMP Prices")

    # Hourly prices (caiso_prices.json) - legacy, used by pre-2023 data
    success1, _ = run_command(
        "python fetch_prices_historical.py",
        "Fetching hourly LMP prices",
        timeout=300
    )

    # 5-min load-weighted prices (caiso_prices_5min.json) - primary source
    success2, _ = run_command(
        "python fetch_prices_5min.py --recent",
        "Fetching 5-min load-weighted LMP prices",
        timeout=300
    )

    return success1 and success2

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

    # Recalculate hourly penetration first (faster to detect issues)
    log("Processing hourly penetration data...")
    success1, _ = run_command(
        "python process_renewable_penetration_hourly_corrected.py",
        "Hourly penetration (5-min aggregated, validated demand)",
        timeout=600
    )

    # Recalculate daily penetration
    log("Processing daily penetration data...")
    success2, _ = run_command(
        "python process_renewable_penetration_with_demand_csv_v2.py",
        "Daily penetration (energy-weighted, validated demand)",
        timeout=600
    )

    if success1 and success2:
        log_success("Penetration calculations complete")
        log("Note: Using validated demand files (cell A1 date = filename)")
    else:
        log_error("Penetration calculation failed")

    return success1 and success2

def update_supporting_data():
    """Update all derived JSON data files from fuelsource CSVs"""
    log_header("STEP 6: Updating Supporting Data")

    scripts = [
        ("process_caiso_battery.py", "Battery peak/charging & solar generation JSONs"),
        ("create_natural_gas_daily.py", "Natural gas daily JSON"),
        ("process_daily_energy.py", "Daily energy breakdown JSON"),
        ("process_daily_energy_with_import_breakdown.py", "Energy breakdown with import classification JSON"),
    ]

    all_success = True
    for script, description in scripts:
        if os.path.exists(script):
            log(f"Processing {description.lower()}...")
            success, _ = run_command(
                f"python {script}",
                description,
                timeout=300
            )
            if not success:
                all_success = False
                log_warning(f"{description} failed - continuing anyway")
        else:
            log_warning(f"Skipping {description} (script {script} not found)")

    return all_success

def regenerate_charts():
    """Regenerate all charts for the website"""
    log_header("STEP 7: Regenerating Charts")

    # Essential charts (must succeed)
    essential_charts = [
        ("plot_renewable_penetration_improved_v3.py", "Renewable penetration chart"),
        ("plot_daily_metrics_4panel.py", "4-panel daily metrics dashboard"),
    ]

    # All other charts (don't fail the pipeline if one breaks)
    other_charts = [
        ("plot_natural_gas_generation.py", "Natural gas generation chart"),
        ("plot_energy_breakdown.py", "Energy breakdown chart"),
        ("plot_energy_breakdown_v2.py", "Energy breakdown V2 chart"),
        ("plot_lmp_vs_battery_by_year.py", "LMP vs battery by year chart"),
        ("plot_negative_prices.py", "Negative price analysis chart"),
        ("plot_negative_prices_with_solar.py", "Negative prices with solar chart"),
        ("plot_battery_gw_vs_lmp.py", "Battery GW vs LMP chart"),
        ("plot_battery_vs_as.py", "Battery vs ancillary services charts"),
        ("export_chart_data.py", "Interactive website chart data (chart_data.json)"),
        ("export_daily_breakdown.py", "Daily breakdown chart data (daily_breakdown.json)"),
    ]

    # Run essential charts
    essential_success = True
    for script, description in essential_charts:
        if os.path.exists(script):
            success, _ = run_command(
                f"python {script}",
                description,
                timeout=120
            )
            if not success:
                essential_success = False
                log_error(f"CRITICAL: Essential chart failed: {description}")
        else:
            log_error(f"CRITICAL: Essential chart missing: {script}")
            essential_success = False

    # Run other charts
    log("\nGenerating additional charts...")
    for script, description in other_charts:
        if os.path.exists(script):
            success, _ = run_command(
                f"python {script}",
                description,
                timeout=120
            )
            if not success:
                log_warning(f"Chart failed: {description} (continuing anyway)")
        else:
            log_warning(f"Chart script not found: {script}")

    return essential_success

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

    # Add files (charts, HTML, and interactive chart data for website)
    log("Staging updated files...")
    files_to_add = [
        "*.png",              # All chart images
        "*.html",             # Any updated HTML files
        "../chart_data.json",       # Interactive website chart data (in repo root)
        "../daily_breakdown.json",  # Daily supply/demand breakdown (in repo root)
    ]

    for file_pattern in files_to_add:
        subprocess.run(f"git add {file_pattern}", shell=True, capture_output=True)

    log("Note: Python scripts, JSON, and CSV files are NOT pushed (local only)")
    log("Only PNG charts and HTML files are pushed to website")

    # Create commit message
    today = date.today()
    commit_msg = f"Auto-update charts for {today.strftime('%a %m/%d/%Y')}"

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

    # Push to simbooni branch (website branch)
    log("Pushing to GitHub (simbooni)...")
    success2, _ = run_command(
        "git push origin simbooni",
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
        if missing_dates == [last_date]:
            log_warning("Source files incomplete for last date - will re-download")
        else:
            log_warning(f"Found {len(missing_dates)} missing/incomplete dates:")
            for d in missing_dates[:5]:
                log(f"  - {d.strftime('%Y-%m-%d')}")
            if len(missing_dates) > 5:
                log(f"  ... and {len(missing_dates) - 5} more")
    else:
        log_success("Source files are up to date - skipping downloads")

    # Execute update steps
    steps_success = []

    # Download data (only if there are missing dates)
    if missing_dates:
        steps_success.append(download_missing_demand(missing_dates))
        steps_success.append(download_missing_supply(missing_dates))
    else:
        log("Skipping download steps (no missing dates)")

    # Always try to fetch prices (they may have become available since last run)
    steps_success.append(update_lmp_prices())
    steps_success.append(update_as_prices())

    # Always process data (picks up any new prices or reprocesses if needed)
    steps_success.append(recalculate_penetration())
    steps_success.append(update_supporting_data())

    # Update comprehensive CSV BEFORE charts (charts read from it)
    if "--skip-csv" in sys.argv:
        log_warning("Skipping comprehensive CSV update (--skip-csv flag)")
        steps_success.append(True)
    else:
        # Use full regeneration if --full-csv flag is set
        use_incremental = "--full-csv" not in sys.argv
        steps_success.append(update_comprehensive_csv(use_incremental=use_incremental))

    # Generate outputs (after CSV is updated so exports use latest data)
    steps_success.append(regenerate_charts())

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
