"""
Fetch CAISO Ancillary Service clearing prices (DAM) from OASIS API.
AS types: Regulation Up, Regulation Down, Spinning Reserve, Non-Spinning Reserve.
Stores hourly prices per day in ancillary_services.json.
"""
import requests
import zipfile
import io
import pandas as pd
import json
import datetime
import time
import calendar
import os

BASE_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
OUTPUT_FILE = "ancillary_services.json"

# CAISO AS regions — use system-wide
AS_REGION = "AS_CAISO_EXP"

# AS type codes returned by OASIS PRC_AS report
AS_TYPES = {
    "RU":  "Regulation Up",
    "RD":  "Regulation Down",
    "RMU": "Regulation Mileage Up",
    "RMD": "Regulation Mileage Down",
    "SR":  "Spinning Reserve",
    "NR":  "Non-Spinning Reserve",
}


def fetch_as_range(start_date, end_date, max_retries=3):
    """Fetch AS clearing prices for a date range from OASIS."""
    start_str = start_date.strftime("%Y%m%d") + "T00:00-0800"
    end_str = end_date.strftime("%Y%m%d") + "T23:59-0800"

    print(f"  Fetching {start_date} to {end_date} ...")

    params = {
        "queryname": "PRC_AS",
        "startdatetime": start_str,
        "enddatetime": end_str,
        "market_run_id": "DAM",
        "anc_type": "ALL",
        "anc_region": AS_REGION,
        "version": "1",
        "resultformat": "6",
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=180)

            if response.status_code == 429:
                wait = 15 * attempt
                print(f"    Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue

            if b"<?xml" in response.content[:100]:
                if b"No data returned" in response.content:
                    print(f"    No data returned.")
                    return pd.DataFrame()
                print(f"    API error: {response.content[:300]}")
                return None

            response.raise_for_status()

            try:
                z = zipfile.ZipFile(io.BytesIO(response.content))
                csv_files = [f for f in z.namelist() if f.endswith(".csv")]
                if not csv_files:
                    print(f"    No CSV in ZIP. Files: {z.namelist()}")
                    return None

                dfs = []
                for f in csv_files:
                    with z.open(f) as csv_file:
                        df = pd.read_csv(csv_file)
                        dfs.append(df)

                if dfs:
                    combined = pd.concat(dfs, ignore_index=True)
                    print(f"    Got {len(combined)} rows, columns: {list(combined.columns)}")
                    return combined
                return None

            except zipfile.BadZipFile:
                print("    Invalid ZIP response.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"    Request error: {e}. Retrying...")
            time.sleep(5 * attempt)

    return None


def generate_month_ranges(start_date, end_date):
    current = start_date.replace(day=1)
    while current <= end_date:
        month_start = max(current, start_date)
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = min(
            datetime.date(current.year, current.month, last_day), end_date
        )
        yield month_start, month_end
        if current.month == 12:
            current = datetime.date(current.year + 1, 1, 1)
        else:
            current = datetime.date(current.year, current.month + 1, 1)


def main():
    start_date = datetime.date(2020, 1, 1)
    end_date = datetime.date.today() - datetime.timedelta(days=1)

    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                existing_data = json.load(f)
            print(f"Loaded {len(existing_data)} days of existing AS data.")
        except json.JSONDecodeError:
            print("Corrupt JSON. Starting fresh.")

    month_ranges = list(generate_month_ranges(start_date, end_date))

    for i, (m_start, m_end) in enumerate(month_ranges, 1):
        # Check completeness
        days_in_month = (m_end - m_start).days + 1
        days_present = sum(
            1
            for d in range(days_in_month)
            if (m_start + datetime.timedelta(days=d)).strftime("%Y-%m-%d")
            in existing_data
        )

        if days_present == days_in_month:
            print(
                f"[{i}/{len(month_ranges)}] {m_start} to {m_end} — already complete. Skipping."
            )
            continue

        print(f"[{i}/{len(month_ranges)}] Processing {m_start} to {m_end}...")

        df = fetch_as_range(m_start, m_end)
        if df is None or df.empty:
            print(f"  No data for this month.")
            time.sleep(5)
            continue

        # Debug: print unique data items and columns on first fetch
        if i == 1 or len(existing_data) == 0:
            print(f"  Columns: {list(df.columns)}")
            if "XML_DATA_ITEM" in df.columns:
                print(f"  Data items: {df['XML_DATA_ITEM'].unique()}")
            if "ANC_TYPE" in df.columns:
                print(f"  ANC_TYPE values: {df['ANC_TYPE'].unique()}")
            if "ANC_REGION" in df.columns:
                print(f"  ANC_REGION values: {df['ANC_REGION'].unique()}")

        # Parse dates
        if "OPR_DT" in df.columns:
            df["OPR_DT"] = pd.to_datetime(df["OPR_DT"])

        # Determine value column
        value_col = "MW" if "MW" in df.columns else "VALUE"

        # Build daily JSON
        current_day = m_start
        while current_day <= m_end:
            day_str = current_day.strftime("%Y-%m-%d")
            day_ts = pd.Timestamp(current_day)

            day_df = df[df["OPR_DT"] == day_ts]
            if day_df.empty:
                current_day += datetime.timedelta(days=1)
                continue

            day_dict = {}
            for h in range(1, 25):
                h_df = day_df[day_df["OPR_HR"] == h]
                if h_df.empty:
                    continue

                h_dict = {}
                for _, row in h_df.iterrows():
                    anc_type = row.get("ANC_TYPE", "")
                    if anc_type in AS_TYPES:
                        val = row[value_col]
                        h_dict[anc_type] = round(float(val), 2)

                if h_dict:
                    day_dict[str(h)] = h_dict

            if day_dict:
                existing_data[day_str] = day_dict

            current_day += datetime.timedelta(days=1)

        # Save after each month
        with open(OUTPUT_FILE, "w") as f:
            json.dump(existing_data, f)

        print(f"  Saved. Total days: {len(existing_data)}")
        time.sleep(5)

    # Final save with formatting
    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing_data, f, indent=2)

    print(f"\nDone. {len(existing_data)} days saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
