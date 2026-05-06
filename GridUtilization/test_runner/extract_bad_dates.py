"""
Extract dates that need re-downloading (Large hydro or Natural gas issues).
"""
import re

log_file = "C:\\Users\\eshan\\.claude\\projects\\c--Users-eshan-OneDrive-Desktop-eshan-website-eshan-website-repo-GridUtilization\\52b655b1-654b-4eca-82aa-73b733c55f79\\tool-results\\b217728.txt"

with open(log_file, 'r') as f:
    content = f.read()

# Find all date sections
date_pattern = r'(\d{4}-\d{2}-\d{2}):'
lines = content.split('\n')

bad_dates = []
current_date = None

for line in lines:
    # Check if this is a date line
    date_match = re.match(r'^\s+(\d{4}-\d{2}-\d{2}):', line)
    if date_match:
        current_date = date_match.group(1)

    # Check if this date has Large hydro or Natural gas issues
    if current_date and ('Large hydro near-zero' in line or 'Natural gas very low' in line):
        if current_date not in bad_dates:
            bad_dates.append(current_date)

# Sort dates
bad_dates.sort()

print(f"Found {len(bad_dates)} dates with Large hydro or Natural gas issues:")
print()

# Group by year
by_year = {}
for date in bad_dates:
    year = date[:4]
    if year not in by_year:
        by_year[year] = []
    by_year[year].append(date)

for year in sorted(by_year.keys()):
    dates = by_year[year]
    print(f"{year}: {len(dates)} dates")

print()
print("Date range summary:")
print(f"  First bad date: {bad_dates[0]}")
print(f"  Last bad date: {bad_dates[-1]}")

# Write to file for download script
output_file = "dates_to_download.txt"
with open(output_file, 'w') as f:
    for date in bad_dates:
        f.write(date + '\n')

print(f"\nWritten all dates to: {output_file}")
print(f"Total: {len(bad_dates)} dates need re-downloading")
