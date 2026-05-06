"""
Negative LMP scatter charts.

Chart 1: x = grid load (GWh), y = LMP ($/MWh)
Chart 2: x = net load (load - solar - wind) (GWh), y = LMP ($/MWh)

Each dot = one interval with negative LMP. Color = month of year.
Panels by year (2020-2026) in a single row.
Reads from caiso_comprehensive_data.csv.
"""
import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime as dt
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")

DOT_COLOR = "#06b6d4"  # cyan

# ── Read CSV ──
print("Reading comprehensive CSV...")
# year -> [(lmp, load_gwh, net_load_gwh, month), ...]
negative_intervals = defaultdict(list)

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        ts = row["timestamp"]
        lmp_str = row.get("lmp", "")
        if not lmp_str or not lmp_str.strip():
            continue
        try:
            lmp = float(lmp_str)
        except (ValueError, TypeError):
            continue
        if lmp >= 0:
            continue

        try:
            load_mw = float(row.get("load_mw", 0) or row.get("demand_mw", 0) or 0)
        except (ValueError, TypeError):
            load_mw = 0

        try:
            solar_mw = max(float(row.get("solar_mw", 0) or 0), 0)
        except (ValueError, TypeError):
            solar_mw = 0
        try:
            wind_mw = max(float(row.get("wind_mw", 0) or 0), 0)
        except (ValueError, TypeError):
            wind_mw = 0

        try:
            if "-" in ts.split(" ")[0]:
                parsed = dt.strptime(ts, "%Y-%m-%d %H:%M")
            else:
                parsed = dt.strptime(ts, "%m/%d/%Y %H:%M")
        except ValueError:
            continue

        year = parsed.year
        if year < 2023:
            continue
        month = parsed.month

        interval_hours = 5.0 / 60.0

        load_gwh = load_mw * interval_hours / 1000.0
        net_load_gwh = (load_mw - solar_mw - wind_mw) * interval_hours / 1000.0

        negative_intervals[year].append((lmp, load_gwh, net_load_gwh, month))
        count += 1

print(f"  Total negative-LMP intervals: {count:,}")
for year in sorted(negative_intervals.keys()):
    n = len(negative_intervals[year])
    min_lmp = min(lmp for lmp, _, _, _ in negative_intervals[year])
    print(f"  {year}: {n:,} intervals, min ${min_lmp:.2f}")

# ── Style ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

YEARS = [2023, 2024, 2025, 2026]
n_panels = len(YEARS)

# Global y range
all_lmps = []
for year in YEARS:
    if year in negative_intervals:
        all_lmps.extend(lmp for lmp, _, _, _ in negative_intervals[year])
y_min = min(all_lmps) if all_lmps else -100


def make_chart(x_index, x_label, title_suffix, filename):
    """Generate one scatter chart. x_index: 1=load_gwh, 2=net_load_gwh."""
    fig, axes = plt.subplots(1, n_panels, figsize=(18, 9), facecolor=BG_OUTER,
                              sharey=True, gridspec_kw={"wspace": 0.06})

    # Global x-axis range across all years
    x_max = 0
    x_min = 0
    for year in YEARS:
        if year in negative_intervals:
            vals = [t[x_index] for t in negative_intervals[year]]
            x_max = max(x_max, max(vals))
            if x_index == 2:
                x_min = min(x_min, min(vals))
    x_max *= 1.1
    x_min *= 1.1

    for idx, (ax, year) in enumerate(zip(axes, YEARS)):
        ax.set_facecolor(BG_INNER)
        ax.tick_params(colors="#888", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(SPINE_COLOR)

        intervals = negative_intervals.get(year, [])
        if not intervals:
            ax.set_title(f"{year}", color="#fff", fontsize=13, fontweight="bold")
            ax.set_ylim(y_min * 1.05, 0)
            continue

        lmps = np.array([t[0] for t in intervals])
        x_vals = np.array([t[x_index] for t in intervals])

        ax.scatter(x_vals, lmps, c=DOT_COLOR, s=8, alpha=0.4,
                   edgecolors="none", rasterized=True)

        # Stats
        n_intervals = len(intervals)
        n_hours = n_intervals * 5 / 60
        n_label = f"{n_hours:,.0f} hrs"

        total_gwh = sum(t[1] for t in intervals)
        min_price = min(lmps)

        ax.text(0.96, 0.97, f"{n_label}\n{total_gwh:,.0f} GWh\nMin: ${min_price:.0f}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color=TEXT_COLOR,
                bbox=dict(boxstyle="round,pad=0.2", fc=BG_INNER, ec=SPINE_COLOR, alpha=0.9))

        ax.set_ylim(y_min * 1.05, 2)
        ax.axhline(0, color=SPINE_COLOR, linewidth=0.5)
        ax.set_xlim(x_min, x_max)

        # Vertical line at x=0 for net load chart
        if x_index == 2:
            ax.axvline(0, color="#ef4444", linewidth=0.8, alpha=0.5, linestyle="--")

        ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.5)
        ax.grid(True, axis="x", color=GRID_COLOR, linewidth=0.5, alpha=0.3)

        year_label = f"{year}" if year < 2026 else f"{year} (YTD)"
        ax.set_title(year_label, color="#fff", fontsize=13, fontweight="bold", pad=8)
        ax.set_xlabel(x_label, fontsize=8, color="#888")

        if idx == 0:
            ax.set_ylabel("LMP Price ($/MWh)", color=TEXT_COLOR, fontsize=11, fontweight="bold")

    fig.suptitle(f"California Grid: Negative LMP Events — {title_suffix}\n"
                 f"Each dot = one 5-min interval with negative price",
                 color="#fff", fontsize=15, fontweight="bold", y=1.02)

    out_path = os.path.join(script_dir, filename)
    fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
    print(f"Saved to {out_path}")
    plt.close()


# ── Generate both charts ──
print("\nChart 1: LMP vs Grid Load...")
make_chart(1, "Grid Load (GWh)", "LMP vs Grid Load", "negative_lmp_volume.png")

print("\nChart 2: LMP vs Net Load...")
make_chart(2, "Net Load (GWh)", "LMP vs Net Load (Load − Solar − Wind)", "negative_lmp_net_load.png")

print("\nDone!")
