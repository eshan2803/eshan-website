"""
Battery storage discharge in GW (daily peak, colored by % of demand)
with daily peak Ancillary Service price scatter (colored by month) on a secondary y-axis.
Generates one chart per AS type.
"""
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from matplotlib.collections import LineCollection
from datetime import datetime

# ── Load data ──────────────────────────────────────────────────────────────
with open("caiso_battery_daily_peak_mw.json") as f:
    daily_peak_mw_raw = json.load(f)

with open("caiso_battery_daily_peak.json") as f:
    daily_peak_pct_raw = json.load(f)

with open("ancillary_services.json") as f:
    as_data = json.load(f)

AS_TYPES = {
    "RU":  "Regulation Up",
    "RD":  "Regulation Down",
    "SR":  "Spinning Reserve",
    "NR":  "Non-Spinning Reserve",
}

# ── Daily peak battery GW and % (pre-computed from CAISO supply data) ────
peak_bat_dates = np.array([datetime.strptime(d, "%Y-%m-%d") for d in sorted(daily_peak_mw_raw.keys())])
peak_bat_vals  = np.array([daily_peak_mw_raw[d] / 1000.0 for d in sorted(daily_peak_mw_raw.keys())])  # Convert MW to GW
peak_bat_pct = np.array([daily_peak_pct_raw.get(d, 0) for d in sorted(daily_peak_mw_raw.keys())])
print(f"Daily peak battery values: {len(peak_bat_vals):,} days, range {peak_bat_vals.min():.2f}-{peak_bat_vals.max():.2f} GW")

# ── Daily peak AS prices (all types) ─────────────────────────────────────
daily_peak_as = {code: {} for code in AS_TYPES}

for date_str, hours_dict in as_data.items():
    if not isinstance(hours_dict, dict):
        continue
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for h_str, vals in hours_dict.items():
        if not isinstance(vals, dict):
            continue
        for code in AS_TYPES:
            if code in vals:
                price = vals[code]
                if dt not in daily_peak_as[code] or price > daily_peak_as[code][dt]:
                    daily_peak_as[code][dt] = price

# ── Seasonal colormap ────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

season_anchors = [
    (0.00, hex_to_rgb("#60a5fa")),
    (0.17, hex_to_rgb("#34d399")),
    (0.33, hex_to_rgb("#4ade80")),
    (0.50, hex_to_rgb("#facc15")),
    (0.67, hex_to_rgb("#f97316")),
    (0.83, hex_to_rgb("#ef4444")),
    (1.00, hex_to_rgb("#60a5fa")),
]
sdict = {"red": [], "green": [], "blue": []}
for pos, (r, g, b) in season_anchors:
    sdict["red"].append((pos, r, r))
    sdict["green"].append((pos, g, g))
    sdict["blue"].append((pos, b, b))
season_cmap = mcolors.LinearSegmentedColormap("season", sdict, N=256)
month_norm = mcolors.Normalize(vmin=1, vmax=13)

BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
# Battery line colormap: % of demand (0-100%)
battery_cmap = plt.cm.plasma
battery_norm = mcolors.Normalize(vmin=0, vmax=100)

