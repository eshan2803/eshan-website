"""Check hourly penetration data for issues in 2020-2021"""
import json

# Load hourly v3 data
with open('renewable_penetration_hourly_v3.json') as f:
    hourly_v3 = json.load(f)

# Load daily corrected_full data
with open('renewable_penetration_daily_corrected_full.json') as f:
    daily_full = json.load(f)

print("="*80)
print("HOURLY PENETRATION ANALYSIS (renewable_penetration_hourly_v3.json)")
print("="*80)

# Check 2020-2021 for >100% values
hours_2020_over_100 = [(k, v) for k, v in hourly_v3.items() if k.startswith('2020') and v > 100]
hours_2021_over_100 = [(k, v) for k, v in hourly_v3.items() if k.startswith('2021') and v > 100]

print(f"\n2020 hours with >100% penetration: {len(hours_2020_over_100)}")
print(f"2021 hours with >100% penetration: {len(hours_2021_over_100)}")

if hours_2020_over_100:
    print(f"\nSample 2020 hours >100%:")
    for k, v in hours_2020_over_100[:10]:
        print(f"  {k}: {v:.1f}%")

# Compare with daily data
print(f"\n{'='*80}")
print("COMPARISON: Hourly vs Daily Data")
print(f"{'='*80}")

# Check specific dates
test_dates = ['2020-01-15', '2020-07-05', '2021-07-05', '2026-03-29']

for date in test_dates:
    if date in daily_full:
        daily_info = daily_full[date]

        # Count hourly >100% for this date
        hourly_over_100 = [v for k, v in hourly_v3.items() if k.startswith(date) and v > 100]
        hourly_count = len(hourly_over_100)

        # Get daily hours_over_100 (in 5-min intervals, needs /12)
        daily_intervals = daily_info['hours_over_100']
        daily_hours = daily_intervals / 12.0

        print(f"\n{date}:")
        print(f"  Daily avg_penetration: {daily_info['avg_penetration']:.2f}%")
        print(f"  Daily max_penetration: {daily_info['max_penetration']:.2f}%")
        print(f"  Daily hours_over_100: {daily_intervals} intervals = {daily_hours:.2f} hours")
        print(f"  Hourly >100% count: {hourly_count} hours")
        if hourly_over_100:
            print(f"  Hourly >100% values: {[f'{v:.1f}' for v in hourly_over_100[:5]]}")

# Check how hourly_v3 was calculated
print(f"\n{'='*80}")
print("SOURCE: How was hourly_v3.json created?")
print(f"{'='*80}")
print("File: process_renewable_penetration_daily_v3.py")
print("Issue: This uses GROSS DEMAND from fuelsource (sum of all sources)")
print("       Does NOT use actual demand from demand CSVs!")
print("       This can lead to incorrect calculations in early years.")
