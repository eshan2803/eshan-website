import json

with open('caiso_prices_5min.json', 'r') as f:
    d5 = json.load(f)

min_v, min_d, min_h = 0, '', 0
for date_str, hours in d5.items():
    if date_str.startswith('2023'):
        for h in range(24):
            vals = [v['LMP'] for t_str, v in hours.items() if int(t_str.split(':')[0]) == h and 'LMP' in v]
            if vals:
                avg = sum(vals) / len(vals)
                if avg < min_v:
                    min_v = avg
                    min_d = date_str
                    min_h = h

print(f"{min_d} HE {min_h+1} had avg {min_v}")

with open('caiso_prices.json', 'r') as f:
    d_hr = json.load(f)

print(f"Let's see what caiso_prices.json has for that exact hour: {d_hr[min_d].get(str(min_h+1), {}).get('LMP')}")
