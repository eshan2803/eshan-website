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
print("Loading comprehensive CSV and computing 40:40:20 hourly averages...")
df = pd.read_csv(CSV_FILE, usecols=['timestamp', 'lmp', 'battery_charging_mw'])
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)
df['lmp'] = pd.to_numeric(df['lmp'], errors='coerce')
df['battery_charging_mw'] = pd.to_numeric(df['battery_charging_mw'], errors='coerce')

# Generate True Hourly Averages across 12 5-min intervals
hourly_df = df.resample('1h').mean()
last_data_date = hourly_df.dropna(subset=['lmp']).index.max()
last_data_label = last_data_date.strftime("%B %d, %Y") if pd.notna(last_data_date) else "Unknown"

# ── Extract negative prices ──
monthly_neg_count = defaultdict(int)
monthly_total_count = defaultdict(int)
neg_by_year = defaultdict(list)

# Also accumulate battery charging daily (in GWh)
daily_battery_mwh = defaultdict(float)

for ts, row in hourly_df.iterrows():
    year = ts.year
    month = ts.month
    m_key = f"{year}-{month:02d}"
    
    # Track Battery
    if not pd.isna(row['battery_charging_mw']):
        # mw average for the hour = mwh for the hour
        daily_battery_mwh[ts.strftime("%Y-%m-%d")] += max(row['battery_charging_mw'], 0)
        
    lmp = row['lmp']
    if pd.isna(lmp):
        continue
        
    monthly_total_count[m_key] += 1
    
    if lmp < 0:
        monthly_neg_count[m_key] += 1
        neg_by_year[year].append(lmp)

battery_dates = []
battery_gwh = []
for date_str in sorted(daily_battery_mwh.keys()):
    battery_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    battery_gwh.append(daily_battery_mwh[date_str] / 1000.0)

battery_dates = np.array(battery_dates)
battery_gwh = np.array(battery_gwh)

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
    if len(lmps) < 10:
        continue

    kde = gaussian_kde(lmps, bw_method=0.06)
    densities = kde(lmps)
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
    frac = (yr - 2020) / 5.0
    bar_colors.append(plt.cm.cool(frac))

bars = ax2.bar(p2_indices, p2_neg_counts, color=bar_colors, alpha=0.7,
               width=0.8, label="Negative LMP Hours")
ax2.set_ylabel("Hours with Negative LMP", color=ACCENT, fontsize=12)
ax2.tick_params(axis="y", colors=ACCENT)

ax2b = ax2.twinx()
ax2b.set_facecolor("none")

month_to_index = {m_key: i for i, m_key in enumerate(p2_m_keys)}

battery_x_pos = []
for bdate in battery_dates:
    m_key = f"{bdate.year}-{bdate.month:02d}"
    if m_key in month_to_index:
        bar_index = month_to_index[m_key]
        battery_x_pos.append(bar_index + bdate.day / 30.0)
    else:
        battery_x_pos.append(np.nan)

battery_x_pos = np.array(battery_x_pos)

ax2b.plot(battery_x_pos, battery_gwh, color=ACCENT_YELLOW, linewidth=1.2,
          alpha=0.8, label="Daily Charging (GWh)", zorder=5)
ax2b.fill_between(battery_x_pos, 0, battery_gwh, color=ACCENT_YELLOW,
                   alpha=0.08)
ax2b.set_ylabel("Daily Battery Charging (GWh)", color=ACCENT_YELLOW,
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

ax2.set_title("Negative Prices Track Battery Growth on the CAISO Grid\n"
              "Monthly Negative-LMP Hours vs Daily Battery Charging Energy",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

lines_bars = [bars]
lines_line = ax2b.get_lines()
labels = ["Negative LMP Hours", "Daily Charging (GWh)"]
ax2.legend(lines_bars + lines_line, labels,
           fontsize=10, facecolor=BG_INNER, edgecolor=SPINE_COLOR,
           labelcolor=TEXT_COLOR, loc="upper left")

# ── Save ──
out_path = os.path.join(script_dir, "negative_price_analysis.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()
