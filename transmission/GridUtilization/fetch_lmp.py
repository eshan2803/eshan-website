"""
Fetch actual hourly LMP (Locational Marginal Price) data from CAISO OASIS API.
Fetches Day-Ahead Market prices for 2020-2025.

Uses PRC_LMP (hourly LMP) with monthly bulk requests to minimize API calls.
Includes exponential backoff for rate limiting.

CAISO OASIS API endpoint:
- Query: PRC_LMP (hourly LMP)
- Market: DAM (Day-Ahead Market) - most reliable for historical data
- Node: TH_SP15_GEN-APND (SP15 Trading Hub)

Output: lmp_data.json with hourly LMP for each day
"""

import requests
import zipfile
import io
import pandas as pd
import json
import datetime
import pytz
import os
import sys
import time
import calendar
import xml.etree.ElementTree as ET

# CAISO OASIS API configuration
BASE_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
NODE = "TH_SP15_GEN-APND"


def parse_xml_lmp(z, xml_filename):
    """
    Parse CAISO OASIS XML response for LMP data.
    Older dates return XML instead of CSV. The XML contains
    OASISReport > MessagePayload > RTO > REPORT_ITEM > REPORT_DATA elements.
    Returns dict of {date_str: [24 hourly values]} or empty dict.
    """
    try:
        with z.open(xml_filename) as f:
            content = f.read()

        # Check for error indicators
        if b'ERR_CODE' in content or b'No data' in content.lower():
            return {}

        root = ET.fromstring(content)
        ns = {'m': 'http://www.caiso.com/soa/OASISReport_v1.xsd'}

        results = {}
        # Navigate: OASISReport > MessagePayload > RTO > REPORT_ITEM > REPORT_DATA
        for report_item in root.findall('.//m:REPORT_ITEM', ns):
            # Check for LMP type (not congestion/loss components)
            data_item = report_item.find('m:REPORT_HEADER/m:DATA_ITEM', ns)
            if data_item is not None and data_item.text and 'LMP_PRC' not in (data_item.text or ''):
                # Also accept if data_item contains 'LMP' but not loss/congestion
                if 'LMP' not in (data_item.text or ''):
                    continue

            for report_data in report_item.findall('m:REPORT_DATA', ns):
                opr_date_el = report_data.find('m:OPR_DATE', ns) or report_data.find('m:OPR_DT', ns)
                opr_hr_el = report_data.find('m:OPR_HR', ns) or report_data.find('m:OPR_HOUR', ns)
                value_el = report_data.find('m:VALUE', ns) or report_data.find('m:MW', ns)

                if opr_date_el is None or opr_hr_el is None or value_el is None:
                    continue

                try:
                    opr_date = opr_date_el.text.strip()
                    opr_hr = int(opr_hr_el.text.strip())
                    value = float(value_el.text.strip())
                except (ValueError, AttributeError):
                    continue

                # Normalize date
                try:
                    d = pd.to_datetime(opr_date).strftime('%Y-%m-%d')
                except Exception:
                    d = opr_date

                if d not in results:
                    results[d] = [None] * 24
                if 1 <= opr_hr <= 24:
                    results[d][opr_hr - 1] = round(value, 2)

        if results:
            valid = sum(1 for v in results.values() if any(x is not None for x in v))
            print(f"  Parsed XML: got data for {valid} days.")
        return results

    except Exception as e:
        print(f"  XML parse error: {e}")
        return {}


