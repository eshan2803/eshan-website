"""
Hourly ramp rate (MW/hr) scatter by generator type.
Ramp rate = Generation[h] - Generation[h-1], computed across consecutive
hours (within each day and across day boundaries).
Non-zero values only.  Sina-plot style, one column per fuel.
"""
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.stats import gaussian_kde
from datetime import datetime

# ── Load data ──────────────────────────────────────────────────────────────
with open("eia_generation.json") as f:
    gen_data = json.load(f)
gen_data.pop("metadata")

# Battery data: EIA "Other" with geothermal subtracted
with open("battery_charging.json") as f:
    battery_raw = json.load(f)
battery_raw.pop("metadata", None)

GEOTHERMAL_BASELINE_MW = 690

# Build battery hourly dict: date -> 24-element list of net battery MW
battery_hourly = {}
for date_str, hourly in battery_raw.items():
    if not isinstance(hourly, list):
        continue
    battery_hourly[date_str] = [
        (v - GEOTHERMAL_BASELINE_MW) if v is not None else None
        for v in hourly
    ]

# Fuel types to plot (EIA-930 names)
FUEL_ORDER = ["Solar", "Wind", "Natural Gas", "Hydro", "Battery", "Nuclear"]
# EIA-930 key for each fuel (where it differs from display name)
FUEL_EIA_KEY = {}  # all EIA fuels match by name; Battery handled separately

# ── Compute hourly ramp rates ─────────────────────────────────────────────
all_dates = sorted(gen_data.keys())

# results[fuel] = {"ramp": [], "hour": []}
results = {f: {"ramp": [], "hour": []} for f in FUEL_ORDER}

for d_idx, date_str in enumerate(all_dates):
    for fuel in FUEL_ORDER:
        # Battery uses its own data source
        if fuel == "Battery":
            hourly = battery_hourly.get(date_str, None)
        else:
            eia_key = FUEL_EIA_KEY.get(fuel, fuel)
            hourly = gen_data[date_str].get(eia_key, None)
        if hourly is None:
            continue

        # Intra-day ramps: hour 1..23 vs previous hour
        for h in range(1, len(hourly)):
            if hourly[h] is None or hourly[h - 1] is None:
                continue
            ramp = hourly[h] - hourly[h - 1]
            if ramp == 0:
                continue
            results[fuel]["ramp"].append(ramp)
            results[fuel]["hour"].append(h)

        # Cross-day ramp: hour 0 of this day vs hour 23 of previous day
        if d_idx > 0:
            prev_date = all_dates[d_idx - 1]
            d_cur = datetime.strptime(date_str, "%Y-%m-%d")
            d_prev = datetime.strptime(prev_date, "%Y-%m-%d")
            if (d_cur - d_prev).days == 1:
                if fuel == "Battery":
                    prev_hourly = battery_hourly.get(prev_date, None)
                else:
                    eia_key = FUEL_EIA_KEY.get(fuel, fuel)
                    prev_hourly = gen_data[prev_date].get(eia_key, None)
                if prev_hourly is not None and len(prev_hourly) == 24:
                    if hourly[0] is not None and prev_hourly[23] is not None:
                        ramp = hourly[0] - prev_hourly[23]
                        if ramp != 0:
                            results[fuel]["ramp"].append(ramp)
                            results[fuel]["hour"].append(0)

# ── Cyclic hour colormap (matches website) ─────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

anchor_colors = [
    (0.00, hex_to_rgb("#3b82f6")),
    (0.25, hex_to_rgb("#22d3ee")),
    (0.50, hex_to_rgb("#facc15")),
    (0.75, hex_to_rgb("#ef4444")),
    (1.00, hex_to_rgb("#3b82f6")),
]
cdict = {"red": [], "green": [], "blue": []}
for pos, (r, g, b) in anchor_colors:
    cdict["red"].append((pos, r, r))
    cdict["green"].append((pos, g, g))
    cdict["blue"].append((pos, b, b))
