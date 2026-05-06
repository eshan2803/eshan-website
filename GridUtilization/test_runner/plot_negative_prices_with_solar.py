import json
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from scipy.stats import gaussian_kde
import pandas as pd
from datetime import datetime as dt

script_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")

# ── Read Comprehensive CSV and Compute Hourly Averages ──
print("Loading comprehensive CSV and computing hourly averages...")
# Use parse_dates and engine='c' for speed
df = pd.read_csv(CSV_FILE, usecols=['timestamp', 'lmp', 'solar_mw', 'battery_charging_mw'], parse_dates=['timestamp'])
df.set_index('timestamp', inplace=True)

# Ensure numeric types
for col in ['lmp', 'solar_mw', 'battery_charging_mw']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Generate True Hourly Averages across 12 5-min intervals
hourly_df = df.resample('1h').mean()
last_data_date = hourly_df.dropna(subset=['lmp']).index.max()
last_data_label = last_data_date.strftime("%B %d, %Y") if pd.notna(last_data_date) else "Unknown"

# ── Extract metrics using vectorized Pandas operations ──
print("Processing metrics...")
# Extract year, month, and date string for grouping
hourly_df['year'] = hourly_df.index.year
hourly_df['month'] = hourly_df.index.month
hourly_df['m_key'] = hourly_df.index.strftime('%Y-%m')
hourly_df['date_str'] = hourly_df.index.strftime('%Y-%m-%d')

# Track Solar and Battery daily (in GWh)
# max(0) ensures we don't count negative generation (which happens rarely in raw data)
daily_solar_mwh = hourly_df.groupby('date_str')['solar_mw'].sum().clip(lower=0)
daily_battery_mwh = hourly_df.groupby('date_str')['battery_charging_mw'].sum().clip(lower=0)

# Negative prices tracking
neg_mask = (hourly_df['lmp'] < 0)
monthly_neg_count_ser = hourly_df[neg_mask].groupby('m_key').size()
# Fix: Ensure grouper matches the length of the series being grouped
monthly_total_count_ser = hourly_df.dropna(subset=['lmp']).groupby('m_key').size()

# Convert series to dictionaries as needed for the rest of the script
monthly_neg_count = monthly_neg_count_ser.to_dict()
monthly_total_count = monthly_total_count_ser.to_dict()

# Group negative LMPs by year
neg_by_year = hourly_df[neg_mask].groupby('year')['lmp'].apply(list).to_dict()

# Prepare solar/battery arrays
sorted_dates = sorted(daily_solar_mwh.index)
solar_dates = np.array([dt.strptime(d, "%Y-%m-%d") for d in sorted_dates])
solar_gwh = np.array([daily_solar_mwh[d] / 1000.0 for d in sorted_dates])
battery_gwh = np.array([daily_battery_mwh[d] / 1000.0 for d in sorted_dates])

m_keys = sorted(monthly_total_count.keys())
years = sorted(neg_by_year.keys())

p2_m_keys = sorted(m_keys)
p2_neg_counts = [monthly_neg_count.get(m, 0) for m in p2_m_keys]

# ── Style constants ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT = "#3b82f6"
ACCENT_RED = "#ef4444"
ACCENT_YELLOW = "#facc15"
ACCENT_CYAN = "#22d3ee"
DOT_COLOR = "#22d3ee"

# ── Figure setup ──
print("Generating chart panels...")
fig, axes = plt.subplots(2, 1, figsize=(16, 14), facecolor=BG_OUTER,
                         gridspec_kw={"hspace": 0.32})

for ax in axes:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# Panel 1: Scatter plot
ax1 = axes[0]
max_half_width = 0.38

for i, yr in enumerate(years):
    lmps = np.array(neg_by_year[yr])
    if len(lmps) < 2: # gaussian_kde needs at least 2 points
        continue

    # Optimized KDE: Evaluate on a grid and interpolate
    # This is MUCH faster than evaluating at every point for large N
    kde = gaussian_kde(lmps, bw_method=0.06)
    
    # Create evaluation grid
    l_min, l_max = lmps.min(), lmps.max()
    if l_min == l_max:
        densities = np.ones_like(lmps)
    else:
        grid = np.linspace(l_min, l_max, 200)
        grid_densities = kde(grid)
        densities = np.interp(lmps, grid, grid_densities)
        
    d_max = densities.max()
    densities_norm = densities / d_max if d_max > 0 else np.ones_like(densities)

    raw_jitter = np.random.uniform(-1, 1, size=len(lmps))
    x_pos = i + raw_jitter * densities_norm * max_half_width

    ax1.scatter(x_pos, lmps, color=DOT_COLOR,
                s=5, alpha=0.7, edgecolors="none", rasterized=True)

    mean_lmp = lmps.mean()
    half_w = max_half_width * 0.85
    ax1.hlines(mean_lmp, i - half_w, i + half_w,
               colors="white", linewidths=2, zorder=5)
    ax1.text(i, mean_lmp + 1, f"${mean_lmp:.1f}",
             ha="center", va="bottom", fontsize=9, color="white",
             fontweight="bold", zorder=6)

    ax1.text(i, 2, f"n={len(lmps):,}",
             ha="center", va="bottom", fontsize=9, color=DOT_COLOR,
             alpha=0.9)

