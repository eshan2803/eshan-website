# CAISO Comprehensive Data CSV

## File: `caiso_comprehensive_data.csv`

**Size**: 69 MB
**Rows**: 656,987 (including header)
**Date Range**: 2020-01-01 to 2026-03-31
**Total Days**: 2,282 days

## Structure

### Time-based Format
- **Timestamp**: 5-minute intervals (`YYYY-MM-DD HH:MM`)
- **Generation data**: Present in ALL 5-minute rows
- **Demand, Prices**: Present ONLY at `:00` minutes (hourly)

### Columns

#### 1. Timestamp (1 column)
- `timestamp`: Date and time in format `YYYY-MM-DD HH:MM`

#### 2. Generation (13 columns, 5-minute intervals)
All values in MW:
- `solar_mw`: Solar photovoltaic generation
- `wind_mw`: Wind generation
- `natural_gas_mw`: Natural gas generation
- `nuclear_mw`: Nuclear generation
- `large_hydro_mw`: Large hydroelectric generation
- `small_hydro_mw`: Small hydroelectric generation
- `geothermal_mw`: Geothermal generation
- `biomass_mw`: Biomass generation
- `biogas_mw`: Biogas generation
- `batteries_mw`: Battery storage (positive = discharge, negative = charge)
- `imports_mw`: Imports from other regions
- `other_mw`: Other generation sources
- `coal_mw`: Coal generation

#### 3. Demand (1 column, hourly at :00)
- `demand_mw`: Grid demand in MW

#### 4. LMP Prices (5 columns, hourly at :00)
All values in $/MWh:
- `lmp`: Locational Marginal Price (total)
- `mcc`: Marginal Cost of Congestion component
- `mec`: Marginal Energy Cost component
- `ghg`: Greenhouse Gas cost component
- `loss`: Loss component

#### 5. Ancillary Services Prices (6 columns, hourly at :00)
All values in $/MW:
- `nr`: Non-Spinning Reserves
- `rd`: Regulation Down
- `rmd`: Regulation Mileage Down
- `rmu`: Regulation Mileage Up
- `ru`: Regulation Up
- `sr`: Spinning Reserves

## Example Data

```csv
timestamp,solar_mw,wind_mw,natural_gas_mw,...,demand_mw,lmp,nr,rd,...
2024-05-15 11:00,18267.0,808.0,5432.0,...,22399.0,19.35,0.1,0.57,...
2024-05-15 11:05,18180.0,804.0,5445.0,...,,,,,...
2024-05-15 11:10,18156.0,800.0,5458.0,...,,,,,...
2024-05-15 11:15,17972.0,790.0,5471.0,...,,,,,...
...
2024-05-15 12:00,18211.0,825.0,5389.0,...,22399.0,18.31,0.1,0.53,...
```

## Usage

### Reading in Python (pandas)
```python
import pandas as pd

# Read full dataset
df = pd.read_csv('caiso_comprehensive_data.csv')

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to specific date range
df_2024 = df[df['timestamp'].dt.year == 2024]

# Get only hourly data (with demand and prices)
df_hourly = df[df['demand_mw'].notna()]

# Calculate clean energy percentage
df['clean_mw'] = (df['solar_mw'] + df['wind_mw'] + df['nuclear_mw'] +
                  df['large_hydro_mw'] + df['small_hydro_mw'] +
                  df['geothermal_mw'] + df['biomass_mw'] + df['biogas_mw'])
df_hourly['clean_pct'] = (df_hourly['clean_mw'] / df_hourly['demand_mw']) * 100
```

### Reading in R
```r
library(tidyverse)

# Read full dataset
df <- read_csv('caiso_comprehensive_data.csv')

# Convert timestamp
df$timestamp <- as.POSIXct(df$timestamp)

# Filter to hourly data
df_hourly <- df %>% filter(!is.na(demand_mw))
```

## Appending New Data

To add new data in the future:

### 1. Add Source Data
- Add new fuelsource CSV files to `caiso_supply/` directory
  - Format: `YYYYMMDD_fuelsource.csv`
- Add new demand CSV files to `caiso_demand_downloads/` directory
  - Format: `YYYYMMDD_demand.csv`
- Update `caiso_prices.json` with new LMP price data
- Update `ancillary_services.json` with new A/S price data

### 2. Regenerate CSV
```bash
python create_comprehensive_csv.py
```

The script will:
- Process all available data files
- Regenerate the complete CSV with all historical + new data
- Maintain the same structure and format

**Note**: The script regenerates the entire file rather than appending. This ensures consistency and handles any corrections to historical data.

## Data Quality Notes

### Missing Values
- Empty cells indicate no data available for that metric at that timestamp
- Demand, LMP, and A/S prices are ONLY filled at `:00` minutes
- If demand CSV is missing for a day, `demand_mw` will be empty for all hours
- If LMP data is missing for a day, all price columns will be empty

### Data Sources
- **Generation**: CAISO Today's Outlook - Supply (5-minute fuel source data)
- **Demand**: CAISO Today's Outlook - Demand Trend (hourly data)
- **LMP Prices**: CAISO OASIS API (hourly data)
- **Ancillary Services**: CAISO OASIS API (hourly data)

### Coverage
- **Generation & Demand**: 2020-01-01 to 2026-03-31 (2,282 days, 100% coverage)
- **LMP Prices**: 2020-01-01 to 2026-04-01 (2,261 days, 99.1% coverage)
- **A/S Prices**: 2020-02-01 to 2026-03-31 (2,282 days from Feb 2020)

## File Maintenance

### Storage Recommendations
- **Local storage**: Keep CSV for fast access
- **Backup**: Store compressed version (.csv.gz saves ~70% space)
- **Cloud**: Consider splitting by year if uploading to cloud storage

### Compression
To compress for storage/transfer:
```bash
# Compress (creates .csv.gz)
gzip -k caiso_comprehensive_data.csv

# Decompress
gunzip caiso_comprehensive_data.csv.gz
```

## Related Files

- `create_comprehensive_csv.py`: Script to generate/regenerate this CSV
- `renewable_penetration_daily_corrected_full.json`: Daily clean energy penetration statistics
- `caiso_prices.json`: Raw hourly LMP price data
- `ancillary_services.json`: Raw hourly A/S price data
- `natural_gas_daily.json`: Daily natural gas generation statistics

## Version History

- **2026-04-02**: Initial comprehensive CSV created
  - 2,282 days of data (2020-01-01 to 2026-03-31)
  - All generation, demand, LMP, and A/S data integrated
  - 656,987 rows (5-minute intervals)
