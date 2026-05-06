"""Find January 2024 dates with data quality issues."""
import re

log_file = "data_issues_log.txt"

with open(log_file, 'r') as f:
    content = f.read()

# Find all dates in January 2024 that have issues
jan2024_pattern = r'(2024-01-\d{2}):'
matches = re.findall(jan2024_pattern, content)

if matches:
    print(f"Found {len(matches)} dates in January 2024 with data issues:")
    print()
    for date in sorted(set(matches)):
        print(f"  {date}")
else:
    print("No January 2024 dates found with issues!")
    print("This means January 2024 data is good!")
