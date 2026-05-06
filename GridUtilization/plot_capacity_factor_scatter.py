"""
Scatter plot of hourly capacity factors by generator type,
colored by hour of day.  Sina-plot style: horizontal jitter
is proportional to the local density of CF values.
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

metadata = gen_data.pop("metadata")

# ── Mapping: EIA fuel type -> capacity_by_resource keys ────────────────────
FUEL_MAP = {
    "Solar":       ["Solar"],
    "Wind":        ["Wind"],
    "Natural Gas": ["Natural Gas - CCGT", "Natural Gas - Peaker",
                    "Natural Gas - Steam", "Natural Gas - ICE"],
    "Nuclear":     ["Nuclear"],
    "Hydro":       ["Water"],
}

# ── Build yearly total capacity for each mapped fuel type ──────────────────
yearly_capacity = {}
for year_str, resources in capacity_data.items():
    yearly_capacity[year_str] = {}
    for fuel, cap_keys in FUEL_MAP.items():
        total = sum(resources.get(k, 0) for k in cap_keys)
        yearly_capacity[year_str][fuel] = total

# ── Compute hourly capacity factors ───────────────────────────────────────
results = {fuel: {"cf": [], "hour": []} for fuel in FUEL_MAP}

for date_str, fuels in gen_data.items():
    year_str = date_str[:4]
    if year_str not in yearly_capacity:
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
            results[fuel]["cf"].append(cf)
            results[fuel]["hour"].append(h)

# ── Custom cyclic colormap matching website ────────────────────────────────
# #3b82f6 (blue) -> #22d3ee (cyan) -> #facc15 (yellow) -> #ef4444 (red) -> #3b82f6
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

anchor_colors = [
    (0.00, hex_to_rgb("#3b82f6")),   # hour 0  – blue
    (0.25, hex_to_rgb("#22d3ee")),   # hour 6  – cyan
    (0.50, hex_to_rgb("#facc15")),   # hour 12 – yellow
    (0.75, hex_to_rgb("#ef4444")),   # hour 18 – red
    (1.00, hex_to_rgb("#3b82f6")),   # hour 24 – blue (wrap)
]
cdict = {"red": [], "green": [], "blue": []}
for pos, (r, g, b) in anchor_colors:
    cdict["red"].append((pos, r, r))
    cdict["green"].append((pos, g, g))
    cdict["blue"].append((pos, b, b))
hour_cmap = mcolors.LinearSegmentedColormap("hour_cycle", cdict, N=256)
norm = mcolors.Normalize(vmin=0, vmax=23)

# ── Plot (dark background) ────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
PANEL_BG = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#ffffff"

fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(PANEL_BG)

fuel_order = ["Solar", "Wind", "Natural Gas", "Nuclear", "Hydro"]
max_half_width = 0.4  # maximum horizontal spread from centre

for i, fuel in enumerate(fuel_order):
    cfs = np.array(results[fuel]["cf"])
    hours = np.array(results[fuel]["hour"])

    # KDE to get density at each point's CF value
    kde = gaussian_kde(cfs, bw_method=0.04)
    densities = kde(cfs)
    # Normalise densities to [0, 1]
    d_max = densities.max()
    if d_max > 0:
        densities_norm = densities / d_max
    else:
        densities_norm = np.ones_like(densities)

    # Jitter: width proportional to local density
    raw_jitter = np.random.uniform(-1, 1, size=len(cfs))
    x_jitter = i + raw_jitter * densities_norm * max_half_width

    ax.scatter(x_jitter, cfs, c=hours, cmap=hour_cmap, norm=norm,
               s=1.0, alpha=0.35, edgecolors="none", rasterized=True)

ax.set_xticks(range(len(fuel_order)))
ax.set_xticklabels(fuel_order, fontsize=12, color=TEXT_COLOR)
ax.set_ylabel("Capacity Factor", fontsize=13, color=TEXT_COLOR)
ax.set_title("Hourly Capacity Factor by Generator Type  (CAISO 2020-2025)",
             fontsize=14, fontweight="bold", color=TEXT_COLOR)
ax.set_ylim(-0.02, 1.15)
ax.tick_params(colors=TEXT_COLOR)
ax.grid(axis="y", alpha=0.15, color=GRID_COLOR)
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
plt.savefig("capacity_factor_scatter.png", dpi=200, bbox_inches="tight",
            facecolor=BG_COLOR)
print("Saved capacity_factor_scatter.png")
