"""
Capacity factor scatter coloured and sized by LMP ($/MWh).
Shows the correlation between generation levels and wholesale prices.
"""
import json
import time
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
with open("caiso_prices.json") as f:
    price_data = json.load(f)

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

# ── Compute capacity factors with LMP ────────────────────────────────────
def month_to_season(m):
    for s, months in SEASONS.items():
        if m in months:
            return s
    return None

results = {f: {s: {"cf": [], "lmp": []} for s in SEASON_ORDER} for f in FUEL_MAP}

for date_str, fuels in gen_data.items():
    year_str = date_str[:4]
    month = int(date_str[5:7])
    season = month_to_season(month)
    if year_str not in yearly_capacity or season is None:
        continue
    prices = price_data.get(date_str, None)
    if prices is None:
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
            # LMP hours are 1-indexed ("1"-"24")
            lmp_entry = prices.get(str(h + 1), None)
            if lmp_entry is None:
                continue
            lmp = lmp_entry.get("LMP", None)
            if lmp is None:
                continue
            results[fuel][season]["cf"].append(cf)
            results[fuel][season]["lmp"].append(lmp)

# ── LMP colormap & normalization ─────────────────────────────────────────
# Gather all LMP values for percentile clipping
all_lmp = []
for fuel in FUEL_MAP:
    for s in SEASON_ORDER:
        all_lmp.extend(results[fuel][s]["lmp"])
all_lmp = np.array(all_lmp)
lmp_p5, lmp_p95 = np.percentile(all_lmp, [5, 95])
print(f"LMP clip range: {lmp_p5:.1f} to {lmp_p95:.1f} $/MWh")

# Diverging colormap: blue (low/negative) → white (median) → red (high)
lmp_cmap = plt.cm.RdYlBu_r  # red=high, blue=low
lmp_norm = mcolors.TwoSlopeNorm(vmin=lmp_p5, vcenter=np.median(all_lmp), vmax=lmp_p95)

# Size mapping: percentile-based, range [0.3, 5.0]
SIZE_MIN, SIZE_MAX = 0.3, 5.0

def lmp_to_size(lmp_arr):
    clipped = np.clip(lmp_arr, lmp_p5, lmp_p95)
    frac = (clipped - lmp_p5) / (lmp_p95 - lmp_p5 + 1e-9)
    return SIZE_MIN + frac * (SIZE_MAX - SIZE_MIN)

# ── Layout geometry ────────────────────────────────────────────────────────
fuel_order = ["Solar", "Wind", "Natural Gas", "Hydro"]
n_fuels = len(fuel_order)
n_seasons = len(SEASON_ORDER)

group_width = 0.8
strip_width = group_width / n_seasons
max_half_strip = strip_width * 0.45

# ── Plot ───────────────────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"

fig, ax = plt.subplots(figsize=(18, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

def lmp_sorted_jitter(cfs, lmps, x_centre, half_width, n_bins=200):
    """KDE-based violin jitter with points sorted by LMP within each band."""
    kde = gaussian_kde(cfs, bw_method=0.04)

    cf_min, cf_max = cfs.min(), cfs.max()
    bin_edges = np.linspace(cf_min - 1e-9, cf_max + 1e-9, n_bins + 1)
    bin_idx = np.digitize(cfs, bin_edges) - 1

    bin_centres = (bin_edges[:-1] + bin_edges[1:]) / 2
    densities = kde(bin_centres)
    d_max = densities.max()

    x_pos = np.empty_like(cfs, dtype=float)

    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue

        density_here = densities[b]
        width = (density_here / d_max) * half_width if d_max > 0 else half_width

        indices = np.where(mask)[0]
        order = np.argsort(lmps[indices])
        sorted_indices = indices[order]

        n = len(sorted_indices)
        positions = np.linspace(-width, width, n)
        x_pos[sorted_indices] = x_centre + positions

    return x_pos

t_total = time.time()
for i, fuel in enumerate(fuel_order):
    for j, season in enumerate(SEASON_ORDER):
        cfs = np.array(results[fuel][season]["cf"])
        lmps = np.array(results[fuel][season]["lmp"])
        if len(cfs) < 10:
            continue

        t0 = time.time()
        x_centre = i - group_width / 2 + strip_width * (j + 0.5)

        x_pos = lmp_sorted_jitter(cfs, lmps, x_centre, max_half_strip)
        sizes = lmp_to_size(lmps)

        # Sort by LMP ascending so high-price points render on top
        draw_order = np.argsort(lmps)

        ax.scatter(x_pos[draw_order], cfs[draw_order],
                   c=lmps[draw_order], cmap=lmp_cmap, norm=lmp_norm,
                   s=sizes[draw_order], alpha=0.45, edgecolors="none",
                   rasterized=True)

        print(f"  {fuel:>12s} / {season}: {len(cfs):>7,} pts  ({time.time()-t0:.1f}s)")

# ── Axes / labels ──────────────────────────────────────────────────────────
for i, fuel in enumerate(fuel_order):
    ax.text(i, 1.05, fuel, ha="center", va="bottom",
            fontsize=12, fontweight="bold", color=TEXT_COLOR)

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

for i in range(1, n_fuels):
    ax.axvline(i - 0.5, color="#334155", linewidth=0.5, alpha=0.6)

ax.set_ylabel("Capacity Factor", fontsize=13, color=TEXT_COLOR)
ax.set_title("Capacity Factor vs LMP  —  dot size & colour ∝ price  ",
             fontsize=14, fontweight="bold", color=TEXT_COLOR)
ax.set_ylim(-0.02, 1.15)
ax.tick_params(axis="y", colors=TEXT_COLOR)
ax.grid(axis="y", alpha=0.15, color="#ffffff")
for spine in ax.spines.values():
    spine.set_color("#334155")

# Colorbar
sm = plt.cm.ScalarMappable(cmap=lmp_cmap, norm=lmp_norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, pad=0.02, aspect=30)
cbar.set_label("LMP ($/MWh)", fontsize=12, color=TEXT_COLOR)
cbar.ax.tick_params(colors=TEXT_COLOR)
cbar.outline.set_edgecolor("#334155")

print(f"Plotting done in {time.time()-t_total:.1f}s total")
plt.tight_layout()
plt.savefig("capacity_factor_lmp.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved capacity_factor_lmp.png")
