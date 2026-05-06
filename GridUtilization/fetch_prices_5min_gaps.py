"""
Fill gaps in caiso_prices_5min.json. Targets only months with missing data.
Uses longer delays (10s between nodes, 15s between months) to avoid rate limiting.
"""
import builtins
import requests
import zipfile
import io
import pandas as pd
import json
import datetime
import time
import calendar
import os

_orig_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _orig_print(*args, **kwargs)

NODES = {
    'DLAP_PGAE-APND': 0.40,
    'DLAP_SCE-APND':  0.40,
    'DLAP_SDGE-APND': 0.20,
}

OUTPUT_FILE = "caiso_prices_5min.json"
BASE_URL = "https://oasis.caiso.com/oasisapi/SingleZip"

COMP_MAP = {
    'LMP_PRC': 'LMP',
    'LMP_ENE_PRC': 'MEC',
    'LMP_CONG_PRC': 'MCC',
    'LMP_LOSS_PRC': 'Loss',
    'LMP_ENE': 'MEC',
    'LMP_CONG': 'MCC',
    'LMP_LOSS': 'Loss',
}

# Months that need filling (from gap analysis)
GAP_MONTHS = [
    (2023, 5), (2023, 7), (2023, 8), (2023, 10), (2023, 12),
    (2024, 1), (2024, 5), (2024, 7), (2024, 8), (2024, 9),
    (2024, 10), (2024, 12),
    (2025, 1), (2025, 5), (2025, 7), (2025, 8), (2025, 10), (2025, 12),
    (2026, 1), (2026, 4),
]


def fetch_node(start_date, end_date, node, max_retries=5):
    start_str = start_date.strftime('%Y%m%d') + 'T00:00-0000'
    end_str = end_date.strftime('%Y%m%d') + 'T23:59-0000'

    params = {
        "queryname": "PRC_INTVL_LMP",
        "startdatetime": start_str,
        "enddatetime": end_str,
        "market_run_id": "RTM",
        "version": "1",
        "node": node,
        "resultformat": "6"
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=180)
            if resp.status_code == 429:
                wait = 20 * attempt
                print(f"      Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(resp.content))

            if 'INVALID_REQUEST.xml' in z.namelist():
                content = z.read('INVALID_REQUEST.xml').decode('utf-8')
                if 'No data returned' in content:
                    return pd.DataFrame()
                print(f"      API error for {node}")
                if attempt < max_retries:
                    time.sleep(15 * attempt)
                    continue
                return None

            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                # XML-only response = rate limit in disguise
                xml_files = [f for f in z.namelist() if f.endswith('.xml')]
                if xml_files and attempt < max_retries:
                    wait = 30 * attempt
                    print(f"      Got XML instead of CSV, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return None

            dfs = [pd.read_csv(z.open(f)) for f in csv_files]
            return pd.concat(dfs, ignore_index=True) if dfs else None

        except zipfile.BadZipFile:
            print(f"      Bad ZIP, retrying...")
            time.sleep(10 * attempt)
            if attempt == max_retries:
                return None
        except requests.exceptions.RequestException as e:
            print(f"      Request error: {e}. Retry {attempt}...")
            time.sleep(10 * attempt)

    return None


def process_month_data(node_dfs):
    weighted_dfs = []
    for node, df in node_dfs.items():
        if df is None or df.empty:
            continue
        weight = NODES[node]
        df = df.copy()
        value_col = 'MW' if 'MW' in df.columns else 'VALUE'
        df['weighted_val'] = df[value_col] * weight
        weighted_dfs.append(df)

    if not weighted_dfs:
        return {}

    full = pd.concat(weighted_dfs, ignore_index=True)
    active_items = {item: COMP_MAP[item] for item in full['XML_DATA_ITEM'].unique() if item in COMP_MAP}
    full = full[full['XML_DATA_ITEM'].isin(active_items.keys())].copy()
    full['comp'] = full['XML_DATA_ITEM'].map(active_items)
    full['OPR_DT'] = pd.to_datetime(full['OPR_DT']).dt.strftime('%Y-%m-%d')
    if 'OPR_INTERVAL' not in full.columns:
        full['OPR_INTERVAL'] = 1

    full['time_str'] = (full['OPR_HR'] - 1).astype(str) + ':' + ((full['OPR_INTERVAL'] - 1) * 5).astype(int).apply(lambda m: f'{m:02d}')
    agg = full.groupby(['OPR_DT', 'time_str', 'comp'])['weighted_val'].sum().reset_index()
    agg['weighted_val'] = agg['weighted_val'].round(2)

    results = {}
    for date_str, date_group in agg.groupby('OPR_DT'):
        day_dict = {}
        for _, row in date_group.iterrows():
            ts = row['time_str']
            if ts not in day_dict:
                day_dict[ts] = {}
            day_dict[ts][row['comp']] = row['weighted_val']
        results[date_str] = day_dict

    return results


def main():
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing days.")

    for idx, (year, month) in enumerate(GAP_MONTHS, 1):
        last_day = calendar.monthrange(year, month)[1]
        m_start = datetime.date(year, month, 1)
        m_end = min(datetime.date(year, month, last_day),
                    datetime.date.today() - datetime.timedelta(days=1))

        if m_end < m_start:
            continue

        print(f"\n[{idx}/{len(GAP_MONTHS)}] {m_start} to {m_end}...")

        node_dfs = {}
        for node in NODES:
            print(f"    Fetching {node}...")
            df = fetch_node(m_start, m_end, node)
            if df is not None and not df.empty:
                node_dfs[node] = df
                print(f"      Got {len(df)} rows")
            else:
                print(f"      No data")
            time.sleep(10)  # Longer delay between nodes

        if not node_dfs:
            print(f"  No data for this month.")
            time.sleep(15)
            continue

        month_results = process_month_data(node_dfs)
        existing.update(month_results)

        with open(OUTPUT_FILE, 'w') as f:
            json.dump(existing, f)
        print(f"  Saved. Total days: {len(existing)}")
        time.sleep(15)  # Longer delay between months

    print(f"\nDone. {len(existing)} days total.")
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
