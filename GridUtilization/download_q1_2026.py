"""
Download all data for Q1 2026 (Jan 1 - Mar 31, 2026):
1. CAISO supply data (fuelsource CSVs)
2. LMP prices (OASIS API)
3. Ancillary service prices (OASIS API)
"""
import os
import time
import datetime
import requests
import zipfile
import io
import json
import calendar
import pandas as pd
from pathlib import Path

script_dir = os.path.dirname(os.path.abspath(__file__))

START_DATE = datetime.date(2026, 1, 1)
END_DATE = datetime.date(2026, 3, 31)

# ═══════════════════════════════════════════════════════════════════
# 1. Download CAISO supply CSVs
# ═══════════════════════════════════════════════════════════════════
SUPPLY_DIR = os.path.join(script_dir, "caiso_supply")
SUPPLY_BASE_URL = "https://www.caiso.com/outlook/SP/history"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv,application/csv,text/plain",
    "Referer": "https://www.caiso.com/todays-outlook/supply"
}

def download_supply():
    print("=" * 60)
    print("STEP 1: Downloading CAISO supply data (fuelsource CSVs)")
    print("=" * 60)

    current = START_DATE
    downloaded = 0
    skipped = 0
    failed = 0

    while current <= END_DATE:
        date_str = current.strftime("%Y%m%d")
        save_path = os.path.join(SUPPLY_DIR, f"{date_str}_fuelsource.csv")

        if os.path.exists(save_path):
            skipped += 1
            current += datetime.timedelta(days=1)
            continue

        url = f"{SUPPLY_BASE_URL}/{date_str}_fuelsource.csv"

        for attempt in range(1, 4):
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)

                if r.status_code == 429:
                    wait = 10 * attempt
                    print(f"  Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if r.status_code == 404:
                    print(f"  {date_str}: 404 Not Found")
                    failed += 1
                    break

                r.raise_for_status()

                if len(r.content) < 50:
                    print(f"  {date_str}: Empty response")
                    failed += 1
                    break

                with open(save_path, "wb") as f:
                    f.write(r.content)
                downloaded += 1
                print(f"  {date_str}: OK ({len(r.content):,} bytes)")
                break

            except requests.exceptions.RequestException as e:
                if attempt == 3:
                    print(f"  {date_str}: Error - {str(e)[:50]}")
                    failed += 1
                time.sleep(3 * attempt)

        time.sleep(0.5)  # Be polite
        current += datetime.timedelta(days=1)

    print(f"\nSupply data: {downloaded} downloaded, {skipped} skipped, {failed} failed")


# ═══════════════════════════════════════════════════════════════════
# 2. Download LMP prices
# ═══════════════════════════════════════════════════════════════════
OASIS_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
NODES = ['DLAP_PGAE-APND', 'DLAP_SCE-APND', 'DLAP_SDGE-APND']
PRICES_FILE = os.path.join(script_dir, "caiso_prices.json")

def fetch_price_range(start_date, end_date, node, max_retries=3):
    start_str = start_date.strftime('%Y%m%d') + 'T00:00-0000'
    end_str = end_date.strftime('%Y%m%d') + 'T23:59-0000'

    params = {
        "queryname": "PRC_RTM_LAPAP",
        "startdatetime": start_str,
        "enddatetime": end_str,
        "market_run_id": "RTM",
        "version": "1",
        "node": node,
        "resultformat": "6"
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(OASIS_URL, params=params, timeout=180)

            if response.status_code == 429:
                wait = 15 * attempt
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            if b"<?xml" in response.content[:100]:
                if b"No data returned" in response.content:
                    print(f"    No data returned for {node}.")
                    return pd.DataFrame()
                print(f"    API error for {node}")
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
                print(f"    Error: {str(e)[:50]}")
                return None
            time.sleep(5 * attempt)

    return None

def download_prices():
    print("\n" + "=" * 60)
    print("STEP 2: Downloading LMP price data")
    print("=" * 60)

    existing_data = {}
    if os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, 'r') as f:
            existing_data = json.load(f)
        print(f"Loaded {len(existing_data)} existing days")

    # Generate month ranges
    months = []
    current = START_DATE.replace(day=1)
    while current <= END_DATE:
        m_start = max(current, START_DATE)
        last_day = calendar.monthrange(current.year, current.month)[1]
        m_end = min(datetime.date(current.year, current.month, last_day), END_DATE)
        months.append((m_start, m_end))
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)

    comp_map = {
        'LMP_PRC': 'LMP',
        'LMP_ENE': 'MEC',
        'LMP_CONG': 'MCC',
        'LMP_LOSS': 'Loss',
        'LMP_GHG': 'GHG'
    }

    for i, (m_start, m_end) in enumerate(months, 1):
        days_in_month = (m_end - m_start).days + 1
        days_present = sum(
            1 for d in range(days_in_month)
            if (m_start + datetime.timedelta(days=d)).strftime('%Y-%m-%d') in existing_data
        )

        if days_present == days_in_month:
            print(f"  [{i}/{len(months)}] {m_start} to {m_end} - Already complete. Skipping.")
            continue

        print(f"  [{i}/{len(months)}] Processing {m_start} to {m_end}...")

        node_dfs = []
        for node in NODES:
            print(f"    Fetching {node}...")
            df = fetch_price_range(m_start, m_end, node)
            if df is not None and not df.empty:
                if 'OPR_DT' in df.columns:
                    df['OPR_DT'] = pd.to_datetime(df['OPR_DT'])
                node_dfs.append(df)
            time.sleep(3)

        if not node_dfs:
            print(f"  No price data for this month.")
            continue

        full_df = pd.concat(node_dfs, ignore_index=True)

        # Map data items
        active_map = {}
        unique_items = full_df['XML_DATA_ITEM'].unique()
        for item in unique_items:
            for key, val in comp_map.items():
                if key in item:
                    active_map[item] = val

        full_df = full_df[full_df['XML_DATA_ITEM'].isin(active_map.keys())]
        value_col = 'MW' if 'MW' in full_df.columns else 'VALUE'

        avg_df = full_df.groupby(['OPR_DT', 'OPR_HR', 'XML_DATA_ITEM'])[value_col].mean().reset_index()

        current_day = m_start
        while current_day <= m_end:
            day_str = current_day.strftime('%Y-%m-%d')
            day_ts = pd.Timestamp(current_day)
            day_data_df = avg_df[avg_df['OPR_DT'] == day_ts]

            if not day_data_df.empty:
                day_dict = {}
                for h in range(1, 25):
                    h_df = day_data_df[day_data_df['OPR_HR'] == h]
                    h_dict = {}
                    for _, row in h_df.iterrows():
                        comp_code = row['XML_DATA_ITEM']
                        if comp_code in active_map:
                            h_dict[active_map[comp_code]] = round(row[value_col], 2)
                    day_dict[str(h)] = h_dict
                existing_data[day_str] = day_dict

            current_day += datetime.timedelta(days=1)

        with open(PRICES_FILE, 'w') as f:
            json.dump(existing_data, f)
        print(f"  Saved. Total days: {len(existing_data)}")
        time.sleep(5)

    # Final save
    with open(PRICES_FILE, 'w') as f:
        json.dump(existing_data, f, indent=2)
    print(f"LMP prices done. Total: {len(existing_data)} days")


