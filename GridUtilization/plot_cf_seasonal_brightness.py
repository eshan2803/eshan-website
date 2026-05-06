"""
Capacity factor scatter – single chart with hour → hue, season → brightness.
Winter is dim, summer is bright, spring/fall in between.
"""
import json, colorsys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
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
    "Winter": [12, 1, 2],
    "Spring": [3, 4, 5],
    "Summer": [6, 7, 8],
    "Fall":   [9, 10, 11],
}
# Brightness multiplier for each season (applied to HSV value channel)
SEASON_BRIGHTNESS = {
    "Winter": 0.45,
    "Spring": 0.70,
    "Summer": 1.00,
    "Fall":   0.70,
}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]

# ── Yearly capacity ───────────────────────────────────────────────────────
yearly_capacity = {}
for year_str, resources in capacity_data.items():
    yearly_capacity[year_str] = {}
    for fuel, cap_keys in FUEL_MAP.items():
        yearly_capacity[year_str][fuel] = sum(resources.get(k, 0) for k in cap_keys)

def month_to_season(m):
    for s, months in SEASONS.items():
        if m in months:
            return s
    return None

# ── Compute CF with hour and season ──────────────────────────────────────
results = {f: {"cf": [], "hour": [], "season": []} for f in FUEL_MAP}

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
            results[fuel]["cf"].append(cf)
            results[fuel]["hour"].append(h)
            results[fuel]["season"].append(season)

# ── Hour colormap (same anchors as website) ────────────────────────────────
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
hour_norm = mcolors.Normalize(vmin=0, vmax=23)

def hour_season_color(hour, season):
    """Return RGBA where hue comes from hour, brightness from season."""
    r, g, b, _ = hour_cmap(hour_norm(hour))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    v *= SEASON_BRIGHTNESS[season]
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (r2, g2, b2)

# ── Plot ───────────────────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
fuel_order = ["Solar", "Wind", "Natural Gas", "Nuclear", "Hydro"]

fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

max_half_width = 0.4

for i, fuel in enumerate(fuel_order):
    cfs = np.array(results[fuel]["cf"])
    hours = np.array(results[fuel]["hour"])
    seasons = results[fuel]["season"]

    if len(cfs) < 10:
        continue

    # KDE jitter
    kde = gaussian_kde(cfs, bw_method=0.04)
    densities = kde(cfs)
    d_max = densities.max()
    densities_norm = densities / d_max if d_max > 0 else np.ones_like(densities)

    raw_jitter = np.random.uniform(-1, 1, size=len(cfs))
    x_pos = i + raw_jitter * densities_norm * max_half_width

    # Compute per-point colour
    colors = np.array([hour_season_color(h, s) for h, s in zip(hours, seasons)])

    ax.scatter(x_pos, cfs, c=colors,
               s=1.0, alpha=0.45, edgecolors="none", rasterized=True)

# ── Axes ──────────────────────────────────────────────────────────────────
ax.set_xticks(range(len(fuel_order)))
ax.set_xticklabels(fuel_order, fontsize=12, color=TEXT_COLOR)
ax.set_ylabel("Capacity Factor", fontsize=13, color=TEXT_COLOR)
ax.set_title("Hourly Capacity Factor by Generator Type  (CAISO 2020-2025)\n"
             "Hue = Hour of Day  |  Brightness = Season",
             fontsize=13, fontweight="bold", color=TEXT_COLOR)
ax.set_ylim(-0.02, 1.15)
ax.tick_params(colors=TEXT_COLOR)
ax.grid(axis="y", alpha=0.15, color="#ffffff")
for spine in ax.spines.values():
    spine.set_color("#334155")

# ── Hour colorbar ─────────────────────────────────────────────────────────
sm = plt.cm.ScalarMappable(cmap=hour_cmap, norm=hour_norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, pad=0.02, aspect=30)
cbar.set_label("Hour of Day", fontsize=12, color=TEXT_COLOR)
cbar.set_ticks([0, 4, 8, 12, 16, 20, 23])
cbar.set_ticklabels(["12a", "4a", "8a", "12p", "4p", "8p", "11p"])
cbar.ax.tick_params(colors=TEXT_COLOR)
cbar.outline.set_edgecolor("#334155")

# ── Brightness legend (season) ────────────────────────────────────────────
# Show small patches at a representative hour (noon = yellow) at each
# season's brightness level
legend_patches = []
for season in SEASON_ORDER:
    r, g, b = hour_season_color(12, season)  # noon yellow at this brightness
    legend_patches.append(
        mpatches.Patch(facecolor=(r, g, b), edgecolor="#334155",
                       label=f"{season} ({int(SEASON_BRIGHTNESS[season]*100)}%)")
    )
leg = ax.legend(handles=legend_patches, loc="upper left", fontsize=9,
                title="Brightness (season)", title_fontsize=9,
                facecolor="#2a2d3e", edgecolor="#334155", labelcolor=TEXT_COLOR)
leg.get_title().set_color(TEXT_COLOR)

plt.tight_layout()
plt.savefig("capacity_factor_seasonal_brightness.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved capacity_factor_seasonal_brightness.png")