ax1.set_xticks(range(len(years)))
ax1.set_xticklabels([str(yr) for yr in years], fontsize=11, color="#888")
ax1.set_ylabel("Negative LMP ($/MWh)", color=DOT_COLOR, fontsize=12)
ax1.tick_params(axis="y", colors=DOT_COLOR)
ax1.set_title(f"Magnitude of Negative Prices by Year\n"
              f"Updated through {last_data_label}",
              color="#fff", fontsize=14, fontweight="bold", pad=12)
ax1.axhline(0, color=ACCENT_RED, linewidth=0.8, linestyle="--", alpha=0.5)

# Panel 2
ax2 = axes[1]
p2_indices = np.arange(len(p2_m_keys))

bar_colors = []
for m in p2_m_keys:
    yr = int(m[:4])
    frac = max(0, min(1, (yr - 2020) / 5.0))
    bar_colors.append(plt.cm.cool(frac))

bars = ax2.bar(p2_indices, p2_neg_counts, color=bar_colors, alpha=0.7,
               width=0.8, label="Negative LMP Hours")
ax2.set_ylabel("Hours with Negative LMP", color=ACCENT, fontsize=12)
ax2.tick_params(axis="y", colors=ACCENT)

ax2b = ax2.twinx()
ax2b.set_facecolor("none")

month_to_index = {m_key: i for i, m_key in enumerate(p2_m_keys)}

solar_x_pos = []
for bdate in solar_dates:
    m_key = f"{bdate.year}-{bdate.month:02d}"
    if m_key in month_to_index:
        bar_index = month_to_index[m_key]
        solar_x_pos.append(bar_index + bdate.day / 30.0)
    else:
        solar_x_pos.append(np.nan)

solar_x_pos = np.array(solar_x_pos)

ax2b.plot(solar_x_pos, solar_gwh, color=ACCENT_YELLOW, linewidth=1.2,
          alpha=0.8, label="Daily Solar Gen (GWh)", zorder=5)
ax2b.fill_between(solar_x_pos, 0, solar_gwh, color=ACCENT_YELLOW,
                   alpha=0.08)
                   
ax2b.plot(solar_x_pos, battery_gwh, color="#10b981", linewidth=1.5,
          alpha=0.9, label="Daily Batt Charge (GWh)", zorder=6)
ax2b.fill_between(solar_x_pos, 0, battery_gwh, color="#10b981",
                   alpha=0.15)

ax2b.set_ylabel("Daily Generation / Charging (GWh)", color=TEXT_COLOR,
                fontsize=12)
ax2b.tick_params(axis="y", colors=ACCENT_YELLOW)
for spine in ax2b.spines.values():
    spine.set_color(SPINE_COLOR)

ax2.set_ylim(bottom=0)
ax2b.set_ylim(bottom=0)

tick_pos = []
tick_lab = []
for i, m in enumerate(p2_m_keys):
    if m.endswith("-01"):
        tick_pos.append(i)
        tick_lab.append(m[:4])
ax2.set_xticks(tick_pos)
ax2.set_xticklabels(tick_lab, fontsize=11, color="#888")

ax2.set_title("Negative Prices Track Solar and Battery Growth on the CAISO Grid\n"
              "Monthly Negative-LMP Hours vs Daily Solar & Battery Energy",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

# Legend handling
lines_bars = [bars]
lines_line1 = [ax2b.get_lines()[0]]
lines_line2 = [ax2b.get_lines()[1]]
labels = ["Negative LMP Hours", "Daily Solar Gen (GWh)", "Daily Batt Charge (GWh)"]
ax2.legend(lines_bars + lines_line1 + lines_line2, labels,
           fontsize=10, facecolor=BG_INNER, edgecolor=SPINE_COLOR,
           labelcolor=TEXT_COLOR, loc="upper left")

# ── Save ──
out_path = os.path.join(script_dir, "negative_price_analysis_with_solar.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()
