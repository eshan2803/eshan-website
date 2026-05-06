"""
Fetch hourly generation by fuel type for California from EIA-930 API.

Produces eia_generation.json with daily entries, each containing 24-hour
generation arrays per fuel type in Pacific time.

Usage:
    python fetch_eia_generation.py                          # Full fetch 2020-2025
    python fetch_eia_generation.py 2024-01-01 2024-01-31    # Custom range
    python fetch_eia_generation.py --resume                 # Resume interrupted fetch
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
OUTPUT_FILE = "eia_generation.json"

# EIA fuel type code -> display name (matches available_capacity.json categories)
# Note: CAL respondent reports 8 fuel types. Geothermal and Battery are
# included in "Other" (OTH) and not reported separately.
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

FUEL_TYPES = list(FUEL_TYPE_MAP.keys())

# Rate limiting
REQUEST_DELAY = 2       # seconds between requests
MAX_RETRIES = 3
RETRY_DELAYS = [10, 20, 40]  # exponential backoff

# Pacific time offsets (standard = UTC-8, daylight = UTC-7)
PST_OFFSET = timezone(timedelta(hours=-8))
PDT_OFFSET = timezone(timedelta(hours=-7))

# ---------------------------------------------------------------------------
# DST transition dates (second Sunday of March, first Sunday of November)
# Pre-computed for 2019-2026 to avoid heavy datetime logic
# ---------------------------------------------------------------------------

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
    """Check if a naive local datetime falls in Pacific Daylight Time."""
    year = dt_naive.year
    if year not in DST_TRANSITIONS:
        return False
    spring_forward, fall_back = DST_TRANSITIONS[year]
    return spring_forward <= dt_naive < fall_back


def utc_to_pacific(utc_str):
    """
    Convert EIA UTC timestamp to Pacific date and hour index (0-23).

    EIA period format: "2020-01-01T08" (hour ending in UTC)
    The value represents generation during the hour ENDING at this time,
    so the actual hour is T-1 in terms of the interval start.

    Returns (date_str "YYYY-MM-DD", hour_index 0-23) or None if invalid.
    """
    try:
        # Parse UTC timestamp
        parts = utc_str.split("T")
        date_part = parts[0]
        hour_utc = int(parts[1]) if len(parts) > 1 else 0

        # EIA hour is hour-ending, so interval starts at hour_utc - 1
        # But for our purposes we store by the start of the interval
        # Actually, EIA-930 uses hour-beginning timestamps
        # Let's just convert the given UTC hour to Pacific

        dt_utc = datetime(
            int(date_part[:4]),
            int(date_part[5:7]),
            int(date_part[8:10]),
            hour_utc,
            tzinfo=timezone.utc,
        )

        # Convert to Pacific: try PDT first (UTC-7), then PST (UTC-8)
        # Check if the resulting local time falls in DST
        dt_pst = dt_utc.astimezone(PST_OFFSET)  # UTC-8
        dt_pdt = dt_utc.astimezone(PDT_OFFSET)  # UTC-7

        # Use the PDT result to check if we're in DST
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


# ---------------------------------------------------------------------------
# Window generation
# ---------------------------------------------------------------------------

def generate_windows(start_date, end_date):
    """
    Generate 6-month UTC windows that cover the full Pacific-time date range.

    Since Pacific time is UTC-8/UTC-7, we need:
    - Start 1 day earlier in UTC to capture early morning Pacific hours of the first day
    - End 1 day later in UTC to capture late evening Pacific hours of the last day

    Returns list of (start_str, end_str) in "YYYY-MM-DDT00" format.
    """
    # Expand to UTC: start 1 day before, end 1 day after the Pacific range
    utc_start = start_date - timedelta(days=1)
    utc_end = end_date + timedelta(days=1)

    windows = []
    current = utc_start
    while current <= utc_end:
        # Window end: 6 months from current, or utc_end
        if current.month <= 6:
            window_end = datetime(current.year, 6, 30)
        else:
            window_end = datetime(current.year, 12, 31)

        if window_end > utc_end:
            window_end = utc_end

        # Extend each window end by 2 days to create overlap with the next window.
        # The EIA API may under-return data for the last UTC day of a window,
        # so overlapping ensures boundary dates are fully covered.
        # The merge function handles duplicates by averaging (same values).
        extended_end = min(window_end + timedelta(days=2), utc_end)
        windows.append((
            current.strftime("%Y-%m-%dT00"),
            extended_end.strftime("%Y-%m-%dT23"),
        ))

        # Next window starts day after the original (non-extended) window_end
        current = window_end + timedelta(days=1)

    return windows


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def fetch_fuel_type_window(api_key, fuel_type, start_str, end_str):
    """
    Fetch hourly generation for one fuel type in one time window.
    Handles pagination. Returns list of {period, value} dicts.
    """
    all_records = []
    offset = 0
    page_size = 5000

    while True:
        params = {
            "api_key": api_key,
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

        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(BASE_URL, params=params, timeout=120)
                r.raise_for_status()
                data = r.json()
                break
            except requests.exceptions.RequestException as e:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 60
                print(f"    Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                print(f"    Waiting {delay}s...")
                time.sleep(delay)
                if attempt == MAX_RETRIES - 1:
                    print(f"    FAILED after {MAX_RETRIES} retries. Skipping window.")
                    return all_records
            except json.JSONDecodeError as e:
                print(f"    JSON decode error: {e}")
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


# ---------------------------------------------------------------------------
# Merge records into output
# ---------------------------------------------------------------------------

def merge_records(output, fuel_display_name, records):
    """
    Merge API records for one fuel type into the output dict.
    Each record has 'period' (UTC timestamp) and 'value' (MWh).
    """
    merged = 0
    skipped = 0

    for rec in records:
        period = rec.get("period")
        value = rec.get("value")

        if period is None or value is None:
            skipped += 1
            continue

        try:
            value = float(value)
        except (ValueError, TypeError):
            skipped += 1
            continue

        # Clamp negative values to 0 (small measurement noise, e.g. solar at night)
        if value < 0:
            value = 0.0

        result = utc_to_pacific(period)
        if result is None:
            skipped += 1
            continue

        date_str, hour_idx = result

        # Initialize date entry if needed
        if date_str not in output:
            output[date_str] = {}

        if fuel_display_name not in output[date_str]:
            output[date_str][fuel_display_name] = [None] * 24

        # Handle DST fall-back duplicates: average if slot already filled
        existing = output[date_str][fuel_display_name][hour_idx]
        if existing is not None:
            output[date_str][fuel_display_name][hour_idx] = round((existing + value) / 2, 1)
        else:
            output[date_str][fuel_display_name][hour_idx] = round(value, 1)

        merged += 1

    return merged, skipped


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def load_existing(filepath):
    """Load existing output file for resume support."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            # Remove metadata key for processing
            metadata = data.pop("metadata", None)
            print(f"Loaded existing data: {len(data)} dates")
            return data, metadata
        except (json.JSONDecodeError, IOError) as e:
            print(f"Could not load existing file: {e}")
    return {}, None


