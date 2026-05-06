"""
Test script to verify daily update system is properly configured.

Checks all dependencies and files without running the actual update.
"""
import os
import sys
import subprocess
import importlib.util

def check_command(command, name):
    """Check if a command line tool is available"""
    try:
        result = subprocess.run(
            f"{command} --version",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ {name}: {version}")
            return True
        else:
            print(f"✗ {name}: Not found")
            return False
    except Exception as e:
        print(f"✗ {name}: Error checking - {e}")
        return False

def check_python_package(package, name=None):
    """Check if a Python package is installed"""
    if name is None:
        name = package

    spec = importlib.util.find_spec(package)
    if spec is not None:
        print(f"✓ {name}: Installed")
        return True
    else:
        print(f"✗ {name}: Not installed")
        return False

def check_file(filename, description):
    """Check if a required file exists"""
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"✓ {description}: Found ({size:,} bytes)")
        return True
    else:
        print(f"✗ {description}: Not found")
        return False

def check_directory(dirname, description):
    """Check if a required directory exists"""
    if os.path.isdir(dirname):
        files = len(os.listdir(dirname))
        print(f"✓ {description}: Found ({files} files)")
        return True
    else:
        print(f"✗ {description}: Not found")
        return False

print("="*70)
print("DAILY UPDATE SYSTEM TEST")
print("="*70)
print()

# Check system commands
print("[1] System Commands")
print("-"*70)
checks = []
checks.append(check_command("python", "Python"))
checks.append(check_command("git", "Git"))
print()

# Check Python packages
print("[2] Python Packages")
print("-"*70)
packages = [
    ("selenium", "Selenium WebDriver"),
    ("matplotlib", "Matplotlib"),
    ("numpy", "NumPy"),
    ("pandas", "Pandas (optional)"),
]
for package, name in packages:
    checks.append(check_python_package(package, name))
print()

# Check critical scripts
print("[3] Update Scripts")
print("-"*70)
scripts = [
    ("daily_update.py", "Main update script"),
    ("daily_update.bat", "Windows batch file"),
    ("download_missing_dates.py", "Demand downloader"),
    ("fetch_prices_historical.py", "LMP price fetcher"),
    ("fetch_as_prices.py", "A/S price fetcher"),
    ("process_renewable_penetration_with_demand_csv_v3.py", "Daily processor"),
    ("process_renewable_penetration_hourly_corrected.py", "Hourly processor"),
]
for script, desc in scripts:
    checks.append(check_file(script, desc))
print()

# Check chart scripts
print("[4] Chart Generation Scripts")
print("-"*70)
chart_scripts = [
    "plot_renewable_penetration_improved_v3.py",
    "plot_daily_metrics_4panel.py",
    "plot_natural_gas_generation.py",
]
for script in chart_scripts:
    checks.append(check_file(script, script))
print()

# Check data directories
print("[5] Data Directories")
print("-"*70)
dirs = [
    ("caiso_supply", "Supply/fuelsource data"),
    ("caiso_demand_downloads", "Demand data"),
]
for dirname, desc in dirs:
    checks.append(check_directory(dirname, desc))
print()

# Check current data files
print("[6] Current Data Files")
print("-"*70)
data_files = [
    ("renewable_penetration_daily_corrected_full.json", "Daily penetration"),
    ("renewable_penetration_hourly_corrected.json", "Hourly penetration"),
    ("caiso_prices.json", "LMP prices"),
    ("ancillary_services.json", "A/S prices"),
]
for filename, desc in data_files:
    checks.append(check_file(filename, desc))
print()

# Check git status
print("[7] Git Repository")
print("-"*70)
try:
    result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Git repository configured")
        print(f"  Remote: {result.stdout.split()[1]}")
        checks.append(True)
    else:
        print("✗ Git repository not configured")
        checks.append(False)
except:
    print("✗ Git repository check failed")
    checks.append(False)
print()

# Check last data date
print("[8] Data Status")
print("-"*70)
try:
    import json
    from datetime import datetime, date

    with open("renewable_penetration_daily_corrected_full.json") as f:
        data = json.load(f)

    dates = sorted(data.keys())
    last_date = datetime.strptime(dates[-1], "%Y-%m-%d").date()
    days_ago = (date.today() - last_date).days

    print(f"✓ Last data date: {last_date} ({days_ago} days ago)")

    if days_ago == 1:
        print("  Status: Up to date!")
    elif days_ago <= 7:
        print(f"  Status: {days_ago} days behind (will update automatically)")
    else:
        print(f"  Status: {days_ago} days behind (may take longer to update)")

    checks.append(True)
except Exception as e:
    print(f"✗ Could not read data status: {e}")
    checks.append(False)
print()

# Summary
print("="*70)
print("SUMMARY")
print("="*70)
passed = sum(checks)
total = len(checks)
print(f"{passed}/{total} checks passed")

if passed == total:
    print()
    print("✓ All checks passed! Daily update system is ready.")
    print()
    print("To run daily update:")
    print("  - Windows: Double-click daily_update.bat")
    print("  - Command line: python daily_update.py")
elif passed >= total * 0.8:
    print()
    print("⚠ Most checks passed, but some components are missing.")
    print("  Update system should work, but may have limited functionality.")
    print()
    print("Install missing packages:")
    print("  pip install selenium matplotlib numpy pandas")
else:
    print()
    print("✗ Many checks failed. Please install missing components.")
    print()
    print("Install Python packages:")
    print("  pip install selenium matplotlib numpy pandas")
    print()
    print("Install system tools:")
    print("  - Python 3.7+: https://www.python.org/")
    print("  - Git: https://git-scm.com/")

print("="*70)
