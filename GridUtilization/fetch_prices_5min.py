"""
Download 5-minute interval LMP prices from CAISO (PRC_INTVL_LMP) for all 3 DLAPs.
Computes load-weighted California average (PG&E 40%, SCE 40%, SDG&E 20%).
Saves to caiso_prices_5min.json incrementally, month by month.

Structure: { "2020-01-01": { "0:00": {"LMP":..,"MCC":..,"MEC":..,"Loss":..}, "0:05": {...}, ... }, ... }
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

# Force unbuffered output
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
    # Legacy names
    'LMP_ENE': 'MEC',
    'LMP_CONG': 'MCC',
    'LMP_LOSS': 'Loss',
}


def fetch_node(start_date, end_date, node, max_retries=3):
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
                wait = 15 * attempt
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
                return None

            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                return None

            dfs = [pd.read_csv(z.open(f)) for f in csv_files]
            return pd.concat(dfs, ignore_index=True) if dfs else None

        except zipfile.BadZipFile:
            print(f"      Bad ZIP from {node}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"      Request error: {e}. Retry {attempt}...")
            time.sleep(5 * attempt)

    return None


def generate_month_ranges(start_date, end_date):
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


def interval_to_time(opr_hr, opr_interval):
    """Convert OPR_HR (1-24) and OPR_INTERVAL (1-12) to time string like '0:00', '14:35'."""
    hour = opr_hr - 1
    minute = (opr_interval - 1) * 5
    return f"{hour}:{minute:02d}"


def process_month_data(node_dfs):
    """Process raw DataFrames from all nodes into load-weighted 5-min prices.
    Uses vectorized pandas operations for speed."""

    # Combine all node DataFrames with weights
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

    # Map component names
    active_items = {item: COMP_MAP[item] for item in full['XML_DATA_ITEM'].unique() if item in COMP_MAP}
    full = full[full['XML_DATA_ITEM'].isin(active_items.keys())].copy()
    full['comp'] = full['XML_DATA_ITEM'].map(active_items)

    # Ensure OPR_DT is string
    full['OPR_DT'] = pd.to_datetime(full['OPR_DT']).dt.strftime('%Y-%m-%d')

    # Ensure OPR_INTERVAL exists
    if 'OPR_INTERVAL' not in full.columns:
        full['OPR_INTERVAL'] = 1

    # Build time strings vectorized
    full['time_str'] = (full['OPR_HR'] - 1).astype(str) + ':' + ((full['OPR_INTERVAL'] - 1) * 5).astype(int).apply(lambda m: f'{m:02d}')

    # Sum weighted values across nodes (groupby date, time, component)
    agg = full.groupby(['OPR_DT', 'time_str', 'comp'])['weighted_val'].sum().reset_index()
    agg['weighted_val'] = agg['weighted_val'].round(2)

    # Pivot to nested dict
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
    import sys
    end_date = datetime.date.today() - datetime.timedelta(days=1)

    # --recent mode: only fetch last ~2 months (for daily pipeline use)
    if '--recent' in sys.argv:
        start_date = (end_date.replace(day=1) - datetime.timedelta(days=45)).replace(day=1)
        print(f"Recent mode: fetching {start_date} to {end_date}")
    else:
        # Full mode: PRC_INTVL_LMP 5-min data only available from Jan 2023 onwards
        start_date = datetime.date(2023, 1, 1)

    existing = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                existing = json.load(f)
            print(f"Loaded {len(existing)} existing days.")
        except json.JSONDecodeError:
            print("Corrupt JSON. Starting fresh.")

    # Clear last 3 days to force re-fetch (CAISO may publish late)
    if '--recent' in sys.argv:
        for days_back in range(0, 3):
            stale = (end_date - datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
            if stale in existing:
                del existing[stale]
                print(f"Cleared stale data for {stale}")

    # Find all missing days
    missing_days = []
    current_check = start_date
    while current_check <= end_date:
        day_str = current_check.strftime('%Y-%m-%d')
        day_data = existing.get(day_str, {})
        if len(day_data) < 280:
            missing_days.append(current_check)
        current_check += datetime.timedelta(days=1)

    if not missing_days:
        print("All days complete. Nothing to fetch.")
    else:
        print(f"Found {len(missing_days)} missing days. Fetching in 7-day chunks...")

        # Group missing days into contiguous chunks of up to 7 days
        CHUNK_SIZE = 7
        chunks = []
        i = 0
        while i < len(missing_days):
            chunk_start = missing_days[i]
            chunk_end = chunk_start
            # Extend chunk with consecutive days up to CHUNK_SIZE
            while (i + 1 < len(missing_days) and
                   missing_days[i + 1] - missing_days[i] <= datetime.timedelta(days=1) and
                   (missing_days[i + 1] - chunk_start).days < CHUNK_SIZE):
                i += 1
                chunk_end = missing_days[i]
            chunks.append((chunk_start, chunk_end))
            i += 1

        print(f"  Grouped into {len(chunks)} chunks")

        for ci, (c_start, c_end) in enumerate(chunks, 1):
            n_days = (c_end - c_start).days + 1
            print(f"[{ci}/{len(chunks)}] {c_start} to {c_end} ({n_days} days)...")

            node_dfs = {}
            for node in NODES:
                print(f"    Fetching {node}...")
                df = fetch_node(c_start, c_end, node)
                if df is not None and not df.empty:
                    node_dfs[node] = df
                time.sleep(5)

            if not node_dfs:
                print(f"  No data for this chunk.")
                continue

            chunk_results = process_month_data(node_dfs)
            existing.update(chunk_results)

            # Save after each chunk
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(existing, f)
            print(f"  Saved. Total days: {len(existing)}")
            time.sleep(3)

    # Final save with indentation
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(existing, f)

    print(f"\nDone. {len(existing)} days in {OUTPUT_FILE}")
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