def save_output(output, filepath, start_date, end_date):
    """Save output with metadata header. Only includes dates within the requested range."""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    # Build final dict with metadata first
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

    # Add dates in sorted order, filtering to requested Pacific-time range
    saved_count = 0
    for date_key in sorted(output.keys()):
        if start_str <= date_key <= end_str:
            final[date_key] = output[date_key]
            saved_count += 1

    with open(filepath, "w") as f:
        json.dump(final, f, indent=1)

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"Saved {filepath} ({saved_count} dates, {size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Check which windows are already fetched (for resume)
# ---------------------------------------------------------------------------

def check_window_complete(output, fuel_display_name, start_str, end_str):
    """
    Check if a fuel type's window is already fully fetched.
    Heuristic: if >80% of expected days have data for this fuel type, skip.
    """
    start_dt = datetime.strptime(start_str[:10], "%Y-%m-%d")
    end_dt = datetime.strptime(end_str[:10], "%Y-%m-%d")
    expected_days = (end_dt - start_dt).days + 1

    found = 0
    for i in range(expected_days):
        date_str = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        if date_str in output and fuel_display_name in output[date_str]:
            arr = output[date_str][fuel_display_name]
            # Check that at least some hours have data (not all None)
            if any(v is not None for v in arr):
                found += 1

    completeness = found / expected_days if expected_days > 0 else 0
    return completeness > 0.8


