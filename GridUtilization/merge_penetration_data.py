"""
Merge renewable penetration data:
- corrected_full.json: Has correct May 2025 data (2020-2025 + 2 days of 2026)
- v3.json: Has all 2026 Q1 data (91 days)

Output: Complete dataset with corrected May 2025 and full 2026 Q1
"""
import json

# Load both files
with open("renewable_penetration_daily_corrected_full.json") as f:
    corrected_full = json.load(f)

with open("renewable_penetration_daily_v3.json") as f:
    v3_data = json.load(f)

# Start with corrected_full (has correct May 2025 data)
merged = corrected_full.copy()

# Add 2026 data from v3 (but keep corrected_full's 2026-03-31 and 2026-04-01 if they exist)
dates_2026_v3 = {k: v for k, v in v3_data.items() if k.startswith('2026')}

for date, data in dates_2026_v3.items():
    # Only add if not already in corrected_full (corrected_full has better data when available)
    if date not in merged:
        merged[date] = data

# Sort by date
merged = dict(sorted(merged.items()))

# Save
with open("renewable_penetration_daily_corrected_full.json", "w") as f:
    json.dump(merged, f, indent=2)

print(f"Merged dataset created: {len(merged)} total days")
print(f"  corrected_full contributed: {len(corrected_full)} days")
print(f"  v3 contributed 2026 data: {len(dates_2026_v3)} days")
print(f"  Final 2026 count: {len([k for k in merged.keys() if k.startswith('2026')])} days")
print(f"  Date range: {min(merged.keys())} to {max(merged.keys())}")

# Verify May 2025 data
may23 = merged.get("2025-05-23", {})
print(f"\nVerification - May 23, 2025: {may23.get('avg_penetration')}% (should be ~84%)")
