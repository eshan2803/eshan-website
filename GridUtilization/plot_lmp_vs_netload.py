"""
Scatter plot: Total LMP vs Net Load.
Net Load = Demand - (Solar + Wind + Hydro + Nuclear + Geothermal + Biomass + Other Thermal)
i.e., the residual load that gas generators must serve.

Uses hourly data for all dates with LMP data (2022-11-07 onwards).
Saves output as lmp_vs_netload.png.
"""

import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
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
lmp_values = []
hours = []

price_dates = sorted(price_data.keys())
print(f"Price data spans {price_dates[0]} to {price_dates[-1]} ({len(price_dates)} days)")

start_ref = datetime(2022, 11, 7)

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

        net_load = dem_val - non_gas_cap

        net_loads.append(net_load)
        lmp_values.append(lmp)
        hours.append(h)

print(f"Total hourly data points: {len(net_loads)}")

net_loads = np.array(net_loads)
lmp_values = np.array(lmp_values)
hours = np.array(hours)

# --- Create the plot ---
fig, ax = plt.subplots(figsize=(14, 9))
fig.patch.set_facecolor("#0f1117")
ax.set_facecolor("#1a1d2e")

scatter = ax.scatter(
    net_loads / 1000,
    lmp_values,
    c=hours,
    cmap="twilight_shifted",
    s=3,
    alpha=0.35,
    edgecolors="none",
    rasterized=True,
)

cbar = plt.colorbar(scatter, ax=ax, pad=0.02, shrink=0.8)
cbar.set_label("Hour of Day", color="#ccc", fontsize=12)
cbar.set_ticks([0, 4, 8, 12, 16, 20, 23])
cbar.set_ticklabels(["12a", "4a", "8a", "12p", "4p", "8p", "11p"])
cbar.ax.tick_params(colors="#888", labelsize=10)

# Bin the data for median + IQR trend
mask = np.isfinite(net_loads) & np.isfinite(lmp_values)
nl_clean = net_loads[mask] / 1000
lmp_clean = lmp_values[mask]

bin_edges = np.linspace(nl_clean.min(), nl_clean.max(), 40)
bin_centers = []
bin_medians = []
bin_p25 = []
bin_p75 = []

for i in range(len(bin_edges) - 1):
    in_bin = (nl_clean >= bin_edges[i]) & (nl_clean < bin_edges[i + 1])
    if in_bin.sum() > 10:
        bin_centers.append((bin_edges[i] + bin_edges[i + 1]) / 2)
        bin_medians.append(np.median(lmp_clean[in_bin]))
        bin_p25.append(np.percentile(lmp_clean[in_bin], 25))
        bin_p75.append(np.percentile(lmp_clean[in_bin], 75))

bin_centers = np.array(bin_centers)
bin_medians = np.array(bin_medians)
bin_p25 = np.array(bin_p25)
bin_p75 = np.array(bin_p75)

ax.plot(bin_centers, bin_medians, color="#60a5fa", linewidth=2.5, label="Median LMP", zorder=5)
ax.fill_between(bin_centers, bin_p25, bin_p75, color="#60a5fa", alpha=0.15, label="IQR (25th-75th)", zorder=4)

# Styling
ax.set_xlabel("Net Load (GW)\nDemand minus Solar, Wind, Hydro, Nuclear, Geothermal, Biomass, Other Thermal",
              color="#ccc", fontsize=12, labelpad=10)
ax.set_ylabel("Total LMP ($/MWh)", color="#ccc", fontsize=12, labelpad=10)
ax.set_title("Total LMP vs Net Load (Residual Gas Demand)\nCAISO Hourly Data: Nov 2022 - Dec 2025",
             color="#fff", fontsize=15, fontweight="bold", pad=15)

ax.set_ylim(top=500)

ax.tick_params(colors="#888", labelsize=10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#3a3d4e")
ax.spines["bottom"].set_color("#3a3d4e")
ax.grid(True, color="#2a2d3e", linewidth=0.5, alpha=0.7)

ax.axhline(y=0, color="#ef4444", linewidth=0.8, linestyle="--", alpha=0.6)

ax.legend(loc="upper left", facecolor="#1a1d2e", edgecolor="#3a3d4e",
          labelcolor="#ccc", fontsize=11)

plt.tight_layout()

out_path = os.path.join(script_dir, "lmp_vs_netload.png")
fig.savefig(out_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()
