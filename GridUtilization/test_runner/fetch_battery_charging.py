"""
Fetch hourly net battery output from EIA-930 "Other" fuel type for California.

The CAL respondent's "Other" category includes Geothermal + Battery (net).
Negative values indicate battery charging exceeding geothermal generation.
We preserve negative values (unlike the main fetch script which clamps to 0).

Produces battery_charging.json with daily entries containing 24-hour arrays.

Usage:
    python fetch_battery_charging.py                     # Full 2020-2025
    python fetch_battery_charging.py --resume             # Resume interrupted
"""

import requests
import json
import sys
import os
import time
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EIA_API_KEY = os.environ.get(
    "EIA_API_KEY", "PhBn6Q4P6a3Gz86kPjyA3b6zye4SmZ64K1NwfxSm"
)
BASE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
RESPONDENT = "CAL"
FUEL_TYPE = "OTH"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "battery_charging.json")

REQUEST_DELAY = 2
MAX_RETRIES = 3
RETRY_DELAYS = [10, 20, 40]

# Pacific time
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
            int(date_part[:4]), int(date_part[5:7]), int(date_part[8:10]),
            hour_utc, tzinfo=timezone.utc,
        )
        dt_pst = dt_utc.astimezone(PST_OFFSET)
        dt_pdt = dt_utc.astimezone(PDT_OFFSET)
        local_naive = dt_pdt.replace(tzinfo=None)
        dt_local = dt_pdt if is_dst(local_naive) else dt_pst
        return dt_local.strftime("%Y-%m-%d"), dt_local.hour
    except (ValueError, IndexError):
        return None


def generate_windows(start_date, end_date):
    utc_start = start_date - timedelta(days=1)
    utc_end = end_date + timedelta(days=1)
    windows = []
    current = utc_start
    while current <= utc_end:
        if current.month <= 6:
            window_end = datetime(current.year, 6, 30)
        else:
            window_end = datetime(current.year, 12, 31)
        if window_end > utc_end:
            window_end = utc_end
        extended_end = min(window_end + timedelta(days=2), utc_end)
        windows.append((
            current.strftime("%Y-%m-%dT00"),
            extended_end.strftime("%Y-%m-%dT23"),
        ))
        current = window_end + timedelta(days=1)
    return windows


def fetch_window(api_key, start_str, end_str):
    all_records = []
    offset = 0
    page_size = 5000
    while True:
        params = {
            "api_key": api_key,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": RESPONDENT,
            "facets[fueltype][]": FUEL_TYPE,
            "start": start_str,
            "end": end_str,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": page_size,
        }
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(BASE_URL, params=params, timeout=120)
                r.raise_for_status()
                data = r.json()
                break
            except requests.exceptions.RequestException as e:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 60
                print(f"  Retry {attempt+1}/{MAX_RETRIES}: {e}")
                time.sleep(delay)
                if attempt == MAX_RETRIES - 1:
                    return all_records
        resp = data.get("response", {})
        records = resp.get("data", [])
        total = int(resp.get("total", 0))
        all_records.extend(records)
        if len(all_records) >= total or not records:
            break
        offset += page_size
        time.sleep(REQUEST_DELAY)
    return all_records


def main():
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 12, 31)
    resume = "--resume" in sys.argv

    print("=" * 60)
    print("EIA-930 Battery Charging Data (OTH fuel type, CAL)")
    print(f"Date range: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}")
    print("=" * 60)

    # Load existing data if resuming
    output = {}
    if resume and os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        data.pop("metadata", None)
        output = data
        print(f"Loaded existing: {len(output)} dates")

    windows = generate_windows(start_date, end_date)
    print(f"Windows: {len(windows)}")

    for i, (ws, we) in enumerate(windows):
        print(f"  [{i+1}/{len(windows)}] {ws[:10]} to {we[:10]}", end="")

        # Skip if we have good coverage already
        if resume:
            ws_dt = datetime.strptime(ws[:10], "%Y-%m-%d")
            we_dt = datetime.strptime(we[:10], "%Y-%m-%d")
            expected = (we_dt - ws_dt).days + 1
            found = sum(1 for d in output
                        if ws[:10] <= d <= we[:10] and output[d] is not None)
            if found / expected > 0.8:
                print(" — SKIP (already fetched)")
                continue

        records = fetch_window(EIA_API_KEY, ws, we)
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
            result = utc_to_pacific(period)
            if result is None:
                continue
            date_str, hour_idx = result
            if date_str not in output:
                output[date_str] = [None] * 24
            existing = output[date_str][hour_idx]
            if existing is not None:
                output[date_str][hour_idx] = round((existing + value) / 2, 1)
            else:
                output[date_str][hour_idx] = round(value, 1)
            merged += 1

        print(f" — {len(records)} records, {merged} merged")
        time.sleep(REQUEST_DELAY)

    # Filter to date range
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    filtered = {d: v for d, v in output.items() if start_str <= d <= end_str}

    # Save
    final = {
        "metadata": {
            "source": "EIA-930 Hourly Electric Grid Monitor",
            "respondent": RESPONDENT,
            "fuel_type": "OTH (Other = Geothermal + Battery net)",
            "timezone": "US/Pacific",
            "units": "MW (negative = net battery charging exceeds geothermal)",
            "note": "Negative values indicate battery charging power exceeds geothermal generation",
            "date_range": [start_str, end_str],
            "last_updated": datetime.now().isoformat(),
        }
    }
    for d in sorted(filtered.keys()):
        final[d] = filtered[d]

    with open(OUTPUT_FILE, "w") as f:
        json.dump(final, f, indent=1)

    dates = sorted(filtered.keys())
    print(f"\nSaved {OUTPUT_FILE}")
    print(f"  Dates: {len(dates)} ({dates[0]} to {dates[-1]})")

    # Summary stats
    for year in range(2020, 2026):
        yr_dates = [d for d in dates if d.startswith(str(year))]
        if not yr_dates:
            continue
        all_vals = []
        for d in yr_dates:
            all_vals.extend(v for v in filtered[d] if v is not None)
        if all_vals:
            mn = min(all_vals)
            mx = max(all_vals)
            neg_count = sum(1 for v in all_vals if v < 0)
            print(f"  {year}: min={mn:>8.0f} MW  max={mx:>8.0f} MW  "
                  f"neg_hours={neg_count:>5}")


if __name__ == "__main__":
    main()
