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

def color_sorted_jitter(values, color_values, x_centre, half_width, n_bins=1200, bw_method=0.06):
    """Place points in density-shaped columns, ordered by color within each y-band."""
    values = np.asarray(values)
    color_values = np.asarray(color_values)

    if len(values) < 2 or np.all(values == values[0]):
        return np.full_like(values, x_centre, dtype=float)

    try:
        kde = gaussian_kde(values, bw_method=bw_method)
    except Exception as e:
        print(f"Warning: KDE failed for ordered jitter: {e}")
        return np.full_like(values, x_centre, dtype=float)

    v_min, v_max = values.min(), values.max()
    bin_edges = np.linspace(v_min - 1e-9, v_max + 1e-9, n_bins + 1)
    bin_idx = np.digitize(values, bin_edges) - 1
    bin_centres = (bin_edges[:-1] + bin_edges[1:]) / 2
    densities = kde(bin_centres)
    d_max = densities.max()

    x_pos = np.empty_like(values, dtype=float)

    for b in range(n_bins):
        mask = bin_idx == b
        if not mask.any():
            continue

        width = (densities[b] / d_max) * half_width if d_max > 0 else half_width
        indices = np.where(mask)[0]
        sorted_indices = indices[np.argsort(color_values[indices])]
        positions = np.linspace(-width, width, len(sorted_indices))
        x_pos[sorted_indices] = x_centre + positions

    return x_pos


