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
import csv
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo
import time

CAISO_TZ = ZoneInfo("America/Los_Angeles")

def caiso_now():
    """Return current time in California, matching CAISO data availability."""
    return datetime.now(CAISO_TZ)

def caiso_today():
    """Return current California date, not the GitHub runner's UTC date."""
    return caiso_now().date()

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
    timestamp = caiso_now().strftime("%H:%M:%S")
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
    return caiso_today() - timedelta(days=2)

def supply_file_is_complete(supply_file):
    """Return True only when a fuelsource CSV has a complete 5-minute day."""
    try:
        rows = []
        with open(supply_file, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line and line[0].isdigit():
                    rows.append(line)

        if len(rows) < 288:
            return False

        last_time = rows[-1].split(",", 1)[0].strip()
        return last_time == "23:55"
    except Exception as e:
        log_warning(f"Could not validate supply CSV {supply_file}: {e}")
        return False

def demand_file_is_complete(demand_file):
    """Return True only when a demand CSV has a full 5-minute day."""
    if not demand_file.exists():
        return False

    try:
        with open(demand_file, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if len(rows) < 4:
            return False

        header = [cell.strip() for cell in rows[0][1:]]
        demand_values = [cell.strip() for cell in rows[3][1:]]

        if "23:55" not in header:
            return False

        end_idx = header.index("23:55")
        if len(demand_values) <= end_idx or not demand_values[end_idx]:
            return False

        return sum(1 for value in demand_values[:end_idx + 1] if value) >= 288
    except Exception as e:
        log_warning(f"Could not validate demand CSV {demand_file}: {e}")
        return False

def remove_file_if_exists(path, reason):
    """Remove a stale generated/downloaded file before re-downloading it."""
    try:
        if path.exists():
            path.unlink()
            log_warning(f"Removed {path} ({reason})")
    except Exception as e:
        log_error(f"Could not remove {path}: {e}")

def get_missing_dates(last_date):
    """Get list of dates between last_date and yesterday that need to be downloaded

    Also verifies that source files exist for the last_date itself.
    If demand or supply files are missing for last_date, includes it in missing list.
    """
    yesterday = caiso_today() - timedelta(days=1)
    missing = []

    # First, verify recent source files exist and are complete. Browser downloads
    # can occasionally leave a partial fuelsource CSV behind; existence alone is
    # not enough for the homepage charts.
    verify_start = max(last_date - timedelta(days=2), caiso_today() - timedelta(days=7))
    current = verify_start
    while current <= yesterday:
        if source_files_need_download(current):
            missing.append(current)
        current += timedelta(days=1)

    # Then check for any dates after last_date
    if last_date < yesterday:
        current = last_date + timedelta(days=1)
        while current <= yesterday:
            if current not in missing:
                missing.append(current)
            current += timedelta(days=1)

    if not missing:
        log_success("Data is up to date and all source files verified")

    return missing

def source_files_need_download(data_date):
    """Check whether a source date should be downloaded or refreshed."""
    demand_file = Path("caiso_demand_downloads") / f"{data_date.strftime('%Y%m%d')}_demand.csv"
    supply_file = Path("caiso_supply") / f"{data_date.strftime('%Y%m%d')}_fuelsource.csv"

    issues = []
    if not demand_file.exists():
        issues.append("missing demand CSV")
    elif not demand_file_is_complete(demand_file):
        issues.append("incomplete demand CSV")

    if not supply_file.exists():
        issues.append("missing supply CSV")
    elif not supply_file_is_complete(supply_file):
        issues.append("incomplete supply CSV")

    if issues:
        log_warning(f"Source files need refresh for {data_date.strftime('%Y-%m-%d')}: {', '.join(issues)}")
        return True

    return False

def download_missing_demand(missing_dates):
    """Download demand CSV files for missing dates"""
    if not missing_dates:
        return True

    log_header(f"STEP 1: Downloading Demand Data ({len(missing_dates)} days)")

    # Check which demand files are missing or partial.
    demand_dir = Path("caiso_demand_downloads")
    actually_missing = []

    for d in missing_dates:
        demand_file = demand_dir / f"{d.strftime('%Y%m%d')}_demand.csv"
        if not demand_file.exists() or not demand_file_is_complete(demand_file):
            actually_missing.append(d)
            remove_file_if_exists(demand_file, "missing/incomplete demand refresh")

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

    # Check which supply files are missing or partial (check caiso_supply for processed files)
    missing_supply = []
    for d in missing_dates:
        supply_file = Path("caiso_supply") / f"{d.strftime('%Y%m%d')}_fuelsource.csv"
        if not supply_file.exists() or not supply_file_is_complete(supply_file):
            missing_supply.append(d)

    if not missing_supply:
        log_success("All supply files already exist")
        return True

    log(f"Need to download {len(missing_supply)} supply files")

    raw_dir = Path("caiso_downloads")
    for d in missing_supply:
        date_prefix = d.strftime("%Y%m%d")
        remove_file_if_exists(raw_dir / f"{date_prefix}_supply_raw.csv", "refreshing incomplete supply day")
        remove_file_if_exists(raw_dir / f"{date_prefix}_renewables_raw.csv", "refreshing incomplete supply day")

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
    # Fetches ~2-3 months of data from 3 DLAPs with rate-limit delays
    success2, _ = run_command(
        "python fetch_prices_5min.py --recent",
        "Fetching 5-min load-weighted LMP prices",
        timeout=900
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
        ("process_daily_energy_with_import_breakdown.py", "Energy breakdown with import classification JSON", 600),
    ]

    all_success = True
    for entry in scripts:
        script, description = entry[0], entry[1]
        timeout = entry[2] if len(entry) > 2 else 300
        if os.path.exists(script):
            log(f"Processing {description.lower()}...")
            success, _ = run_command(
                f"python {script}",
                description,
                timeout=timeout
            )
            if not success:
                all_success = False
                log_warning(f"{description} failed - continuing anyway")
        else:
            log_warning(f"Skipping {description} (script {script} not found)")

    return all_success

def regenerate_charts():
    """Regenerate all charts for the website"""
    log_header("STEP 8: Regenerating Charts")

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
        ("plot_5min_lmp_distribution_batt.py", "5-min LMP distribution charts (negative and all)"),
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
                timeout=300
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
                timeout=300
            )
            if not success:
                log_warning(f"Chart failed: {description} (continuing anyway)")
        else:
            log_warning(f"Chart script not found: {script}")

    return essential_success

def latest_complete_source_date():
    """Find the newest date with complete demand and supply source files."""
    supply_dir = Path("caiso_supply")
    demand_dir = Path("caiso_demand_downloads")
    complete_dates = []

    for supply_file in supply_dir.glob("*_fuelsource.csv"):
        date_str = supply_file.name.split("_", 1)[0]
        try:
            data_date = datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            continue

        demand_file = demand_dir / f"{date_str}_demand.csv"
        if supply_file_is_complete(supply_file) and demand_file_is_complete(demand_file):
            complete_dates.append(data_date)

    return max(complete_dates) if complete_dates else None

def validate_homepage_data_freshness():
    """Fail the update if homepage JSON outputs do not reflect fresh complete data."""
    log_header("STEP 9: Validating Homepage Data Freshness")

    latest_source_date = latest_complete_source_date()
    if latest_source_date is None:
        log_error("No complete source date found for homepage validation")
        return False

    expected_min_date = caiso_today() - timedelta(days=1)
    if latest_source_date < expected_min_date:
        log_error(
            f"Latest complete source date is {latest_source_date}, expected at least {expected_min_date}"
        )
        return False

    breakdown_file = Path("../daily_breakdown.json")
    if not breakdown_file.exists():
        log_error("daily_breakdown.json is missing")
        return False

    try:
        with open(breakdown_file, encoding="utf-8") as f:
            breakdown = json.load(f)
        breakdown_date = datetime.strptime(breakdown["date"], "%Y-%m-%d").date()
    except Exception as e:
        log_error(f"Could not validate daily_breakdown.json: {e}")
        return False

    if breakdown_date != latest_source_date:
        log_error(
            f"daily_breakdown.json is {breakdown_date}, but latest complete source date is {latest_source_date}"
        )
        return False

    chart_file = Path("../chart_data.json")
    if not chart_file.exists():
        log_error("chart_data.json is missing")
        return False

    try:
        with open(chart_file, encoding="utf-8") as f:
            chart_data = json.load(f)
    except Exception as e:
        log_error(f"Could not read chart_data.json: {e}")
        return False

    latest_chart_date = None
    if isinstance(chart_data, dict):
        date_keys = [key for key in chart_data.keys() if isinstance(key, str) and len(key) == 10]
        if date_keys:
            latest_chart_date = max(datetime.strptime(key, "%Y-%m-%d").date() for key in date_keys)
        elif "dates" in chart_data and isinstance(chart_data["dates"], list) and chart_data["dates"]:
            latest_chart_date = max(datetime.strptime(key, "%Y-%m-%d").date() for key in chart_data["dates"])

    if latest_chart_date and latest_chart_date < latest_source_date:
        log_error(f"chart_data.json ends at {latest_chart_date}, expected {latest_source_date}")
        return False

    log_success(f"Homepage JSON is fresh through {latest_source_date}")
    return True

def update_comprehensive_csv(use_incremental=True):
    """Update the comprehensive CSV file"""
    log_header("STEP 7: Updating Comprehensive CSV")

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
    log_header("STEP 10: Pushing to GitHub")

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
    today = caiso_today()
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

    # Pull latest to avoid rejected pushes, then push to simbooni branch
    log("Pulling latest and Pushing to GitHub (simbooni)...")
    success2, _ = run_command(
        "git pull --rebase --autostash origin simbooni && git push origin simbooni",
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

    log(f"Starting update process at {caiso_now().strftime('%Y-%m-%d %H:%M:%S %Z')}")

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
    steps_success.append(validate_homepage_data_freshness())

    # Push to GitHub unless the caller owns commit/push orchestration.
    # GitHub Actions uses --no-git so the workflow can commit all generated
    # artifacts in one place after it refreshes the archive.
    if "--no-git" in sys.argv:
        log("Skipping internal git commit/push (--no-git flag)")
        steps_success.append(True)
    else:
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
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass

    sys.exit(exit_code)
