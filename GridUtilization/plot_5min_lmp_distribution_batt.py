import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from scipy.stats import gaussian_kde
from datetime import datetime as dt

script_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")

# ── Style constants (consistent with other charts) ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_RED = "#ef4444"
DOT_COLOR = "#22d3ee"

# Curtailment/Battery colormap: light gray -> cyan -> green -> yellow -> orange -> red
curtail_cmap = mcolors.LinearSegmentedColormap.from_list("curtailment", [
    "#cbd5e1", "#06b6d4", "#10b981", "#fbbf24", "#f97316", "#ef4444",
])

def generate_distribution_chart(df_plot, title, filename, show_positive=False, color_col='batt_gw'):
    """
    Generates a jittered distribution chart of LMP prices by year.
    """
    print(f"Generating chart: {filename}...")
    
    years = sorted(df_plot['year'].unique())
    
    # Setup figure
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=BG_OUTER)
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

    max_half_width = 0.38
    
    # Configure colormap and normalization based on what we are plotting
    if color_col == 'batt_op_gw':
        vmax = max(abs(df_plot[color_col].min()), abs(df_plot[color_col].max()))
        if vmax == 0: vmax = 1.0
        norm = mcolors.Normalize(vmin=-vmax, vmax=vmax)
        # Diverging colormap: Blue (Charging) -> Gray (Zero) -> Red (Discharging)
        cmap = mcolors.LinearSegmentedColormap.from_list("batt_ops", [
            "#0284c7", "#38bdf8", "#475569", "#fbbf24", "#ef4444"
        ])
        cbar_label = "Battery Operation (GW)\n<-- Charging    |    Discharging -->"
    else:
        vmax = df_plot[color_col].max()
        if vmax == 0: vmax = 1.0
        norm = mcolors.Normalize(vmin=0, vmax=vmax)
        cmap = curtail_cmap
        cbar_label = "Battery Charging (GW)"
        
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)

    for i, yr in enumerate(years):
        year_df = df_plot[df_plot['year'] == yr].copy()
        # Drop NaNs for LMP
        year_df = year_df.dropna(subset=['lmp'])
        
        lmps = year_df['lmp'].values
        batt_vals = year_df[color_col].values
        
        if len(lmps) < 2:
            continue

        # Check for variance - gaussian_kde fails if all values are identical
        if np.all(lmps == lmps[0]):
            densities = np.ones_like(lmps)
        else:
            try:
                # Optimized KDE evaluation for jittering
                kde = gaussian_kde(lmps, bw_method=0.06)
                
                # Evaluation grid
                l_min, l_max = lmps.min(), lmps.max()
                grid = np.linspace(l_min, l_max, 200)
                grid_densities = kde(grid)
                densities = np.interp(lmps, grid, grid_densities)
            except Exception as e:
                print(f"Warning: KDE failed for year {yr}: {e}")
                densities = np.ones_like(lmps)
            
        d_max = densities.max()
        densities_norm = densities / d_max if d_max > 0 else np.ones_like(densities)

        # Generate jitter
        raw_jitter = np.random.uniform(-1, 1, size=len(lmps))
        x_pos = i + raw_jitter * densities_norm * max_half_width

        # Sort by absolute battery value so extreme points (high charging OR discharging) are on top
        sort_idx = np.argsort(np.abs(batt_vals))
        
        # Scatter plot with reduced marker size and alpha for better visibility of variations
        ax.scatter(x_pos[sort_idx], lmps[sort_idx], c=batt_vals[sort_idx],
                    cmap=cmap, norm=norm,
                    s=1.5, alpha=0.5, edgecolors="none", rasterized=True)

        # Mean line
        mean_lmp = lmps.mean()
        half_w = max_half_width * 0.85
        ax.hlines(mean_lmp, i - half_w, i + half_w,
                   colors="white", linewidths=2, zorder=5)
        
        # Text labels
        ax.text(i, mean_lmp + (1 if not show_positive else 5), f"${mean_lmp:.1f}",
                 ha="center", va="bottom", fontsize=9, color="white",
                 fontweight="bold", zorder=6)

        label_y = 2 if not show_positive else ax.get_ylim()[1] * 0.9
        ax.text(i, label_y, f"n={len(lmps):,}",
                 ha="center", va="bottom", fontsize=9, color="#888",
                 alpha=0.9)

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(yr) for yr in years], fontsize=11, color="#888")
    ax.set_ylabel("LMP Price ($/MWh)", color=TEXT_COLOR, fontsize=12)
    
    ax.set_title(title, color="#fff", fontsize=16, fontweight="bold", pad=20)
    ax.axhline(0, color=ACCENT_RED, linewidth=0.8, linestyle="--", alpha=0.5)

    # Colorbar
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", pad=0.02, aspect=40)
    cbar.set_label(cbar_label, color=TEXT_COLOR, fontsize=11, fontweight="bold")
    cbar.ax.tick_params(colors="#888", labelsize=9)
    cbar.outline.set_edgecolor(SPINE_COLOR)

    out_path = os.path.join(script_dir, filename)
    fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
    print(f"Saved to {out_path}")
    plt.close()

def main():
    print("Loading data from comprehensive CSV...")
    # Load required columns
    df = pd.read_csv(CSV_FILE, usecols=['timestamp', 'lmp', 'battery_charging_mw', 'batteries_mw'], parse_dates=['timestamp'])
    
    # Ensure numeric
    df['lmp'] = pd.to_numeric(df['lmp'], errors='coerce')
    df['battery_charging_mw'] = pd.to_numeric(df['battery_charging_mw'], errors='coerce').fillna(0)
    df['batteries_mw'] = pd.to_numeric(df['batteries_mw'], errors='coerce').fillna(0)
    
    df['batt_gw'] = df['battery_charging_mw'] / 1000.0
    df['batt_op_gw'] = df['batteries_mw'] / 1000.0
    df['year'] = df.index.year if isinstance(df.index, pd.DatetimeIndex) else df['timestamp'].dt.year
    
    # Version 1: Only negative prices
    print("Processing Version 1: Negative LMPs...")
    df_neg = df[df['lmp'] < 0].copy()
    generate_distribution_chart(
        df_neg, 
        "Distribution of 5-Minute Negative LMP Prices by Year\nColored by Battery Charging (GW)",
        "negative_lmp_5min_distribution_batt.png",
        show_positive=False,
        color_col='batt_gw'
    )
    
    # Version 2: All prices since 2023
    print("Processing Version 2: All LMPs since 2023...")
    df_all = df[df['year'] >= 2023].copy()
    
    # Capping LMP to 150 to keep the chart readable and focus on the main distribution
    # since occasional spikes to $1000 can squash the entire violin plot
    df_all = df_all[df_all['lmp'] <= 250]
    df_all = df_all[df_all['lmp'] >= -100]

    generate_distribution_chart(
        df_all,
        "Distribution of 5-Minute LMP Prices (2023-Present)\nColored by Battery Operation (GW)",
        "all_lmp_5min_distribution_batt.png",
        show_positive=True,
        color_col='batt_op_gw'
    )

if __name__ == "__main__":
    main()
