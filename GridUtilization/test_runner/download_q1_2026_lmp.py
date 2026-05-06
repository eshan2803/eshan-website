"""
Download DAM LMP prices for Q1 2026 from OASIS and append to caiso_prices.json.
Uses PRC_LMP DAM with node filter (fast: ~2K rows per query instead of millions).
"""
import requests
import zipfile
import io
import pandas as pd
import json
import datetime
import time
import calendar
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
OASIS_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
NODES = ['DLAP_PGAE-APND', 'DLAP_SCE-APND', 'DLAP_SDGE-APND']
OUTPUT_FILE = os.path.join(script_dir, "caiso_prices.json")

START_DATE = datetime.date(2026, 1, 1)
END_DATE = datetime.date(2026, 3, 31)

COMP_MAP = {
    'LMP_PRC': 'LMP',
    'LMP_ENE': 'MEC',
    'LMP_CONG': 'MCC',
    'LMP_LOSS': 'Loss',
    'LMP_GHG': 'GHG'
}


def fetch_node_range(start_date, end_date, node, max_retries=3):
    start_str = start_date.strftime('%Y%m%d') + 'T08:00-0000'
    next_day = end_date + datetime.timedelta(days=1)
    end_str = next_day.strftime('%Y%m%d') + 'T08:00-0000'

    params = {
        "queryname": "PRC_LMP",
        "startdatetime": start_str,
        "enddatetime": end_str,
        "market_run_id": "DAM",
        "version": "1",
        "node": node,
        "resultformat": "6"
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(OASIS_URL, params=params, timeout=180)

            if response.status_code == 429:
                wait = 20 * attempt
                print(f"rate limited, waiting {wait}s...", end=" ", flush=True)
                time.sleep(wait)
                continue

            if b"<?xml" in response.content[:100]:
                if b"No data returned" in response.content:
                    return pd.DataFrame()
                if b"INVALID_REQUEST" in response.content:
                    return None
                return None

            response.raise_for_status()

            z = zipfile.ZipFile(io.BytesIO(response.content))
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                return None

            dfs = []
            for f in csv_files:
                with z.open(f) as csv_file:
                    dfs.append(pd.read_csv(csv_file))

            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return None

        except (requests.exceptions.RequestException, zipfile.BadZipFile) as e:
            if attempt == max_retries:
                print(f"error", end=" ", flush=True)
                return None
            time.sleep(10 * attempt)

    return None


def generate_month_ranges(start_date, end_date):
    current = start_date.replace(day=1)
    while current <= end_date:
        m_start = max(current, start_date)
        last_day = calendar.monthrange(current.year, current.month)[1]
        m_end = min(datetime.date(current.year, current.month, last_day), end_date)
        yield m_start, m_end
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)


def main():
    print(f"Downloading DAM LMP prices for Q1 2026: {START_DATE} to {END_DATE}")

    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            existing_data = json.load(f)
        print(f"Loaded {len(existing_data)} existing days\n")

    months = list(generate_month_ranges(START_DATE, END_DATE))

    for m_start, m_end in months:
        days_in_month = (m_end - m_start).days + 1
        days_present = sum(
            1 for d in range(days_in_month)
            if (m_start + datetime.timedelta(days=d)).strftime('%Y-%m-%d') in existing_data
        )
        if days_present == days_in_month:
            print(f"{m_start} to {m_end}: Already complete. Skipping.")
            continue

        print(f"{m_start} to {m_end} ({days_present}/{days_in_month} present):")

        node_dfs = []
        for node in NODES:
            print(f"  {node}...", end=" ", flush=True)
            df = fetch_node_range(m_start, m_end, node)
            if df is not None and not df.empty:
                if 'OPR_DT' in df.columns:
                    df['OPR_DT'] = pd.to_datetime(df['OPR_DT'])
                node_dfs.append(df)
                print(f"{len(df):,} rows", flush=True)
            else:
                print("no data", flush=True)
            time.sleep(5)

        if not node_dfs:
            print("  No data for this month.")
            time.sleep(10)
            continue

        full_df = pd.concat(node_dfs, ignore_index=True)

        # Map XML_DATA_ITEM
        active_map = {}
        for item in full_df['XML_DATA_ITEM'].unique():
            for key, val in COMP_MAP.items():
                if key in item:
                    active_map[item] = val

        full_df = full_df[full_df['XML_DATA_ITEM'].isin(active_map.keys())]
        value_col = 'MW' if 'MW' in full_df.columns else 'VALUE'

        # Average across nodes
        avg_df = full_df.groupby(['OPR_DT', 'OPR_HR', 'XML_DATA_ITEM'])[value_col].mean().reset_index()

        # Parse each day
        added = 0
        for opr_dt in sorted(avg_df['OPR_DT'].unique()):
            opr_str = pd.Timestamp(opr_dt).strftime('%Y-%m-%d')
            if opr_str in existing_data:
                continue

            day_data = avg_df[avg_df['OPR_DT'] == opr_dt]
            day_dict = {}
            for h in range(1, 25):
                h_df = day_data[day_data['OPR_HR'] == h]
                h_dict = {}
                for _, row in h_df.iterrows():
                    comp_code = row['XML_DATA_ITEM']
                    if comp_code in active_map:
                        h_dict[active_map[comp_code]] = round(row[value_col], 2)
                if h_dict:
                    day_dict[str(h)] = h_dict

            if day_dict:
                existing_data[opr_str] = day_dict
                added += 1

        # Save after month
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(existing_data, f)
        print(f"  Added {added} days. Total: {len(existing_data)}")
        time.sleep(10)

    # Final save with formatting
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(existing_data, f, indent=2)

    dates_2026 = sorted([d for d in existing_data if d.startswith('2026')])
    print(f"\nDone. Total: {len(existing_data)} days. 2026: {len(dates_2026)} days")
    if dates_2026:
        print(f"  Range: {dates_2026[0]} to {dates_2026[-1]}")


if __name__ == "__main__":
    main()
