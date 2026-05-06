#!/usr/bin/env python3
"""
Plot normalized LMP vs minimum effective headroom
One data point per day (minimum headroom for that day)
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

# CA Natural Gas Citygate Prices ($/MCF) - Source: EIA
GAS_PRICES = {
    '2020-01': 3.32, '2020-02': 2.55, '2020-03': 2.43, '2020-04': 2.36,
    '2020-05': 2.47, '2020-06': 2.65, '2020-07': 2.69, '2020-08': 2.27,
    '2020-09': 3.41, '2020-10': 3.08, '2020-11': 3.79, '2020-12': 4.03,
    '2021-01': 2.25, '2021-02': 1.28, '2021-03': 4.09, '2021-04': 3.65,
    '2021-05': 3.92, '2021-06': 4.25, '2021-07': 5.14, '2021-08': 5.26,
    '2021-09': 5.00, '2021-10': 6.42, '2021-11': 6.97, '2021-12': 6.76,
    '2022-01': 7.92, '2022-02': 6.04, '2022-03': 5.86, '2022-04': 6.32,
    '2022-05': 7.47, '2022-06': 10.07, '2022-07': 7.31, '2022-08': 10.38,
    '2022-09': 9.20, '2022-10': 6.38, '2022-11': 7.08, '2022-12': 11.83,
    '2023-01': 28.61, '2023-02': 11.10, '2023-03': 4.57, '2023-04': 4.97,
    '2023-05': 3.95, '2023-06': 3.78, '2023-07': 4.41, '2023-08': 4.78,
    '2023-09': 4.49, '2023-10': 3.21, '2023-11': 5.97, '2023-12': 6.66,
    '2024-01': 4.35, '2024-02': 5.59, '2024-03': 4.23, '2024-04': 2.66,
    '2024-05': 2.51, '2024-06': 2.50, '2024-07': 2.98, '2024-08': 3.14,
    '2024-09': 2.44, '2024-10': 3.22, '2024-11': 3.74, '2024-12': 4.68,
    '2025-01': 4.84, '2025-02': 4.92, '2025-03': 4.12, '2025-04': 3.12,
    '2025-05': 2.92, '2025-06': 2.83, '2025-07': 4.17, '2025-08': 3.91,
    '2025-09': 5.00, '2025-10': 3.85, '2025-11': 5.97, '2025-12': 6.66,
}

def compute_reserves(demand):
    """Compute required reserves based on CAISO methodology"""
    reserves = []
    for h in range(24):
        d = demand[h]
        if 16 <= h <= 20:  # Peak hours (4-9 PM)
            r = max(d * 0.084, 3500)
        elif 12 <= h <= 15 or 21 <= h <= 23:  # Shoulder hours
            r = max(d * 0.077, 3500)
        else:  # Off-peak
            r = max(d * 0.070, 3500)
        reserves.append(r)
    return reserves

def main():
    # Load data files
    with open('demand_forecast.json', 'r') as f:
        demand_data = json.load(f)
        if 'metadata' in demand_data:
            del demand_data['metadata']

    with open('available_capacity.json', 'r') as f:
        capacity_data = json.load(f)
        if 'metadata' in capacity_data:
            del capacity_data['metadata']

    with open('caiso_prices.json', 'r') as f:
        price_data = json.load(f)
        if 'metadata' in price_data:
            del price_data['metadata']

    # Prepare output arrays
    min_headrooms = []  # Minimum effective headroom per day (MW)
    norm_lmps = []      # Normalized LMP per day (MWh^-1 · MCF)
    dates = []

    # Iterate through all days
    start_date = datetime(2020, 1, 1)
    for i in range(2192):  # 2020-01-01 to 2025-12-31
        date = start_date + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        year = str(date.year)
        month = str(date.month).zfill(2)
        month_key = f"{year}-{month}"

        # Get data for this day
        demand = demand_data.get(date_str)
        capacity = capacity_data.get(year, {}).get(month)
        prices = price_data.get(date_str)
        gas_price = GAS_PRICES.get(month_key, 3.0)

        # Skip if missing data
        if not demand or not capacity or not prices:
            continue

        # Get total available capacity
        total_avail = capacity.get('Total')
        if not total_avail:
            continue

        # Compute headroom for each hour and find minimum
        headrooms = []
        for h in range(24):
            d = demand[h] if demand[h] is not None else 0
            a = total_avail[h]

            # Compute reserves
            if 16 <= h <= 20:  # Peak hours
                r = max(d * 0.084, 3500)
            elif 12 <= h <= 15 or 21 <= h <= 23:  # Shoulder
                r = max(d * 0.077, 3500)
            else:  # Off-peak
                r = max(d * 0.070, 3500)

            headroom = a - d - r
            headrooms.append(headroom)

        min_headroom = min(headrooms)

        # Compute weighted average LMP for the day
        lmp_sum = 0
        lmp_count = 0
        for h in range(24):
            hr_key = str(h + 1)  # Price data uses 1-24 indexing
            if hr_key in prices and prices[hr_key].get('LMP') is not None:
                lmp_sum += prices[hr_key]['LMP']
                lmp_count += 1

        if lmp_count == 0:
            continue

        avg_lmp = lmp_sum / lmp_count
        norm_lmp = avg_lmp / gas_price

        # Filter outliers (normalized LMP > 200)
        if norm_lmp > 200:
            continue

        # Store results
        min_headrooms.append(min_headroom / 1000)  # Convert to GW
        norm_lmps.append(norm_lmp)
        dates.append(date)

    # Create scatter plot
    plt.figure(figsize=(12, 8))

    # Color by year
    years = [d.year for d in dates]
    colors = plt.cm.viridis((np.array(years) - 2020) / 5)  # 2020-2025 = 0 to 5

    scatter = plt.scatter(min_headrooms, norm_lmps, c=years, cmap='viridis',
                         alpha=0.6, s=30, edgecolors='black', linewidth=0.5)

    plt.xlabel('Minimum Effective Headroom (GW)', fontsize=12, fontweight='bold')
    plt.ylabel('Normalized LMP ($/MWh per $/MCF)', fontsize=12, fontweight='bold')
    plt.title('Normalized LMP vs Minimum Effective Headroom\n(One point per day, 2020-2025)',
              fontsize=14, fontweight='bold')

    # Add colorbar
    cbar = plt.colorbar(scatter, label='Year')
    cbar.set_ticks([2020, 2021, 2022, 2023, 2024, 2025])

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save figure
    output_file = 'lmp_norm_vs_min_headroom.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot to {output_file}")
    print(f"Total days plotted: {len(min_headrooms)}")
    print(f"Min headroom range: {min(min_headrooms):.1f} to {max(min_headrooms):.1f} GW")
    print(f"Normalized LMP range: {min(norm_lmps):.1f} to {max(norm_lmps):.1f} MCF^-1")

    plt.show()

if __name__ == '__main__':
    main()