# ---------------------------------------------------------------------------
# Fill missing hours with 0 (for cleaner output)
# ---------------------------------------------------------------------------

def fill_missing_hours(output):
    """Replace None values with 0 for hours where no data was returned."""
    for date_str in output:
        for fuel_type in output[date_str]:
            arr = output[date_str][fuel_type]
            for i in range(24):
                if arr[i] is None:
                    arr[i] = 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Parse arguments
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 12, 31)
    resume = False

    args = [a for a in sys.argv[1:] if a != "--resume"]
    if "--resume" in sys.argv:
        resume = True

    if len(args) >= 2:
        start_date = datetime.strptime(args[0], "%Y-%m-%d")
        end_date = datetime.strptime(args[1], "%Y-%m-%d")
    elif len(args) == 1:
        start_date = datetime.strptime(args[0], "%Y-%m-%d")

    print("=" * 60)
    print("EIA-930 Hourly Generation by Fuel Type — California")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"API key: {EIA_API_KEY[:8]}...")
    print(f"Fuel types: {', '.join(FUEL_TYPES)}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 60)

    # Load existing data for resume
    output = {}
    if resume or os.path.exists(OUTPUT_FILE):
        output, _ = load_existing(OUTPUT_FILE)

    # Generate time windows
    windows = generate_windows(start_date, end_date)
    print(f"\nTime windows: {len(windows)}")
    for i, (ws, we) in enumerate(windows):
        print(f"  {i + 1}. {ws[:10]} to {we[:10]}")

    total_requests = len(FUEL_TYPES) * len(windows)
    completed = 0
    skipped_windows = 0

    print(f"\nTotal requests planned: {total_requests}")
    print()

    for fuel_code in FUEL_TYPES:
        fuel_name = FUEL_TYPE_MAP[fuel_code]
        print(f"[{fuel_code}] Fetching {fuel_name}...")

        for i, (win_start, win_end) in enumerate(windows):
            completed += 1

            # Check if already fetched (resume support)
            if resume and check_window_complete(output, fuel_name, win_start, win_end):
                skipped_windows += 1
                print(f"  Window {i + 1}/{len(windows)}: {win_start[:10]} to {win_end[:10]} — SKIPPED (already fetched)")
                continue

            print(f"  Window {i + 1}/{len(windows)}: {win_start[:10]} to {win_end[:10]}", end="")

            records = fetch_fuel_type_window(EIA_API_KEY, fuel_code, win_start, win_end)
            merged, skip = merge_records(output, fuel_name, records)

            print(f" — {len(records)} records, {merged} merged" +
                  (f", {skip} skipped" if skip else "") +
                  f"  [{completed}/{total_requests}]")

            time.sleep(REQUEST_DELAY)

        # Incremental save after each fuel type
        save_output(output, OUTPUT_FILE, start_date, end_date)
        print(f"  [Saved after {fuel_name}]\n")

    # Final cleanup: fill None with 0, filter to requested Pacific-time range
    fill_missing_hours(output)

    # Remove dates outside the requested range (caused by UTC buffer days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    out_of_range = [d for d in output if d < start_str or d > end_str]
    for d in out_of_range:
        del output[d]
    if out_of_range:
        print(f"Filtered {len(out_of_range)} out-of-range dates (UTC buffer)")

    save_output(output, OUTPUT_FILE, start_date, end_date)

    # Summary
    dates = sorted(output.keys())
    print("\n" + "=" * 60)
    print("COMPLETE")
    print(f"  Dates: {len(dates)} ({dates[0]} to {dates[-1]})")
    print(f"  Fuel types: {len(FUEL_TYPE_MAP)}")
    if skipped_windows:
        print(f"  Skipped windows (resume): {skipped_windows}")

    # Spot-check: print one day's data
    sample_date = dates[len(dates) // 2]
    print(f"\n  Sample day: {sample_date}")
    if sample_date in output:
        for ft, arr in sorted(output[sample_date].items()):
            peak = max(arr)
            total = sum(arr)
            print(f"    {ft:<15} peak={peak:>8.1f} MW  daily={total:>10.1f} MWh")

    print()


if __name__ == "__main__":
    main()
