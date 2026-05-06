import json

file = "caiso_prices.json"
with open(file, "r") as f:
    d = json.load(f)

count = 0
for k in list(d.keys()):
    if k.startswith("2026-03") or k.startswith("2026-04"):
        del d[k]
        count += 1

print(f"Deleted {count} days of stale data from Jan-April 2026.")

with open(file, "w") as f:
    json.dump(d, f, indent=2)
