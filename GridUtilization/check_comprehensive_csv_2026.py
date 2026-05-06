"""Check 2026 data coverage in comprehensive CSV"""
import csv

dates_2026 = set()
sample_rows = []
count = 0

with open('caiso_comprehensive_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        timestamp = row['timestamp']
        if timestamp.startswith('2026'):
            date = timestamp[:10]
            dates_2026.add(date)
            if len(sample_rows) < 3:
                sample_rows.append((timestamp, row.get('demand_mw', 'N/A')))
        count += 1

print(f"Total rows in CSV: {count:,}")
print(f"\n2026 dates in comprehensive CSV: {len(dates_2026)}")
if dates_2026:
    print(f"  First: {min(dates_2026)}")
    print(f"  Last: {max(dates_2026)}")
    print(f"\nSample 2026 rows:")
    for ts, demand in sample_rows:
        print(f"  {ts}: demand={demand} MW")
