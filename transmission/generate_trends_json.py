import os
import zipfile
import pandas as pd
import json
from collections import defaultdict

def generate_trends():
    archive_dir = r"C:\Users\eshan\OneDrive\Desktop\eshan-website\eshan-website-repo\archive"
    output_dir = r"C:\Users\eshan\OneDrive\Desktop\eshan-website\eshan-website-repo\transmission"
    
    ranges = [
        ("20250101", "20251231", "Full Year 2025"),
        ("20260101", "20260128", "Jan 2026"),
        ("20250101", "20250331", "Q1 2025"),
        ("20250401", "20250630", "Q2 2025"),
        ("20250701", "20250930", "Q3 2025"),
        ("20251001", "20251231", "Q4 2025"),
        ("20250301", "20250531", "Spring 2025"),
        ("20250601", "20250831", "Summer 2025"),
        ("20250901", "20251130", "Fall 2025"),
        ("20251201", "20260228", "Winter 2025"),
    ]
    
    # Correct month end dates to match HTML presets
    month_ends = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }
    for m, end_day in month_ends.items():
        ranges.append((f"2025{m:02d}01", f"2025{m:02d}{end_day:02d}", f"Month {m:02d} 2025"))

    accumulators = {r: {'nodes': defaultdict(lambda: {
        'LMP': [[0.0]*24, [0]*24],
        'ENERGY': [[0.0]*24, [0]*24],
        'CONGESTION': [[0.0]*24, [0]*24],
        'LOSS': [[0.0]*24, [0]*24]
    }), 'days': 0} for r in ranges}

    suffix_map = {
        '_LMP_v12.csv': 'LMP',
        '_MCE_v12.csv': 'ENERGY',
        '_MCC_v12.csv': 'CONGESTION',
        '_MCL_v12.csv': 'LOSS'
    }

    zip_files = [f for f in os.listdir(archive_dir) if f.startswith('caiso_dam_') and f.endswith('.zip')]
    zip_files.sort()

    for i, zip_file in enumerate(zip_files):
        date_s = zip_file.replace('caiso_dam_', '').replace('.zip', '')
        active_ranges = [r for r in ranges if r[0] <= date_s <= r[1]]
        if not active_ranges: continue
            
        print(f"[{i+1}/{len(zip_files)}] {zip_file}")
        zip_path = os.path.join(archive_dir, zip_file)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                for csv_name in z.namelist():
                    t_key = None
                    for suffix, key in suffix_map.items():
                        if csv_name.endswith(suffix):
                            t_key = key
                            break
                    if not t_key: continue

                    with z.open(csv_name) as f:
                        header = pd.read_csv(f, nrows=0)
                        cols = header.columns.tolist()
                        node_col = next((c for c in ['NODE', 'NODE_ID', 'NODE_ID_XML', 'PNODE_NAME'] if c in cols), None)
                        val_col = next((c for c in ['MW', 'VALUE', 'LMP', 'AMOUNT'] if c in cols), None)
                        hr_col = next((c for c in ['OPR_HR', 'HE', 'HOUR'] if c in cols), None)
                        
                        if not (node_col and val_col and hr_col): continue
                        
                        f.seek(0)
                        df = pd.read_csv(f, usecols=[node_col, val_col, hr_col])
                        df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
                        df[hr_col] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0).astype(int)
                        df = df[(df[hr_col] >= 1) & (df[hr_col] <= 24)].dropna()
                        
                        summary = df.groupby([node_col, hr_col])[val_col].agg(['sum', 'count']).reset_index()
                        
                        for r_info in active_ranges:
                            acc = accumulators[r_info]['nodes']
                            for row in summary.itertuples(index=False):
                                node, he, v_sum, v_count = row
                                h_sum, h_count = acc[node][t_key]
                                h_sum[he-1] += v_sum
                                h_count[he-1] += v_count
                                        
            for r_info in active_ranges:
                accumulators[r_info]['days'] += 1
                
        except Exception as e:
            print(f"  Error: {e}")

    # Finalize
    for r, data in accumulators.items():
        if data['days'] == 0: continue
        print(f"Saving {r[2]}...")
        nodes_output = []
        for node, types in data['nodes'].items():
            entry = {'node': node}
            complete = True
            for tk in ['LMP', 'ENERGY', 'CONGESTION', 'LOSS']:
                h_sums, h_counts = types[tk]
                hourly, t_sum, t_count = [], 0, 0
                for s, c in zip(h_sums, h_counts):
                    avg = round(s/c, 2) if c > 0 else 0
                    hourly.append(avg)
                    t_sum += s
                    t_count += c
                if t_count > 0:
                    entry[f'avg_{tk.lower()}'] = round(t_sum/t_count, 2)
                    entry[f'hourly_{tk.lower()}'] = hourly
                else: complete = False
            
            if complete:
                # Add Curtailment (max(0, -LMP))
                entry['avg_curtailment'] = round(max(0, -entry['avg_lmp']), 2)
                entry['hourly_curtailment'] = [round(max(0, -v), 2) for v in entry['hourly_lmp']]
                nodes_output.append(entry)
        
        with open(os.path.join(output_dir, f"trends_all_{r[0]}_{r[1]}.json"), 'w') as f:
            json.dump({"start_date": r[0], "end_date": r[1], "days_processed": data['days'], "node_count": len(nodes_output), "nodes": nodes_output}, f)
    print("All tasks completed.")

if __name__ == "__main__":
    generate_trends()
