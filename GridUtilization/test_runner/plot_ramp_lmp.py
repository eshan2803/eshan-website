"""
Ramp rate scatter coloured and sized by LMP ($/MWh).
Shows the correlation between ramping behaviour and wholesale prices.
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
with open("caiso_prices.json") as f:
    price_data = json.load(f)

# Battery data
with open("battery_charging.json") as f:
    battery_raw = json.load(f)
battery_raw.pop("metadata", None)

GEOTHERMAL_BASELINE_MW = 690
battery_hourly = {}
for date_str, hourly in battery_raw.items():
    if not isinstance(hourly, list):
        continue
    battery_hourly[date_str] = [
        (v - GEOTHERMAL_BASELINE_MW) if v is not None else None
        for v in hourly
    ]

FUEL_ORDER = ["Solar", "Wind", "Natural Gas", "Hydro", "Battery", "Nuclear"]
FUEL_EIA_KEY = {}

# ── Compute hourly ramp rates with LMP ───────────────────────────────────
all_dates = sorted(gen_data.keys())
results = {f: {"ramp": [], "lmp": []} for f in FUEL_ORDER}

for d_idx, date_str in enumerate(all_dates):
    prices = price_data.get(date_str, None)
    if prices is None:
        continue
    for fuel in FUEL_ORDER:
        if fuel == "Battery":
            hourly = battery_hourly.get(date_str, None)
        else:
            eia_key = FUEL_EIA_KEY.get(fuel, fuel)
            hourly = gen_data[date_str].get(eia_key, None)
        if hourly is None:
            continue

        # Intra-day ramps
        for h in range(1, len(hourly)):
            if hourly[h] is None or hourly[h - 1] is None:
                continue
            ramp = hourly[h] - hourly[h - 1]
            if ramp == 0:
                continue
            lmp_entry = prices.get(str(h + 1), None)
            if lmp_entry is None:
                continue
            lmp = lmp_entry.get("LMP", None)
            if lmp is None:
                continue
            results[fuel]["ramp"].append(ramp)
            results[fuel]["lmp"].append(lmp)

        # Cross-day ramp
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
                            lmp_entry = prices.get("1", None)
                            if lmp_entry is not None:
                                lmp = lmp_entry.get("LMP", None)
                                if lmp is not None:
                                    results[fuel]["ramp"].append(ramp)
                                    results[fuel]["lmp"].append(lmp)

# ── LMP colormap & normalization ─────────────────────────────────────────
all_lmp = []
for fuel in FUEL_ORDER:
    all_lmp.extend(results[fuel]["lmp"])
all_lmp = np.array(all_lmp)
lmp_p5, lmp_p95 = np.percentile(all_lmp, [5, 95])
print(f"LMP clip range: {lmp_p5:.1f} to {lmp_p95:.1f} $/MWh")

lmp_cmap = plt.cm.RdYlBu_r
lmp_norm = mcolors.TwoSlopeNorm(vmin=lmp_p5, vcenter=np.median(all_lmp), vmax=lmp_p95)

SIZE_MIN, SIZE_MAX = 0.3, 5.0

def lmp_to_size(lmp_arr):
    clipped = np.clip(lmp_arr, lmp_p5, lmp_p95)
    frac = (clipped - lmp_p5) / (lmp_p95 - lmp_p5 + 1e-9)
    return SIZE_MIN + frac * (SIZE_MAX - SIZE_MIN)

# ── Layout geometry ────────────────────────────────────────────────────────
n_fuels = len(FUEL_ORDER)
max_half_width = 0.4

# ── Plot ───────────────────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"

fig, ax = plt.subplots(figsize=(14, 8), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

def lmp_sorted_jitter(values, lmps, x_centre, half_width, n_bins=1500):
    """KDE-based violin jitter with points sorted by LMP within each band."""
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
        order = np.argsort(lmps[indices])
        sorted_indices = indices[order]

        n = len(sorted_indices)
        positions = np.linspace(-width, width, n)
        x_pos[sorted_indices] = x_centre + positions

    return x_pos

t_total = time.time()
for i, fuel in enumerate(FUEL_ORDER):
    ramps = np.array(results[fuel]["ramp"])
    lmps = np.array(results[fuel]["lmp"])
    if len(ramps) < 10:
        continue

    t0 = time.time()
    x_pos = lmp_sorted_jitter(ramps, lmps, i, max_half_width)
    sizes = lmp_to_size(lmps)

    # Sort by LMP ascending so high-price points render on top
    draw_order = np.argsort(lmps)

    ax.scatter(x_pos[draw_order], ramps[draw_order],
               c=lmps[draw_order], cmap=lmp_cmap, norm=lmp_norm,
               s=sizes[draw_order], alpha=0.45, edgecolors="none",
               rasterized=True)

    print(f"  {fuel:>12s}: {len(ramps):>7,} pts  ({time.time()-t0:.1f}s)")

# ── Axes / labels ──────────────────────────────────────────────────────────
ax.axhline(0, color="#94a3b8", linewidth=0.6, alpha=0.5)

y_top = ax.get_ylim()[1]
for i, fuel in enumerate(FUEL_ORDER):
    ax.text(i, y_top * 0.95, fuel, ha="center", va="top",
            fontsize=12, fontweight="bold", color=TEXT_COLOR)

ax.set_xticks(range(n_fuels))
ax.set_xticklabels([""] * n_fuels)
ax.tick_params(axis="x", length=0)

ax.set_ylabel("Ramp Rate (MW/hr)", fontsize=13, color=TEXT_COLOR)
ax.set_title("Ramp Rate vs LMP  —  dot size & colour ∝ price  ",
             fontsize=14, fontweight="bold", color=TEXT_COLOR)
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
plt.savefig("ramp_rate_lmp.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved ramp_rate_lmp.png")
