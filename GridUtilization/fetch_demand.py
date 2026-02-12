import requests
import zipfile
import io
import pandas as pd
import json
import datetime
import pytz
import sys
import time
import calendar
import os

def fetch_demand_range(start_date, end_date, max_retries=3):
    """
    Fetch actual system demand from CAISO OASIS API for a date range (up to ~31 days).
    Filters to TAC Area Name: CA ISO-TAC (CAISO - TOTAL).
    Returns a dict of {date_str: [24 hourly MW values]}, or empty dict on failure.
    """
    pst = pytz.timezone('US/Pacific')

    start_dt = pst.localize(datetime.datetime.combine(start_date, datetime.time(0, 0)))
    end_dt = pst.localize(datetime.datetime.combine(end_date, datetime.time(23, 59)))

    start_str = start_date.strftime('%Y%m%d') + 'T00:00' + start_dt.strftime('%z')
    end_str = end_date.strftime('%Y%m%d') + 'T23:59' + end_dt.strftime('%z')

    print(f"  Fetching {start_date} to {end_date} ...")

    base_url = "https://oasis.caiso.com/oasisapi/SingleZip"
    params = {
        "queryname": "SLD_FCST",
        "startdatetime": start_str,
        "enddatetime": end_str,
        "market_run_id": "ACTUAL",
        "version": "1",
        "resultformat": "6"
    }

    # Retry with backoff for rate limiting
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(base_url, params=params, timeout=180)
            if response.status_code == 429:
                wait = 10 * attempt
                print(f"  Rate limited (429). Waiting {wait}s before retry {attempt}/{max_retries}...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait = 10 * attempt
                print(f"  Request error: {e}. Waiting {wait}s before retry {attempt}/{max_retries}...")
                time.sleep(wait)
            else:
                print(f"  Failed after {max_retries} retries: {e}")
                return {}
    else:
        print(f"  Failed after {max_retries} retries (rate limited).")
        return {}

    if b"<?xml" in response.content[:100]:
        # Check if it's an error XML inside a ZIP
        pass

    try:
        z = zipfile.ZipFile(io.BytesIO(response.content))
    except Exception:
        print(f"  Response is not a valid ZIP.")
        return {}

    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
    if not csv_files:
        # Check for error XML
        xml_files = [f for f in z.namelist() if f.endswith('.xml')]
        if xml_files:
            print(f"  API returned error XML: {xml_files[0]}")
        else:
            print(f"  No CSV files in ZIP. Contents: {z.namelist()}")
        return {}

    frames = []
    for csv_name in csv_files:
        with z.open(csv_name) as f:
            df = pd.read_csv(f)
            frames.append(df)

    if not frames:
        return {}

    df = pd.concat(frames, ignore_index=True)

    # Filter to CAISO TOTAL
    if 'TAC_AREA_NAME' in df.columns:
        mask = df['TAC_AREA_NAME'].str.strip().str.upper() == 'CA ISO-TAC'
        if mask.any():
            df = df[mask]
        else:
            print(f"  WARNING: CA ISO-TAC not found in TAC areas.")
            return {}

    # Identify columns
    hour_col = next((c for c in ['OPR_HR', 'HE', 'HOUR'] if c in df.columns), None)
    value_col = next((c for c in ['MW', 'VALUE', 'LOAD', 'AMOUNT'] if c in df.columns), None)
    date_col = next((c for c in ['OPR_DT', 'OPR_DATE'] if c in df.columns), None)

    if not hour_col or not value_col:
        print(f"  Missing hour/value columns. Available: {list(df.columns)}")
        return {}

    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
    df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce')

    # Group by date and hour
    results = {}
    if date_col:
        for opr_date, day_df in df.groupby(date_col):
            hourly = day_df.groupby(hour_col)[value_col].mean()
            demand_24h = []
            for h in range(1, 25):
                if h in hourly.index and pd.notna(hourly[h]):
                    demand_24h.append(round(float(hourly[h]), 1))
                else:
                    demand_24h.append(None)
            # Normalize date format to YYYY-MM-DD
            try:
                d = pd.to_datetime(opr_date).strftime('%Y-%m-%d')
            except Exception:
                d = str(opr_date)
            results[d] = demand_24h
    else:
        # Single day fallback
        hourly = df.groupby(hour_col)[value_col].mean()
        demand_24h = []
        for h in range(1, 25):
            if h in hourly.index and pd.notna(hourly[h]):
                demand_24h.append(round(float(hourly[h]), 1))
            else:
                demand_24h.append(None)
        results[str(start_date)] = demand_24h

    days_fetched = sum(1 for v in results.values() if any(x is not None for x in v))
    print(f"  Got data for {days_fetched} days.")
    return results


def generate_month_ranges(start_date, end_date):
    """Generate (month_start, month_end) tuples covering the date range."""
    current = start_date.replace(day=1)
    while current <= end_date:
        month_start = max(current, start_date)
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = min(datetime.date(current.year, current.month, last_day), end_date)
        yield month_start, month_end
        # Move to first day of next month
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)


def main():
    pst = pytz.timezone('US/Pacific')
    today = datetime.datetime.now(pst).date()

    if len(sys.argv) >= 3:
        start_date = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    elif len(sys.argv) == 2:
        start_date = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end_date = start_date
    else:
        start_date = today
        end_date = today

    total_days = (end_date - start_date).days + 1
    month_ranges = list(generate_month_ranges(start_date, end_date))

    print("==============================================")
    print("CAISO Actual Demand - TOTAL")
    print(f"Date range: {start_date} to {end_date} ({total_days} days)")
    print(f"Fetching in {len(month_ranges)} monthly chunks")
    print("==============================================")

    # Load existing results if available (resume support)
    output_path = "demand_forecast.json"
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            all_results = json.load(f)
        print(f"Loaded {len(all_results)} existing days from {output_path}")
    else:
        all_results = {}

    for i, (m_start, m_end) in enumerate(month_ranges, 1):
        # Skip months where we already have all data
        days_in_range = (m_end - m_start).days + 1
        existing = sum(1 for d in range((m_end - m_start).days + 1)
                       if str(m_start + datetime.timedelta(days=d)) in all_results
                       and any(v is not None for v in all_results.get(str(m_start + datetime.timedelta(days=d)), [])))
        if existing == days_in_range:
            print(f"[{i}/{len(month_ranges)}] {m_start} to {m_end} - already have {existing} days, skipping.")
            continue

        print(f"\n[{i}/{len(month_ranges)}] {m_start} to {m_end}")
        chunk = fetch_demand_range(m_start, m_end)
        all_results.update(chunk)

        # Save incrementally after each month
        with open(output_path, 'w') as f:
            json.dump(all_results, f)
        print(f"  Saved progress: {len(all_results)} total days.")

        # Delay between requests to avoid rate limiting
        if i < len(month_ranges):
            time.sleep(6)

    # Final save with indent for readability
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    valid_days = sum(1 for v in all_results.values() if any(x is not None for x in v))
    print(f"\n==============================================")
    print(f"Complete: {valid_days}/{total_days} days with data.")
    print(f"Saved to {output_path}")
    print("==============================================")

    if valid_days == 0:
        print("No demand data retrieved. Exiting with error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
