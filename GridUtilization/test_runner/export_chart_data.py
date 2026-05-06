"""
Export chart data as a compact JSON file for the interactive website charts.
Run this after daily_update.py to refresh the web data.
"""
import csv
import json
import os
from collections import defaultdict
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load sources
with open(os.path.join(script_dir, "renewable_penetration_daily_corrected_full.json")) as f:
    renewable = json.load(f)
with open(os.path.join(script_dir, "natural_gas_daily.json")) as f:
    gas = json.load(f)

# Read LMP from comprehensive CSV (single source of truth)
# CSV has a mix of 5-min and hourly LMP. For 5-min dates, average to hourly.
# Structure: lmp_by_date[date_iso] = {hour: [list of LMP values]}
lmp_by_date = defaultdict(lambda: defaultdict(list))
csv_path = os.path.join(script_dir, "caiso_comprehensive_data.csv")
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        lmp_str = row.get('lmp', '')
        if not lmp_str:
            continue
        ts = row['timestamp']
        space_idx = ts.index(' ')
        date_part = ts[:space_idx]
        time_part = ts[space_idx + 1:]
        # Normalize date to YYYY-MM-DD
        if '/' in date_part:
            date_iso = datetime.strptime(date_part, '%m/%d/%Y').strftime('%Y-%m-%d')
        else:
            date_iso = date_part
        hour = int(time_part.split(':')[0])
        lmp_by_date[date_iso][hour].append(float(lmp_str))

# Compute hourly averages and find daily peak
lmp_dates = set(lmp_by_date.keys())

# Build compact arrays
all_dates = sorted(set(renewable.keys()) | set(gas.keys()) | lmp_dates)

dates = []
clean_hours = []    # Panel 1: hours >= 100% clean
gas_mw = []         # Panel 2: avg natural gas MW
clean_pct = []      # Panel 3: avg clean energy %
peak_lmp = []       # Panel 4: daily peak hourly-avg LMP
peak_lmp_hour = []  # Panel 4: hour when peak LMP occurred (0-23)

for d in all_dates:
    r = renewable.get(d)
    g = gas.get(d)

    dates.append(d)
    clean_hours.append(round(r["hours_over_100"] / 12.0, 2) if r else None)
    gas_mw.append(round(g["avg_gas_mw"], 0) if g else None)
    clean_pct.append(round(r["avg_penetration"], 2) if r else None)

    if d in lmp_by_date:
        hourly_avgs = []
        for hour, values in lmp_by_date[d].items():
            avg = sum(values) / len(values)
            hourly_avgs.append((hour, avg))
        if hourly_avgs:
            peak_h, peak_v = max(hourly_avgs, key=lambda x: x[1])
            peak_lmp.append(round(peak_v, 2))
            peak_lmp_hour.append(peak_h)
        else:
            peak_lmp.append(None)
            peak_lmp_hour.append(None)
    else:
        peak_lmp.append(None)
        peak_lmp_hour.append(None)

output = {
    "dates": dates,
    "clean_hours": clean_hours,
    "gas_mw": gas_mw,
    "clean_pct": clean_pct,
    "peak_lmp": peak_lmp,
    "peak_lmp_hour": peak_lmp_hour,
}

out_path = os.path.join(script_dir, "..", "chart_data.json")
with open(out_path, "w") as f:
    json.dump(output, f, separators=(",", ":"))

size_kb = os.path.getsize(out_path) / 1024
print(f"Exported {len(dates)} data points to {out_path} ({size_kb:.0f} KB)")
