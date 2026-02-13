"""
Fetch actual hourly LMP (Locational Marginal Price) data from CAISO OASIS API.
Fetches Real-Time Market prices for 2020-2025 (2,192 days).

CAISO OASIS API endpoint for LMP:
- Query: PRC_INTVL_LMP (5-minute interval LMP)
- Market: RTM (Real-Time Market) for actual prices
- Node: TH_SP15_GEN-APND (SP15 Trading Hub - most representative for CA system)

Output: lmp_data.json with hourly average LMP for each day
"""

import requests
import zipfile
import io
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz
import os
import sys
import time

# CAISO OASIS API configuration
BASE_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
QUERY_NAME = "PRC_INTVL_LMP"
MARKET = "RTM"  # Real-Time Market (actual prices)
# SP15 Trading Hub (Southern California - most liquid trading hub)
NODE = "TH_SP15_GEN-APND"

def fetch_lmp_for_day(date_str):
    """
    Fetch 5-minute interval LMP data for a single day and aggregate to hourly.
    date_str format: YYYY-MM-DD
    Returns: List of 24 hourly average LMP values, or None if error
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        next_day = date_obj + timedelta(days=1)

        # Format for CAISO API (Pacific Time)
        pst = pytz.timezone("America/Los_Angeles")
        start_dt = pst.localize(date_obj)
        end_dt = pst.localize(next_day)

        # API expects format: YYYYMMDDThh:mm-0800 (or -0700 for PDT)
        start_str = start_dt.strftime("%Y%m%dT%H:%M") + start_dt.strftime("%z")[:3] + ":" + start_dt.strftime("%z")[3:]
        end_str = end_dt.strftime("%Y%m%dT%H:%M") + end_dt.strftime("%z")[:3] + ":" + end_dt.strftime("%z")[3:]

        params = {
            "queryname": QUERY_NAME,
            "market_run_id": MARKET,
            "node": NODE,
            "startdatetime": start_str,
            "enddatetime": end_str,
            "version": "1",
            "resultformat": "6"  # CSV in ZIP
        }

        response = requests.get(BASE_URL, params=params, timeout=60)
        response.raise_for_status()

        # Extract CSV from ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                return None

            with z.open(csv_files[0]) as f:
                df = pd.read_csv(f)

        # CAISO LMP CSV columns typically include:
        # INTERVALSTARTTIME_GMT, INTERVALENDTIME_GMT, OPR_DT, OPR_HR, OPR_INTERVAL,
        # NODE_ID, NODE, LMP_TYPE, XML_DATA_ITEM, PNODE_RESMRID, MW (price value)

        # Filter for total LMP (not components)
        df = df[df['LMP_TYPE'] == 'LMP']

        # Parse timestamp and aggregate to hourly
        df['INTERVALSTARTTIME_GMT'] = pd.to_datetime(df['INTERVALSTARTTIME_GMT'])
        df_pst = df.copy()
        df_pst['INTERVALSTARTTIME_PST'] = df_pst['INTERVALSTARTTIME_GMT'].dt.tz_convert('America/Los_Angeles')
        df_pst['hour'] = df_pst['INTERVALSTARTTIME_PST'].dt.hour

        # Aggregate 5-minute intervals to hourly average
        hourly_lmp = df_pst.groupby('hour')['MW'].mean().to_dict()

        # Create 24-hour array (some hours might be missing)
        hourly_array = [round(hourly_lmp.get(h, None), 2) if h in hourly_lmp else None for h in range(24)]

        return hourly_array

    except Exception as e:
        print(f"    Error fetching {date_str}: {e}")
        return None


def fetch_lmp_range(start_date, end_date):
    """
    Fetch LMP data for a date range.
    Returns dict of {date_str: [24 hourly LMP values]}
    """
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    results = {}
    dates_to_fetch = []

    while current <= end:
        dates_to_fetch.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    total_days = len(dates_to_fetch)
    print(f"  Fetching {total_days} days from {start_date} to {end_date}...")

    for i, date_str in enumerate(dates_to_fetch, 1):
        lmp_data = fetch_lmp_for_day(date_str)
        if lmp_data:
            results[date_str] = lmp_data

        # Progress update every 10 days
        if i % 10 == 0 or i == total_days:
            print(f"    Progress: {i}/{total_days} days")

        # Rate limiting: 1 request per 2 seconds to be respectful
        time.sleep(2)

    print(f"  Got data for {len(results)}/{total_days} days.")
    return results


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "lmp_data.json")

    # Date range: 2020-01-01 to 2025-12-31
    start_date = "2020-01-01"
    end_date = "2025-12-31"

    print("=" * 60)
    print("CAISO Real-Time Market LMP - SP15 Trading Hub")
    print(f"Date range: {start_date} to {end_date} (2192 days)")
    print(f"Fetching hourly average LMP from 5-minute intervals")
    print("=" * 60)
    print()

    # Fetch in monthly chunks to manage API load
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    all_data = {}
    chunk_num = 0

    # Calculate total months
    months = []
    temp = current
    while temp <= end:
        months.append((temp.year, temp.month))
        # Move to next month
        if temp.month == 12:
            temp = datetime(temp.year + 1, 1, 1)
        else:
            temp = datetime(temp.year, temp.month + 1, 1)

    total_months = len(months)

    for year, month in months:
        chunk_num += 1

        # Get first and last day of month
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(days=1)

        # Don't exceed end_date
        if month_end > end:
            month_end = end

        chunk_start_str = month_start.strftime("%Y-%m-%d")
        chunk_end_str = month_end.strftime("%Y-%m-%d")

        print(f"[{chunk_num}/{total_months}] {chunk_start_str} to {chunk_end_str}")

        chunk_data = fetch_lmp_range(chunk_start_str, chunk_end_str)
        all_data.update(chunk_data)

        # Save progress after each month
        with open(output_file, "w") as f:
            json.dump(all_data, f, indent=2)
        print(f"  Saved progress: {len(all_data)} total days.")
        print()

    print("=" * 60)
    print(f"Complete: {len(all_data)}/{2192} days with data.")
    print(f"Saved to {output_file}")
    print("=" * 60)

    # Print sample statistics
    all_prices = []
    for date_data in all_data.values():
        all_prices.extend([p for p in date_data if p is not None])

    if all_prices:
        print(f"\nSample statistics:")
        print(f"  Mean LMP: ${sum(all_prices)/len(all_prices):.2f}/MWh")
        print(f"  Min LMP: ${min(all_prices):.2f}/MWh")
        print(f"  Max LMP: ${max(all_prices):.2f}/MWh")


if __name__ == "__main__":
    main()
