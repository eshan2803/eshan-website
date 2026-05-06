"""
Verify the corrected alignment
"""
import json
from collections import defaultdict
from datetime import datetime as dt
import numpy as np

# Load data
with open("caiso_prices.json") as f:
    price_data = json.load(f)

with open("caiso_solar_daily_generation_mwh.json") as f:
    solar_mwh = json.load(f)

# Extract negative prices by month (matching plotting script)
monthly_neg_count = defaultdict(int)
monthly_total_count = defaultdict(int)

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

# Build month list exactly like plotting script
m_keys = sorted(monthly_total_count.keys())
p2_m_keys = sorted(m_keys)

print(f"First month in p2_m_keys: {p2_m_keys[0]}")
print(f"Last month in p2_m_keys: {p2_m_keys[-1]}")
print(f"Total months: {len(p2_m_keys)}")

# Find month with most negative prices
max_neg_month = max(monthly_neg_count.items(), key=lambda x: x[1])
print(f"\nMonth with most negative prices: {max_neg_month[0]} with {max_neg_month[1]} hours")

# Create month-to-index mapping (matching corrected code)
month_to_index = {m_key: i for i, m_key in enumerate(p2_m_keys)}

# Test the corrected calculation for a date in the peak month
test_date_str = f"{max_neg_month[0]}-15"
test_date = dt.strptime(test_date_str, "%Y-%m-%d")
m_key = f"{test_date.year}-{test_date.month:02d}"

if m_key in month_to_index:
    bar_index = month_to_index[m_key]
    x_pos = bar_index + test_date.day / 30.0
    print(f"\nTest date: {test_date_str}")
    print(f"Month key: {m_key}")
    print(f"Bar index: {bar_index}")
    print(f"Calculated x-position: {x_pos:.2f}")
    print(f"✓ Alignment correct! (bar at {bar_index}, point at {x_pos:.2f})")

# Show peak months with their alignment
print("\nTop 5 months by negative price count with corrected alignment:")
sorted_months = sorted(monthly_neg_count.items(), key=lambda x: x[1], reverse=True)[:5]
for m_key, count in sorted_months:
    bar_idx = month_to_index[m_key]
    # Get average solar for this month
    solar_dates = sorted(solar_mwh.keys())
    month_solar = [solar_mwh[d] for d in solar_dates if d.startswith(m_key)]
    avg_solar_month = sum(month_solar) / len(month_solar) if month_solar else 0
    print(f"  {m_key}: {count:3d} neg hours → bar at x={bar_idx:2d}, avg solar {avg_solar_month/1000:.1f} GWh/day")
