import os
script_dir = os.path.dirname(os.path.abspath(__file__))
target_file = os.path.join(script_dir, "plot_negative_lmp_curtailment_hourly.py")

with open(target_file, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Extract battery charging MW
search_1 = """        try:
            wind_mw = max(float(row.get("wind_mw", 0) or 0), 0)
        except (ValueError, TypeError):
            wind_mw = 0"""

replace_1 = """        try:
            wind_mw = max(float(row.get("wind_mw", 0) or 0), 0)
        except (ValueError, TypeError):
            wind_mw = 0

        try:
            battery_charging_mw = max(float(row.get("battery_charging_mw", 0) or 0), 0)
        except (ValueError, TypeError):
            battery_charging_mw = 0"""

text = text.replace(search_1, replace_1)

# 2. Append to negative_intervals
search_2 = """        total_curtail = local_curtail + system_curtail
        negative_intervals[year].append((lmp, load_gwh, net_load_gwh, local_curtail, system_curtail, total_curtail))"""
replace_2 = """        total_curtail = local_curtail + system_curtail
        batt_charging_gw = battery_charging_mw / 1000.0
        negative_intervals[year].append((lmp, load_gwh, net_load_gwh, local_curtail, system_curtail, total_curtail, batt_charging_gw))"""

text = text.replace(search_2, replace_2)

# 3. Max val calculations
search_3 = """all_local = []
all_system = []
all_total = []
for year in YEARS:
    if year in negative_intervals:
        all_local.extend(t[3] for t in negative_intervals[year])
        all_system.extend(t[4] for t in negative_intervals[year])
        all_total.extend(t[5] for t in negative_intervals[year])

local_max = max(all_local) if all_local else 1000
system_max = max(all_system) if all_system else 1000
total_max = max(all_total) if all_total else 1000"""

replace_3 = """all_local = []
all_system = []
all_total = []
all_batt_charge = []
for year in YEARS:
    if year in negative_intervals:
        all_local.extend(t[3] for t in negative_intervals[year])
        all_system.extend(t[4] for t in negative_intervals[year])
        all_total.extend(t[5] for t in negative_intervals[year])
        all_batt_charge.extend(t[6] for t in negative_intervals[year])

local_max = max(all_local) if all_local else 1000
system_max = max(all_system) if all_system else 1000
total_max = max(all_total) if all_total else 1000
batt_charge_max = max(all_batt_charge) if all_batt_charge else 100"""

text = text.replace(search_3, replace_3)

# 4. Remove (MW) hardcoding inside colorbar and suptitle
search_4 = """    cbar.set_label(f"{curtail_label} (MW)", fontsize=10, color=TEXT_COLOR, fontweight="bold")"""
replace_4 = """    cbar.set_label(f"{curtail_label}", fontsize=10, color=TEXT_COLOR, fontweight="bold")"""
text = text.replace(search_4, replace_4)

search_5 = """f"Each dot = one hour with negative price, colored by {curtail_label.lower()} (hourly, 2020-2026)","""
replace_5 = """f"Each dot = one hour with negative price, colored by {curtail_label.lower()} (hourly, 2020-2026)","""
# Actually, the string just uses a literal. That's fine. Wait, let's update the existing make_chart calls to include (MW)

search_calls = """           "negative_lmp_local_curtail_hourly.png", 3, "Local Curtailment", local_max)"""
replace_calls = """           "negative_lmp_local_curtail_hourly.png", 3, "Local Curtailment (MW)", local_max)"""
text = text.replace(search_calls, replace_calls)

search_calls2 = """           "negative_lmp_net_load_local_curtail_hourly.png", 3, "Local Curtailment", local_max)"""
replace_calls2 = """           "negative_lmp_net_load_local_curtail_hourly.png", 3, "Local Curtailment (MW)", local_max)"""
text = text.replace(search_calls2, replace_calls2)

search_calls3 = """           "negative_lmp_system_curtail_hourly.png", 4, "System Curtailment", system_max)"""
replace_calls3 = """           "negative_lmp_system_curtail_hourly.png", 4, "System Curtailment (MW)", system_max)"""
text = text.replace(search_calls3, replace_calls3)

search_calls4 = """           "negative_lmp_net_load_system_curtail_hourly.png", 4, "System Curtailment", system_max)"""
replace_calls4 = """           "negative_lmp_net_load_system_curtail_hourly.png", 4, "System Curtailment (MW)", system_max)"""
text = text.replace(search_calls4, replace_calls4)

search_calls5 = """           "negative_lmp_total_curtail_hourly.png", 5, "Total Curtailment", total_max)"""
replace_calls5 = """           "negative_lmp_total_curtail_hourly.png", 5, "Total Curtailment (MW)", total_max)"""
text = text.replace(search_calls5, replace_calls5)

search_calls6 = """           "negative_lmp_net_load_total_curtail_hourly.png", 5, "Total Curtailment", total_max)"""
replace_calls6 = """           "negative_lmp_net_load_total_curtail_hourly.png", 5, "Total Curtailment (MW)", total_max)"""
text = text.replace(search_calls6, replace_calls6)

# 5. Append Chart 7 and Chart 8
search_end = """print("\nDone!")"""
replace_end = """print("\nChart 7: LMP vs Grid Load, colored by Battery Charging...")
make_chart(1, "Grid Load (GWh)", "LMP vs Grid Load",
           "negative_lmp_batt_charge_hourly.png", 6, "Battery Charging (GW)", batt_charge_max)

print("\nChart 8: LMP vs Net Load, colored by Battery Charging...")
make_chart(2, "Net Load (GWh)", "LMP vs Net Load (Load − Solar − Wind)",
           "negative_lmp_net_load_batt_charge_hourly.png", 6, "Battery Charging (GW)", batt_charge_max)

print("\nDone!")"""
text = text.replace(search_end, replace_end)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully generated modification script.")
