import os
import zipfile
import pandas as pd
import json
import numpy as np

# Configuration
DOWNLOAD_DIR = "caiso_downloads"
OUTPUT_FILE = "caiso_prices.json"
MIN_FILE_SIZE = 2000  # Bytes

# Price Component Mapping
# Actual DATA_ITEM values in the CSV have _PRC suffix
COMPONENT_MAP = {
    'LMP_PRC': 'LMP',
    'LMP_ENE_PRC': 'MEC',
    'LMP_CONG_PRC': 'MCC',
    'LMP_LOSS_PRC': 'Loss',
    'LMP_GHG_PRC': 'GHG'
}

# California Demand LAPs and approximate load shares
# Source: CAISO annual reports — PG&E ~40%, SCE ~40%, SDG&E ~12%
# VEA excluded (tiny, Nevada-based)
DLAP_WEIGHTS = {
    'DLAP_PGAE-APND': 0.435,
    'DLAP_SCE-APND':  0.435,
    'DLAP_SDGE-APND': 0.130,
}
DLAP_NAMES = set(DLAP_WEIGHTS.keys())

def process_caiso_prices():
    print(f"Starting processing of CAISO prices from {DOWNLOAD_DIR}...")
    print(f"Filtering to California DLAPs with load weights: {DLAP_WEIGHTS}")

    all_data = {}
    files = sorted([f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.zip')])

    valid_files_count = 0
    skipped_files_count = 0
    total_records = 0

    # Track unique items encountered to debug if mapping fails
    encountered_items = set()

    for i, file_name in enumerate(files):
        file_path = os.path.join(DOWNLOAD_DIR, file_name)

        if os.path.getsize(file_path) < MIN_FILE_SIZE:
            skipped_files_count += 1
            continue

        if i % 10 == 0:
            print(f"  Processing {file_name}...")

        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # Find CSV (any .csv)
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]

                dfs = []
                for csv_file in csv_files:
                    with z.open(csv_file) as f:
                        try:
                            df = pd.read_csv(f, usecols=[
                                'OPR_DATE', 'INTERVAL_NUM', 'RESOURCE_NAME',
                                'DATA_ITEM', 'VALUE'
                            ])
                            dfs.append(df)
                        except Exception as e:
                            try:
                                # Fallback: read all and rename
                                df = pd.read_csv(f)
                                rename_map = {
                                    'INTERVAL': 'INTERVAL_NUM',
                                    'XML_DATA_ITEM': 'DATA_ITEM',
                                    'OPR_DT': 'OPR_DATE'
                                }
                                df.rename(columns=rename_map, inplace=True)
                                needed = ['OPR_DATE', 'INTERVAL_NUM', 'RESOURCE_NAME',
                                          'DATA_ITEM', 'VALUE']
                                if all(c in df.columns for c in needed):
                                    dfs.append(df[needed])
                            except:
                                print(f"    Could not read {csv_file} in {file_name}")
                                continue

                if not dfs:
                    continue

                full_df = pd.concat(dfs, ignore_index=True)

                # Update encountered items for debugging
                encountered_items.update(full_df['DATA_ITEM'].unique())

                # Filter to known price components
                full_df = full_df[full_df['DATA_ITEM'].isin(COMPONENT_MAP.keys())]

                if full_df.empty:
                    if len(encountered_items) < 10:
                        print(f"    Warning: No matching components in {file_name}. Found: {encountered_items}")
                    continue

                # Filter to California DLAPs only
                full_df = full_df[full_df['RESOURCE_NAME'].isin(DLAP_NAMES)]

                if full_df.empty:
                    continue

                # Handle INTERVAL_NUM to Hour
                max_interval = full_df['INTERVAL_NUM'].max()
                if max_interval > 24:
                    full_df['OPR_HR'] = np.ceil(full_df['INTERVAL_NUM'] / 12).astype(int)
                else:
                    full_df['OPR_HR'] = full_df['INTERVAL_NUM'].astype(int)

                # For sub-hourly data, first average within each LAP per hour
                if max_interval > 24:
                    full_df = full_df.groupby(
                        ['OPR_DATE', 'OPR_HR', 'RESOURCE_NAME', 'DATA_ITEM']
                    )['VALUE'].mean().reset_index()

                # Apply load weights
                full_df['WEIGHT'] = full_df['RESOURCE_NAME'].map(DLAP_WEIGHTS)
                full_df['WVALUE'] = full_df['VALUE'] * full_df['WEIGHT']

                # Weighted average: sum(w*v) / sum(w) per date/hour/component
                grouped = full_df.groupby(['OPR_DATE', 'OPR_HR', 'DATA_ITEM']).agg(
                    wsum=('WVALUE', 'sum'),
                    wtotal=('WEIGHT', 'sum')
                ).reset_index()
                grouped['VALUE'] = grouped['wsum'] / grouped['wtotal']

                count = 0
                for date_val, date_group in grouped.groupby('OPR_DATE'):
                    date_str = str(date_val)
                    if ' ' in date_str: date_str = date_str.split(' ')[0]

                    if date_str not in all_data:
                        all_data[date_str] = {}

                    for hr_val, hr_group in date_group.groupby('OPR_HR'):
                        hr_str = str(int(hr_val))

                        hr_data = {}
                        for _, row in hr_group.iterrows():
                            comp = COMPONENT_MAP.get(row['DATA_ITEM'])
                            val = round(row['VALUE'], 2)
                            hr_data[comp] = val

                        all_data[date_str][hr_str] = hr_data
                        count += 1

                total_records += count
                valid_files_count += 1

        except Exception as e:
            print(f"    Error processing {file_name}: {e}")

    print(f"\nProcessing Complete.")
    print(f"  Processed {valid_files_count} valid files.")
    print(f"  Skipped {skipped_files_count} small files.")
    print(f"  Total Day-Hours recorded: {total_records}")
    print(f"  Encountered DATA_ITEMs: {encountered_items}")

    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_data, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    process_caiso_prices()
