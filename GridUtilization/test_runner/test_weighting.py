import json
from collections import defaultdict

# 1. Load 5-min JSON (which already has 40:40:20 weighted average applied during download!)
with open('caiso_prices_5min.json', 'r') as f:
    d5 = json.load(f)

# 2. Load hourly JSON (which was downloaded using simple unweighted mean or older LAP API)
with open('caiso_prices.json', 'r') as f:
    d_hr = json.load(f)

# Compute hourly average directly from the 40:40:20 5-minute data
res5 = []
for date_str, hours in d5.items():
    if date_str.startswith('2023'):
        for h in range(24):
            vals = []
            for t_str, v in hours.items():
                if int(t_str.split(':')[0]) == h and 'LMP' in v:
                    vals.append(v['LMP'])
            if len(vals) > 0:
                res5.append(sum(vals) / len(vals))

# Read hourly averages from the simple JSON
res_hr = []
for date_str, hours in d_hr.items():
    if date_str.startswith('2023'):
        for h_str, v in hours.items():
            if isinstance(v, dict) and 'LMP' in v:
                res_hr.append(v['LMP'])

print('Minimum hourly average computed from 40:40:20 5-minute telemetry:', min(res5) if res5 else None)
print('Minimum hourly average strictly read from caiso_prices.json:', min(res_hr) if res_hr else None)