def fetch_lmp_month(start_date, end_date, max_retries=5):
    """
    Fetch hourly LMP data from CAISO OASIS API for a date range (up to ~31 days).
    Uses PRC_LMP query for hourly data (much less data than 5-min intervals).
    Returns a dict of {date_str: [24 hourly $/MWh values]}, or empty dict on failure.
    """
    pst = pytz.timezone('US/Pacific')

    start_dt = pst.localize(datetime.datetime.combine(start_date, datetime.time(0, 0)))
    end_dt = pst.localize(datetime.datetime.combine(end_date, datetime.time(23, 59)))

    start_str = start_date.strftime('%Y%m%d') + 'T00:00' + start_dt.strftime('%z')
    end_str = end_date.strftime('%Y%m%d') + 'T23:59' + end_dt.strftime('%z')

    print(f"  Fetching {start_date} to {end_date} ...")

    params = {
        "queryname": "PRC_LMP",
        "market_run_id": "DAM",
        "node": NODE,
        "startdatetime": start_str,
        "enddatetime": end_str,
        "version": "1",
        "resultformat": "6"
    }

    # Retry with exponential backoff
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=180)
            if response.status_code == 429:
                wait = min(15 * (2 ** (attempt - 1)), 120)  # 15, 30, 60, 120s
                print(f"  Rate limited (429). Waiting {wait}s before retry {attempt}/{max_retries}...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait = min(15 * (2 ** (attempt - 1)), 120)
                print(f"  Request error: {e}. Waiting {wait}s before retry {attempt}/{max_retries}...")
                time.sleep(wait)
            else:
                print(f"  Failed after {max_retries} retries: {e}")
                return {}
    else:
        print(f"  Failed after {max_retries} retries (rate limited).")
        return {}

    # Check for XML error response
    if b"<?xml" in response.content[:200] and b"ERR" in response.content[:500]:
        print(f"  API returned error XML response.")
        return {}

    try:
        z = zipfile.ZipFile(io.BytesIO(response.content))
    except Exception:
        print(f"  Response is not a valid ZIP.")
        return {}

    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
    if not csv_files:
        xml_files = [f for f in z.namelist() if f.endswith('.xml')]
        if xml_files:
            # Try to parse XML for data (older dates return XML instead of CSV)
            xml_results = parse_xml_lmp(z, xml_files[0])
            if xml_results:
                return xml_results
            print(f"  No usable data in XML: {xml_files[0]}")
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

    # Filter for total LMP (not congestion/loss components)
    if 'LMP_TYPE' in df.columns:
        df = df[df['LMP_TYPE'] == 'LMP']

    # Identify columns
    hour_col = next((c for c in ['OPR_HR', 'HE', 'HOUR'] if c in df.columns), None)
    value_col = next((c for c in ['MW', 'VALUE', 'LMP', 'AMOUNT'] if c in df.columns), None)
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
            lmp_24h = []
            for h in range(1, 25):
                if h in hourly.index and pd.notna(hourly[h]):
                    lmp_24h.append(round(float(hourly[h]), 2))
                else:
                    lmp_24h.append(None)
            # Normalize date format
            try:
                d = pd.to_datetime(opr_date).strftime('%Y-%m-%d')
            except Exception:
                d = str(opr_date)
            results[d] = lmp_24h
    else:
        # Single day fallback
        hourly = df.groupby(hour_col)[value_col].mean()
        lmp_24h = []
        for h in range(1, 25):
            if h in hourly.index and pd.notna(hourly[h]):
                lmp_24h.append(round(float(hourly[h]), 2))
            else:
                lmp_24h.append(None)
        results[str(start_date)] = lmp_24h

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
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)


def main():
    pst = pytz.timezone('US/Pacific')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "lmp_data.json")

    if len(sys.argv) >= 3:
        start_date = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    elif len(sys.argv) == 2:
        start_date = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end_date = start_date
    else:
        start_date = datetime.date(2020, 1, 1)
        end_date = datetime.date(2025, 12, 31)

    total_days = (end_date - start_date).days + 1
    month_ranges = list(generate_month_ranges(start_date, end_date))

    print("=" * 60)
    print("CAISO Day-Ahead Market LMP - SP15 Trading Hub")
    print(f"Date range: {start_date} to {end_date} ({total_days} days)")
    print(f"Fetching in {len(month_ranges)} monthly chunks")
    print(f"Query: PRC_LMP (hourly), Node: {NODE}")
    print("=" * 60)

    # Load existing results if available (resume support)
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            all_results = json.load(f)
        print(f"Loaded {len(all_results)} existing days from {output_file}")
    else:
        all_results = {}

    for i, (m_start, m_end) in enumerate(month_ranges, 1):
        # Skip months where we already have all data
        days_in_range = (m_end - m_start).days + 1
        existing = sum(1 for d in range(days_in_range)
                       if str(m_start + datetime.timedelta(days=d)) in all_results
                       and any(v is not None for v in all_results.get(str(m_start + datetime.timedelta(days=d)), [])))
        if existing == days_in_range:
            print(f"[{i}/{len(month_ranges)}] {m_start} to {m_end} - already have {existing} days, skipping.")
            continue

        print(f"\n[{i}/{len(month_ranges)}] {m_start} to {m_end}")
        chunk = fetch_lmp_month(m_start, m_end)
        all_results.update(chunk)

        # Save incrementally
        with open(output_file, 'w') as f:
            json.dump(all_results, f)
        print(f"  Saved progress: {len(all_results)} total days.")

        # Delay between requests - be very conservative
        if i < len(month_ranges):
            time.sleep(8)

    # Final save with indent
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    valid_days = sum(1 for v in all_results.values() if any(x is not None for x in v))
    all_prices = []
    for date_data in all_results.values():
        all_prices.extend([p for p in date_data if p is not None])

    print(f"\n{'=' * 60}")
    print(f"Complete: {valid_days}/{total_days} days with data.")
    print(f"Saved to {output_file}")

    if all_prices:
        print(f"\nStatistics:")
        print(f"  Mean LMP: ${sum(all_prices)/len(all_prices):.2f}/MWh")
        print(f"  Min LMP: ${min(all_prices):.2f}/MWh")
        print(f"  Max LMP: ${max(all_prices):.2f}/MWh")
    print("=" * 60)

    if valid_days == 0:
        print("No LMP data retrieved. Exiting with error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
