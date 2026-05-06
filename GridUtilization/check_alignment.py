"""
Check alignment of dates between monthly bars and daily line data
"""
import json
from collections import defaultdict
from datetime import datetime as dt

# Load data
with open("caiso_prices.json") as f:
    price_data = json.load(f)

with open("caiso_solar_daily_generation_mwh.json") as f:
    solar_mwh = json.load(f)

# Extract negative prices by month
monthly_neg_count = defaultdict(int)

for date_str in sorted(price_data.keys()):
    year = int(date_str[:4])
    month = int(date_str[5:7])
    m_key = f"{year}-{month:02d}"

    day_data = price_data[date_str]
    for hr_key in range(1, 25):
        hr_data = day_data.get(str(hr_key), {})
        lmp = hr_data.get("LMP")
        if lmp is not None and lmp < 0:
            monthly_neg_count[m_key] += 1

# Sort months
p2_m_keys = sorted(monthly_neg_count.keys())

# Find month with most negative prices
max_neg_month = max(monthly_neg_count.items(), key=lambda x: x[1])
print(f"\nMonth with most negative prices: {max_neg_month[0]} with {max_neg_month[1]} hours")

# Check bar position for that month
bar_index = p2_m_keys.index(max_neg_month[0])
print(f"Bar index for {max_neg_month[0]}: {bar_index}")

# Calculate average solar generation for that month
solar_dates = sorted(solar_mwh.keys())
month_solar_vals = []
for date_str in solar_dates:
    if date_str.startswith(max_neg_month[0]):
        month_solar_vals.append(solar_mwh[date_str])

if month_solar_vals:
    avg_solar = sum(month_solar_vals) / len(month_solar_vals)
    print(f"Average solar generation in {max_neg_month[0]}: {avg_solar:.2f} MWh/day ({avg_solar/1000:.2f} GWh/day)")
    print(f"Number of days: {len(month_solar_vals)}")

# Check a sample date's x-position calculation
sample_date_str = f"{max_neg_month[0]}-15"  # 15th of the month
first_month_dt = dt.strptime(p2_m_keys[0], "%Y-%m")
sample_date = dt.strptime(sample_date_str, "%Y-%m-%d")

months_diff = (sample_date.year - first_month_dt.year) * 12 + (sample_date.month - first_month_dt.month)
months_diff += sample_date.day / 30.0

print(f"\nSample date: {sample_date_str}")
print(f"First month: {p2_m_keys[0]}")
print(f"Calculated x-position: {months_diff:.2f}")
print(f"Expected bar position: {bar_index}")
print(f"Difference: {abs(months_diff - bar_index):.2f}")

# Show top 5 months by negative price count
print("\nTop 5 months by negative price count:")
sorted_months = sorted(monthly_neg_count.items(), key=lambda x: x[1], reverse=True)[:5]
for m_key, count in sorted_months:
    bar_idx = p2_m_keys.index(m_key)
    # Get average solar for this month
    month_solar = [solar_mwh[d] for d in solar_dates if d.startswith(m_key)]
    avg_solar_month = sum(month_solar) / len(month_solar) if month_solar else 0
    print(f"  {m_key}: {count:3d} hours (bar index {bar_idx:2d}, avg solar {avg_solar_month/1000:.1f} GWh/day)")

# Check seasonal patterns
print("\nSeasonal averages (2020-2025):")
seasons = {
    "Winter (Dec-Feb)": [12, 1, 2],
    "Spring (Mar-May)": [3, 4, 5],
    "Summer (Jun-Aug)": [6, 7, 8],
    "Fall (Sep-Nov)": [9, 10, 11],
}

for season_name, months in seasons.items():
    season_neg_hours = 0
    season_solar_mwh = []

    for m_key in p2_m_keys:
        month = int(m_key.split("-")[1])
        if month in months:
            season_neg_hours += monthly_neg_count.get(m_key, 0)
            # Get solar for this month
            month_solar = [solar_mwh[d] for d in solar_dates if d.startswith(m_key)]
            season_solar_mwh.extend(month_solar)

    avg_solar = sum(season_solar_mwh) / len(season_solar_mwh) if season_solar_mwh else 0
    print(f"  {season_name}: {season_neg_hours:4d} neg hours total, avg solar {avg_solar/1000:.1f} GWh/day")
