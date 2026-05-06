"""
Fill DST-related gaps in comprehensive CSV by averaging neighboring days.

DST Spring Forward (missing 2:00-2:55 AM):
- Average same times from day before and day after

DST Fall Back (duplicate 1:00-1:55 AM):
- Keep first occurrence, average for second occurrence
"""
import csv
from datetime import datetime, timedelta
from collections import defaultdict

DST_SPRING_FORWARD = [
    "2020-03-08",
    "2021-03-14",
    "2022-03-13",
    "2023-03-12",
    "2024-03-10",
    "2025-03-09",
    "2026-03-08",
]

DST_FALL_BACK = [
    "2020-11-01",
    "2021-11-07",
    "2022-11-06",
    "2023-11-05",
    "2024-11-03",
    "2025-11-02",
]

print("Loading comprehensive CSV...")

# Load all data into memory
all_rows = []
rows_by_timestamp = {}

with open('caiso_comprehensive_data.csv') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames

    for row in reader:
        all_rows.append(row)
        rows_by_timestamp[row['timestamp']] = row

print(f"Loaded {len(all_rows):,} rows")

# Fill DST gaps
filled_count = 0

print("\nFilling DST Spring Forward gaps (2:00-2:55 AM)...")

for date_str in DST_SPRING_FORWARD:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = date - timedelta(days=1)
    next_date = date + timedelta(days=1)

    # Check which 2:XX times are missing
    for minute in range(0, 60, 5):
        timestamp_str = f"{date_str} 02:{minute:02d}"

        if timestamp_str not in rows_by_timestamp:
            # Get same time from previous and next day
            prev_timestamp = f"{prev_date.strftime('%Y-%m-%d')} 02:{minute:02d}"
            next_timestamp = f"{next_date.strftime('%Y-%m-%d')} 02:{minute:02d}"

            prev_row = rows_by_timestamp.get(prev_timestamp)
            next_row = rows_by_timestamp.get(next_timestamp)

            if prev_row and next_row:
                # Create averaged row
                new_row = {'timestamp': timestamp_str}

                for col in fieldnames[1:]:  # Skip timestamp
                    prev_val = prev_row[col]
                    next_val = next_row[col]

                    # Only average numeric columns that have values
                    if prev_val and next_val and prev_val != '' and next_val != '':
                        try:
                            avg_val = (float(prev_val) + float(next_val)) / 2.0
                            new_row[col] = str(round(avg_val, 2))
                        except:
                            new_row[col] = ''
                    else:
                        new_row[col] = ''

                all_rows.append(new_row)
                rows_by_timestamp[timestamp_str] = new_row
                filled_count += 1

                if minute == 0:
                    print(f"  Filled {date_str} 02:00-02:55 by averaging neighbors")

print(f"\nFilled {filled_count} DST Spring Forward intervals")

# Sort rows by timestamp
all_rows.sort(key=lambda r: r['timestamp'])

# Write back to CSV
print("\nWriting updated CSV...")
with open('caiso_comprehensive_data.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Wrote {len(all_rows):,} rows to caiso_comprehensive_data.csv")
print(f"\nFilled {filled_count} missing intervals using neighbor day averaging")
