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

# Read LMP from price JSONs. The daily homepage chart must avoid hourly fallback
# for recent 5-minute days, but this historical daily peak panel can use hourly
# prices when a full 5-minute cache is not retained in the repo archive.
# Structure: lmp_by_date[date_iso] = {hour: [list of LMP values]}
lmp_by_date = defaultdict(lambda: defaultdict(list))

prices_5min_path = os.path.join(script_dir, "caiso_prices_5min.json")
if os.path.exists(prices_5min_path):
    with open(prices_5min_path) as f:
        prices_5min = json.load(f)
    for date_iso, day_data in prices_5min.items():
        if not isinstance(day_data, dict):
            continue
        for time_part, values in day_data.items():
            if not isinstance(values, dict) or values.get("LMP") is None:
                continue
            hour = int(time_part.split(":")[0])
            lmp_by_date[date_iso][hour].append(float(values["LMP"]))

prices_hourly_path = os.path.join(script_dir, "caiso_prices.json")
if os.path.exists(prices_hourly_path):
    with open(prices_hourly_path) as f:
        prices_hourly = json.load(f)
    for date_iso, day_data in prices_hourly.items():
        if date_iso in lmp_by_date or not isinstance(day_data, dict):
            continue
        for hour_str, values in day_data.items():
            if not isinstance(values, dict) or values.get("LMP") is None:
                continue
            hour = int(hour_str) - 1
            lmp_by_date[date_iso][hour].append(float(values["LMP"]))

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