# ── Generate one chart per AS type ────────────────────────────────────────
for code, label in AS_TYPES.items():
    peak_dates = np.array(sorted(daily_peak_as[code].keys()))
    peak_vals = np.array([daily_peak_as[code][d] for d in peak_dates])

    if len(peak_vals) < 10:
        print(f"  {code} ({label}): not enough data, skipping")
        continue

    p99 = np.percentile(peak_vals, 99)
    print(f"  {code} ({label}): {len(peak_vals)} days, "
          f"range ${peak_vals.min():.2f}-${peak_vals.max():.1f}, p99=${p99:.1f}")

    fig, ax1 = plt.subplots(figsize=(16, 6), facecolor=BG_COLOR,
                            layout="constrained")
    ax1.set_facecolor(BG_COLOR)

    # ── Left axis: battery line colored by % of demand ───────────────────
    x_num = mdates.date2num(peak_bat_dates)
    points = np.column_stack([x_num, peak_bat_vals]).reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    seg_pct = (peak_bat_pct[:-1] + peak_bat_pct[1:]) / 2.0

    lc = LineCollection(segments, cmap=battery_cmap, norm=battery_norm,
                        linewidths=1.2, alpha=0.9, zorder=5)
    lc.set_array(seg_pct)
    ax1.add_collection(lc)
    ax1.set_xlim(x_num[0], x_num[-1])
    ax1.set_ylim(0, peak_bat_vals.max() * 1.08)

    ax1.set_ylabel("Daily Peak Battery Discharge (GW)",
                   fontsize=12, color="#fbbf24", fontweight="bold")
    ax1.tick_params(axis="y", colors="#fbbf24")

    # ── Right axis: AS price scatter (colored by month) ─────────────────
    ax2 = ax1.twinx()
    ax2.set_facecolor("none")

    # Color scatter by month
    months_as = np.array([d.month for d in peak_dates])

    ax2.scatter(peak_dates, peak_vals,
                c=months_as, cmap=season_cmap, norm=month_norm,
                s=8.0, alpha=0.7,
                edgecolors="none", rasterized=True, zorder=3)

    ax2.set_ylim(0, p99 * 1.1)
    ax2.set_ylabel(f"Daily Peak {label} ($/MWh)",
                   fontsize=12, color="#f97316")
    ax2.tick_params(axis="y", colors="#f97316")
    for spine in ax2.spines.values():
        spine.set_color("#334155")

    # ── X-axis / styling ─────────────────────────────────────────────────
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    ax1.tick_params(axis="x", colors=TEXT_COLOR, labelsize=10)

    last_data_date = min(sorted(daily_peak_mw_raw.keys())[-1], sorted(as_data.keys())[-1])
    last_data_label = datetime.strptime(last_data_date, "%Y-%m-%d").strftime("%B %d, %Y")
    ax1.set_title(
        f"Battery Storage vs {label} Price  |  Updated through {last_data_label}",
        fontsize=14, fontweight="bold", color=TEXT_COLOR)
    ax1.grid(axis="y", alpha=0.15, color="#ffffff")
    ax1.grid(axis="x", alpha=0.08, color="#ffffff")
    for spine in ax1.spines.values():
        spine.set_color("#334155")

    # ── Colorbars ─────────────────────────────────────────────────────────
    # Battery % of demand colorbar
    sm_battery = plt.cm.ScalarMappable(cmap=battery_cmap, norm=battery_norm)
    sm_battery.set_array([])
    cbar1 = fig.colorbar(sm_battery, ax=[ax1, ax2], pad=0.02,
                         aspect=30, fraction=0.015)
    cbar1.set_label("Line: Battery % of Demand", fontsize=9, color="#fbbf24")
    cbar1.set_ticks([0, 20, 40, 60, 80, 100])
    cbar1.ax.tick_params(colors=TEXT_COLOR, labelsize=7)
    cbar1.outline.set_edgecolor("#334155")

    # Month colorbar for scatter
    sm_season = plt.cm.ScalarMappable(cmap=season_cmap, norm=month_norm)
    sm_season.set_array([])
    cbar2 = fig.colorbar(sm_season, ax=[ax1, ax2], pad=0.01,
                         aspect=30, fraction=0.015)
    cbar2.set_label(f"Scatter: Month", fontsize=9, color="#f97316")
    cbar2.set_ticks([1, 3, 5, 7, 9, 11])
    cbar2.set_ticklabels(["Jan", "Mar", "May", "Jul", "Sep", "Nov"])
    cbar2.ax.tick_params(colors=TEXT_COLOR, labelsize=7)
    cbar2.outline.set_edgecolor("#334155")

    fname = f"battery_vs_{code.lower()}.png"
    plt.savefig(fname, dpi=200, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  Saved {fname}")

print("Done.")
