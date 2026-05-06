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
import statistics

# Configuration
# Major Load Aggregation Points (LAPs) that represent the system average
NODES = ['DLAP_PGAE-APND', 'DLAP_SCE-APND', 'DLAP_SDGE-APND']
OUTPUT_FILE = "caiso_prices.json"
BASE_URL = "https://oasis.caiso.com/oasisapi/SingleZip"

def fetch_price_range(start_date, end_date, node, max_retries=3):
    """
    Fetch RTM interval LMP prices for a specific node and date range.
    Using Report: PRC_INTVL_LMP (5-minute intervals, averaged to hourly).
    Note: PRC_RTM_LAPAP was deprecated by CAISO circa April 2026.
    """
    # Format: YYYYMMDDTHH:MM-HHMM
    start_str = start_date.strftime('%Y%m%d') + 'T00:00-0000'
    end_str = end_date.strftime('%Y%m%d') + 'T23:59-0000'

    print(f"    Fetching {node} from {start_date} to {end_date} ...")

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
            response = requests.get(BASE_URL, params=params, timeout=180)
            if response.status_code == 429:
                wait = 15 * attempt
                print(f"      Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()

            try:
                z = zipfile.ZipFile(io.BytesIO(response.content))

                # Check for error response inside ZIP
                if 'INVALID_REQUEST.xml' in z.namelist():
                    content = z.read('INVALID_REQUEST.xml').decode('utf-8')
                    if 'No data returned' in content:
                        print(f"      No data returned for {node}.")
                        return pd.DataFrame()
                    print(f"      API error: {content[:200]}")
                    return None

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

            except zipfile.BadZipFile:
                print("      Invalid ZIP response.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"      Request error: {e}. Retrying...")
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

def main():
    # Only fetch recent months for daily updates.
    # Pre-2023 hourly data already exists from the old PRC_RTM_LAPAP API.
    # PRC_INTVL_LMP (current API) only has data from 2023 onwards.
    # Look back 3 months to catch any gaps.
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    start_date = (end_date.replace(day=1) - datetime.timedelta(days=90)).replace(day=1)
    
    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                existing_data = json.load(f)
            print(f"Loaded {len(existing_data)} days of existing price data.")
        except json.JSONDecodeError:
            print("Corrupt JSON file. Starting fresh.")
    
    # Remove last 3 days from existing data to force re-fetch
    # (CAISO may not have published all hours when we last ran)
    for days_back in range(1, 4):
        stale_date = (end_date - datetime.timedelta(days=days_back - 1)).strftime('%Y-%m-%d')
        if stale_date in existing_data:
            del existing_data[stale_date]
            print(f"Cleared stale data for {stale_date} (will re-fetch)")

    month_ranges = list(generate_month_ranges(start_date, end_date))

    for i, (m_start, m_end) in enumerate(month_ranges, 1):
        # Check if we have all days in this month
        days_in_month = (m_end - m_start).days + 1
        days_present = 0
        current_check = m_start
        while current_check <= m_end:
            if current_check.strftime('%Y-%m-%d') in existing_data:
                days_present += 1
            current_check += datetime.timedelta(days=1)

        if days_present == days_in_month:
             print(f"[{i}/{len(month_ranges)}] {m_start} to {m_end} - Already have all days. Skipping.")
             continue
        
        print(f"[{i}/{len(month_ranges)}] Processing {m_start} to {m_end}...")
        
        node_dfs = []
        for node in NODES:
            df = fetch_price_range(m_start, m_end, node)
            if df is not None and not df.empty:
                # Standardize
                if 'OPR_DT' in df.columns:
                    df['OPR_DT'] = pd.to_datetime(df['OPR_DT'])
                node_dfs.append(df)
            
            # Sleep between nodes to be polite
            time.sleep(3)
            
        if not node_dfs:
            print(f"  No data for this month from any node.")
            continue
            
        # Combine all nodes
        full_df = pd.concat(node_dfs, ignore_index=True)
        
        # Filter Components
        # PRC_INTVL_LMP items: LMP_PRC, LMP_ENE_PRC, LMP_CONG_PRC, LMP_LOSS_PRC
        # (Old PRC_RTM_LAPAP used: LMP_PRC, LMP_ENE, LMP_CONG, LMP_LOSS, LMP_GHG)
        comp_map = {
            'LMP_PRC': 'LMP',
            'LMP_ENE_PRC': 'MEC',
            'LMP_CONG_PRC': 'MCC',
            'LMP_LOSS_PRC': 'Loss',
            # Legacy names (for existing data downloaded before API change)
            'LMP_ENE': 'MEC',
            'LMP_CONG': 'MCC',
            'LMP_LOSS': 'Loss',
            'LMP_GHG': 'GHG',
        }

        # Build active map from items actually present in the data
        unique_items = full_df['XML_DATA_ITEM'].unique()
        active_map = {item: comp_map[item] for item in unique_items if item in comp_map}

        full_df = full_df[full_df['XML_DATA_ITEM'].isin(active_map.keys())]
        
        value_col = 'MW' if 'MW' in full_df.columns else 'VALUE'
        
        # Average across nodes (Group by Date, Hour, Component)
        # OPR_DT, OPR_HR, XML_DATA_ITEM -> mean(MW)
        avg_df = full_df.groupby(['OPR_DT', 'OPR_HR', 'XML_DATA_ITEM'])[value_col].mean().reset_index()
        
        # Transform to JSON
        current_day = m_start
        while current_day <= m_end:
            day_str = current_day.strftime('%Y-%m-%d')
            day_ts = pd.Timestamp(current_day)
            
            day_data_df = avg_df[avg_df['OPR_DT'] == day_ts]
            
            if day_data_df.empty:
                current_day += datetime.timedelta(days=1)
                continue
                
            day_dict = {}
            # Hourly 1-24
            for h in range(1, 25):
                h_df = day_data_df[day_data_df['OPR_HR'] == h]
                if h_df.empty:
                    pass
                
                h_dict = {}
                for idx, row in h_df.iterrows():
                    comp_code = row['XML_DATA_ITEM']
                    val = row[value_col]
                    if comp_code in active_map:
                        mapped_code = active_map[comp_code]
                        h_dict[mapped_code] = round(val, 2)
                
                day_dict[str(h)] = h_dict
            
            existing_data[day_str] = day_dict
            current_day += datetime.timedelta(days=1)
            
        # Save after month
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(existing_data, f)
        
        print(f"  Saved month. Total days: {len(existing_data)}")
        time.sleep(5)

    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(existing_data, f, indent=2)

if __name__ == "__main__":
    main()
