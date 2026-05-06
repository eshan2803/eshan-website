import os

script_dir = os.path.dirname(os.path.abspath(__file__))
target = os.path.join(script_dir, "plot_negative_lmp_curtailment_hourly.py")

with open(target, "r", encoding="utf-8") as f:
    text = f.read()

start_marker = '# ── Read CSV (hourly rows only) ──'
end_marker = 'for year in sorted(negative_intervals.keys()):'

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Could not find markers.")
    exit(1)

new_chunk = """# ── Read CSV and compute Hourly Averages ──
print("Reading comprehensive CSV and computing true hourly averages...")
import pandas as pd
df = pd.read_csv(CSV_FILE, usecols=['timestamp', 'lmp', 'load_mw', 'demand_mw', 'solar_mw', 'wind_mw', 'battery_charging_mw'])

# Combine load and demand safely
if 'load_mw' in df.columns and 'demand_mw' in df.columns:
    df['load_mw'] = df['load_mw'].fillna(df['demand_mw'])

# Convert numeric columns
cols_to_avg = ['lmp', 'load_mw', 'solar_mw', 'wind_mw', 'battery_charging_mw']
for c in cols_to_avg:
    df[c] = pd.to_numeric(df[c], errors='coerce')

df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Important: Resample mathematically averages the 12 5-minute intervals inside each hour
hourly_df = df[cols_to_avg].resample('1h').mean()

negative_intervals = defaultdict(list)
count = 0
matched = 0

for ts, row in hourly_df.iterrows():
    if pd.isna(row['lmp']) or row['lmp'] >= 0:
        continue
        
    year = ts.year
    date_str = ts.strftime("%Y-%m-%d")
    hour = ts.hour
    
    lmp = float(row['lmp'])
    load_mw = float(row['load_mw']) if not pd.isna(row['load_mw']) else 0
    solar_mw = float(row['solar_mw']) if not pd.isna(row['solar_mw']) else 0
    wind_mw = float(row['wind_mw']) if not pd.isna(row['wind_mw']) else 0
    battery_charging_mw = float(row['battery_charging_mw']) if not pd.isna(row['battery_charging_mw']) else 0
    
    # Floor at 0 for generation/metrics just like previous script
    load_mw = max(load_mw, 0)
    solar_mw = max(solar_mw, 0)
    wind_mw = max(wind_mw, 0)
    battery_charging_mw = max(battery_charging_mw, 0)
    
    load_gwh = load_mw / 1000.0
    net_load_gwh = (load_mw - solar_mw - wind_mw) / 1000.0
    
    local_curtail = 0.0
    system_curtail = 0.0
    if (date_str, hour) in curtailment:
        local_curtail, system_curtail = curtailment[(date_str, hour)]
        matched += 1
        
    total_curtail = local_curtail + system_curtail
    batt_charging_gw = battery_charging_mw / 1000.0
    
    negative_intervals[year].append((lmp, load_gwh, net_load_gwh, local_curtail, system_curtail, total_curtail, batt_charging_gw))
    count += 1

print(f"  Total negative-LMP hours: {count:,}")
print(f"  Matched curtailment data: {matched:,} ({100*matched/max(count,1):.1f}%)")

"""

new_text = text[:start_idx] + new_chunk + text[end_idx:]

with open(target, "w", encoding="utf-8") as f:
    f.write(new_text)

print("Modification complete.")