def generate_distribution_chart(df_plot, title, filename, show_positive=False, color_col='batt_gw', last_date_label=None, full_y_axis=False, ordered_by_color=False, light_theme=False, marker_size=1.5, marker_alpha=0.5):
    """
    Generates a jittered distribution chart of LMP prices by year.
    """
    print(f"Generating chart: {filename}...")
    
    years = sorted(df_plot['year'].unique())
    
    # Setup figure
    bg_outer = "#f8fafc" if light_theme else BG_OUTER
    bg_inner = "#ffffff" if light_theme else BG_INNER
    text_color = "#111827" if light_theme else TEXT_COLOR
    grid_color = "#d9e2ec" if light_theme else GRID_COLOR
    spine_color = "#94a3b8" if light_theme else SPINE_COLOR
    tick_color = "#475569" if light_theme else "#888"
    mean_color = "#0f172a" if light_theme else "white"
    label_color = "#64748b" if light_theme else "#888"
    zero_color = "#dc2626" if light_theme else ACCENT_RED

    fig, ax = plt.subplots(figsize=(16, 10), facecolor=bg_outer)
    ax.set_facecolor(bg_inner)
    ax.tick_params(colors=tick_color, labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(spine_color)
    ax.grid(True, color=grid_color, linewidth=0.6, alpha=0.8)

    max_half_width = 0.38
    
    # Configure colormap and normalization based on what we are plotting
    if color_col == 'hour':
        norm = mcolors.Normalize(vmin=0, vmax=23)
        cmap = mcolors.LinearSegmentedColormap.from_list("hour_of_day", [
            (0/23, "#1e3a5f"),
            (4/23, "#2563eb"),
            (7/23, "#fbbf24"),
            (10/23, "#f97316"),
            (13/23, "#ef4444"),
            (16/23, "#dc2626"),
            (18/23, "#a855f7"),
            (21/23, "#6366f1"),
            (23/23, "#1e3a5f"),
        ])
        cbar_label = "Hour of Day"
    elif color_col == 'batt_op_gw':
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
        color_vals = year_df[color_col].values
        
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

        # Generate x-position. Hour-colored charts use deterministic ordering
        # within each y-band so the color distribution is easier to read.
        if ordered_by_color:
            x_pos = color_sorted_jitter(lmps, color_vals, i, max_half_width)
        else:
            raw_jitter = np.random.uniform(-1, 1, size=len(lmps))
            x_pos = i + raw_jitter * densities_norm * max_half_width

        # Sort so the most visually important points are drawn on top.
        if color_col == 'hour':
            sort_idx = np.argsort(color_vals)
        else:
            sort_idx = np.argsort(np.abs(color_vals))
        
        # Scatter plot with reduced marker size and alpha for better visibility of variations
        ax.scatter(x_pos[sort_idx], lmps[sort_idx], c=color_vals[sort_idx],
                    cmap=cmap, norm=norm,
                    s=marker_size, alpha=marker_alpha, edgecolors="none", rasterized=True)

        # Mean line
        mean_lmp = lmps.mean()
        half_w = max_half_width * 0.85
        ax.hlines(mean_lmp, i - half_w, i + half_w,
                   colors=mean_color, linewidths=2, zorder=5)
        
        # Text labels
        ax.text(i, mean_lmp + (1 if not show_positive else 5), f"${mean_lmp:.1f}",
                 ha="center", va="bottom", fontsize=9, color=mean_color,
                 fontweight="bold", zorder=6)

        label_y = 2 if not show_positive else ax.get_ylim()[1] * 0.9
        ax.text(i, label_y, f"n={len(lmps):,}",
                 ha="center", va="bottom", fontsize=9, color=label_color,
                 alpha=0.9)

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(yr) for yr in years], fontsize=11, color=tick_color)
    ax.set_ylabel("LMP Price ($/MWh)", color=text_color, fontsize=12)

    if full_y_axis:
        y_min = df_plot['lmp'].min()
        y_max = df_plot['lmp'].max()
        y_pad = max((y_max - y_min) * 0.04, 10)
        ax.set_ylim(y_min - y_pad, y_max + y_pad)
    
    if last_date_label:
        title = f"{title}\nUpdated through {last_date_label}"
    ax.set_title(title, color=text_color, fontsize=16, fontweight="bold", pad=20)
    ax.axhline(0, color=zero_color, linewidth=0.8, linestyle="--", alpha=0.65)

    # Colorbar
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", pad=0.02, aspect=40)
    cbar.set_label(cbar_label, color=text_color, fontsize=11, fontweight="bold")
    if color_col == 'hour':
        cbar.set_ticks([0, 4, 8, 12, 16, 20, 23])
        cbar.set_ticklabels(["12am", "4am", "8am", "12pm", "4pm", "8pm", "11pm"])
    cbar.ax.tick_params(colors=tick_color, labelsize=9)
    cbar.outline.set_edgecolor(spine_color)

    out_path = os.path.join(script_dir, filename)
    fig.savefig(out_path, dpi=200, facecolor=bg_outer, bbox_inches="tight")
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
    last_date_label = df['timestamp'].max().strftime("%B %d, %Y")
    
    # Version 1: Only negative prices
    print("Processing Version 1: Negative LMPs...")
    df_neg = df[(df['lmp'] < 0) & (df['year'] >= 2023)].copy()
    generate_distribution_chart(
        df_neg, 
        "Distribution of 5-Minute Negative LMP Prices by Year\nColored by Battery Charging (GW)",
        "negative_lmp_5min_distribution_batt.png",
        show_positive=False,
        color_col='batt_gw',
        last_date_label=last_date_label
    )

    print("Processing Version 1b: Negative LMPs through May 3 in each year...")
    ytd_mask = (df['timestamp'].dt.month < 5) | (
        (df['timestamp'].dt.month == 5) & (df['timestamp'].dt.day <= 3)
    )
    df_neg_ytd = df[(df['lmp'] < 0) & (df['year'] >= 2023) & ytd_mask].copy()
    generate_distribution_chart(
        df_neg_ytd,
        "Distribution of 5-Minute Negative LMP Prices by Year\nJan 1-May 3 Comparison, Colored by Battery Charging (GW)",
        "negative_lmp_5min_distribution_batt_v2.png",
        show_positive=False,
        color_col='batt_gw',
        last_date_label="May 03 in each year"
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
        color_col='batt_op_gw',
        last_date_label=last_date_label
    )

    print("Processing Version 2b: Hourly all LMPs since 2023...")
    hourly = df.set_index('timestamp')[['lmp']].resample('1h').mean().dropna().reset_index()
    hourly['year'] = hourly['timestamp'].dt.year
    hourly['hour'] = hourly['timestamp'].dt.hour
    hourly_all = hourly[hourly['year'] >= 2023].copy()
    generate_distribution_chart(
        hourly_all,
        "Distribution of Hourly LMP Prices (2023-Present)\nFull Y-Axis Range, Colored by Hour of Day",
        "all_lmp_hourly_distribution_batt_v2.png",
        show_positive=True,
        color_col='hour',
        last_date_label=last_date_label,
        full_y_axis=True,
        ordered_by_color=True,
        light_theme=True,
        marker_size=4.0,
        marker_alpha=0.72
    )

if __name__ == "__main__":
    main()
