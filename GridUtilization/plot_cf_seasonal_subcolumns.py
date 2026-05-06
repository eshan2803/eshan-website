"""
Capacity factor scatter – sub-columns per season within each fuel type.
4 narrow sina-strips (Win | Spr | Sum | Fall) per generator, colored by hour.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.stats import gaussian_kde

# ── Load data ──────────────────────────────────────────────────────────────
with open("capacity_by_resource.json") as f:
    capacity_data = json.load(f)
with open("eia_generation.json") as f:
    gen_data = json.load(f)
gen_data.pop("metadata")

FUEL_MAP = {
    "Solar":       ["Solar"],
    "Wind":        ["Wind"],
    "Natural Gas": ["Natural Gas - CCGT", "Natural Gas - Peaker",
                    "Natural Gas - Steam", "Natural Gas - ICE"],
    "Nuclear":     ["Nuclear"],
    "Hydro":       ["Water"],
}

SEASONS = {
    "Win": [12, 1, 2],
    "Spr": [3, 4, 5],
    "Sum": [6, 7, 8],
    "Fall": [9, 10, 11],
}
SEASON_ORDER = ["Win", "Spr", "Sum", "Fall"]

# ── Yearly capacity ───────────────────────────────────────────────────────
yearly_capacity = {}
for year_str, resources in capacity_data.items():
    yearly_capacity[year_str] = {}
    for fuel, cap_keys in FUEL_MAP.items():
        yearly_capacity[year_str][fuel] = sum(resources.get(k, 0) for k in cap_keys)

# ── Compute capacity factors with season tag ──────────────────────────────
def month_to_season(m):
    for s, months in SEASONS.items():
        if m in months:
            return s
    return None

# results[fuel][season] = {"cf": [], "hour": []}
results = {f: {s: {"cf": [], "hour": []} for s in SEASON_ORDER} for f in FUEL_MAP}

for date_str, fuels in gen_data.items():
    year_str = date_str[:4]
    month = int(date_str[5:7])
    season = month_to_season(month)
    if year_str not in yearly_capacity or season is None:
        continue
    for fuel in FUEL_MAP:
        cap = yearly_capacity[year_str].get(fuel, 0)
        if cap <= 0:
            continue
        hourly_gen = fuels.get(fuel, None)
        if hourly_gen is None:
            continue
        for h, gen_mw in enumerate(hourly_gen):
            cf = gen_mw / cap
            if cf < 0:
                continue
            results[fuel][season]["cf"].append(cf)
            results[fuel][season]["hour"].append(h)

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
fuel_order = ["Solar", "Wind", "Natural Gas", "Hydro"]
n_fuels = len(fuel_order)
n_seasons = len(SEASON_ORDER)

# Each fuel group occupies x ∈ [i - group_half, i + group_half]
# Within that, 4 sub-strips with small gaps
group_width = 0.8          # total width per fuel group
strip_width = group_width / n_seasons  # width of each season strip
max_half_strip = strip_width * 0.45    # max jitter radius within a strip

# ── Plot ───────────────────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"

fig, ax = plt.subplots(figsize=(18, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

for i, fuel in enumerate(fuel_order):
    for j, season in enumerate(SEASON_ORDER):
        cfs = np.array(results[fuel][season]["cf"])
        hours = np.array(results[fuel][season]["hour"])
        if len(cfs) < 10:
            continue

        # Centre of this sub-strip
        x_centre = i - group_width / 2 + strip_width * (j + 0.5)

        # KDE-based density jitter
        kde = gaussian_kde(cfs, bw_method=0.04)
        densities = kde(cfs)
        d_max = densities.max()
        densities_norm = densities / d_max if d_max > 0 else np.ones_like(densities)

        raw_jitter = np.random.uniform(-1, 1, size=len(cfs))
        x_pos = x_centre + raw_jitter * densities_norm * max_half_strip

        ax.scatter(x_pos, cfs, c=hours, cmap=hour_cmap, norm=norm,
                   s=0.6, alpha=0.35, edgecolors="none", rasterized=True)

# ── Axes / labels ──────────────────────────────────────────────────────────
# Fuel names as text labels inside chart area, just above y=1.0
for i, fuel in enumerate(fuel_order):
    ax.text(i, 1.05, fuel, ha="center", va="bottom",
            fontsize=12, fontweight="bold", color=TEXT_COLOR)

# Season labels on BOTTOM (only axis)
minor_positions = []
minor_labels = []
for i in range(n_fuels):
    for j, season in enumerate(SEASON_ORDER):
        x = i - group_width / 2 + strip_width * (j + 0.5)
        minor_positions.append(x)
        minor_labels.append(season)
ax.set_xticks(minor_positions)
ax.set_xticklabels(minor_labels, fontsize=7, color="#94a3b8")
ax.tick_params(which="major", length=0, colors="#94a3b8", pad=4)

# Light vertical separators between fuel groups
for i in range(1, n_fuels):
    ax.axvline(i - 0.5, color="#334155", linewidth=0.5, alpha=0.6)

ax.set_ylabel("Capacity Factor", fontsize=13, color=TEXT_COLOR)
ax.set_title("Hourly Capacity Factor by Generator Type & Season  (CAISO 2020-2025)",
             fontsize=14, fontweight="bold", color=TEXT_COLOR)
ax.set_ylim(-0.02, 1.15)
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

plt.tight_layout()
plt.savefig("capacity_factor_seasonal_subcolumns.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved capacity_factor_seasonal_subcolumns.png")
