import requests
import json
import sys
import time

EIA_API_KEY = "PhBn6Q4P6a3Gz86kPjyA3b6zye4SmZ64K1NwfxSm"
BASE_URL = "https://api.eia.gov/v2/electricity/operating-generator-capacity/data"

def fetch_ca_capacity_for_period(period, offset=0, page_size=5000):
    """
    Fetch all operating generators in California for a given period (e.g. '2024-01').
    Returns list of generator records, handling pagination.
    """
    all_records = []
    while True:
        params = {
            "api_key": EIA_API_KEY,
            "frequency": "monthly",
            "data[]": "nameplate-capacity-mw",
            "facets[stateid][]": "CA",
            "facets[status][]": "OP",  # Only operating generators
            "start": period,
            "end": period,
            "offset": offset,
            "length": page_size,
        }

        try:
            r = requests.get(BASE_URL, params=params, timeout=60)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  Error: {e}")
            break

        data = r.json()
        resp = data.get("response", {})
        records = resp.get("data", [])
        total = int(resp.get("total", 0))

        all_records.extend(records)
        print(f"  Fetched {len(all_records)}/{total} generators for {period}...")

        if len(all_records) >= total or not records:
            break
        offset += page_size
        time.sleep(1)

    return all_records


NG_TECHNOLOGY_MAP = {
    "Natural Gas Fired Combined Cycle": "Natural Gas - CCGT",
    "Natural Gas Fired Combustion Turbine": "Natural Gas - Peaker",
    "Natural Gas Steam Turbine": "Natural Gas - Steam",
    "Natural Gas Internal Combustion Engine": "Natural Gas - ICE",
    "Other Natural Gas": "Natural Gas - ICE",
}


def aggregate_by_resource(records):
    """
    Aggregate nameplate capacity (MW) by energy source description.
    Natural Gas generators are sub-categorized by technology field.
    Returns dict of {resource_type: total_mw}.
    """
    capacity = {}
    for rec in records:
        resource = rec.get("energy-source-desc", "Unknown")
        mw = rec.get("nameplate-capacity-mw")
        if mw is None:
            continue
        try:
            mw = float(mw)
        except (ValueError, TypeError):
            continue

        # Sub-categorize Natural Gas by technology
        if resource == "Natural Gas":
            tech = rec.get("technology", "")
            resource = NG_TECHNOLOGY_MAP.get(tech, "Natural Gas - ICE")

        capacity[resource] = capacity.get(resource, 0) + mw

    # Round values
    return {k: round(v, 1) for k, v in sorted(capacity.items(), key=lambda x: -x[1])}


def main():
    start_year = 2020
    end_year = 2025

    if len(sys.argv) >= 3:
        start_year = int(sys.argv[1])
        end_year = int(sys.argv[2])
    elif len(sys.argv) == 2:
        start_year = int(sys.argv[1])
        end_year = start_year

    print("==============================================")
    print("California Installed Capacity by Resource Type")
    print(f"Years: {start_year} to {end_year}")
    print(f"Source: EIA-860/860M (Operating Generators)")
    print("==============================================")

    # Fetch January of each year as the snapshot
    results = {}
    all_resources = set()

    for year in range(start_year, end_year + 1):
        period = f"{year}-01"
        print(f"\nFetching {year} (snapshot: {period})...")
        records = fetch_ca_capacity_for_period(period)

        if not records:
            print(f"  No data for {year}.")
            continue

        capacity = aggregate_by_resource(records)
        results[str(year)] = capacity
        all_resources.update(capacity.keys())

        total = sum(capacity.values())
        print(f"  Total installed: {total:,.1f} MW across {len(capacity)} resource types.")
        time.sleep(2)

    if not results:
        print("\nNo data retrieved.")
        sys.exit(1)

    # Save to JSON
    output_path = "capacity_by_resource.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {output_path}")

    # Print summary table
    sorted_resources = sorted(all_resources)
    print("\n--- California Installed Capacity by Resource Type (MW) ---")
    header = f"{'Resource Type':<30}"
    for year in sorted(results.keys()):
        header += f" {year:>10}"
    print(header)
    print("-" * len(header))

    for resource in sorted_resources:
        row = f"{resource:<30}"
        for year in sorted(results.keys()):
            val = results[year].get(resource)
            if val is not None:
                row += f" {val:>10,.1f}"
            else:
                row += f" {'-':>10}"
        print(row)

    # Total row
    print("-" * len(header))
    row = f"{'TOTAL':<30}"
    for year in sorted(results.keys()):
        total = sum(results[year].values())
        row += f" {total:>10,.1f}"
    print(row)


if __name__ == "__main__":
    main()
