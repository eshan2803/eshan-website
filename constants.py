"""
constants.py
All constant values and configuration data for the transport LCA model.
Extracted from app.py for better organization and maintainability.
"""

import os

# =================================================================
# API KEYS
# =================================================================
API_KEY_GOOGLE = os.environ.get("API_KEY_GOOGLE", "ESHAN_API_KEY_GOOGLE")
API_KEY_SEAROUTES = os.environ.get("API_KEY_SEAROUTES", "ESHAN_API_KEY_SEAROUTES")
API_KEY_EIA = os.environ.get("API_KEY_EIA", "ESHAN_API_KEY_EIA")
API_KEY_WEATHER = os.environ.get("API_KEY_WEATHER", "ESHAN_API_KEY_WEATHER")
API_KEY_OPENAI = os.environ.get("API_KEY_OPENAI", "ESHAN_API_KEY_OPENAI")
API_KEY_ELECTRICITYMAP = os.environ.get("API_KEY_ELECTRICITYMAP", "ESHAN_API_KEY_ELECTRICITYMAP")

# =================================================================
# FUEL PROPERTIES
# =================================================================
HHV_DIESEL = 45.6  # Higher heating value of diesel (MJ/kg)
DIESEL_DENSITY = 3.22  # kg/L
CO2E_DIESEL = 10.21  # kg CO2e per kg diesel

# =================================================================
# SAFETY & CERTIFICATION COSTS
# =================================================================
SAFETY_CERTIFICATION_COST_PER_KG = {
    0: {'base_cost_usd': 15000, 'per_kg_rate': 0.01, 'threshold_kg': 10000},  # Liquid Hydrogen
    1: {'base_cost_usd': 10000, 'per_kg_rate': 0.005, 'threshold_kg': 10000}, # Ammonia
    2: {'base_cost_usd': 5000, 'per_kg_rate': 0.002, 'threshold_kg': 10000}   # Methanol
}

FOOD_INSPECTION_COST_PER_SHIPMENT = {
    "strawberry": {'base_cost_usd': 1000, 'per_container_usd': 300},
    "hass_avocado": {'base_cost_usd': 1500, 'per_container_usd': 400},
    "banana": {'base_cost_usd': 750, 'per_container_usd': 200}
}

# =================================================================
# VOYAGE & SHIP OPERATING COSTS
# =================================================================
VOYAGE_OVERHEADS_DATA = {
    'small': {
        'daily_operating_cost_usd': 8500,
        'daily_capital_cost_usd': 10000,
        'port_fee_usd': 30000,
        'suez_toll_per_gt_usd': 9.00,
        'panama_toll_per_gt_usd': 9.00,
        'daily_maintenance_cost_usd': 1400
    },
    'midsized': {
        'daily_operating_cost_usd': 15500,
        'daily_capital_cost_usd': 20000,
        'port_fee_usd': 50000,
        'suez_toll_per_gt_usd': 8.50,
        'panama_toll_per_gt_usd': 9.50,
        'daily_maintenance_cost_usd': 2500
    },
    'standard': {
        'daily_operating_cost_usd': 22000,
        'daily_capital_cost_usd': 35000,
        'port_fee_usd': 60000,
        'suez_toll_per_gt_usd': 8.00,
        'panama_toll_per_gt_usd': 9.00,
        'daily_maintenance_cost_usd': 3500
    },
    'q-flex': {
        'daily_operating_cost_usd': 20000,
        'daily_capital_cost_usd': 55000,
        'port_fee_usd': 80000,
        'suez_toll_per_gt_usd': 7.50,
        'panama_toll_per_gt_usd': 8.00,
        'daily_maintenance_cost_usd': 4500
    },
    'q-max': {
        'daily_operating_cost_usd': 25000,
        'daily_capital_cost_usd': 75000,
        'port_fee_usd': 90000,
        'suez_toll_per_gt_usd': 7.00,
        'panama_toll_per_gt_usd': 7.50,
        'daily_maintenance_cost_usd': 5500
    }
}

