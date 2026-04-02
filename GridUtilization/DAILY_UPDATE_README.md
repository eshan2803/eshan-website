# Daily Update Process

## Overview

The daily update system automatically:
1. ✅ Downloads latest CAISO data (demand, supply, LMP, A/S prices)
2. ✅ Detects and backfills missing dates
3. ✅ Recalculates renewable penetration with corrected methodology
4. ✅ Regenerates all charts
5. ✅ Commits and pushes to GitHub

## One-Click Update

### Windows Users

**Simply double-click**: `daily_update.bat`

The batch file will:
- Check for Python and Git installations
- Run the update script
- Show progress in a command window
- Keep window open to review results

### Advanced Options

```batch
# Force update even if data is current
daily_update.bat --force

# Skip comprehensive CSV update (faster, but CSV won't be updated)
daily_update.bat --skip-csv

# Both options
daily_update.bat --force --skip-csv
```

**Note**: By default, the comprehensive CSV is ALWAYS updated to keep all data in sync.

## What Happens During Update

### Step 0: Check for Missing Dates
- Reads `renewable_penetration_daily_corrected_full.json`
- Identifies last data date
- Finds all missing dates between last date and yesterday
- **Example**: If last date is April 8 and today is April 12, it will update April 9, 10, and 11

### Step 1: Download Demand Data
- Downloads CSV files from CAISO Today's Outlook - Demand Trend
- Saves to `caiso_demand_downloads/YYYYMMDD_demand.csv`
- Uses Selenium WebDriver (headless Chrome)
- **Time**: ~4 seconds per day

### Step 2: Download Supply Data
- Checks for missing fuelsource CSV files in `caiso_supply/`
- **Note**: Currently requires manual download from CAISO
- Script will warn if supply files are missing

### Step 3: Update LMP Prices
- Fetches latest prices from CAISO OASIS API
- Updates `caiso_prices.json` with LMP components (MCC, MEC, GHG, Loss)
- **Time**: ~1-2 minutes

### Step 4: Update A/S Prices
- Fetches ancillary services prices from OASIS API
- Updates `ancillary_services.json` with NR, RD, RMD, RMU, RU, SR
- **Time**: ~1-2 minutes

### Step 5: Recalculate Penetration
- Processes daily data with energy-weighted methodology
- Formula: `(Total Clean MWh / Total Load MWh) × 100`
- Load = CAISO Demand + Battery Charging ✓
- Merges with 2026 Q1 data
- **Time**: ~2-3 minutes

### Step 6: Update Supporting Data
- Natural gas generation statistics
- Daily energy breakdown
- **Time**: ~1 minute

### Step 7: Regenerate Charts
- Main renewable penetration chart (2-panel)
- 4-panel daily metrics dashboard
- Natural gas, energy breakdown, capacity factors
- Battery vs prices, ramp rates, etc.
- **Time**: ~2-3 minutes

### Step 8: Update Comprehensive CSV
- Always runs by default (skip with `--skip-csv`)
- Regenerates 69MB CSV with all data
- **Time**: ~5-10 minutes

### Step 9: Push to GitHub
- Stages updated files (charts, JSON, CSV)
- Creates commit: "Auto-update CAISO data for [date]"
- Pushes to `main` branch
- **Time**: ~10-20 seconds

## Total Time

- **Standard update** (no missing dates): ~10-15 minutes (includes CSV)
- **With backfill** (1-2 missing days): ~15-20 minutes
- **Large backfill** (5+ missing days): ~20-35 minutes
- **Quick mode** (with --skip-csv): ~5-8 minutes (no CSV update)

## Handling Missed Days

The script automatically detects and handles missed days:

### Example: Missed 3 Days

```
Last data: 2026-04-08
Today: 2026-04-12
Missing: April 9, 10, 11

Script will:
1. Download demand for all 3 days
2. Update prices for all 3 days
3. Recalculate metrics for entire period
4. Regenerate all charts
5. Push single commit with all updates
```

### Backfill Limits

