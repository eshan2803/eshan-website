"""
Scatter plot: MEC (energy component of LMP) vs Net Load.
Net Load = Demand - (Solar + Wind + Hydro + Nuclear + Geothermal + Biomass + Other Thermal)
i.e., the residual load that gas generators must serve.

Uses hourly data for all dates with LMP data (2020-01-01 onwards).
Saves output as mec_vs_netload.png.
"""

import json
import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
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

# Non-gas resources to subtract from demand
NON_GAS = ["Solar", "Wind", "Hydro", "Nuclear", "Geothermal", "Biomass", "Other Thermal"]

net_loads = []
mec_values = []
hours = []  # for coloring by time of day
dates_float = []  # for coloring by date

# Get sorted dates that have price data
price_dates = sorted(price_data.keys())
print(f"Price data spans {price_dates[0]} to {price_dates[-1]} ({len(price_dates)} days)")

start_ref = datetime(2020, 1, 1)
end_ref = datetime(2025, 12, 31)

for date_str in price_dates:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if dt < start_ref:
        continue

    year = str(dt.year)
    month = f"{dt.month:02d}"

    demand = demand_data.get(date_str)
    cap_month = capacity_data.get(year, {}).get(month)
    p_data = price_data.get(date_str)

    if not demand or not cap_month or not p_data:
        continue

    for h in range(24):
        hr_key = str(h + 1)  # price data uses 1-24
        hr_prices = p_data.get(hr_key, {})
        mec = hr_prices.get("MEC")
        if mec is None:
            continue

        dem_val = demand[h] if demand[h] is not None else 0

        # Sum non-gas available capacity for this hour
        non_gas_cap = 0
        for res in NON_GAS:
            res_arr = cap_month.get(res)
            if res_arr:
                non_gas_cap += res_arr[h]

        net_load = dem_val - non_gas_cap

        net_loads.append(net_load)
        mec_values.append(mec)
        hours.append(h)
        days_since = (dt - start_ref).days
        dates_float.append(days_since)

print(f"Total hourly data points: {len(net_loads)}")

net_loads = np.array(net_loads)
mec_values = np.array(mec_values)
hours = np.array(hours)
dates_float = np.array(dates_float)

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

# Color by hour of day
scatter = ax.scatter(
    net_loads / 1000,  # convert to GW
    mec_values,
    c=hours,
    cmap=hour_cmap,
    vmin=0, vmax=23,
    s=6,
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
ax.set_ylabel("Marginal Energy Cost - MEC ($/MWh)", color="#ccc", fontsize=12, labelpad=10)
ax.set_title("MEC vs Net Load (Residual Gas Demand)\nCAISO Hourly Data: Jan 2020 - Dec 2025",
             color="#fff", fontsize=15, fontweight="bold", pad=15)

ax.tick_params(colors="#888", labelsize=10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#3a3d4e")
ax.spines["bottom"].set_color("#3a3d4e")
ax.grid(True, color="#2a2d3e", linewidth=0.5, alpha=0.7)

ax.set_ylim(-50, 300)

# Add zero line
ax.axhline(y=0, color="#ef4444", linewidth=0.8, linestyle="--", alpha=0.6)

plt.tight_layout()

out_path = os.path.join(script_dir, "mec_vs_netload.png")
fig.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()
