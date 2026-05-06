"""Check which days in January 2024 have high renewable penetration hours."""
import json
from collections import defaultdict

# Load V3 data
with open("renewable_penetration_hourly_v3.json", "r") as f:
    data = json.load(f)

# Count hours >= 100% per day in January 2024
daily_counts = defaultdict(int)
for datetime_str, pct in data.items():
    if datetime_str.startswith("2024-01") and pct >= 100:
        date = datetime_str.split()[0]
        daily_counts[date] += 1

# Sort by count
sorted_days = sorted(daily_counts.items(), key=lambda x: x[1], reverse=True)

print(f"January 2024: {len(sorted_days)} days with >= 1 hour at 100%+ renewable")
print(f"Total hours >= 100%: {sum(daily_counts.values())}")
print()
print("Top 10 days with most hours >= 100%:")
for day, count in sorted_days[:10]:
    print(f"  {day}: {count} hours")
