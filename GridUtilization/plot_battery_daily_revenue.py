import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from scipy.stats import gaussian_kde
import matplotlib.ticker as ticker

script_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")

# ── Style constants ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_RED = "#ef4444"

# Create a cyclic colormap for the seasons/months
# Winter (Blue) -> Spring (Green) -> Summer (Orange) -> Fall (Red/Purple) -> Winter (Blue)
season_colors = ["#3b82f6", "#10b981", "#fbbf24", "#ef4444", "#3b82f6"]
season_cmap = mcolors.LinearSegmentedColormap.from_list("seasons", season_colors)

def generate_revenue_chart(df_daily, title, filename):
    print(f"Generating chart: {filename}...")
    
    years = sorted(df_daily['year'].unique())
    
    # Setup figure
    fig, ax = plt.subplots(figsize=(16, 10), facecolor=BG_OUTER)
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

    max_half_width = 0.38
    
    # Normalize day of year for coloring
    norm = mcolors.Normalize(vmin=1, vmax=365)
    sm = plt.cm.ScalarMappable(cmap=season_cmap, norm=norm)

    for i, yr in enumerate(years):
        year_df = df_daily[df_daily['year'] == yr].copy()
        
        revs = year_df['revenue_m'].values
        doy = year_df['day_of_year'].values
        
        if len(revs) < 2:
            continue

        # Check for variance - gaussian_kde fails if all values are identical
        if np.all(revs == revs[0]):
            densities = np.ones_like(revs)
        else:
            try:
                # Optimized KDE evaluation for jittering
                kde = gaussian_kde(revs, bw_method=0.1)
                
                # Evaluation grid
                l_min, l_max = revs.min(), revs.max()
                grid = np.linspace(l_min, l_max, 200)
                grid_densities = kde(grid)
                densities = np.interp(revs, grid, grid_densities)
            except Exception as e:
                print(f"Warning: KDE failed for year {yr}: {e}")
                densities = np.ones_like(revs)
            
        d_max = densities.max()
        densities_norm = densities / d_max if d_max > 0 else np.ones_like(densities)

        # Generate jitter
        raw_jitter = np.random.uniform(-1, 1, size=len(revs))
        x_pos = i + raw_jitter * densities_norm * max_half_width
        
        # Sort by day of year so later days don't blindly overlap early days
        sort_idx = np.random.permutation(len(revs))
        
        # Scatter plot with seasonal colors
        ax.scatter(x_pos[sort_idx], revs[sort_idx], c=doy[sort_idx],
                    cmap=season_cmap, norm=norm,
                    s=15, alpha=0.8, edgecolors="none", rasterized=True)

        # Mean line
        mean_rev = revs.mean()
        half_w = max_half_width * 0.85
        ax.hlines(mean_rev, i - half_w, i + half_w,
                   colors="white", linewidths=2, zorder=5)
        
        # Text labels
        ax.text(i, mean_rev + (ax.get_ylim()[1] - ax.get_ylim()[0])*0.015, f"${mean_rev:.2f}M",
                 ha="center", va="bottom", fontsize=10, color="white",
                 fontweight="bold", zorder=6)

        # Total Yearly Revenue label at the bottom
        total_yr_rev = year_df['total_revenue'].sum() / 1_000_000.0
        label_y = ax.get_ylim()[1] * 0.95
        ax.text(i, label_y, f"Total: ${total_yr_rev:.0f}M",
                 ha="center", va="bottom", fontsize=11, color="#888",
                 alpha=0.9, fontweight="bold")

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(yr) for yr in years], fontsize=12, color="#888")
    ax.set_ylabel("Daily Arbitrage Revenue (Millions $)", color=TEXT_COLOR, fontsize=12)
    
    # Format Y axis as $XX M
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"${x:,.1f}M"))
    
    ax.set_title(title, color="#fff", fontsize=16, fontweight="bold", pad=20)
    ax.axhline(0, color=ACCENT_RED, linewidth=1, linestyle="--", alpha=0.7)

    # Colorbar formatted with Month names
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", pad=0.02, aspect=40)
    cbar.set_label("Time of Year", color=TEXT_COLOR, fontsize=12, fontweight="bold")
    cbar.ax.tick_params(colors="#888", labelsize=10)
    cbar.outline.set_edgecolor(SPINE_COLOR)
    
    # Set colorbar ticks to roughly middle of months
    cbar.set_ticks([15, 45, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349])
    cbar.set_ticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

    out_path = os.path.join(script_dir, filename)
    fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
    print(f"Saved to {out_path}")
    plt.close()

def main():
    print("Loading data from comprehensive CSV...")
    # Load required columns
    df = pd.read_csv(CSV_FILE, usecols=['timestamp', 'lmp', 'batteries_mw'], parse_dates=['timestamp'])
    
    # Ensure numeric
    df['lmp'] = pd.to_numeric(df['lmp'], errors='coerce')
    df['batteries_mw'] = pd.to_numeric(df['batteries_mw'], errors='coerce').fillna(0)
    
    print("Calculating interval revenue...")
    df['interval_revenue'] = df['batteries_mw'] * df['lmp'] / 12.0
    
    # Add date columns
    df['date'] = df['timestamp'].dt.date
    
    print("Grouping by day...")
    daily_df = df.groupby('date').agg(
        total_revenue=('interval_revenue', 'sum')
    ).reset_index()
    
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    daily_df['year'] = daily_df['date'].dt.year
    daily_df['day_of_year'] = daily_df['date'].dt.dayofyear
    
    # Convert revenue to millions
    daily_df['revenue_m'] = daily_df['total_revenue'] / 1_000_000.0
    
    # Filter since 2023
    df_plot = daily_df[daily_df['year'] >= 2023].copy()
    
    print(f"Generating chart for {len(df_plot)} days...")
    
    generate_revenue_chart(
        df_plot,
        "Distribution of Daily Battery Arbitrage Revenue (2023-Present)\nColored by Daily LMP Spread",
        "battery_daily_revenue_distribution.png"
    )

if __name__ == "__main__":
    main()
