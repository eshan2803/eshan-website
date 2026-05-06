"""
Export the last day's 5-minute supply/demand breakdown as JSON for the homepage chart.
Reads from caiso_comprehensive_data.csv and outputs daily_breakdown.json to the repo root.
"""
import csv
import json
import os
from pathlib import Path

script_dir = Path(__file__).parent
CSV_FILE = script_dir / "caiso_comprehensive_data.csv"
OUT_FILE = script_dir.parent / "daily_breakdown.json"


def main():
    if not CSV_FILE.exists():
        print("ERROR: caiso_comprehensive_data.csv not found")
        return 1

    # Read CSV and find the last date
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("ERROR: CSV is empty")
        return 1

    last_ts = rows[-1]["timestamp"]
    last_date = last_ts.split(" ")[0]

    # Filter rows for the last date
    day_rows = [r for r in rows if r["timestamp"].startswith(last_date)]
    print(f"Exporting breakdown for {last_date} ({len(day_rows)} rows)")

    def safe_float(v):
        try:
            return round(float(v), 1) if v and v.strip() else 0
        except (ValueError, TypeError):
            return 0

    timestamps = []
    sources = {
        "solar": [], "wind": [], "nuclear": [], "large_hydro": [], "small_hydro": [],
        "geothermal": [], "biomass": [], "biogas": [],
        "battery_discharging": [], "imports": [],
        "natural_gas": [], "other": [], "coal": [],
    }
    load = []
    demand = []
    battery_charging = []

    for r in day_rows:
        ts = r["timestamp"]
        time_part = ts.split(" ")[1] if " " in ts else "0:00"
        timestamps.append(time_part)

        sources["solar"].append(safe_float(r.get("solar_mw", "")))
        sources["wind"].append(safe_float(r.get("wind_mw", "")))
        sources["nuclear"].append(safe_float(r.get("nuclear_mw", "")))
        sources["large_hydro"].append(safe_float(r.get("large_hydro_mw", "")))
        sources["small_hydro"].append(safe_float(r.get("small_hydro_mw", "")))
        sources["geothermal"].append(safe_float(r.get("geothermal_mw", "")))
        sources["biomass"].append(safe_float(r.get("biomass_mw", "")))
        sources["biogas"].append(safe_float(r.get("biogas_mw", "")))
        sources["battery_discharging"].append(safe_float(r.get("battery_discharging_mw", "")))
        sources["imports"].append(safe_float(r.get("imports_mw", "")))
        sources["natural_gas"].append(safe_float(r.get("natural_gas_mw", "")))
        sources["other"].append(safe_float(r.get("other_mw", "")))
        sources["coal"].append(safe_float(r.get("coal_mw", "")))

        load.append(safe_float(r.get("load_mw", "")))
        demand.append(safe_float(r.get("demand_mw", "")))
        battery_charging.append(safe_float(r.get("battery_charging_mw", "")))

    # LMP prices (5-min where available, hourly at :00 otherwise)
    lmp = []
    for r in day_rows:
        val = r.get("lmp", "")
        if val and val.strip():
            lmp.append(round(float(val), 2))
        else:
            lmp.append(None)

    output = {
        "date": last_date,
        "timestamps": timestamps,
        "sources": sources,
        "load": load,
        "demand": demand,
        "battery_charging": battery_charging,
        "lmp": lmp,
    }

    with open(OUT_FILE, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"[OK] Exported to {OUT_FILE} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    exit(main())
