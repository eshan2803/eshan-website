"""
Scatter plot: LMP normalized by CA Natural Gas Citygate price vs Net Load.
Y-axis = LMP ($/MWh) / Gas Price ($/MCF) → units: MCF/MWh (implied heat rate proxy)
Net Load = Demand - (Solar + Wind + Hydro + Nuclear + Geothermal + Biomass + Other Thermal)

Uses hourly data for all dates with LMP data (2020-01-01 onwards).
Saves output as lmp_norm_vs_netload.png.
"""

import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load data
with open(os.path.join(script_dir, "demand_forecast.json")) as f:
    demand_data = json.load(f)

with open(os.path.join(script_dir, "available_capacity.json")) as f:
    capacity_data = json.load(f)

with open(os.path.join(script_dir, "caiso_prices.json")) as f:
    price_data = json.load(f)

# CA Natural Gas Citygate Prices ($/MCF) — Source: EIA
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

# Non-gas resources to subtract from demand
NON_GAS = ["Solar", "Wind", "Hydro", "Nuclear", "Geothermal", "Biomass", "Other Thermal"]
GAS_RESOURCES = ["Gas CCGT", "Gas Peaker", "Gas Steam", "Gas ICE"]

net_loads = []
norm_lmp_values = []
hours = []
headrooms = []

price_dates = sorted(price_data.keys())
print(f"Price data spans {price_dates[0]} to {price_dates[-1]} ({len(price_dates)} days)")

start_ref = datetime(2020, 1, 1)

for date_str in price_dates:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if dt < start_ref:
        continue

    year = str(dt.year)
    month = f"{dt.month:02d}"
    gas_key = f"{year}-{month}"
    gas_price = GAS_PRICES.get(gas_key)
    if not gas_price:
        continue

    demand = demand_data.get(date_str)
    cap_month = capacity_data.get(year, {}).get(month)
    p_data = price_data.get(date_str)

    if not demand or not cap_month or not p_data:
        continue

    for h in range(24):
        hr_key = str(h + 1)
        hr_prices = p_data.get(hr_key, {})
        lmp = hr_prices.get("LMP")
        if lmp is None:
            continue

        dem_val = demand[h] if demand[h] is not None else 0

        non_gas_cap = 0
        for res in NON_GAS:
            res_arr = cap_month.get(res)
            if res_arr:
                non_gas_cap += res_arr[h]

        gas_cap = 0
        for res in GAS_RESOURCES:
            res_arr = cap_month.get(res)
            if res_arr:
                gas_cap += res_arr[h]

        net_load = dem_val - non_gas_cap
        headroom = gas_cap - net_load  # MW remaining above net load

        net_loads.append(net_load)
        norm_lmp_values.append(lmp / gas_price)
        hours.append(h)
        headrooms.append(headroom)

print(f"Total hourly data points: {len(net_loads)}")

net_loads = np.array(net_loads)
norm_lmp_values = np.array(norm_lmp_values)
hours = np.array(hours)
headrooms = np.array(headrooms)

# Inverse headroom sizing: smallest headroom → largest point
# Linear map from [min_headroom, max_headroom] → [max_size, min_size]
SIZE_MIN, SIZE_MAX = 1, 60
sizes = SIZE_MIN + (SIZE_MAX - SIZE_MIN) * (headrooms.max() - headrooms) / (headrooms.max() - headrooms.min())
print(f"Headroom range: {headrooms.min():.0f} to {headrooms.max():.0f} MW")

# --- Create the plot ---
fig, ax = plt.subplots(figsize=(14, 9))
fig.patch.set_facecolor("#0f1117")
ax.set_facecolor("#1a1d2e")

# High-contrast colormap for dark background: night=blue, morning=cyan, midday=yellow, evening=red
hour_cmap = LinearSegmentedColormap.from_list("hour_bright", [
    (0.0,  "#3b82f6"),   # 0h  midnight - blue
    (0.25, "#22d3ee"),   # 6h  dawn - cyan
    (0.5,  "#facc15"),   # 12h noon - yellow
    (0.75, "#ef4444"),   # 18h evening - red
    (1.0,  "#3b82f6"),   # 24h back to midnight - blue
])

scatter = ax.scatter(
    net_loads / 1000,
    norm_lmp_values,
    c=hours,
    cmap=hour_cmap,
    vmin=0, vmax=23,
    s=sizes,
    alpha=0.5,
    edgecolors="none",
    rasterized=True,
)

cbar = plt.colorbar(scatter, ax=ax, pad=0.02, shrink=0.8)
cbar.set_label("Hour of Day", color="#ccc", fontsize=12)
cbar.set_ticks([0, 4, 8, 12, 16, 20, 23])
cbar.set_ticklabels(["12a", "4a", "8a", "12p", "4p", "8p", "11p"])
cbar.ax.tick_params(colors="#888", labelsize=10)

# Styling
ax.set_xlabel("Net Load (GW)\nDemand minus Solar, Wind, Hydro, Nuclear, Geothermal, Biomass, Other Thermal",
              color="#ccc", fontsize=12, labelpad=10)
ax.set_ylabel("LMP / Gas Price (MWh⁻¹ · MCF)", color="#ccc", fontsize=12, labelpad=10)
ax.set_title("LMP Normalized by CA Gas Citygate Price vs Net Load\nCAISO Hourly Data: Jan 2020 – Dec 2025",
             color="#fff", fontsize=15, fontweight="bold", pad=15)

ax.set_ylim(norm_lmp_values.min(), norm_lmp_values.max())

ax.tick_params(colors="#888", labelsize=10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#3a3d4e")
ax.spines["bottom"].set_color("#3a3d4e")
ax.grid(True, color="#2a2d3e", linewidth=0.5, alpha=0.7)

ax.axhline(y=0, color="#ef4444", linewidth=0.8, linestyle="--", alpha=0.6)

plt.tight_layout()

out_path = os.path.join(script_dir, "lmp_norm_vs_netload.png")
fig.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()
