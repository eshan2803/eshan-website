"""
Verify both battery and solar are correctly aligned with negative price bars
"""
import json
from collections import defaultdict
from datetime import datetime as dt

# Load all data
with open("caiso_prices.json") as f:
    price_data = json.load(f)

with open("caiso_battery_daily_charging_mwh.json") as f:
    battery_mwh = json.load(f)

with open("caiso_solar_daily_generation_mwh.json") as f:
    solar_mwh = json.load(f)

# Build month list exactly like plotting script
monthly_total_count = defaultdict(int)
monthly_neg_count = defaultdict(int)

for date_str in sorted(price_data.keys()):
    year = int(date_str[:4])
    month = int(date_str[5:7])
    m_key = f"{year}-{month:02d}"

    day_data = price_data[date_str]
    for hr_key in range(1, 25):
        hr_data = day_data.get(str(hr_key), {})
        lmp = hr_data.get("LMP")
        if lmp is not None:
            monthly_total_count[m_key] += 1
            if lmp < 0:
                monthly_neg_count[m_key] += 1

m_keys = sorted(monthly_total_count.keys())
p2_m_keys = sorted(m_keys)
month_to_index = {m_key: i for i, m_key in enumerate(p2_m_keys)}

# Find peak months for each metric
max_neg_month = max(monthly_neg_count.items(), key=lambda x: x[1])
print(f"Peak negative prices: {max_neg_month[0]} with {max_neg_month[1]} hours (bar index {month_to_index[max_neg_month[0]]})")

# Calculate monthly averages for battery and solar
monthly_battery = defaultdict(list)
monthly_solar = defaultdict(list)

for date_str in sorted(battery_mwh.keys()):
    m_key = date_str[:7]  # YYYY-MM
    monthly_battery[m_key].append(battery_mwh[date_str])

for date_str in sorted(solar_mwh.keys()):
    m_key = date_str[:7]  # YYYY-MM
    monthly_solar[m_key].append(solar_mwh[date_str])

# Find peak battery month
battery_avgs = {m: sum(vals)/len(vals) for m, vals in monthly_battery.items()}
max_battery_month = max(battery_avgs.items(), key=lambda x: x[1])
print(f"Peak battery charging: {max_battery_month[0]} with avg {max_battery_month[1]/1000:.1f} GWh/day (bar index {month_to_index.get(max_battery_month[0], 'N/A')})")

# Find peak solar month
solar_avgs = {m: sum(vals)/len(vals) for m, vals in monthly_solar.items()}
max_solar_month = max(solar_avgs.items(), key=lambda x: x[1])
print(f"Peak solar generation: {max_solar_month[0]} with avg {max_solar_month[1]/1000:.1f} GWh/day (bar index {month_to_index.get(max_solar_month[0], 'N/A')})")

# Show spring 2024 alignment (where we expect correlation)
print("\nSpring 2024 months (high negative prices expected):")
for m_key in ["2024-03", "2024-04", "2024-05"]:
    neg_hours = monthly_neg_count.get(m_key, 0)
    battery_avg = battery_avgs.get(m_key, 0) / 1000
    solar_avg = solar_avgs.get(m_key, 0) / 1000
    bar_idx = month_to_index.get(m_key, -1)
    print(f"  {m_key} (bar {bar_idx:2d}): {neg_hours:3d} neg hours, {battery_avg:5.1f} GWh/day battery, {solar_avg:5.1f} GWh/day solar")

# Show summer 2024 (high solar, but lower negative prices due to demand)
print("\nSummer 2024 months (high solar, but higher demand):")
for m_key in ["2024-06", "2024-07", "2024-08"]:
    neg_hours = monthly_neg_count.get(m_key, 0)
    battery_avg = battery_avgs.get(m_key, 0) / 1000
    solar_avg = solar_avgs.get(m_key, 0) / 1000
    bar_idx = month_to_index.get(m_key, -1)
    print(f"  {m_key} (bar {bar_idx:2d}): {neg_hours:3d} neg hours, {battery_avg:5.1f} GWh/day battery, {solar_avg:5.1f} GWh/day solar")

# Test specific date alignment
test_dates = [
    "2024-05-15",  # Peak negative prices
    "2024-07-15",  # Peak solar (expected)
    "2025-12-15",  # Recent, high battery
]

print("\nTest date alignments:")
for date_str in test_dates:
    test_date = dt.strptime(date_str, "%Y-%m-%d")
    m_key = f"{test_date.year}-{test_date.month:02d}"

    if m_key in month_to_index:
        bar_index = month_to_index[m_key]
        x_pos = bar_index + test_date.day / 30.0

        battery_val = battery_mwh.get(date_str, 0) / 1000
        solar_val = solar_mwh.get(date_str, 0) / 1000
        neg_hours = monthly_neg_count.get(m_key, 0)

        print(f"  {date_str}: bar={bar_index}, x={x_pos:.2f}, neg_hrs={neg_hours}, battery={battery_val:.1f}GWh, solar={solar_val:.1f}GWh")
