"""
Analyze seasonal patterns in ancillary services pricing
"""
import json
from collections import defaultdict
import numpy as np

# Load ancillary services data
with open("ancillary_services.json") as f:
    as_data = json.load(f)

AS_TYPES = {
    "RU":  "Regulation Up",
    "RD":  "Regulation Down",
    "RMU": "Regulation Mileage Up",
    "RMD": "Regulation Mileage Down",
    "SR":  "Spinning Reserve",
    "NR":  "Non-Spinning Reserve",
}

# Collect prices by month and AS type
monthly_prices = {code: defaultdict(list) for code in AS_TYPES}

for date_str, hours_dict in as_data.items():
    if not isinstance(hours_dict, dict):
        continue

    year = int(date_str[:4])
    month = int(date_str[5:7])

    for h_str, vals in hours_dict.items():
        if not isinstance(vals, dict):
            continue

        for code in AS_TYPES:
            if code in vals and vals[code] is not None:
                price = vals[code]
                monthly_prices[code][month].append(price)

# Calculate seasonal statistics
print("="*80)
print("SEASONAL ANCILLARY SERVICES PRICING ANALYSIS (2020-2025)")
print("="*80)

seasons = {
    "Winter (Dec-Feb)": [12, 1, 2],
    "Spring (Mar-May)": [3, 4, 5],
    "Summer (Jun-Aug)": [6, 7, 8],
    "Fall (Sep-Nov)": [9, 10, 11],
}

for code, label in AS_TYPES.items():
    print(f"\n{label} ({code}):")
    print("-" * 70)

    seasonal_stats = {}

    for season_name, months in seasons.items():
        season_prices = []
        for month in months:
            if month in monthly_prices[code]:
                season_prices.extend(monthly_prices[code][month])

        if season_prices:
            avg_price = np.mean(season_prices)
            p95_price = np.percentile(season_prices, 95)
            p99_price = np.percentile(season_prices, 99)
            max_price = np.max(season_prices)

            seasonal_stats[season_name] = {
                'avg': avg_price,
                'p95': p95_price,
                'p99': p99_price,
                'max': max_price,
                'count': len(season_prices)
            }

    # Sort by average price to see which season is highest
    sorted_seasons = sorted(seasonal_stats.items(), key=lambda x: x[1]['avg'], reverse=True)

    for i, (season_name, stats) in enumerate(sorted_seasons):
        marker = "  <<< HIGHEST" if i == 0 else ""
        print(f"  {season_name:20s}: avg=${stats['avg']:6.2f}, p95=${stats['p95']:7.2f}, "
              f"p99=${stats['p99']:8.2f}, max=${stats['max']:9.2f}{marker}")

# Look at specific summer months
print("\n" + "="*80)
print("SUMMER MONTH BREAKDOWN (Jun-Jul-Aug)")
print("="*80)

for code, label in AS_TYPES.items():
    print(f"\n{label} ({code}):")
    print("-" * 70)

    for month_num, month_name in [(6, "June"), (7, "July"), (8, "August")]:
        if month_num in monthly_prices[code]:
            prices = monthly_prices[code][month_num]
            avg_price = np.mean(prices)
            p95_price = np.percentile(prices, 95)
            p99_price = np.percentile(prices, 99)
            max_price = np.max(prices)

            print(f"  {month_name:10s}: avg=${avg_price:6.2f}, p95=${p95_price:7.2f}, "
                  f"p99=${p99_price:8.2f}, max=${max_price:9.2f}")

# High price event analysis
print("\n" + "="*80)
print("HIGH PRICE EVENTS (>$100/MWh) BY SEASON")
print("="*80)

for code, label in AS_TYPES.items():
    print(f"\n{label} ({code}):")
    print("-" * 70)

    for season_name, months in seasons.items():
        season_prices = []
        for month in months:
            if month in monthly_prices[code]:
                season_prices.extend(monthly_prices[code][month])

        high_price_events = sum(1 for p in season_prices if p > 100)
        total_events = len(season_prices)
        pct = (high_price_events / total_events * 100) if total_events > 0 else 0

        if high_price_events > 0:
            print(f"  {season_name:20s}: {high_price_events:5d} events (>{100:3d}$/MWh) = {pct:5.2f}% of hours")