# =================================================================
# TRUCK TRANSPORT COSTS
# =================================================================
ANNUAL_WORKING_DAYS = 330

TRUCK_CAPEX_PARAMS = {
    0: {'cost_usd_per_truck': 1500000, 'useful_life_years': 10, 'annualization_factor': 0.15},  # Hydrogen
    1: {'cost_usd_per_truck': 800000, 'useful_life_years': 10, 'annualization_factor': 0.15},   # Ammonia
    2: {'cost_usd_per_truck': 200000, 'useful_life_years': 10, 'annualization_factor': 0.15}    # Methanol
}

MAINTENANCE_COST_PER_KM_TRUCK = 0.10  # $/km

# =================================================================
# INSURANCE & FINANCIAL COSTS
# =================================================================
INSURANCE_PERCENTAGE_OF_CARGO_VALUE = 1.0  # 1% of cargo value

BASE_PER_TRANSIT_INSURANCE_PERCENTAGE = 0.25  # 0.25% base rate
MINIMUM_INSURANCE_PREMIUM_USD = 750  # Minimum premium per shipment

ANNUAL_FINANCING_RATE = 0.06  # 6% annual interest rate for working capital

BROKERAGE_AND_AGENT_FEE_USD = 5000  # Flat fee per shipment

CONTINGENCY_PERCENTAGE = 0.10  # 10% contingency

COMMODITY_RISK_FACTORS = {
    "Liquid Hydrogen": 1.5,
    "Ammonia": 1.2,
    "Methanol": 0.8,
    "Strawberry": 0.6,
    "Hass Avocado": 0.7,
    "Banana": 0.75,
}

ROUTE_RISK_ZONES = [
    {
        "name": "Gulf of Aden/Somali Basin",
        "bbox": {"lon_min": 42.5, "lat_min": 10.0, "lon_max": 55.0, "lat_max": 18.0},
        "risk_multiplier": 2.5
    },
    {
        "name": "West African Coast",
        "bbox": {"lon_min": 0.0, "lat_min": 0.0, "lon_max": 15.0, "lat_max": 10.0},
        "risk_multiplier": 1.8
    },
    {
        "name": "South China Sea",
        "bbox": {"lon_min": 105.0, "lat_min": 0.0, "lon_max": 120.0, "lat_max": 20.0},
        "risk_multiplier": 1.3
    },
    {
        "name": "Hurricane Alley (Atlantic)",
        "bbox": {"lon_min": -95.0, "lat_min": 10.0, "lon_max": -40.0, "lat_max": 40.0},
        "risk_multiplier": 1.15
    },
]

# =================================================================
# BOG (Boil-Off Gas) EQUIPMENT COSTS
# =================================================================
BOG_EQUIPMENT_CAPEX = {
    'reliquefaction_unit': {
        'truck': {'cost_usd': 50000, 'life_years': 10, 'annualization_factor': 0.15},
        'ship': {'cost_usd_per_m3_volume': 100, 'life_years': 20, 'annualization_factor': 0.09},
        'storage': {'cost_usd_per_kg_capacity': 5.0, 'life_years': 20, 'annualization_factor': 0.09}
    },
    'aux_fuel_integration': {
        'truck': {'cost_usd': 10000, 'life_years': 10, 'annualization_factor': 0.15},
        'ship': {'cost_usd_per_m3_volume': 50, 'life_years': 20, 'annualization_factor': 0.09},
        'storage': {'cost_usd_per_kg_capacity': 1.5, 'life_years': 20, 'annualization_factor': 0.09}
    },
    'burner_flare': {
        'truck': {'cost_usd': 5000, 'life_years': 5, 'annualization_factor': 0.25},
        'ship': {'cost_usd_per_m3_volume': 20, 'life_years': 15, 'annualization_factor': 0.12},
        'storage': {'cost_usd_per_kg_capacity': 0.5, 'life_years': 15, 'annualization_factor': 0.12}
    }
}

