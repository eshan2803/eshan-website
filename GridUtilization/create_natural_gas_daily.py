"""
Create natural_gas_daily.json from fuelsource CSVs.
Includes avg_gas_mw and avg_gas_pct (gas as % of gross supply).
Falls back to natural_gas_hourly.json for dates without fuelsource files.
Incremental: loads existing output and only processes new fuelsource files.
"""
import csv
import json
import os
import glob
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(script_dir, "natural_gas_daily.json")

# Load existing output if available (for incremental updates)
output = {}
existing_fuelsource_dates = set()
if os.path.exists(out_path):
    with open(out_path) as f:
        output = json.load(f)
    # Track which dates have fuelsource-quality data (have avg_gas_pct != 0)
    existing_fuelsource_dates = {d for d, v in output.items() if v.get("avg_gas_pct", 0) != 0}

# Fill in hourly-based data for dates without fuelsource files
hourly_path = os.path.join(script_dir, "natural_gas_hourly.json")
if os.path.exists(hourly_path):
    with open(hourly_path) as f:
        hourly = json.load(f)
    daily = defaultdict(lambda: {"total": 0.0, "count": 0})
    for key, val in hourly.items():
        date_str = key.split()[0]
        daily[date_str]["total"] += val["gas_mw"]
        daily[date_str]["count"] += 1
    for d, v in daily.items():
        if d not in output:
            output[d] = {"avg_gas_mw": round(v["total"] / v["count"], 2), "avg_gas_pct": 0}

# Process only new fuelsource CSVs
supply_dir = os.path.join(script_dir, "caiso_supply")
all_files = sorted(glob.glob(os.path.join(supply_dir, "*_fuelsource.csv")))
files_to_process = []
for fpath in all_files:
    fname = os.path.basename(fpath)
    date_str = f"{fname[:4]}-{fname[4:6]}-{fname[6:8]}"
    if date_str not in existing_fuelsource_dates:
        files_to_process.append(fpath)

print(f"Processing {len(files_to_process)}/{len(all_files)} fuelsource files "
      f"(skipping {len(all_files) - len(files_to_process)} already processed)")

for fpath in files_to_process:
    fname = os.path.basename(fpath)
    date_str = f"{fname[:4]}-{fname[4:6]}-{fname[6:8]}"
    with open(fpath) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        continue

    col_map = {c.lower(): c for c in rows[0].keys()}
    gas_col = col_map.get("natural gas")
    if not gas_col:
        continue

    gen_names = [
        "solar", "wind", "geothermal", "biomass", "biogas", "small hydro",
        "coal", "nuclear", "natural gas", "large hydro", "batteries", "imports", "other",
    ]
    gen_cols = [col_map[n] for n in gen_names if n in col_map]

    gas_vals = []
    total_vals = []
    for r in rows:
        gv = r.get(gas_col, "").strip()
        if gv:
            gas_vals.append(float(gv))
        total = sum(float(r.get(c, 0) or 0) for c in gen_cols if r.get(c, "").strip())
        total_vals.append(total)

    if gas_vals and total_vals:
        avg_gas = sum(gas_vals) / len(gas_vals)
        avg_total = sum(total_vals) / len(total_vals)
        avg_pct = (avg_gas / avg_total * 100) if avg_total > 0 else 0
        output[date_str] = {"avg_gas_mw": round(avg_gas, 2), "avg_gas_pct": round(avg_pct, 2)}

output = dict(sorted(output.items()))

with open(out_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"Created natural_gas_daily.json with {len(output)} days")
print(f"Date range: {list(output.keys())[0]} to {list(output.keys())[-1]}")
