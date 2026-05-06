import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

plt.rcParams['figure.facecolor'] = '#0f1117'
plt.rcParams['axes.facecolor'] = '#0f1117'
plt.rcParams['text.color'] = '#e0e0e0'
plt.rcParams['axes.labelcolor'] = '#e0e0e0'
plt.rcParams['xtick.color'] = '#cccccc'
plt.rcParams['ytick.color'] = '#cccccc'

# Load data
print("Loading data files...")
with open('available_capacity.json', 'r') as f:
    capacity_json = json.loads(f.read())

with open('eia_generation.json', 'r') as f:
    generation_json = json.loads(f.read())

if 'metadata' in generation_json:
    del generation_json['metadata']

print(f"Loaded {len(generation_json)} days of generation data")

resource_types = ['Solar', 'Wind', 'Natural Gas', 'Hydro', 'Nuclear', 'Geothermal']

# Collect data by hour for batch plotting: {hour: {resource: [(x_jittered, cf)]}}
hour_data = {h: {res: [] for res in resource_types} for h in range(24)}
resource_to_x = {res: i for i, res in enumerate(resource_types)}

print("Calculating capacity factors...")
processed_days = 0

for date_str in generation_json:
    gen_day = generation_json[date_str]
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        continue

    year_str = str(date_obj.year)
    month_str = f"{date_obj.month:02d}"

    if year_str not in capacity_json or month_str not in capacity_json[year_str]:
        continue

    cap_month = capacity_json[year_str][month_str]

    for h in range(24):
        # Solar
        if 'Solar' in gen_day and 'Solar' in cap_month:
            gen = gen_day['Solar'][h] if h < len(gen_day['Solar']) else 0
            cap = cap_month['Solar'][h] if h < len(cap_month['Solar']) else 0
            if cap > 0:
                cf = gen / cap
                if 0 <= cf <= 1.5:
                    hour_data[h]['Solar'].append(cf)

        # Wind
        if 'Wind' in gen_day and 'Wind' in cap_month:
            gen = gen_day['Wind'][h] if h < len(gen_day['Wind']) else 0
            cap = cap_month['Wind'][h] if h < len(cap_month['Wind']) else 0
            if cap > 0:
                cf = gen / cap
                if 0 <= cf <= 1.5:
                    hour_data[h]['Wind'].append(cf)

        # Natural Gas
        if 'Natural Gas' in gen_day:
            gen = gen_day['Natural Gas'][h] if h < len(gen_day['Natural Gas']) else 0
            gas_cap = 0
            for gas_type in ['Gas CCGT', 'Gas Steam', 'Gas ICE', 'Gas Peaker']:
                if gas_type in cap_month:
                    gas_cap += cap_month[gas_type][h] if h < len(cap_month[gas_type]) else 0
            if gas_cap > 0:
                cf = gen / gas_cap
                if 0 <= cf <= 1.5:
                    hour_data[h]['Natural Gas'].append(cf)

        # Hydro
        if 'Hydro' in gen_day and 'Hydro' in cap_month:
            gen = gen_day['Hydro'][h] if h < len(gen_day['Hydro']) else 0
            cap = cap_month['Hydro'][h] if h < len(cap_month['Hydro']) else 0
            if cap > 0:
                cf = gen / cap
                if 0 <= cf <= 1.5:
                    hour_data[h]['Hydro'].append(cf)

        # Nuclear
        if 'Nuclear' in gen_day and 'Nuclear' in cap_month:
            gen = gen_day['Nuclear'][h] if h < len(gen_day['Nuclear']) else 0
            cap = cap_month['Nuclear'][h] if h < len(cap_month['Nuclear']) else 0
            if cap > 0:
                cf = gen / cap
                if 0 <= cf <= 1.5:
                    hour_data[h]['Nuclear'].append(cf)

        # Geothermal
        if 'Geothermal' in gen_day and 'Geothermal' in cap_month:
            gen = gen_day['Geothermal'][h] if h < len(gen_day['Geothermal']) else 0
            cap = cap_month['Geothermal'][h] if h < len(cap_month['Geothermal']) else 0
            if cap > 0:
                cf = gen / cap
                if 0 <= cf <= 1.5:
                    hour_data[h]['Geothermal'].append(cf)

    processed_days += 1
    if processed_days % 500 == 0:
        print(f"  {processed_days} days...")

print(f"Processed {processed_days} days")

# Count total
total_pts = sum(len(hour_data[h][r]) for h in range(24) for r in resource_types)
print(f"Total data points: {total_pts:,}")

# Summary
print("\nCapacity Factor Summary:")
for res in resource_types:
    vals = []
    for h in range(24):
        vals.extend(hour_data[h][res])
    if vals:
        print(f"  {res:15s}: n={len(vals):>6,}  mean={np.mean(vals):.3f}  median={np.median(vals):.3f}")

# ── Plot ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 9))

cmap = plt.cm.twilight
hour_colors = [cmap(h / 23) for h in range(24)]

np.random.seed(42)

print("\nPlotting...")
for h in range(24):
    for res in resource_types:
        cfs = hour_data[h][res]
        if not cfs:
            continue
        n = len(cfs)
        x_base = resource_to_x[res]
        xs = x_base + np.random.uniform(-0.35, 0.35, size=n)
        ys = np.array(cfs)
        ax.scatter(xs, ys, c=[hour_colors[h]], s=4, alpha=0.25,
                   marker='_', linewidths=0.8, edgecolors='none')

# Axes
ax.set_xticks(range(len(resource_types)))
ax.set_xticklabels(resource_types, fontsize=13, fontweight='600')
ax.set_ylabel('Capacity Factor', fontsize=14, fontweight='600')
ax.set_title('Capacity Factor Variation by Generator Type',
             fontsize=18, fontweight='700', pad=16, color='white')

subtitle = 'California ISO  |  2020 \u2013 2025  |  Hourly observations colored by time of day'
ax.text(0.5, 1.01, subtitle, transform=ax.transAxes, ha='center', va='bottom',
        fontsize=11, color='#888888')

ax.set_ylim(-0.02, 1.12)
ax.set_xlim(-0.6, len(resource_types) - 0.4)

# Grid
ax.grid(axis='y', alpha=0.15, linestyle='-', color='#ffffff')
ax.grid(axis='x', visible=False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#333333')
ax.spines['bottom'].set_color('#333333')
ax.tick_params(axis='both', which='both', length=0)

# 100% capacity reference
ax.axhline(y=1.0, color='#ef4444', linestyle='--', linewidth=1, alpha=0.6)
ax.text(len(resource_types) - 0.45, 1.015, '100% Capacity', fontsize=9,
        color='#ef4444', ha='right', alpha=0.8)

# Colorbar
sm = plt.cm.ScalarMappable(cmap='twilight', norm=plt.Normalize(vmin=0, vmax=23))
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.015, fraction=0.025,
                     aspect=30)
cbar.set_label('Hour of Day', fontsize=11, fontweight='600', color='#cccccc')
cbar.set_ticks([0, 6, 12, 18, 23])
cbar.set_ticklabels(['12am', '6am', '12pm', '6pm', '11pm'])
cbar.ax.tick_params(colors='#aaaaaa', length=0)
cbar.outline.set_edgecolor('#333333')

plt.tight_layout()
plt.savefig('capacity_factors_scatter.png', dpi=300, bbox_inches='tight',
            facecolor='#0f1117', edgecolor='none')
print("Saved: capacity_factors_scatter.png")

plt.close('all')
print("Done!")
