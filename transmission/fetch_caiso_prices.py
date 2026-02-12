import requests
import zipfile
import io
import pandas as pd
import json
import datetime
import pytz
import os
import sys

def process_local_zip(zip_path, geojson_path):
    """
    Process a local ZIP file downloaded from CAISO OASIS.
    The zip contains multiple CSV files for different LMP components.
    """
    print(f"Processing local ZIP: {zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                print("No CSV files found in ZIP.")
                return
            
            # Dataframes for each component
            comp_dfs = {}
            
            # Map file suffixes to our standard names
            # Files look like: ..._LMP_v12.csv, ..._MCE_v12.csv, etc.
            suffix_map = {
                '_LMP_v12.csv': 'LMP_PRC',
                '_MCE_v12.csv': 'LMP_ENE',
                '_MCC_v12.csv': 'LMP_CONG',
                '_MCL_v12.csv': 'LMP_LOSS',
                '_MGHG_v12.csv': 'LMP_GHG'
            }
            
            for csv_name in csv_files:
                matched = False
                for suffix, comp_name in suffix_map.items():
                    if csv_name.endswith(suffix):
                        print(f"Reading component {comp_name} from {csv_name}")
                        with z.open(csv_name) as f:
                            df = pd.read_csv(f)
                            comp_dfs[comp_name] = df
                        matched = True
                        break
                
                if not matched:
                    # Generic case for other versions or files
                    print(f"Reading generic file: {csv_name}")
                    with z.open(csv_name) as f:
                        df = pd.read_csv(f)
                        # We'll try to determine the type later
                        if 'XML_DATA_ITEM' in df.columns:
                            items = df['XML_DATA_ITEM'].unique()
                            for item in items:
                                comp_dfs[item] = df[df['XML_DATA_ITEM'] == item]

            if not comp_dfs:
                print("Could not identify LMP components in the ZIP.")
                return

            # Determine current operating hour (HE - Hour Ending)
            # PST time
            pst = pytz.timezone('US/Pacific')
            now_pst = datetime.datetime.now(pst)
            current_he = now_pst.hour + 1 # hour is 0-23, HE is 1-24 (e.g. 11:45 is HE 12)
            
            print(f"Current time (PST): {now_pst.strftime('%Y-%m-%d %H:%M')}, Target HE: {current_he}")

            # Combine all components into a node master dictionary
            # node -> {component: {hour: price}}
            node_data = {}
            
            for comp_name, df in comp_dfs.items():
                # Identify columns
                node_col = None
                for col in ['NODE', 'NODE_ID', 'NODE_ID_XML', 'PNODE_NAME']:
                    if col in df.columns:
                        node_col = col
                        break
                
                value_col = None
                for col in ['MW', 'VALUE', 'LMP', 'AMOUNT']:
                    if col in df.columns:
                        value_col = col
                        break
                
                hour_col = None
                for col in ['OPR_HR', 'HE', 'HOUR']:
                    if col in df.columns:
                        hour_col = col
                        break
                
                if not node_col or not value_col or not hour_col:
                    print(f"Skipping {comp_name}: missing required columns")
                    continue
                
                # Convert values
                df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
                df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce')
                
                # Group by Node and Hour to get hourly prices
                # We want a full 24h profile for each node
                # pivot_table is cleaner: index=Node, columns=Hour, values=Price
                pivot = df.pivot_table(index=node_col, columns=hour_col, values=value_col, aggfunc='mean')
                
                # Iterate through nodes in the pivot
                for node in pivot.index:
                    if node not in node_data:
                        node_data[node] = {}
                    
                    # Store hourly values as a dict {1: val, 2: val, ... 24: val}
                    # Convert to standard python dict
                    # Handle missing hours with None or 0? None is better.
                    hours_dict = {}
                    for h in range(1, 25):
                        if h in pivot.columns:
                            val = pivot.loc[node, h]
                            if pd.notna(val):
                                hours_dict[h] = round(float(val), 2)
                            else:
                                hours_dict[h] = None
                        else:
                            hours_dict[h] = None
                    
                    node_data[node][comp_name] = hours_dict

            print(f"Processed 24h price profiles for {len(node_data)} unique nodes.")
            
            # Match to substations
            match_to_substations(node_data, geojson_path)

    except Exception as e:
        print(f"Error processing local zip: {e}")
        import traceback
        traceback.print_exc()

import statistics

def match_to_substations(node_data, geojson_path):
    """
    Match node prices to substations in GeoJSON.
    """
    print(f"Matching prices to substations in {geojson_path}...")
    
    with open(geojson_path, 'r') as f:
        substations = json.load(f)
    
    matched_count = 0
    pnode_keys = list(node_data.keys())
    
    # Determine current hour for legacy scalar support
    pst = pytz.timezone('US/Pacific')
    now_pst = datetime.datetime.now(pst)
    current_he = now_pst.hour + 1

    for feature in substations['features']:
        sub_name = feature['properties'].get('Name', '').upper()
        if not sub_name:
            continue
        
        # IMPROVED MATCHING STRATEGY:
        # 1. Prioritize matches starting with the substation name 
        #    (e.g. "BAKER" -> "BAKER_1_N001", "RIO HONDO" -> "RIOHONDO_...")
        # 2. Fallback to containment if no startswith match found
        
        normalized_sub = sub_name.replace(' ', '')
        
        matches = [p for p in pnode_keys if p.startswith(sub_name) or p.startswith(normalized_sub)]
        
        if not matches:
            # Fallback
            matches = [p for p in pnode_keys if sub_name in p or normalized_sub in p]
        
        if matches:
            # Storage for component arrays (Hour 1-24)
            # { 'LMP_Total': [[vals_h1], [vals_h2]...], ... }
            comp_hourly_vals = {
                'LMP_Total': [[] for _ in range(25)], # Use 1-24 indices
                'LMP_Energy': [[] for _ in range(25)],
                'LMP_Congestion': [[] for _ in range(25)],
                'LMP_Loss': [[] for _ in range(25)],
                'LMP_GHG': [[] for _ in range(25)]
            }
            
            # Map OASIS names to our GeoJSON properties
            key_map = {
                'LMP_PRC': 'LMP_Total',
                'LMP_ENE': 'LMP_Energy',
                'LMP_CONG': 'LMP_Congestion',
                'LMP_LOSS': 'LMP_Loss',
                'LMP_GHG': 'LMP_GHG'
            }
            
            for m in matches:
                node_profile = node_data[m]
                
                for oasis_key, geo_key in key_map.items():
                    if oasis_key in node_profile:
                        # node_profile[oasis_key] is a dict {1: val, 2: val...}
                        hours_dict = node_profile[oasis_key]
                        for h in range(1, 25):
                            if hours_dict[h] is not None:
                                comp_hourly_vals[geo_key][h].append(hours_dict[h])
            
            # Calculate Medians for each hour and store 24h array
            # Also set the scalar value for the current hour
            for geo_key, hourly_bins in comp_hourly_vals.items():
                profile_24h = []
                for h in range(1, 25): # Hours 1 to 24
                    vals = hourly_bins[h]
                    if vals:
                        median_val = round(statistics.median(vals), 2)
                        profile_24h.append(median_val)
                    else:
                        profile_24h.append(None)
                
                # Store 24h array property
                feature['properties'][f"{geo_key}_24h"] = profile_24h
                
                # Store scalar for current hour (legacy)
                # handle array index (HE 1 is index 0)
                current_val = profile_24h[current_he - 1] if 1 <= current_he <= 24 else None
                feature['properties'][geo_key] = current_val
            
            feature['properties']['LMP_Nodes_Matched'] = len(matches)
            matched_count += 1
        else:
            # Clear properties if no match
            for key in ['LMP_Total', 'LMP_Energy', 'LMP_Congestion', 'LMP_Loss', 'LMP_GHG']:
                feature['properties'][key] = None
                feature['properties'][f"{key}_24h"] = [None] * 24
            feature['properties']['LMP_Nodes_Matched'] = 0

    print(f"Matched prices for {matched_count} / {len(substations['features'])} substations.")
    
    output_path = geojson_path.replace('.geojson', '_with_prices.geojson')
    with open(output_path, 'w') as f:
        json.dump(substations, f)
    
    print(f"Saved updated substations to {output_path}")

def fetch_caiso_dam_prices():
    """
    Fetch Day-Ahead Market (DAM) LMP prices for all nodes from CAISO OASIS API.
    Returns a DataFrame with all LMP components.
    """
    pst = pytz.timezone('US/Pacific')
    now = datetime.datetime.now(pst)
    
    # Query window: Current operating day (today in PST)
    # OASIS expects format: YYYYMMDDTHH:MM-HHMM (timezone offset)
    # For Pacific time, offset is -0800 (PST) or -0700 (PDT)
    # Use the actual PST offset from the current time
    offset = now.strftime('%z')  # Returns '-0800' for PST or '-0700' for PDT
    start_date_str = now.strftime('%Y%m%d') + 'T00:00' + offset
    end_date_str = now.strftime('%Y%m%d') + 'T23:59' + offset

    print(f"Fetching CAISO Day-Ahead LMP for {now.strftime('%Y-%m-%d')} (PST)...")
    print(f"Query time range: {start_date_str} to {end_date_str}")

    # OASIS API URL - PRC_LMP with DAM market, CSV format
    base_url = "https://oasis.caiso.com/oasisapi/SingleZip"
    params = {
        "queryname": "PRC_LMP",
        "startdatetime": start_date_str,
        "enddatetime": end_date_str,
        "market_run_id": "DAM",
        "version": "12", # Use v12 for components
        "grp_type": "ALL",
        "resultformat": "6"  # CSV format
    }

    try:
        print(f"Requesting API: {base_url}")
        print(f"Params: {params}")
        response = requests.get(base_url, params=params, timeout=180) # Increased timeout for large file
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error downloading data from API: {e}")
        return None

    # Check if response is XML error
    if b"<?xml" in response.content[:100]:
        print("Received XML response (likely error or maintenance):")
        print(response.content[:1000].decode('utf-8', errors='ignore'))
        return None

    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                print("No CSV files found in ZIP response.")
                return None
            
            print(f"Successfully downloaded ZIP with {len(csv_files)} CSV files.")
            # We can reuse the process_local_zip logic by saving this to a temp file
            # or by refactoring process_local_zip to accept a ZipFile object.
            # For simplicity let's save to a temp ID
            temp_zip = f"temp_caiso_{now.strftime('%Y%m%d')}.zip"
            with open(temp_zip, 'wb') as f:
                f.write(response.content)
            print(f"Saved API response to temporary file: {temp_zip}")

            # --- Archive Logic ---
            try:
                archive_dir = "archive"
                if not os.path.exists(archive_dir):
                    os.makedirs(archive_dir)
                
                archive_name = f"caiso_dam_{now.strftime('%Y%m%d_%H%M')}.zip"
                archive_path = os.path.join(archive_dir, archive_name)
                
                with open(archive_path, 'wb') as f:
                    f.write(response.content)
                print(f"Archived data to: {archive_path}")
            except Exception as archive_err:
                print(f"Warning: Failed to archive data: {archive_err}")
            # ---------------------

            return temp_zip

    except Exception as e:
        print(f"Error parsing ZIP/CSV from API: {e}")
        return None
    return None

if __name__ == "__main__":
    # Check if a zip file was passed as argument (manual override)
    local_zip = None
    
    if len(sys.argv) > 1:
        local_zip = sys.argv[1]

    if local_zip and os.path.exists(local_zip):
        print(f"Using provided local zip: {local_zip}")
        process_local_zip(local_zip, "substations.geojson")
    else:
        print("No command-line argument passed. Attempting automatic API fetch for today's data...")
        api_zip = fetch_caiso_dam_prices()
        if api_zip:
            process_local_zip(api_zip, "substations.geojson")
            # Optional: Clean up temp file
            # os.remove(api_zip)
        else:
            print("API fetch failed. Exiting with error.")
            sys.exit(1)
