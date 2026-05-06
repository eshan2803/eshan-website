"""
Replicate V3 calculation EXACTLY to understand the 90.93% value.

V3 methodology:
1. For EACH 5-minute interval: calculate clean_pct = clean_mw / gross_demand_mw * 100
2. Average all 5-min percentages within each hour -> hourly_penetration
3. Average all hourly_penetration values -> avg_penetration

Key: V3 uses gross_demand from the fuelsource CSV itself (sum of all columns),
not the demand from a separate demand file!
"""
import csv

date_str = "20250524"
fuelsource_file = f"caiso_supply/{date_str}_fuelsource.csv"

CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]
VALUE_COLS = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Coal", "Nuclear", "Natural Gas", "Large Hydro", "Batteries",
    "Imports", "Other",
]

hourly_data = {}
for h in range(24):
    hourly_data[h] = []  # Store all 5-min percentages for this hour

with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        time_str = row.get("Time", "")
        if not time_str:
            continue

        try:
            hour = int(time_str.split(":")[0])
        except (ValueError, IndexError):
            continue

        # Calculate clean energy
        clean_mw = 0.0
        for col in CLEAN_COLS:
            try:
                clean_mw += float(row.get(col, 0) or 0)
            except (ValueError, TypeError):
                pass

        # Add battery discharge (only when positive)
        battery_mw = 0.0
        try:
            battery_mw = float(row.get("Batteries", 0) or 0)
            if battery_mw > 0:
                clean_mw += battery_mw
        except (ValueError, TypeError):
            pass

        # Calculate net demand (sum of all sources)
        net_demand_mw = 0.0
        for col in VALUE_COLS:
            try:
                net_demand_mw += float(row.get(col, 0) or 0)
            except (ValueError, TypeError):
                pass

        # Calculate gross demand (add back battery charging)
        gross_demand_mw = net_demand_mw - min(battery_mw, 0)

        # Calculate penetration percentage for this 5-minute interval
        if gross_demand_mw > 0:
            clean_pct = (clean_mw / gross_demand_mw) * 100.0
            hourly_data[hour].append(clean_pct)

# Compute hourly averages (like V3 does)
hourly_penetration = []
for hour in range(24):
    if hourly_data[hour]:
        avg_pct = sum(hourly_data[hour]) / len(hourly_data[hour])
        hourly_penetration.append(avg_pct)
        print(f"Hour {hour:2d}: {avg_pct:6.2f}% (from {len(hourly_data[hour])} 5-min intervals)")

# Calculate daily average (like V3 does)
if hourly_penetration:
    avg_penetration = sum(hourly_penetration) / len(hourly_penetration)
    max_penetration = max(hourly_penetration)
    hours_over_100 = sum(1 for p in hourly_penetration if p >= 100)

    print("\n" + "="*80)
    print("V3 REPLICATION RESULTS:")
    print("="*80)
    print(f"Average Penetration: {avg_penetration:.2f}%")
    print(f"Max Penetration:     {max_penetration:.2f}%")
    print(f"Hours over 100%:     {hours_over_100}")
    print()
    print(f"Expected from V3:    90.93%")
    print(f"Difference:          {avg_penetration - 90.93:+.2f} pp")
    print("="*80)

    # Now calculate ENERGY-BASED percentage
    print("\n" + "="*80)
    print("ENERGY-BASED CALCULATION (What You Want):")
    print("="*80)

    # Recalculate with energy totals
    total_clean_mwh = 0
    total_load_mwh = 0

    with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            time_str = row.get("Time", "")
            if not time_str:
                continue

            # Calculate clean energy
            clean_mw = 0.0
            for col in CLEAN_COLS:
                try:
                    clean_mw += float(row.get(col, 0) or 0)
                except (ValueError, TypeError):
                    pass

            # Add battery discharge (only when positive)
            battery_mw = 0.0
            try:
                battery_mw = float(row.get("Batteries", 0) or 0)
                if battery_mw > 0:
                    clean_mw += battery_mw
            except (ValueError, TypeError):
                pass

            # Calculate net demand
            net_demand_mw = 0.0
            for col in VALUE_COLS:
                try:
                    net_demand_mw += float(row.get(col, 0) or 0)
                except (ValueError, TypeError):
                    pass

            # Calculate gross demand
            gross_demand_mw = net_demand_mw - min(battery_mw, 0)

            # Accumulate MWh (5-min interval = 1/12 hour)
            interval_hours = 1.0 / 12.0
            total_clean_mwh += clean_mw * interval_hours
            total_load_mwh += gross_demand_mw * interval_hours

    energy_based_pct = (total_clean_mwh / total_load_mwh * 100) if total_load_mwh > 0 else 0

    print(f"Total Clean Energy: {total_clean_mwh:,.0f} MWh")
    print(f"Total Load:         {total_load_mwh:,.0f} MWh")
    print(f"Energy-Based %:     {energy_based_pct:.2f}%")
    print()
    print(f"Comparison:")
    print(f"  V3 (avg of hourly %):      90.93%")
    print(f"  Energy-based (total/total): {energy_based_pct:.2f}%")
    print(f"  Difference:                {90.93 - energy_based_pct:+.2f} pp")
    print("="*80)
