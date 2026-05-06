"""
Trace a specific data point through the plotting logic to verify alignment
"""
import json
from collections import defaultdict
from datetime import datetime as dt
import numpy as np

# Load all data
with open("caiso_prices.json") as f:
    price_data = json.load(f)

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

# Test case: 2024-05 peak negative prices month
peak_month = "2024-05"
peak_bar_index = month_to_index[peak_month]
peak_neg_count = monthly_neg_count[peak_month]

print(f"Peak negative price month: {peak_month}")
print(f"Bar index: {peak_bar_index}")
print(f"Negative hour count: {peak_neg_count}")

# Now check solar data for dates in this month
print(f"\nSolar values for days in {peak_month}:")
solar_dates_in_month = [d for d in sorted(solar_mwh.keys()) if d.startswith(peak_month)]

for date_str in solar_dates_in_month[:5]:  # Show first 5 days
    test_date = dt.strptime(date_str, "%Y-%m-%d")
    m_key = f"{test_date.year}-{test_date.month:02d}"

    if m_key in month_to_index:
        bar_index = month_to_index[m_key]
        x_pos = bar_index + test_date.day / 30.0
        solar_val = solar_mwh[date_str] / 1000.0  # GWh

        print(f"  {date_str}: bar_index={bar_index}, x_pos={x_pos:.2f}, solar={solar_val:.1f} GWh")

# Compare to summer peak solar month
print(f"\n{'='*60}")
summer_month = "2024-06"  # Summer should have higher solar
summer_bar_index = month_to_index[summer_month]
summer_neg_count = monthly_neg_count[summer_month]

print(f"Summer month (expect HIGH solar, LOW negative prices): {summer_month}")
print(f"Bar index: {summer_bar_index}")
print(f"Negative hour count: {summer_neg_count}")

print(f"\nSolar values for days in {summer_month}:")
solar_dates_summer = [d for d in sorted(solar_mwh.keys()) if d.startswith(summer_month)]

for date_str in solar_dates_summer[:5]:
    test_date = dt.strptime(date_str, "%Y-%m-%d")
    m_key = f"{test_date.year}-{test_date.month:02d}"

    if m_key in month_to_index:
        bar_index = month_to_index[m_key]
        x_pos = bar_index + test_date.day / 30.0
        solar_val = solar_mwh[date_str] / 1000.0

        print(f"  {date_str}: bar_index={bar_index}, x_pos={x_pos:.2f}, solar={solar_val:.1f} GWh")

print(f"\n{'='*60}")
print("Expected pattern:")
print(f"  Bar {peak_bar_index} (2024-05): TALL purple bar (~{peak_neg_count} hrs), green line ~170-180 GWh")
print(f"  Bar {summer_bar_index} (2024-06): SHORT purple bar (~{summer_neg_count} hrs), green line ~190-200 GWh (HIGHER)")
print(f"\nGreen line should peak AFTER purple bars (summer has more solar but fewer negative prices)")