# =================================================================
# CARBON TAX RATES BY COUNTRY ($/ton CO2)
# =================================================================
CARBON_TAX_PER_TON_CO2_DICT = {
    "Sweden": 144.62,          # 2025 rate from Tax Foundation
    "Switzerland": 136.04,     # 2025 rate from Tax Foundation
    "Liechtenstein": 136.04,   # 2025 rate from Tax Foundation
    "Poland": 0.10,            # 2025 rate from Tax Foundation
    "Ukraine": 0.73,           # 2025 rate from Tax Foundation
    "Norway": 107.78,          # 2024 rate from World Population Review
    "Finland": 100.02,         # 2024 rate from World Population Review
    "Netherlands": 71.51,      # 2024 rate from World Population Review
    "Portugal": 60.48,         # 2024 rate from World Population Review
    "Ireland": 60.22,          # 2024 rate from World Population Review
    "Luxembourg": 49.92,       # 2024 rate from World Population Review
    "Germany": 48.39,          # 2024 rate from World Population Review
    "Austria": 48.37,          # 2024 rate from World Population Review
    "France": 47.96,           # 2024 rate from World Population Review
    "Iceland": 36.51,          # 2024 rate from World Population Review
    "Denmark": 28.10,          # 2024 rate from World Population Review
    "United Kingdom": 22.62,   # 2024 rate from World Population Review
    "Slovenia": 18.60,         # 2024 rate from World Population Review
    "Spain": 16.13,            # 2024 rate from World Population Review
    "Latvia": 16.13,           # 2024 rate from World Population Review
    "Estonia": 2.18,           # 2024 rate from World Population Review
    "South Africa": 10.69,     # 2024 rate from World Population Review
    "Singapore": 19.55,        # 2024 rate from World Population Review
    "Uruguay": 167.00,         # 2024 rate from Statista
    "Japan": 2.65              # Rate from academic sources, stable since implementation
}

# =================================================================
# EU MEMBER COUNTRIES
# =================================================================
EU_MEMBER_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden"
]

# =================================================================
# IMPORT TARIFF RATES BY COUNTRY
# =================================================================
# Representative MFN Applied Tariffs (Source: World Bank, WTO)
# These are illustrative. For precise calculations, specific HS codes are needed.
IMPORT_TARIFF_RATES_DICT = {
    "United States": 0.034,  # 3.4%
    "China": 0.076,          # 7.6%
    "Japan": 0.025,          # 2.5%
    "Germany": 0.043,        # 4.3% (EU Common External Tariff)
    "United Kingdom": 0.043, # 4.3% (Mirrors EU for now)
    "India": 0.176,          # 17.6%
    "Brazil": 0.135,         # 13.5%
    "South Korea": 0.138,    # 13.8%
    "Canada": 0.041,         # 4.1%
    "Australia": 0.026,      # 2.6%
    "European Union": 0.043  # 4.3% (EU Common External Tariff)
}

# Add EU countries to map to the EU tariff rate
for country in EU_MEMBER_COUNTRIES:
    if country not in IMPORT_TARIFF_RATES_DICT:
        IMPORT_TARIFF_RATES_DICT[country] = IMPORT_TARIFF_RATES_DICT["European Union"]

# =================================================================
# LOADING/UNLOADING INFRASTRUCTURE CAPEX
# =================================================================
LOADING_UNLOADING_CAPEX_PARAMS = {
    0: {'total_capex_M_usd': 500, 'annualization_factor': 0.08},  # Hydrogen
    1: {'total_capex_M_usd': 200, 'annualization_factor': 0.08},  # Ammonia
    2: {'total_capex_M_usd': 80, 'annualization_factor': 0.08}   # Methanol
}

REFERENCE_ANNUAL_THROUGHPUT_TONS = {
    0: 1000000,   # Hydrogen - 1M tons/year
    1: 5000000,   # Ammonia - 5M tons/year
    2: 10000000   # Methanol - 10M tons/year
}

# =================================================================
# CACHE CONFIGURATION
# =================================================================
MAX_CACHE_SIZE = 500  # Limit cache to 500 entries to prevent memory issues
