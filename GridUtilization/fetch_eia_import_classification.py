"""
Refresh EIA hourly NW/SW import classification for recent CAISO import data.

The historical 2019-2024 dispatch file is kept separately. This script updates
the 2025+ extension used by process_daily_energy_with_import_breakdown.py.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests


BASE_URL = "https://api.eia.gov/v2/electricity/rto/interchange-data/data/"
SCRIPT_DIR = Path(__file__).parent
OUT_INTERCHANGE = SCRIPT_DIR / "EIA_Interchange_2025_latest.csv"
OUT_CLASSIFIED = SCRIPT_DIR / "EIA_Import_Dispatch_and_CI_2025_latest.csv"

MIX_CANDIDATES = [
    SCRIPT_DIR / "import_mix_all_years.csv",
    SCRIPT_DIR.parent / "curtailmentdata" / "import_mix_all_years.csv",
    Path(r"C:\Users\eshan\OneDrive\Desktop\eshan-website\curtailmentdata\import_mix_all_years.csv"),
]

SOURCES = [
    "Solar", "Wind", "Nuclear", "Geothermal", "Biomass", "Small Hydro",
    "Large Hydro", "Unspecified", "Other", "Natural Gas", "Coal", "Oil",
]
CLEAN_SOURCES = {"Solar", "Wind", "Nuclear", "Geothermal", "Biomass", "Small Hydro", "Large Hydro"}
FOSSIL_SOURCES = {"Natural Gas", "Coal", "Oil"}
UNKNOWN_SOURCES = {"Unspecified", "Other"}

HOURLY_CF = {
    "Solar": [0, 0, 0, 0, 0, 0.05, 0.15, 0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.85, 0.8, 0.7, 0.3, 0.05, 0, 0, 0, 0, 0, 0],
    "Wind": [0.4, 0.42, 0.45, 0.46, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.2, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4],
    "Nuclear": [0.90] * 24,
    "Geothermal": [0.90] * 24,
    "Biomass": [0.85] * 24,
    "Small Hydro": [0.40] * 24,
    "Large Hydro": [1.0] * 24,
    "Coal": [1.0] * 24,
    "Natural Gas": [1.0] * 24,
    "Unspecified": [0.50] * 24,
    "Other": [0.50] * 24,
    "Oil": [1.0] * 24,
}


def fetch_pair(fromba, toba, start="2025-01-01T00-08", end=None):
    rows = []
    offset = 0
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        raise RuntimeError("EIA_API_KEY is not set")

    while True:
        params = {
            "frequency": "local-hourly",
            "data[0]": "value",
            "facets[fromba][]": fromba,
            "facets[toba][]": toba,
            "start": start,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": str(offset),
            "length": "5000",
        }
        if api_key:
            params["api_key"] = api_key
        if end:
            params["end"] = end

        response = requests.get(BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()["response"]
        batch = payload["data"]
        rows.extend(batch)
        if offset + len(batch) >= int(payload["total"]) or not batch:
            break
        offset += len(batch)

    return rows


def period_to_date_hour(period):
    stamp = datetime.strptime(period[:13], "%Y-%m-%dT%H")
    if stamp.hour == 0:
        day = stamp.date() - timedelta(days=1)
        hour = 24
    else:
        day = stamp.date()
        hour = stamp.hour
    return f"{day.month}/{day.day}/{day.year}", hour


def fetch_interchange_2025_plus():
    print("Fetching EIA local-hourly NW->CAL and SW->CAL interchange...")
    nw = fetch_pair("NW", "CAL")
    sw = fetch_pair("SW", "CAL")
    print(f"  NW rows: {len(nw):,}; SW rows: {len(sw):,}")

    by_key = {}
    for region, rows in [("NW Import", nw), ("SW Import", sw)]:
        for row in rows:
            date, hour = period_to_date_hour(row["period"])
            key = (date, hour)
            by_key.setdefault(key, {"Year": int(date.split("/")[-1]), "Date": date, "Hour": hour})
            by_key[key][region] = float(row["value"])

    df = pd.DataFrame(by_key.values())
    df["NW Import"] = pd.to_numeric(df.get("NW Import", 0), errors="coerce").fillna(0.0)
    df["SW Import"] = pd.to_numeric(df.get("SW Import", 0), errors="coerce").fillna(0.0)
    df["Date_dt"] = pd.to_datetime(df["Date"])
    return df.sort_values(["Date_dt", "Hour"]).drop(columns=["Date_dt"])


def load_2024_mix():
    mix_path = next((path for path in MIX_CANDIDATES if path.exists()), None)
    if mix_path is None:
        raise FileNotFoundError("import_mix_all_years.csv not found")

    print(f"Loading import mix from {mix_path}")
    mix = pd.read_csv(mix_path)
    mix = mix[mix["Year"] == 2024]
    nw = dict(zip(mix["Source"], mix["NW_Mix_Pct"]))
    sw = dict(zip(mix["Source"], mix["SW_Mix_Pct"]))
    return nw, sw


def dispatch_hour(import_mw, mix, hour):
    import_mw = max(float(import_mw or 0), 0.0)
    if import_mw <= 0:
        return {source: 0.0 for source in SOURCES}

    hour_index = int(hour) - 1
    raw = {
        source: float(mix.get(source, 0) or 0) * HOURLY_CF.get(source, [0.5] * 24)[hour_index]
        for source in SOURCES
    }
    total = sum(raw.values())
    if total <= 0:
        return {source: 0.0 for source in SOURCES}
    return {source: import_mw * raw[source] / total for source in SOURCES}


def classify_interchange(df):
    nw_mix, sw_mix = load_2024_mix()
    rows = []

    for _, row in df.iterrows():
        out = row.to_dict()
        nw_dispatch = dispatch_hour(row.get("NW Import", 0), nw_mix, row["Hour"])
        sw_dispatch = dispatch_hour(row.get("SW Import", 0), sw_mix, row["Hour"])
        clean = fossil = unknown = 0.0

        for prefix, dispatch in [("NW", nw_dispatch), ("SW", sw_dispatch)]:
            for source, value in dispatch.items():
                out[f"{prefix}_{source}_MWh"] = value
                if source in CLEAN_SOURCES:
                    clean += value
                elif source in FOSSIL_SOURCES:
                    fossil += value
                elif source in UNKNOWN_SOURCES:
                    unknown += value

        total = clean + fossil + unknown
        out["Import_Clean_Ratio"] = clean / total if total else 0.0
        out["Import_Fossil_Ratio"] = fossil / total if total else 0.0
        out["Import_Unknown_Ratio"] = unknown / total if total else 0.0
        rows.append(out)

    return pd.DataFrame(rows)


def main():
    if not os.environ.get("EIA_API_KEY") and OUT_CLASSIFIED.exists():
        print("EIA_API_KEY is not set; using cached EIA import classification file.")
        print(f"Cached file: {OUT_CLASSIFIED}")
        return 0

    interchange = fetch_interchange_2025_plus()
    interchange.to_csv(OUT_INTERCHANGE, index=False)
    print(f"Saved {OUT_INTERCHANGE} ({len(interchange):,} rows)")
    if not interchange.empty:
        print(f"Range: {interchange.iloc[0]['Date']} hour {interchange.iloc[0]['Hour']} to {interchange.iloc[-1]['Date']} hour {interchange.iloc[-1]['Hour']}")

    classified = classify_interchange(interchange)
    classified.to_csv(OUT_CLASSIFIED, index=False)
    print(f"Saved {OUT_CLASSIFIED} ({len(classified):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
