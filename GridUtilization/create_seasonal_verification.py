"""
Create a simple verification chart showing the 2024 seasonal pattern clearly
"""
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Load data
with open("caiso_prices.json") as f:
    price_data = json.load(f)

with open("caiso_solar_daily_generation_mwh.json") as f:
    solar_mwh = json.load(f)

# Focus on 2024 months only
months_2024 = [f"2024-{m:02d}" for m in range(1, 13)]

# Calculate monthly data
monthly_neg_hours = []
monthly_avg_solar = []
month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

for m_key in months_2024:
    # Count negative hours
    neg_count = 0
    for date_str in sorted(price_data.keys()):
        if date_str.startswith(m_key):
            day_data = price_data[date_str]
            for hr_key in range(1, 25):
                hr_data = day_data.get(str(hr_key), {})
                lmp = hr_data.get("LMP")
                if lmp is not None and lmp < 0:
                    neg_count += 1
    monthly_neg_hours.append(neg_count)

    # Average solar
    solar_vals = [solar_mwh[d]/1000 for d in solar_mwh if d.startswith(m_key)]
    monthly_avg_solar.append(np.mean(solar_vals) if solar_vals else 0)

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), facecolor="#0f1117")

for ax in [ax1, ax2]:
    ax.set_facecolor("#1a1d2e")
    ax.tick_params(colors="#888", labelsize=11)
    for spine in ax.spines.values():
        spine.set_color("#3a3d4e")
    ax.grid(True, color="#2a2d3e", linewidth=0.5, alpha=0.7)

# Top panel: Negative hours
bars = ax1.bar(range(12), monthly_neg_hours, color="#a855f7", alpha=0.8, edgecolor="none")
ax1.set_ylabel("Negative LMP Hours", fontsize=13, color="#a855f7", fontweight="bold")
ax1.set_title("2024 California Grid: Why Spring Has Most Negative Prices",
              fontsize=15, fontweight="bold", color="#fff", pad=15)
ax1.set_xticks(range(12))
ax1.set_xticklabels(month_labels, fontsize=11, color="#888")
ax1.tick_params(axis="y", colors="#a855f7")

# Highlight spring
ax1.axvspan(2.5, 5.5, alpha=0.15, color="#10b981", zorder=0, label="Spring: High neg prices")
ax1.axvspan(5.5, 8.5, alpha=0.15, color="#f59e0b", zorder=0, label="Summer: Low neg prices")

# Bottom panel: Solar generation
line = ax2.plot(range(12), monthly_avg_solar, color="#10b981", linewidth=3, marker="o",
                markersize=8, markerfacecolor="#10b981", markeredgewidth=0, label="Avg Daily Solar")
ax2.fill_between(range(12), 0, monthly_avg_solar, color="#10b981", alpha=0.15)
ax2.set_ylabel("Avg Daily Solar Generation (GWh)", fontsize=13, color="#10b981", fontweight="bold")
ax2.set_xlabel("Month", fontsize=13, color="#888", fontweight="bold")
ax2.set_xticks(range(12))
ax2.set_xticklabels(month_labels, fontsize=11, color="#888")
ax2.tick_params(axis="y", colors="#10b981")

# Highlight same seasons
ax2.axvspan(2.5, 5.5, alpha=0.15, color="#10b981", zorder=0)
ax2.axvspan(5.5, 8.5, alpha=0.15, color="#f59e0b", zorder=0)

# Add annotations
ax1.annotate("Spring Peak\nGood solar\n+ Low demand\n= Oversupply",
             xy=(4, max(monthly_neg_hours)), xytext=(4, max(monthly_neg_hours)*1.15),
             ha="center", fontsize=10, color="#10b981", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1d2e", edgecolor="#10b981", linewidth=2))

ax1.annotate("Summer Drop\nBest solar\n+ High AC demand\n= Absorbed",
             xy=(6.5, monthly_neg_hours[6]), xytext=(6.5, max(monthly_neg_hours)*0.4),
             ha="center", fontsize=10, color="#f59e0b", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1d2e", edgecolor="#f59e0b", linewidth=2))

ax2.annotate("Solar peaks\nAFTER\nneg price drop",
             xy=(6, monthly_avg_solar[6]), xytext=(8.5, monthly_avg_solar[6]*0.85),
             ha="center", fontsize=10, color="#f59e0b", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1d2e", edgecolor="#f59e0b", linewidth=2),
             arrowprops=dict(arrowstyle="->", color="#f59e0b", lw=2))

plt.tight_layout()
plt.savefig("seasonal_verification_2024.png", dpi=200, facecolor="#0f1117", bbox_inches="tight")
print("Saved seasonal_verification_2024.png")
print(f"\nKey insight: May has {monthly_neg_hours[4]} neg hours with {monthly_avg_solar[4]:.1f} GWh solar")
print(f"             July has {monthly_neg_hours[6]} neg hours with {monthly_avg_solar[6]:.1f} GWh solar (HIGHER)")
plt.close()
