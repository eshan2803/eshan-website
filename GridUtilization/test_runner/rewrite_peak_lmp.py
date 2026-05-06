import os

with open("plot_peak_lmp_timeshift.py", "r", encoding="utf-8") as f:
    orig = f.read()

# Extract battery logic
batt_extract = """
# ── Read battery discharge data from CSV at 5-min resolution ──
print("Reading comprehensive CSV for battery window...")
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")
daily_5min = defaultdict(dict)
count = 0

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts = row["timestamp"]
        discharge = row.get("battery_discharging_mw", "")
        if not discharge or not discharge.strip():
            continue
        try:
            val = float(discharge)
        except (ValueError, TypeError):
            continue
        try:
            if "-" in ts.split(" ")[0]:
                parsed = dt.strptime(ts, "%Y-%m-%d %H:%M")
            else:
                parsed = dt.strptime(ts, "%m/%d/%Y %H:%M")
        except ValueError:
            continue
        date_key = parsed.strftime("%Y-%m-%d")
        slot = parsed.hour * 12 + parsed.minute // 5
        daily_5min[date_key][slot] = val
        count += 1
        if count % 500000 == 0:
            print(f"  Read {count:,} rows...")

batt_dates_sorted = sorted(daily_5min.keys())
batt_date_objs = [dt.strptime(d, "%Y-%m-%d") for d in batt_dates_sorted]
batt_n_days = len(batt_dates_sorted)
batt_N_SLOTS = 288
batt_heatmap = np.full((batt_N_SLOTS, batt_n_days), np.nan)
for j, date_key in enumerate(batt_dates_sorted):
    for slot, mw in daily_5min[date_key].items():
        if 0 <= slot < batt_N_SLOTS:
            batt_heatmap[slot, j] = mw

print(f"  Battery heatmap shape: {batt_heatmap.shape}")
"""

orig = orig.replace(
    "from collections import defaultdict\n\nscript_dir = os.path.dirname(os.path.abspath(__file__))",
    "import csv\nfrom collections import defaultdict\n\nscript_dir = os.path.dirname(os.path.abspath(__file__))\n" + batt_extract
)

old_panels = """# ── Figure: 2 panels ──
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(22, 14), facecolor=BG_OUTER,
                                 gridspec_kw={"hspace": 0.3, "height_ratios": [0.8, 1.2]})"""
new_panels = """# ── Figure: 3 panels ──
fig, (ax1, ax_batt, ax2) = plt.subplots(3, 1, figsize=(22, 21), facecolor=BG_OUTER,
                                 gridspec_kw={"hspace": 0.35, "height_ratios": [0.8, 1.0, 1.2]})"""
orig = orig.replace(old_panels, new_panels)

panel2_marker = "# ═══════════ Panel 2: Heatmap — Month × Hour, one sub-panel per year ═══════════"

batt_panel_draw = """
# ═══════════ Panel 2 (Battery): Normalized 5-min Heatmap ═══════════
print("Creating Panel 2: Battery discharge heatmap...")
ax_batt.set_facecolor(BG_INNER)

if len(batt_date_objs) > 0:
    batt_x_dates = mdates.date2num(batt_date_objs)
    batt_cmap = mcolors.LinearSegmentedColormap.from_list("battery", [
        "#1a1d2e", "#1e3a5f", "#2563eb", "#06b6d4", "#fbbf24", "#ffffff"
    ])
    batt_cmap.set_bad(BG_INNER)
    batt_vmax = np.nanpercentile(batt_heatmap, 99.5)
    batt_norm = mcolors.Normalize(vmin=0, vmax=batt_vmax)
    
    batt_x_edges = np.append(batt_x_dates, batt_x_dates[-1] + 1)
    batt_y_edges = np.arange(batt_N_SLOTS + 1)
    
    im_batt = ax_batt.pcolormesh(batt_x_edges, batt_y_edges, batt_heatmap, cmap=batt_cmap, norm=batt_norm,
                         shading="flat", rasterized=True)
    
    ax_batt.set_xlim(date_nums[0] - 10, date_nums[-1] + 10)
    
    cbar_batt = fig.colorbar(im_batt, ax=ax_batt, orientation="vertical", pad=0.01, aspect=20, fraction=0.03)
    cbar_batt.set_label("Discharge (MW)", fontsize=10, color=TEXT_COLOR)
    cbar_batt.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    cbar_batt.outline.set_edgecolor(SPINE_COLOR)

ax_batt.set_ylabel("Hour of Day\\n(Battery Discharge)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax_batt.set_ylim(0, batt_N_SLOTS)
hour_ticks = [h * 12 for h in [0, 3, 6, 9, 12, 15, 18, 21, 24]]
ax_batt.set_yticks(hour_ticks)
ax_batt.set_yticklabels(["12am", "3am", "6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"], fontsize=10)
ax_batt.invert_yaxis()

ax_batt.xaxis.set_major_locator(mdates.YearLocator())
ax_batt.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


batt_last_date = dt.strptime(batt_dates_sorted[-1], "%Y-%m-%d").strftime("%B %d, %Y") if len(batt_dates_sorted) > 0 else ""
ax_batt.set_title(f"California Grid: Battery Discharge Window Expansion (5-Min Data)",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

ax_batt.tick_params(colors="#888", labelsize=10)
for spine in ax_batt.spines.values():
    spine.set_color(SPINE_COLOR)


# ═══════════ Panel 3: Heatmap — Month × Hour, one sub-panel per year ═══════════
"""
orig = orig.replace(panel2_marker, batt_panel_draw)

with open("plot_peak_lmp_timeshift_new.py", "w", encoding="utf-8") as f:
    f.write(orig)
    
print("Success")
