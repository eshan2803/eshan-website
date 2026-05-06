"""
Fix missing data at 6-month window boundaries in eia_generation.json.

The original fetch used contiguous non-overlapping UTC windows (Jan-Jun, Jul-Dec).
The EIA API appears to under-return data for the last UTC day of each window, causing
gaps at June 29-30 and Dec 30-31 every year.

This script re-fetches just those boundary periods and merges them in.
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

# Import shared config from the main fetcher
EIA_API_KEY = os.environ.get(
    "EIA_API_KEY", "PhBn6Q4P6a3Gz86kPjyA3b6zye4SmZ64K1NwfxSm"
)
BASE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
RESPONDENT = "CAL"
OUTPUT_FILE = "eia_generation.json"

FUEL_TYPE_MAP = {
    "SUN": "Solar",
    "WND": "Wind",
    "NG":  "Natural Gas",
    "NUC": "Nuclear",
    "WAT": "Hydro",
    "COL": "Coal",
    "OIL": "Oil",
    "OTH": "Other",
}

PST_OFFSET = timezone(timedelta(hours=-8))
PDT_OFFSET = timezone(timedelta(hours=-7))

DST_TRANSITIONS = {
    2019: (datetime(2019, 3, 10, 2), datetime(2019, 11, 3, 2)),
    2020: (datetime(2020, 3, 8, 2),  datetime(2020, 11, 1, 2)),
    2021: (datetime(2021, 3, 14, 2), datetime(2021, 11, 7, 2)),
    2022: (datetime(2022, 3, 13, 2), datetime(2022, 11, 6, 2)),
    2023: (datetime(2023, 3, 12, 2), datetime(2023, 11, 5, 2)),
    2024: (datetime(2024, 3, 10, 2), datetime(2024, 11, 3, 2)),
    2025: (datetime(2025, 3, 9, 2),  datetime(2025, 11, 2, 2)),
    2026: (datetime(2026, 3, 8, 2),  datetime(2026, 11, 1, 2)),
}


def is_dst(dt_naive):
    year = dt_naive.year
    if year not in DST_TRANSITIONS:
        return False
    spring_forward, fall_back = DST_TRANSITIONS[year]
    return spring_forward <= dt_naive < fall_back


def utc_to_pacific(utc_str):
    try:
        parts = utc_str.split("T")
        date_part = parts[0]
        hour_utc = int(parts[1]) if len(parts) > 1 else 0

        dt_utc = datetime(
            int(date_part[:4]),
            int(date_part[5:7]),
            int(date_part[8:10]),
            hour_utc,
            tzinfo=timezone.utc,
        )

        dt_pst = dt_utc.astimezone(PST_OFFSET)
        dt_pdt = dt_utc.astimezone(PDT_OFFSET)

        local_naive = dt_pdt.replace(tzinfo=None)
        if is_dst(local_naive):
            dt_local = dt_pdt
        else:
            dt_local = dt_pst

        date_str = dt_local.strftime("%Y-%m-%d")
        hour_idx = dt_local.hour
        return date_str, hour_idx

    except (ValueError, IndexError):
        return None


def fetch_records(fuel_type, start_str, end_str):
    """Fetch hourly generation for one fuel type in a short window."""
    all_records = []
    offset = 0
    page_size = 5000

    while True:
        params = {
            "api_key": EIA_API_KEY,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": RESPONDENT,
            "facets[fueltype][]": fuel_type,
            "start": start_str,
            "end": end_str,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": page_size,
        }

        for attempt in range(3):
            try:
                r = requests.get(BASE_URL, params=params, timeout=120)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                print(f"    Retry {attempt + 1}/3: {e}")
                time.sleep(10 * (attempt + 1))
                if attempt == 2:
                    return all_records

        resp = data.get("response", {})
        records = resp.get("data", [])
        total = int(resp.get("total", 0))

        all_records.extend(records)

        if len(all_records) >= total or not records:
            break
        offset += page_size
        time.sleep(1)

    return all_records


def merge_records(output, fuel_display_name, records):
    """Merge API records into the output dict."""
    merged = 0
    for rec in records:
        period = rec.get("period")
        value = rec.get("value")
        if period is None or value is None:
            continue
        try:
            value = float(value)
        except (ValueError, TypeError):
            continue
        if value < 0:
            value = 0.0

        result = utc_to_pacific(period)
        if result is None:
            continue

        date_str, hour_idx = result

        if date_str not in output:
            output[date_str] = {}

        if fuel_display_name not in output[date_str]:
            output[date_str][fuel_display_name] = [None] * 24

        existing = output[date_str][fuel_display_name][hour_idx]
        if existing is not None and existing != 0:
            # Already has real data, average with new
            output[date_str][fuel_display_name][hour_idx] = round((existing + value) / 2, 1)
        else:
            output[date_str][fuel_display_name][hour_idx] = round(value, 1)

        merged += 1

    return merged


def main():
    # Load existing data
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    metadata = data.pop("metadata", None)

    # Identify boundary dates: we need to re-fetch UTC windows that overlap
    # the 6-month boundaries. Each boundary is June 30/July 1 and Dec 31/Jan 1.
    # We fetch UTC ranges that cover June 28-July 2 and Dec 29-Jan 2 to be safe.
    boundary_windows = []
    for year in range(2020, 2026):
        # Mid-year boundary: fetch UTC June 28 - July 2
        boundary_windows.append((
            f"{year}-06-28T00",
            f"{year}-07-02T23",
        ))
        # Year-end boundary: fetch UTC Dec 29 - Jan 2
        boundary_windows.append((
            f"{year}-12-29T00",
            f"{year + 1}-01-02T23",
        ))

    print(f"Boundary windows to re-fetch: {len(boundary_windows)}")
    total_requests = len(boundary_windows) * len(FUEL_TYPE_MAP)
    completed = 0

    for fuel_code, fuel_name in FUEL_TYPE_MAP.items():
        print(f"\n[{fuel_code}] Fetching {fuel_name}...")
        for start_str, end_str in boundary_windows:
            completed += 1
            print(f"  {start_str[:10]} to {end_str[:10]}", end="")

            records = fetch_records(fuel_code, start_str, end_str)
            merged = merge_records(data, fuel_name, records)

            print(f" — {len(records)} records, {merged} merged  [{completed}/{total_requests}]")
            time.sleep(1.5)

    # Fill remaining None values with 0
    for date_str in data:
        for fuel_type in data[date_str]:
            arr = data[date_str][fuel_type]
            for i in range(24):
                if arr[i] is None:
                    arr[i] = 0

    # Filter to original date range
    start_str = "2020-01-01"
    end_str = "2025-12-31"
    out_of_range = [d for d in data if d < start_str or d > end_str]
    for d in out_of_range:
        del data[d]
    if out_of_range:
        print(f"\nFiltered {len(out_of_range)} out-of-range dates")

    # Save
    final = {
        "metadata": {
            "source": "EIA-930 Hourly Electric Grid Monitor",
            "endpoint": BASE_URL,
            "respondent": RESPONDENT,
            "timezone": "US/Pacific",
            "units": "MWh (hourly, equivalent to avg MW)",
            "fuel_types": list(FUEL_TYPE_MAP.values()),
            "note": "Geothermal and Battery are included in 'Other' by the CAL respondent",
            "last_updated": datetime.now().isoformat(),
            "date_range": [start_str, end_str],
        }
    }

    for date_key in sorted(data.keys()):
        if start_str <= date_key <= end_str:
            final[date_key] = data[date_key]

    with open(OUTPUT_FILE, "w") as f:
        json.dump(final, f, indent=1)

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\nSaved {OUTPUT_FILE} ({len(data)} dates, {size_mb:.1f} MB)")

    # Verify: check the boundary dates that were problematic
    print("\n=== Verification ===")
    check_dates = []
    for year in range(2020, 2026):
        check_dates.extend([f"{year}-06-29", f"{year}-06-30", f"{year}-12-30", f"{year}-12-31"])

    for d in check_dates:
        if d in data:
            ng = data[d].get("Natural Gas", [0]*24)
            ng_zeros = sum(1 for v in ng if v == 0)
            if ng_zeros > 2:
                zero_hrs = [i for i, v in enumerate(ng) if v == 0]
                print(f"  STILL MISSING: {d} - NG has {ng_zeros} zero hours at: {zero_hrs}")
            else:
                print(f"  OK: {d}")
        else:
            print(f"  MISSING DATE: {d}")


if __name__ == "__main__":
    main()
