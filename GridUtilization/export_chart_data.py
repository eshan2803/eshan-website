"""
Export chart data as a compact JSON file for the interactive website charts.
Run this after daily_update.py to refresh the web data.

Updated to use energy-based penetration: Total Clean MWh / Total Load MWh × 100
(Previously used average of hourly percentages)
"""
import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load sources
with open(os.path.join(script_dir, "renewable_penetration_daily_energy_based.json")) as f:
    renewable = json.load(f)
with open(os.path.join(script_dir, "natural_gas_daily.json")) as f:
    gas = json.load(f)
with open(os.path.join(script_dir, "caiso_prices.json")) as f:
    prices = json.load(f)

# Build compact arrays
all_dates = sorted(set(renewable.keys()) | set(gas.keys()) | set(prices.keys()))

dates = []
clean_hours = []    # Panel 1: hours >= 100% clean
gas_mw = []         # Panel 2: avg natural gas MW
clean_pct = []      # Panel 3: avg clean energy %
peak_lmp = []       # Panel 4: daily peak LMP
peak_lmp_hour = []  # Panel 4: hour when peak LMP occurred (1-24)

for d in all_dates:
    r = renewable.get(d)
    g = gas.get(d)
    p = prices.get(d)

    dates.append(d)
    clean_hours.append(round(r["hours_over_100"] / 12.0, 2) if r else None)
    gas_mw.append(round(g["avg_gas_mw"], 0) if g else None)
    clean_pct.append(round(r["avg_penetration"], 2) if r else None)

    if p:
        lmp_entries = [(h, p[h]["LMP"]) for h in p.keys()]
        if lmp_entries:
            peak_h, peak_v = max(lmp_entries, key=lambda x: x[1])
            peak_lmp.append(round(peak_v, 2))
            peak_lmp_hour.append(int(peak_h))
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