- **Demand data**: Available going back to 2020
- **LMP prices**: Available going back to 2020
- **A/S prices**: Available going back to February 2020
- **Supply data**: May need manual download for older dates

## Error Handling

### Common Issues

#### 1. "Python is not installed"
**Solution**: Install Python 3.7+ from https://www.python.org/
- Check "Add Python to PATH" during installation
- Restart terminal after installation

#### 2. "Git is not installed"
**Solution**: Install Git from https://git-scm.com/
- Or use GitHub Desktop

#### 3. "Chrome/ChromeDriver not found"
**Solution**: Script uses Selenium for downloads
```bash
pip install selenium
```
Chrome browser must be installed

#### 4. "OASIS API timeout"
**Solution**: CAISO API may be slow or down
- Script will retry failed requests
- Run again later if persistent

#### 5. "Supply files missing"
**Solution**: Manual download needed
- Go to https://www.caiso.com/todays-outlook/supply
- Download fuelsource CSV for missing dates
- Save to `caiso_supply/YYYYMMDD_fuelsource.csv`

## Manual Run (Python)

If you prefer command line:

```bash
# Change to GridUtilization directory
cd C:\Users\eshan\OneDrive\Desktop\eshan-website\eshan-website-repo\GridUtilization

# Run update
python daily_update.py

# With options
python daily_update.py --force
python daily_update.py --full
python daily_update.py --force --full
```

## Scheduled Task (Windows)

To run automatically every day:

1. Open **Task Scheduler**
2. Create Basic Task
3. Name: "CAISO Daily Update"
4. Trigger: Daily at 8:00 AM
5. Action: Start a program
   - Program: `C:\Users\eshan\OneDrive\Desktop\eshan-website\eshan-website-repo\GridUtilization\daily_update.bat`
6. Finish

## Verification

After update completes, verify:

1. **Console Output**: Should show all steps completed
2. **GitHub**: Check latest commit at https://github.com/eshan2803/eshan-website
3. **Website**: Visit https://eshan2803.github.io/eshan-website/
4. **Charts**: Check dates in chart filenames (should be today)

```bash
# Check last update time
ls -lh renewable_penetration_improved_v3.png

# Check latest data date
python -c "import json; data=json.load(open('renewable_penetration_daily_corrected_full.json')); print(max(data.keys()))"
```

## Dependencies

### Python Packages
```bash
pip install selenium
pip install pandas
pip install matplotlib
pip install numpy
pip install requests
```

### System Requirements
- Python 3.7+
- Git
- Google Chrome (for Selenium downloads)
- ~500MB free disk space
- Internet connection

## Troubleshooting

### Script Won't Run
1. Check Python installation: `python --version`
2. Check current directory: `cd` should show GridUtilization folder
3. Check file exists: `dir daily_update.py`

### Downloads Fail
1. Check internet connection
2. Try running with `--force` flag
3. Check CAISO website is accessible
4. Try manual download for one day to test

### Charts Don't Update
1. Check if matplotlib is installed: `pip install matplotlib`
2. Verify JSON data files exist
3. Run chart scripts individually to see errors

### Git Push Fails
1. Check Git credentials
2. Verify internet connection
3. Check GitHub repository access
4. Try manual push: `git push origin main`

## Log Files

The script outputs to console. To save logs:

```bash
# Windows
python daily_update.py > update_log.txt 2>&1

# Or redirect in batch file
daily_update.bat > update_log.txt 2>&1
```

## Support Files

- `daily_update.py` - Main Python script
- `daily_update.bat` - Windows batch launcher
- `download_missing_dates.py` - Download demand CSVs
- `fetch_prices_historical.py` - Fetch LMP prices
- `fetch_as_prices.py` - Fetch A/S prices
- `process_renewable_penetration_with_demand_csv_v3.py` - Daily calculation
- `process_renewable_penetration_hourly_corrected.py` - Hourly calculation
- `plot_*.py` - Chart generation scripts

## Future Enhancements

- [ ] Email notifications on completion/errors
- [ ] Automatic supply data download
- [ ] Data quality checks before pushing
- [ ] Rolling backup of old data
- [ ] Web dashboard for update status