hour_cmap = mcolors.LinearSegmentedColormap("hour_cycle", cdict, N=256)
norm = mcolors.Normalize(vmin=0, vmax=23)

# ── Layout geometry ────────────────────────────────────────────────────────
n_fuels = len(FUEL_ORDER)
max_half_width = 0.4

# ── Plot ───────────────────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"

fig, ax = plt.subplots(figsize=(14, 8), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

def color_sorted_jitter(values, hours, x_centre, half_width, n_bins=1500):
    """Assign x-positions so that within each y-band, points are sorted
    by hour (colour).  This groups similar colours together at each
    y-level while preserving the overall density-driven shape."""
    kde = gaussian_kde(values, bw_method=0.04)

    v_min, v_max = values.min(), values.max()
    bin_edges = np.linspace(v_min - 1e-9, v_max + 1e-9, n_bins + 1)
    bin_idx = np.digitize(values, bin_edges) - 1

    bin_centres = (bin_edges[:-1] + bin_edges[1:]) / 2
    densities = kde(bin_centres)
    d_max = densities.max()

    x_pos = np.empty_like(values, dtype=float)

    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue

        density_here = densities[b]
        width = (density_here / d_max) * half_width if d_max > 0 else half_width

        indices = np.where(mask)[0]
        order = np.argsort(hours[indices])
        sorted_indices = indices[order]

        n = len(sorted_indices)
        positions = np.linspace(-width, width, n)
        x_pos[sorted_indices] = x_centre + positions

    return x_pos

t_total = time.time()
for i, fuel in enumerate(FUEL_ORDER):
    ramps = np.array(results[fuel]["ramp"])
    hours = np.array(results[fuel]["hour"])
    if len(ramps) < 10:
        continue

    t0 = time.time()
    x_pos = color_sorted_jitter(ramps, hours, i, max_half_width)
    print(f"  {fuel:>12s}: {len(ramps):>7,} pts  ({time.time()-t0:.1f}s)")

    ax.scatter(x_pos, ramps, c=hours, cmap=hour_cmap, norm=norm,
               s=1.0, alpha=0.35, edgecolors="none", rasterized=True)

# ── Axes / labels ──────────────────────────────────────────────────────────
# Zero line
ax.axhline(0, color="#94a3b8", linewidth=0.6, alpha=0.5)

# Fuel labels at top of chart area (using axes transform for x, data for y)
y_top = ax.get_ylim()[1]
for i, fuel in enumerate(FUEL_ORDER):
    ax.text(i, y_top * 0.95, fuel, ha="center", va="top",
            fontsize=12, fontweight="bold", color=TEXT_COLOR)

# Remove bottom x-tick labels
ax.set_xticks(range(n_fuels))
ax.set_xticklabels([""] * n_fuels)
ax.tick_params(axis="x", length=0)

ax.set_ylabel("Ramp Rate (MW/hr)", fontsize=13, color=TEXT_COLOR)
ax.set_title("Hourly Ramp Rate by Generator Type  ",
             fontsize=14, fontweight="bold", color=TEXT_COLOR)
ax.tick_params(axis="y", colors=TEXT_COLOR)
ax.grid(axis="y", alpha=0.15, color="#ffffff")
for spine in ax.spines.values():
    spine.set_color("#334155")

# Colorbar
sm = plt.cm.ScalarMappable(cmap=hour_cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, pad=0.02, aspect=30)
cbar.set_label("Hour of Day", fontsize=12, color=TEXT_COLOR)
cbar.set_ticks([0, 4, 8, 12, 16, 20, 23])
cbar.set_ticklabels(["12a", "4a", "8a", "12p", "4p", "8p", "11p"])
cbar.ax.tick_params(colors=TEXT_COLOR)
cbar.outline.set_edgecolor("#334155")

print(f"Plotting done in {time.time()-t_total:.1f}s total")
plt.tight_layout()
plt.savefig("ramp_rate_seasonal.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved ramp_rate_seasonal.png")