# ═══════════════════════════════════════════════════════════════════
# 3. Download Ancillary Service prices
# ═══════════════════════════════════════════════════════════════════
AS_FILE = os.path.join(script_dir, "ancillary_services.json")
AS_REGION = "AS_CAISO_EXP"
AS_TYPES = {"RU", "RD", "RMU", "RMD", "SR", "NR"}

def fetch_as_range(start_date, end_date, max_retries=3):
    start_str = start_date.strftime("%Y%m%d") + "T00:00-0800"
    end_str = end_date.strftime("%Y%m%d") + "T23:59-0800"

    params = {
        "queryname": "PRC_AS",
        "startdatetime": start_str,
        "enddatetime": end_str,
        "market_run_id": "DAM",
        "anc_type": "ALL",
        "anc_region": AS_REGION,
        "version": "1",
        "resultformat": "6",
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(OASIS_URL, params=params, timeout=180)

            if response.status_code == 429:
                wait = 15 * attempt
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            if b"<?xml" in response.content[:100]:
                if b"No data returned" in response.content:
                    print(f"    No AS data returned.")
                    return pd.DataFrame()
                return None

            response.raise_for_status()

            z = zipfile.ZipFile(io.BytesIO(response.content))
            csv_files = [f for f in z.namelist() if f.endswith(".csv")]
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
                print(f"    Error: {str(e)[:50]}")
                return None
            time.sleep(5 * attempt)

    return None

def download_as_prices():
    print("\n" + "=" * 60)
    print("STEP 3: Downloading Ancillary Services data")
    print("=" * 60)

    existing_data = {}
    if os.path.exists(AS_FILE):
        with open(AS_FILE, "r") as f:
            existing_data = json.load(f)
        print(f"Loaded {len(existing_data)} existing days")

    # Generate month ranges
    months = []
    current = START_DATE.replace(day=1)
    while current <= END_DATE:
        m_start = max(current, START_DATE)
        last_day = calendar.monthrange(current.year, current.month)[1]
        m_end = min(datetime.date(current.year, current.month, last_day), END_DATE)
        months.append((m_start, m_end))
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)

    for i, (m_start, m_end) in enumerate(months, 1):
        days_in_month = (m_end - m_start).days + 1
        days_present = sum(
            1 for d in range(days_in_month)
            if (m_start + datetime.timedelta(days=d)).strftime("%Y-%m-%d") in existing_data
        )

        if days_present == days_in_month:
            print(f"  [{i}/{len(months)}] {m_start} to {m_end} - Already complete. Skipping.")
            continue

        print(f"  [{i}/{len(months)}] Processing {m_start} to {m_end}...")

        df = fetch_as_range(m_start, m_end)
        if df is None or df.empty:
            print(f"  No AS data for this month.")
            time.sleep(5)
            continue

        if "OPR_DT" in df.columns:
            df["OPR_DT"] = pd.to_datetime(df["OPR_DT"])

        value_col = "MW" if "MW" in df.columns else "VALUE"

        current_day = m_start
        while current_day <= m_end:
            day_str = current_day.strftime("%Y-%m-%d")
            day_ts = pd.Timestamp(current_day)
            day_df = df[df["OPR_DT"] == day_ts]

            if not day_df.empty:
                day_dict = {}
                for h in range(1, 25):
                    h_df = day_df[day_df["OPR_HR"] == h]
                    if h_df.empty:
                        continue
                    h_dict = {}
                    for _, row in h_df.iterrows():
                        anc_type = row.get("ANC_TYPE", "")
                        if anc_type in AS_TYPES:
                            h_dict[anc_type] = round(float(row[value_col]), 2)
                    if h_dict:
                        day_dict[str(h)] = h_dict
                if day_dict:
                    existing_data[day_str] = day_dict

            current_day += datetime.timedelta(days=1)

        with open(AS_FILE, "w") as f:
            json.dump(existing_data, f)
        print(f"  Saved. Total days: {len(existing_data)}")
        time.sleep(5)

    with open(AS_FILE, "w") as f:
        json.dump(existing_data, f, indent=2)
    print(f"AS prices done. Total: {len(existing_data)} days")


# ═══════════════════════════════════════════════════════════════════
# Run all downloads
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"Downloading data for Q1 2026: {START_DATE} to {END_DATE}")
    print()
    download_supply()
    download_prices()
    download_as_prices()
    print("\n" + "=" * 60)
    print("ALL DOWNLOADS COMPLETE")
    print("=" * 60)
