        // --- FIREBASE IMPORTS ---
        import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
        import { getAuth, signInAnonymously } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";
        import { getFirestore, doc, runTransaction, setLogLevel } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";

        // --- HARDCODED FIREBASE CONFIGURATION ---
        const firebaseConfig = {
          apiKey: "AIzaSyCdEeu0VugTfZD-R-62pFvBdb313TeM4xs",
          authDomain: "grid-decarbonization.firebaseapp.com",
          projectId: "grid-decarbonization",
          storageBucket: "grid-decarbonization.appspot.com",
          messagingSenderId: "902419724670",
          appId: "1:902419724670:web:b636a75ea44325946a9b2f",
          measurementId: "G-3Q9HE19CGN"
        };
        
        // --- INITIALIZE FIREBASE & DEFINE KEY VARIABLES ---
        const app = initializeApp(firebaseConfig);
        const db = getFirestore(app);
        const auth = getAuth(app);
        const appId = firebaseConfig.appId;

        // --- MODEL PARAMETERS & DATA (GLOBAL SCOPE) ---
        const HOURS = Array.from({ length: 24 }, (_, i) => `${i}:00`);
        
        const countryGridMixData = {
            "California": { 
                totalCapacityMW: 89223, 
                peakLoadsMW: { summer: 52061, winter: 47500, fall: 46000, spring: 41000 },
                mix: { coal: 0.1, naturalGas: 43.4, hydro: 15.7, wind: 7.1, offshoreWind: 0, solar: 26.1, nuclear: 2.7, geothermal: 3.0, biomass: 1.0 , rng: 0.4},
                storageGWh: { battery4hr: 53.0 },
                defaultExportPrice: -20
            },
            "China": { 
                totalCapacityMW: 3400000, 
                peakLoadsMW: { summer: 1340000, winter: 1206000, fall: 1179200, spring: 1072000 },
                mix: { coal: 40.0, naturalGas: 8.0, hydro: 12.5, wind: 14.0, offshoreWind: 1.6, solar: 20.0, nuclear: 2.5, geothermal: 0.1, biomass: 0.9 , rng: 0.4},
                storageGWh: { battery4hr: 222 }
            },
            "United States": { 
                totalCapacityMW: 1275000, 
                peakLoadsMW: { summer: 800000, winter: 720000, fall: 704000, spring: 640000 },
                mix: { coal: 15.0, naturalGas: 48.0, hydro: 7.8, wind: 11.5, offshoreWind: 0.2, solar: 9.0, nuclear: 8.0, geothermal: 0.3, biomass: 0.8 , rng: 0.4},
                storageGWh: { battery4hr: 95 }
            },
            "India": { 
                totalCapacityMW: 476000, 
                peakLoadsMW: { summer: 243000, winter: 206550, fall: 213840, spring: 194400 },
                mix: { coal: 50.0, naturalGas: 6.0, hydro: 10.0, wind: 9.5, offshoreWind: 0, solar: 18.0, nuclear: 1.8, geothermal: 0.0, biomass: 1.9 , rng: 0.8},
                storageGWh: { battery4hr: 1 }
            },
            "Japan": { 
                totalCapacityMW: 295000, 
                peakLoadsMW: { summer: 181000, winter: 162900, fall: 159280, spring: 144800 },
                mix: { coal: 20.0, naturalGas: 35.0, hydro: 17.0, wind: 1.6, offshoreWind: 0.1, solar: 15.5, nuclear: 10.5, geothermal: 0.2, biomass: 1.1 , rng: 0.5},
                storageGWh: { battery4hr: 1.2 }
            },
            "Russia": { 
                totalCapacityMW: 248000, 
                peakLoadsMW: { winter: 160000, summer: 144000, fall: 140800, spring: 128000 },
                mix: { coal: 15.0, naturalGas: 52.0, hydro: 20.0, wind: 0.9, offshoreWind: 0, solar: 0.8, nuclear: 11.3, geothermal: 0.0, biomass: 0.1 , rng: 0.1} 
            },
            "Brazil": { 
                totalCapacityMW: 180000, 
                peakLoadsMW: { summer: 101860, winter: 91674, fall: 89637, spring: 81488 },
                mix: { coal: 2.0, naturalGas: 18.0, hydro: 59.0, wind: 10.5, offshoreWind: 0, solar: 9.5, nuclear: 1.0, geothermal: 0.0, biomass: 5.6 , rng: 2.4} 
            },
            "Germany": { 
                totalCapacityMW: 210000, 
                peakLoadsMW: { winter: 84000, summer: 75600, fall: 73920, spring: 67200 },
                mix: { coal: 14.0, naturalGas: 38.0, hydro: 4.0, wind: 22.0, offshoreWind: 4.0, solar: 12.0, nuclear: 5.0, geothermal: 0.0, biomass: 4.2 , rng: 1.8},
                storageGWh: { battery4hr: 22.1 }
            },
            "Canada": { 
                totalCapacityMW: 165000, 
                peakLoadsMW: { winter: 140000, summer: 126000, fall: 123200, spring: 112000 },
                mix: { coal: 4.5, naturalGas: 13.5, hydro: 57.0, wind: 8.5, offshoreWind: 0, solar: 2.5, nuclear: 14.0, geothermal: 0.0, biomass: 1.4 , rng: 0.6},
                storageGWh: { battery4hr: 1 }
            },
            "South Korea": { 
                totalCapacityMW: 125000, 
                peakLoadsMW: { summer: 93000, winter: 83700, fall: 81840, spring: 74400 },
                mix: { coal: 34.0, naturalGas: 20.0, hydro: 5.0, wind: 1.4, offshoreWind: 0.1, solar: 12.5, nuclear: 27.0, geothermal: 0.0, biomass: 0.7 , rng: 0.3},
                storageGWh: { battery4hr: 9 }
            },
            "France": { 
                totalCapacityMW: 115000, 
                peakLoadsMW: { winter: 102000, summer: 91800, fall: 89760, spring: 81600 },
                mix: { coal: 1.0, naturalGas: 10.0, hydro: 10.0, wind: 8.0, offshoreWind: 0.5, solar: 6.0, nuclear: 64.0, geothermal: 0.0, biomass: 0.3 , rng: 0.1},
                storageGWh: { battery4hr: 1.0 }
            },
            "United Kingdom": { 
                totalCapacityMW: 78000, 
                peakLoadsMW: { winter: 60000, summer: 54000, fall: 52800, spring: 48000 },
                mix: { coal: 1.0, naturalGas: 38.0, hydro: 2.0, wind: 15.0, offshoreWind: 14.0, solar: 19.0, nuclear: 9.0, geothermal: 0.0, biomass: 4.2 , rng: 1.8},
                 storageGWh: { battery4hr: 16.0 }
            },
            "Australia": { 
                totalCapacityMW: 65000, 
                peakLoadsMW: { summer: 47000, winter: 42300, fall: 41360, spring: 37600 },
                mix: { coal: 45.0, naturalGas: 18.0, hydro: 13.0, wind: 10.0, offshoreWind: 0, solar: 13.0, nuclear: 0.0, geothermal: 0.0, biomass: 0.7 , rng: 0.3},
                storageGWh: { battery4hr: 5.6 }
            },
            "Spain": { 
                totalCapacityMW: 120000, 
                peakLoadsMW: { summer: 45000, winter: 40500, fall: 39600, spring: 36000 },
                mix: { coal: 2.0, naturalGas: 22.0, hydro: 17.0, wind: 27.5, offshoreWind: 0, solar: 21.5, nuclear: 7.0, geothermal: 0.0, biomass: 1.0 , rng: 0.4},
                storageGWh: { battery4hr: 1.7 }
            },
            "Italy": { 
                totalCapacityMW: 122000, 
                peakLoadsMW: { summer: 60000, winter: 54000, fall: 52800, spring: 48000 },
                mix: { coal: 4.0, naturalGas: 47.0, hydro: 18.0, wind: 10.0, offshoreWind: 0, solar: 19.0, nuclear: 0.0, geothermal: 1.0, biomass: 1.4 , rng: 0.6},
                storageGWh: { battery4hr: 6 }
            },
            "Indonesia": { 
                totalCapacityMW: 75000, 
                peakLoadsMW: { summer: 50000, winter: 45000, fall: 44000, spring: 40000 },
                mix: { coal: 48.0, naturalGas: 28.0, hydro: 9.0, wind: 0.2, offshoreWind: 0, solar: 2.8, nuclear: 0.0, geothermal: 3.0, biomass: 0.7 , rng: 0.3} 
            },
            "South Africa": { 
                totalCapacityMW: 60000, 
                peakLoadsMW: { winter: 34000, summer: 30600, fall: 29920, spring: 27200 },
                mix: { coal: 78.0, naturalGas: 6.0, hydro: 6.0, wind: 5.5, offshoreWind: 0, solar: 3.5, nuclear: 0.0, geothermal: 0.0, biomass: 0.3 , rng: 0.1},
                storageGWh: { battery4hr: 2 }
            },
            "Mexico": { 
                totalCapacityMW: 88000, 
                peakLoadsMW: { summer: 50000, winter: 45000, fall: 44000, spring: 40000 },
                mix: { coal: 5.0, naturalGas: 58.0, hydro: 15.0, wind: 9.0, offshoreWind: 0, solar: 11.0, nuclear: 1.0, geothermal: 1.0, biomass: 0.3 , rng: 0.1} ,
                storageGWh: { battery4hr: 0.6 }
            },
            "Norway": { 
                totalCapacityMW: 39000, 
                peakLoadsMW: { winter: 25000, summer: 22500, fall: 22000, spring: 20000 },
                mix: { coal: 0.0, naturalGas: 0.0, hydro: 91.0, wind: 8.5, offshoreWind: 0, solar: 0.5, nuclear: 0.0, geothermal: 0.0, biomass: 0.0 , rng: 0.0} ,
                storageGWh: { battery4hr: 0.2 }
            },
            "New Zealand": { 
                totalCapacityMW: 9800, 
                peakLoadsMW: { winter: 7000, summer: 6300, fall: 6160, spring: 5600 },
                mix: { coal: 0.0, naturalGas: 14.0, hydro: 56.0, wind: 7.5, offshoreWind: 0, solar: 1.5, nuclear: 0.0, geothermal: 20.0, biomass: 0.7 , rng: 0.3},
                storageGWh: { battery4hr: 0.4 } 
            },
            "Vietnam": { 
                totalCapacityMW: 80000, 
                peakLoadsMW: { summer: 45000, winter: 40500, fall: 39600, spring: 36000 },
                mix: { coal: 32.0, naturalGas: 9.0, hydro: 28.0, wind: 6.0, offshoreWind: 0, solar: 24.0, nuclear: 0.0, geothermal: 0.0, biomass: 0.7 , rng: 0.3},
                storageGWh: { battery4hr: 0.1 } 
            }
        };

        const carbonTaxes = {
            "California": 26, "Canada": 61, "China": 8, "France": 48, "Germany": 43, "Japan": 2, 
            "South Korea": 22, "Spain": 16, "United Kingdom": 22, "South Africa": 9,
            "Mexico": 3, "Norway": 85, "New Zealand": 50
        };
        const SEASONAL_DEMAND_PROFILES = {
            'spring-high':    [28, 26, 25, 24, 24, 25, 28, 32, 33, 32, 30, 28, 27, 28, 30, 34, 39, 45, 48, 46, 42, 38, 34, 30],
            'summer-high':    [30, 28, 27, 26, 26, 27, 29, 33, 37, 40, 42, 44, 46, 48, 50, 52, 55, 56, 55, 52, 48, 43, 38, 33],
            'fall-high':      [27, 25, 24, 23, 23, 24, 27, 31, 34, 36, 37, 38, 39, 40, 41, 43, 46, 50, 49, 46, 42, 37, 32, 29],
            'winter-high':    [32, 30, 29, 29, 30, 34, 40, 45, 44, 42, 40, 39, 39, 40, 41, 43, 45, 46, 45, 42, 39, 36, 34, 32]
        };
        
        // This object will hold the calculated POTENTIAL generation, not a pre-dispatched baseline.
        let BASELINE_POTENTIAL_GENERATION = {}; 
        let currentCountryInstalledCapacity = {};
        let currentBaselineStorage = {};
        let dailyGenerationTotalsGWh = {}; // For tooltips

        const SOLAR_CF_PROFILE = [0,0,0,0,0,0.05,0.15,0.3,0.5,0.7,0.8,0.85,0.9,0.85,0.8,0.7,0.3,0.05,0,0,0,0,0,0];
        const WIND_CF_PROFILE = [0.4,0.42,0.45,0.46,0.45,0.4,0.35,0.3,0.25,0.2,0.2,0.2,0.25,0.3,0.35,0.4,0.5,0.6,0.65,0.6,0.55,0.5,0.45,0.4];
        const OFFSHORE_WIND_CF_PROFILE = [0.55,0.56,0.57,0.58,0.58,0.57,0.55,0.52,0.5,0.48,0.47,0.46,0.47,0.48,0.5,0.52,0.55,0.6,0.62,0.61,0.6,0.58,0.57,0.56];

        const SEASONAL_HYDRO_CF = {
            spring: 0.50,
            summer: 0.30,
            fall: 0.25,
            winter: 0.35
        };

        const SEASONAL_MULTIPLIERS = {
            spring: { solar: 1.0, wind: 1.0, offshoreWind: 1.0 },
            summer: { solar: 1.1, wind: 0.8, offshoreWind: 0.9 },
            fall: { solar: 0.8, wind: 1.0, offshoreWind: 1.0 },
            winter: { solar: 0.6, wind: 1.1, offshoreWind: 1.1 }
        };
        const countryProfiles = {
            "California": { // Using default CA profile
                solar: SOLAR_CF_PROFILE,
                wind: WIND_CF_PROFILE,
                offshoreWind: OFFSHORE_WIND_CF_PROFILE
            },
            "Germany": {
                solar: [0,0,0,0,0,0.02,0.1,0.25,0.45,0.6,0.7,0.75,0.7,0.6,0.4,0.15,0.05,0,0,0,0,0,0,0],
                wind: [0.5,0.52,0.55,0.56,0.55,0.5,0.45,0.4,0.35,0.3,0.3,0.3,0.35,0.4,0.45,0.5,0.6,0.7,0.75,0.7,0.65,0.6,0.55,0.5],
                offshoreWind: [0.6,0.62,0.65,0.66,0.65,0.6,0.55,0.5,0.45,0.4,0.4,0.4,0.45,0.5,0.55,0.6,0.7,0.8,0.85,0.8,0.75,0.7,0.65,0.6]
            },
            "United Kingdom": {
                solar: [0,0,0,0,0,0.01,0.08,0.2,0.4,0.55,0.65,0.7,0.65,0.55,0.35,0.1,0.02,0,0,0,0,0,0,0],
                wind: [0.6,0.62,0.65,0.68,0.66,0.6,0.55,0.5,0.45,0.4,0.4,0.4,0.45,0.5,0.55,0.6,0.7,0.8,0.85,0.8,0.75,0.7,0.65,0.6],
                offshoreWind: [0.7,0.72,0.75,0.78,0.76,0.7,0.65,0.6,0.55,0.5,0.5,0.5,0.55,0.6,0.65,0.7,0.8,0.9,0.95,0.9,0.85,0.8,0.75,0.7]
            },
            "Australia": {
                solar: [0,0,0,0,0,0.08,0.2,0.4,0.6,0.8,0.9,0.95,0.9,0.8,0.6,0.3,0.1,0,0,0,0,0,0,0],
                wind: [0.3,0.3,0.3,0.25,0.2,0.2,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.45,0.4,0.35,0.3,0.3,0.3,0.35,0.4,0.4,0.35,0.3],
                offshoreWind: [0.4,0.4,0.4,0.35,0.3,0.3,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.55,0.5,0.45,0.4,0.4,0.4,0.45,0.5,0.5,0.45,0.4]
            },
            "default": {
                solar: SOLAR_CF_PROFILE,
                wind: WIND_CF_PROFILE,
                offshoreWind: OFFSHORE_WIND_CF_PROFILE
            }
        };
        const EMISSION_FACTORS = { naturalGas: 395, hydro: 0, nuclear: 0, solar: 0, wind: 0, offshoreWind: 0, geothermal: 0, coal: 850, biomass: 0, rng: 0 };
        
        const COST_DATA = {
            capex: { 
                solar: 1200, wind: 1500, offshoreWind: 5000, nuclear: 7242, geothermal: 3329, biomass: 3500, rng: 3000,
                naturalGas: 1300, hydro: 3336, coal: 4407,
                battery4hr: 350, battery8hr: 300, longduration: 300, // $/kWh
                dac: 1000 // $/ton/year
            },
            fixed_om: {
                solar: 15, wind: 35, offshoreWind: 100, nuclear: 140, geothermal: 120, biomass: 100, rng: 95, // $/kW-year
                naturalGas: 20, hydro: 20, coal: 40,
                battery4hr: 15, battery8hr: 15, longduration: 60, // $/kW-year
                dac: 20 // $/ton/year
            },
            variable_om: { 
                solar: 0, wind: 1, offshoreWind: 0, nuclear: 10, geothermal: 5, biomass: 10, rng: 50, // $/MWh
                naturalGasCCGT: { start: 35, end: 80 }, // NEW: $/MWh
                naturalGasCT: { start: 100, end: 150 }, // NEW: $/MWh
                hydro: 5, coal: 30, // $/MWh 
                battery4hr: 0, battery8hr: 2, longduration: 1,
                dac: 400, // $/ton
                storage: 30 // $/MWh - an assumed opportunity cost for dispatching storage
            },
            lifetime: {
                solar: 30, wind: 30, offshoreWind: 30, nuclear: 60, geothermal: 30, biomass: 25, rng: 25,
                naturalGas: 30, hydro: 80, coal: 40,
                battery4hr: 15, battery8hr: 15, longduration: 25, dac: 25
            },
            capacity_factor: {
                solar: 0.25, wind: 0.35, offshoreWind: 0.50, nuclear: 0.9, geothermal: 0.9, biomass: 0.85, rng: 0.85,
                naturalGas: 0.55, hydro: 0.45, coal: 0.6
            },
            discount_rate: 0.07
        };

        document.addEventListener('DOMContentLoaded', async function() {
            setLogLevel('debug');

            // --- DOM ELEMENTS ---
            const sliders = {
                solar: document.getElementById('solar-slider'), wind: document.getElementById('wind-slider'), offshoreWind: document.getElementById('offshoreWind-slider'),
                geothermal: document.getElementById('geothermal-slider'), nuclear: document.getElementById('nuclear-slider'),
                biomass: document.getElementById('biomass-slider') rng: document.getElementById('rng-slider'),
                battery4hr: document.getElementById('battery4hr-slider'), battery8hr: document.getElementById('battery8hr-slider'),
                longduration: document.getElementById('longduration-slider'), demandflex: document.getElementById('demandflex-slider'),
                dac: document.getElementById('dac-slider'), solarIncentive: document.getElementById('solar-incentive-slider'),
                windIncentive: document.getElementById('wind-incentive-slider'), offshoreWindIncentive: document.getElementById('offshoreWind-incentive-slider'),
                geothermalIncentive: document.getElementById('geothermal-incentive-slider'),
                nuclearIncentive: document.getElementById('nuclear-incentive-slider'), biomassIncentive: document.getElementById('biomass-incentive-slider')
                rngIncentive: document.getElementById('rng-incentive-slider'),
                storageIncentive: document.getElementById('storage-incentive-slider'),
                dacIncentive: document.getElementById('dac-incentive-slider'), carbonTax: document.getElementById('carbon-tax-slider'),
                exportPrice: document.getElementById('export-price-slider'),
            };
            const inputs = {
                solar: document.getElementById('solar-input'), wind: document.getElementById('wind-input'), offshoreWind: document.getElementById('offshoreWind-input'),
                geothermal: document.getElementById('geothermal-input'), nuclear: document.getElementById('nuclear-input'),
                biomass: document.getElementById('biomass-input') rng: document.getElementById('rng-input'),
                battery4hr: document.getElementById('battery4hr-input'), battery8hr: document.getElementById('battery8hr-input'),
                longduration: document.getElementById('longduration-input'), demandflex: document.getElementById('demandflex-input'),
                dac: document.getElementById('dac-input'), solarIncentive: document.getElementById('solar-incentive-input'),
                windIncentive: document.getElementById('wind-incentive-input'), offshoreWindIncentive: document.getElementById('offshoreWind-incentive-input'),
                geothermalIncentive: document.getElementById('geothermal-incentive-input'),
                nuclearIncentive: document.getElementById('nuclear-incentive-input'), biomassIncentive: document.getElementById('biomass-incentive-input')
                rngIncentive: document.getElementById('rng-incentive-input'),
                storageIncentive: document.getElementById('storage-incentive-input'),
                dacIncentive: document.getElementById('dac-incentive-input'), carbonTax: document.getElementById('carbon-tax-input'),
                exportPrice: document.getElementById('export-price-input'),
            };

            const billImpactEl = document.getElementById('bill-impact');
            const systemCostImpactEl = document.getElementById('system-cost-impact');
            const co2AvoidedEl = document.getElementById('co2-avoided-text');
            const resetToZeroButton = document.getElementById('reset-to-zero-button');
            const makeDefaultButton = document.getElementById('make-default-button');
            const resetToDefaultButton = document.getElementById('reset-to-default-button');
            const undoButton = document.getElementById('undo-button');
            const redoButton = document.getElementById('redo-button');
            const gridMixSlidersContainer = document.getElementById('grid-mix-sliders');
            const storageCapacityDisplayContainer = document.getElementById('storage-capacity-display');
            const generationMixSlidersContainer = document.getElementById('generation-mix-sliders');
            const countrySelect = document.getElementById('country-select');
            const hoverTooltip = document.getElementById('hover-tooltip');
            const startTutorialBtn = document.getElementById('start-tutorial-btn');
            
            const currentDemandProfileText = document.getElementById('current-demand-profile-text');
            const editDemandBtn = document.getElementById('edit-demand-btn');
            const confirmDemandBtn = document.getElementById('confirm-demand-btn');
            const revertDemandBtn = document.getElementById('revert-demand-btn');
            const demandPresetsDiv = document.getElementById('demand-presets');

            const currentCFProfileText = document.getElementById('current-cf-profile-text');
            const editCFBtn = document.getElementById('edit-cf-btn');
            const confirmCFBtn = document.getElementById('confirm-cf-btn');
            const revertCFBtn = document.getElementById('revert-cf-btn');
            const cfPresetsDiv = document.getElementById('cf-presets');
            const visitorCountEl = document.getElementById('visitor-count');


            // --- STATE MANAGEMENT ---
            let stateHistory = [];
            let historyIndex = -1;
            let userDefaultState = {};
            let systemDefaultState = {};
            let customBaselineSystemCost = 0;
            let customBaselineConsumerCost = 0; // NEW
            let customBaselineTotalAnnualCO2 = 0;
            let enabledTechnologies = {};
            let defaultCapacityMix = {};
            let defaultGenerationMix = {};
            let currentSystemDefaultProfileName = 'spring-typical';
            
            let isDemandEditMode = false;
            let currentDemand = [...SEASONAL_DEMAND_PROFILES['spring-high']];
            let originalDemandBeforeEdit = [];
            let currentDemandProfileName = 'Spring Typical';

            let isCFEditMode = false;
            let currentSolarCFProfile = [];
            let currentWindCFProfile = [];
            let currentOffshoreWindCFProfile = [];
            let currentHydroCF = SEASONAL_HYDRO_CF.spring; // Initialize with spring
            let originalSolarCFBeforeEdit = [];
            let originalWindCFBeforeEdit = [];
            let originalOffshoreWindCFBeforeEdit = [];
            let currentCFProfileName = 'Spring';


            // --- CHARTING SETUP ---
            const generationCtx = document.getElementById('generationMixChart').getContext('2d');
            const marginalPriceCtx = document.getElementById('marginalPriceChart').getContext('2d'); // NEW
            const co2Ctx = document.getElementById('co2EmissionsChart').getContext('2d');
            const capacityFactorCtx = document.getElementById('capacityFactorChart').getContext('2d');
            
            const COLORS = {
                naturalGas: 'rgba(107, 114, 128, 0.8)', hydro: 'rgba(59, 130, 246, 0.8)', 
                nuclear: 'rgba(239, 68, 68, 0.8)', solar: 'rgba(251, 191, 36, 1)', 
                wind: 'rgba(52, 211, 153, 0.8)', /* CHANGE: Lighter green for Onshore Wind */
                offshoreWind: 'rgba(12, 148, 103, 0.8)', 
                geothermal: 'rgba(120, 40, 40, 0.8)',
                biomass: 'rgba(101,
                rng: 'rgba(132, 204, 22, 0.8)', 67, 33, 0.8)',
                storage: 'rgba(168, 85, 247, 0.8)', demand: 'rgba(17, 24, 39, 1)',
                curtailment: 'rgba(253, 186, 116, 0.8)', coal: 'rgba(0, 0, 0, 0.8)',
                price: 'rgba(79, 70, 229, 1)' // NEW for price chart
            };

            // Helper function to create a patterned fill for "to Storage" generation
            function createPattern(baseColor, patternColor) {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = 10;
                canvas.height = 10;
                ctx.fillStyle = baseColor;
                ctx.fillRect(0, 0, 10, 10);
                ctx.strokeStyle = patternColor;
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(0, 10);
                ctx.lineTo(10, 0);
                ctx.moveTo(-1, 1);
                ctx.lineTo(1, -1);
                ctx.moveTo(9, 11);
                ctx.lineTo(11, 9);
                ctx.stroke();
                return ctx.createPattern(canvas, 'repeat');
            }

            const PATTERNS = {
                solarToStorage: createPattern(COLORS.solar, 'rgba(168, 85, 247, 0.7)'),
                windToStorage: createPattern(COLORS.wind, 'rgba(168, 85, 247, 0.7)'),
                offshoreWindToStorage: createPattern(COLORS.offshoreWind, 'rgba(168, 85, 247, 0.7)'),
                hydroToStorage: createPattern(COLORS.hydro, COLORS.storage),
                geothermalToStorage: createPattern(COLORS.geothermal, COLORS.storage),
                nuclearToStorage: createPattern(COLORS.nuclear, COLORS.storage),
                coalToStorage: createPattern(COLORS.coal, COLORS.storage),
                naturalGasToStorage: createPattern(COLORS.naturalGas, COLORS.storage),
                biomassToStorage: createPattern(COLORS.biomass, COLORS.storage),
            };
            
            const generationChartConfig = {
                type: 'bar',
                data: {
                    labels: HOURS,
                    datasets: [
                        { label: 'Nuclear', data: [], backgroundColor: COLORS.nuclear, stack: 'generators', dragData: false },
                        { label: 'Geothermal', data: [], backgroundColor: COLORS.geothermal, stack: 'generators', dragData: false },
                        { label: 'Biomass', data: [], backgroundColor: COLORS.biomass, stack: 'generators', dragData: false },
                        { label: 'RNG (Biogas)', data: [], backgroundColor: COLORS.rng, stack: 'generators', dragData: false },
                        { label: 'Hydro', data: [], backgroundColor: COLORS.hydro, stack: 'generators', dragData: false },
                        { label: 'Onshore Wind', data: [], backgroundColor: COLORS.wind, stack: 'generators', dragData: false },
                        { label: 'Offshore Wind', data: [], backgroundColor: COLORS.offshoreWind, stack: 'generators', dragData: false },
                        { label: 'Solar', data: [], backgroundColor: COLORS.solar, stack: 'generators', dragData: false },
                        { label: 'Natural Gas', data: [], backgroundColor: COLORS.naturalGas, stack: 'generators', dragData: false },
                        { label: 'Coal', data: [], backgroundColor: COLORS.coal, stack: 'generators', dragData: false },
                        { label: 'Storage', data: [], backgroundColor: COLORS.storage, stack: 'generators', dragData: false },
                        { label: 'Curtailment', data: [], backgroundColor: COLORS.curtailment, stack: 'generators', dragData: false },
                        { label: 'Solar to Storage', data: [], backgroundColor: PATTERNS.solarToStorage, stack: 'generators', dragData: false, hidden: false },
                        { label: 'Onshore Wind to Storage', data: [], backgroundColor: PATTERNS.windToStorage, stack: 'generators', dragData: false, hidden: false },
                        { label: 'Offshore Wind to Storage', data: [], backgroundColor: PATTERNS.offshoreWindToStorage, stack: 'generators', dragData: false, hidden: false },
                        { label: 'Demand', data: currentDemand, type: 'line', borderColor: COLORS.demand, borderWidth: 3, pointRadius: 0, fill: false, order: -1 }
                    ]
                },
                options: {
                    responsive: true, animation: { duration: 0 },
                    plugins: { 
                        tooltip: {
                            mode: 'index',
                            callbacks: {
                                title: function(context) {
                                    return context[0].label;
                                },
                                label: function(context) {
                                    return ''; // We build the full tooltip in the footer
                                },
                                footer: function(tooltipItems) {
                                    const totals = {};
                                    let stackTotal = 0;

                                    tooltipItems.forEach(function(tooltipItem) {
                                        let label = tooltipItem.dataset.label;
                                        const value = tooltipItem.raw;
                                        if (value === 0) return;

                                        // Consolidate "to Storage" tooltips
                                        if (label.includes('to Storage')) {
                                            const sourceTech = label.replace(' to Storage', '');
                                            label = `${sourceTech} (to Storage)`;
                                        }

                                        totals[label] = (totals[label] || 0) + value;
                                        
                                        if(tooltipItem.dataset.type !== 'line') {
                                           if (!label.includes('to Storage') && label !== 'Curtailment') {
                                                stackTotal += value;
                                            }
                                        }
                                    });

                                    const lines = [];
                                    const tooltipOrder = ['Coal', 'Natural Gas', 'Hydro', 'Geothermal', 'Biomass', 'RNG (Biogas)', 'Nuclear', 'Solar', 'Onshore Wind', 'Offshore Wind', 'Storage', 'Curtailment', 'Solar (to Storage)', 'Onshore Wind (to Storage)', 'Offshore Wind (to Storage)', 'Demand'];
                                    tooltipOrder.forEach(label => {
                                        if (totals[label] > 0.01) { 
                                            lines.push(`${label}: ${totals[label].toFixed(2)}`);
                                        }
                                    });
                                    
                                    if(stackTotal > 0) {
                                        lines.push('------------------');
                                        lines.push(`Total Gen to Grid: ${stackTotal.toFixed(2)}`);
                                    }
                                    return lines;
                                }
                            }
                        }, 
                        legend: { 
                            position: 'bottom',
                            labels: {
                                filter: function(legendItem) {
                                    return !legendItem.text.includes('to Storage') && legendItem.text !== 'Demand';
                                }
                            }
                        },
                        dragData: { enabled: false }
                    },
                    scales: {
                        x: { stacked: true, title: { display: true, text: 'Hour of Day' } },
                        y: { stacked: true, title: { display: true, text: 'Generation (GWh)' } }
                    }
                }
            };
            const marginalPriceChartConfig = { // NEW
                type: 'line',
                data: {
                    labels: HOURS,
                    datasets: [{
                        label: 'Marginal Price (with Storage)', data: [],
                        borderColor: COLORS.price, backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        fill: true, tension: 0.3, pointRadius: 0
                    }, {
                        label: 'Marginal Price (without Storage)', data: [],
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderDash: [5, 5],
                        fill: false, tension: 0.3, pointRadius: 0
                    }]
                },
                options: {
                    responsive: true, animation: { duration: 0 },
                    scales: {
                         x: { title: { display: true, text: 'Hour of Day' } },
                        y: { title: { display: true, text: 'Price ($/MWh)' } }
                    },
                    plugins: { 
                        legend: { display: true }
                    }
                }
            };
            const co2ChartConfig = {
                type: 'line',
                data: {
                    labels: HOURS,
                    datasets: [{
                        label: 'CO2 Emissions', data: [],
                        borderColor: 'rgba(239, 68, 68, 1)', backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true, tension: 0.3
                    }]
                },
                options: {
                    responsive: true, animation: { duration: 0 },
                    scales: {
                         x: { title: { display: true, text: 'Hour of Day' } },
                        y: { beginAtZero: true, title: { display: true, text: 'CO2 (Metric Tons)' } }
                    },
                    plugins: { 
                        legend: { display: false },
                        annotation: {
                            annotations: {
                                totalCO2: {
                                    type: 'label',
                                    content: 'Total Daily CO2: 0 tons',
                                    position: {
                                      x: 'center',
                                      y: 'top'
                                    },
                                    yAdjust: 10,
                                    backgroundColor: 'rgba(249, 250, 251, 0.85)',
                                    borderColor: 'rgba(209, 213, 219, 1)',
                                    borderWidth: 1,
                                    borderRadius: 6,
                                    color: '#1f2937',
                                    font: {
                                        weight: 'bold',
                                        size: 20
                                    },
                                    padding: 8,
                                }
                            }
                        }
                    }
                }
            };
            const capacityFactorChartConfig = {
                type: 'line',
                data: {
                    labels: HOURS,
                    datasets: [
                        { label: 'Solar', data: [], borderColor: COLORS.solar, borderWidth: 3, pointRadius: 0, fill: false, tension: 0.4, dragData: false },
                        { label: 'Onshore Wind', data: [], borderColor: COLORS.wind, borderWidth: 3, pointRadius: 0, fill: false, tension: 0.4, dragData: false },
                        { label: 'Offshore Wind', data: [], borderColor: COLORS.offshoreWind, borderWidth: 3, pointRadius: 0, fill: false, tension: 0.4, dragData: false }
                    ]
                },
                options: {
                    responsive: true, animation: { duration: 0 },
                    plugins: { 
                        legend: { position: 'bottom' },
                        dragData: {
                            round: 2,
                            showTooltip: true,
                            onDragEnd: (e, datasetIndex, index, value) => {
                                const chart = e.chart;
                                let updatedValue = value;
                                if (value < 0) updatedValue = 0;
                                if (value > 1) updatedValue = 1;
                                chart.data.datasets[datasetIndex].data[index] = updatedValue;
                                chart.update('none');
                            }
                        }
                    },
                    scales: {
                        x: { title: { display: true, text: 'Hour of Day' } },
                        y: { title: { display: true, text: 'Capacity Factor (%)' }, min: 0, max: 1, ticks: { callback: value => `${value * 100}%` } }
                    }
                }
            };

            const generationChart = new Chart(generationCtx, generationChartConfig);
            const marginalPriceChart = new Chart(marginalPriceCtx, marginalPriceChartConfig); // NEW
            const co2Chart = new Chart(co2Ctx, co2ChartConfig);
            const capacityFactorChart = new Chart(capacityFactorCtx, capacityFactorChartConfig);


            // --- COST CALCULATION ---
            function calculateTotalAnnualSystemCost(generation, capacity, currentIncentives, curtailedEnergy, baselineCapacity, baselineStorage, gasGenDetails) {
                let totalAnnualCost = 0;
                const d = COST_DATA.discount_rate;

                for (const tech in COST_DATA.capacity_factor) {
                    if (tech === 'naturalGas') continue; // Skip NG here, will be calculated separately

                    const techData = COST_DATA;
                    if (!techData.lifetime[tech]) continue;
                    const n = techData.lifetime[tech];
                    const crf = (d * Math.pow(1 + d, n)) / (Math.pow(1 + d, n) - 1);
                    
                    const baselineCapacityGW = baselineCapacity[tech] || 0;
                    const newCapacityGW = capacity[tech] || 0;
                    const totalCapacityKW = (baselineCapacityGW + newCapacityGW) * 1000000;

                    if (totalCapacityKW > 0) {
                        const annualized_capex = techData.capex[tech] * totalCapacityKW * crf;
                        const annual_fom = techData.fixed_om[tech] * totalCapacityKW;
                        
                        const annual_generation_mwh = (generation[tech] || []).reduce((a, b) => a + b, 0) * 1000 * 365;
                        const annual_vom = techData.variable_om[tech] * annual_generation_mwh;

                        let annual_ptc = 0;
                        if (currentIncentives[tech]) {
                            annual_ptc = currentIncentives[tech] * annual_generation_mwh;
                        }

                        totalAnnualCost += annualized_capex + annual_fom + annual_vom - annual_ptc;
                    }
                }
                
                // --- NEW: Natural Gas Cost Calculation ---
                const baselineNGCapacityGW = baselineCapacity.naturalGas || 0;
                const newNGCapacityGW = capacity.naturalGas || 0;
                const totalNGCapacityKW = (baselineNGCapacityGW + newNGCapacityGW) * 1000000;

                if (totalNGCapacityKW > 0) {
                    const n = COST_DATA.lifetime.naturalGas;
                    const crf = (d * Math.pow(1 + d, n)) / (Math.pow(1 + d, n) - 1);
                    const annualized_capex = COST_DATA.capex.naturalGas * totalNGCapacityKW * crf;
                    const annual_fom = COST_DATA.fixed_om.naturalGas * totalNGCapacityKW;
                    
                    // The VOM for gas is now calculated based on the hourly dispatch cost
                    const annual_vom_ng = (gasGenDetails.ccgt.cost + gasGenDetails.ct.cost) * 365;

                    totalAnnualCost += annualized_capex + annual_fom + annual_vom_ng;
                }


                for (const type of ['battery4hr', 'battery8hr', 'longduration']) {
                    if (!enabledTechnologies[type]) continue; // Skip disabled storage
                    const baseline_gwh = baselineStorage[type] || 0;
                    const new_gwh = capacity[type] || 0;
                    const total_gwh = baseline_gwh + new_gwh;

                    if (total_gwh > 0) {
                        if (!COST_DATA.lifetime[type]) continue;
                        const n = COST_DATA.lifetime[type];
                        const crf = (d * Math.pow(1 + d, n)) / (Math.pow(1 + d, n) - 1);
                        
                        let capex_per_kwh = COST_DATA.capex[type] - currentIncentives.storage;
                        const total_kwh = total_gwh * 1000000;
                        const duration = type === 'longduration' ? 24 : parseInt(type.match(/\d+/)[0]);
                        const total_kw = total_kwh / duration;

                        const annualized_capex = capex_per_kwh * total_kwh * crf;
                        const annual_fom = COST_DATA.fixed_om[type] * total_kw;
                        
                        const annual_discharge_mwh = generation.storage.reduce((a, b) => a + b, 0) * 1000 * 365;
                        const annual_vom = COST_DATA.variable_om[type] * annual_discharge_mwh;
                        
                        totalAnnualCost += annualized_capex + annual_fom + annual_vom;
                    }
                }
                
                if (capacity.dac > 0) {
                    const annualDacCapacityTons = capacity.dac * 24 * 365;
                    const n = COST_DATA.lifetime.dac;
                    const crf = (d * Math.pow(1 + d, n)) / (Math.pow(1 + d, n) - 1);

                    const annualizedDacCapex = COST_DATA.capex.dac * annualDacCapacityTons * crf;
                    const annualDacFom = COST_DATA.fixed_om.dac * annualDacCapacityTons;
                    const dacVariableCost = annualDacCapacityTons * COST_DATA.variable_om.dac;
                    const dacIncentiveValue = annualDacCapacityTons * currentIncentives.dac;

                    totalAnnualCost += (annualizedDacCapex + annualDacFom + dacVariableCost - dacIncentiveValue);
                }
                
                const totalAnnualCO2 = calculateEmissions(generation, 0).reduce((a, b) => a + b, 0) * 365;
                totalAnnualCost += totalAnnualCO2 * currentIncentives.carbonTax;

                const annualExportRevenue = curtailedEnergy.reduce((a, b) => a + b, 0) * 1000 * 365 * currentIncentives.exportPrice;
                totalAnnualCost -= annualExportRevenue;

                return totalAnnualCost;
            }
            
            // NEW: Function to calculate consumer cost based on marginal price
            function calculateAnnualConsumerCost(hourlyMarginalPrice, demand) {
                let totalCost = 0;
                for (let i = 0; i < 24; i++) {
                    totalCost += hourlyMarginalPrice[i] * demand[i] * 1000; // price is $/MWh, demand is GWh
                }
                return totalCost * 365;
            }


            // --- REWRITTEN DISPATCH LOGIC ---
            function getSimulationResult(inputs, solarProfile, windProfile, offshoreWindProfile, potentialGen, baselineStorageGWh = {}, hydroCF, countryName, storageOverrideDisabled = false) {
                const VRE_SOURCES = ['solar', 'wind', 'offshoreWind'];
                const INFLEXIBLE_SOURCES = ['nuclear', 'geothermal', 'biomass', 'rng'];
                
                let finalGeneration = {
                    coal: Array(24).fill(0), naturalGas: Array(24).fill(0),
                    hydro: Array(24).fill(0), nuclear: Array(24).fill(0),
                    geothermal: Array(24).fill(0), biomass: Array(24).fill(0), rng: Array(24).fill(0),
                    solar: Array(24).fill(0), wind: Array(24).fill(0), offshoreWind: Array(24).fill(0),
                    storage: Array(24).fill(0), curtailment: Array(24).fill(0),
                    solarToStorage: Array(24).fill(0), windToStorage: Array(24).fill(0), offshoreWindToStorage: Array(24).fill(0)
                };
                
                let curtailmentBySource = { solar: Array(24).fill(0), wind: Array(24).fill(0), offshoreWind: Array(24).fill(0) };

                let modifiedDemand = [...currentDemand];
                if (inputs.capacity.demandflex > 0) {
                    const originalPeak = Math.max(...currentDemand);
                    let totalAmountToShift = originalPeak * (inputs.capacity.demandflex / 100);
                    const shiftIncrement = 0.1;

                    while (totalAmountToShift > 0.01) {
                        const currentPeak = Math.max(...modifiedDemand);
                        const currentTrough = Math.min(...modifiedDemand);
                        const peakIndex = modifiedDemand.indexOf(currentPeak);
                        const troughIndex = modifiedDemand.indexOf(currentTrough);
                        if (peakIndex === troughIndex || currentPeak <= currentTrough) break;
                        const amountThisIteration = Math.min(shiftIncrement, totalAmountToShift);
                        modifiedDemand[peakIndex] -= amountThisIteration;
                        modifiedDemand[troughIndex] += amountThisIteration;
                        totalAmountToShift -= amountThisIteration;
                    }
                }

                let currentPotential = JSON.parse(JSON.stringify(potentialGen));
                for (let i = 0; i < 24; i++) {
                    currentPotential.solar[i] += inputs.capacity.solar * solarProfile[i];
                    currentPotential.wind[i] += inputs.capacity.wind * windProfile[i];
                    currentPotential.offshoreWind[i] += inputs.capacity.offshoreWind * offshoreWindProfile[i];
                    currentPotential.nuclear[i] += inputs.capacity.nuclear * COST_DATA.capacity_factor.nuclear;
                    currentPotential.geothermal[i] += inputs.capacity.geothermal * COST_DATA.capacity_factor.geothermal;
                    currentPotential.biomass[i] += inputs.capacity.biomass * COST_DATA.capacity_factor.biomass;
                    currentPotential.rng[i] += inputs.capacity.rng * COST_DATA.capacity_factor.rng;
                }
                const hydroCapacity = (currentCountryInstalledCapacity.hydro || 0) + (inputs.capacity.hydro || 0);
                const maxHourlyHydroOutput = countryName === 'California' ? hydroCapacity * 0.32 : hydroCapacity;

                let netLoad = Array(24).fill(0);
                for (let i = 0; i < 24; i++) {
                    let vreAndInflexibleGen = 0;
                    [...INFLEXIBLE_SOURCES, ...VRE_SOURCES].forEach(tech => {
                        const potential = currentPotential[tech][i];
                        finalGeneration[tech][i] = potential; 
                        vreAndInflexibleGen += potential;
                    });
                    netLoad[i] = modifiedDemand[i] - vreAndInflexibleGen;
                }
                
                if (!storageOverrideDisabled) {
                    const storageDispatch = dispatchStorageEconomically(netLoad, inputs, baselineStorageGWh, currentPotential);
                    finalGeneration.storage = storageDispatch.discharge;
                    
                    for (let i = 0; i < 24; i++) {
                        netLoad[i] += storageDispatch.charge[i];
                        netLoad[i] -= storageDispatch.discharge[i];
                        
                        // FIX 1: Subtract charged amount from VRE sources for correct visual accounting
                        if (storageDispatch.charge[i] > 0) {
                            let totalVrePotential = finalGeneration.solar[i] + finalGeneration.wind[i] + finalGeneration.offshoreWind[i];
                            if (totalVrePotential > 0) {
                                let solarCharge = (finalGeneration.solar[i] / totalVrePotential) * storageDispatch.charge[i];
                                let windCharge = (finalGeneration.wind[i] / totalVrePotential) * storageDispatch.charge[i];
                                let offshoreCharge = (finalGeneration.offshoreWind[i] / totalVrePotential) * storageDispatch.charge[i];
                                
                                finalGeneration.solarToStorage[i] = solarCharge;
                                finalGeneration.windToStorage[i] = windCharge;
                                finalGeneration.offshoreWindToStorage[i] = offshoreCharge;

                                finalGeneration.solar[i] -= solarCharge;
                                finalGeneration.wind[i] -= windCharge;
                                finalGeneration.offshoreWind[i] -= offshoreCharge;
                            }
                        }
                    }
                }
                
                for (let i = 0; i < 24; i++) {
                    if (netLoad[i] < 0) {
                        finalGeneration.curtailment[i] = -netLoad[i];
                        let availableForCurtailment = 0;
                        [...INFLEXIBLE_SOURCES, ...VRE_SOURCES].forEach(tech => {
                            availableForCurtailment += finalGeneration[tech][i];
                        });
                         if (availableForCurtailment > 0) {
                            [...INFLEXIBLE_SOURCES, ...VRE_SOURCES].forEach(tech => {
                                const proportion = finalGeneration[tech][i] / availableForCurtailment;
                                const reduction = finalGeneration.curtailment[i] * proportion;
                                if (curtailmentBySource.hasOwnProperty(tech)) {
                                    curtailmentBySource[tech][i] += reduction;
                                }                                
                                finalGeneration[tech][i] -= reduction;
                            });
                        }
                        netLoad[i] = 0;
                    }
                }
                
                
                const totalDailyHydroEnergy = hydroCapacity * hydroCF * 24;
                const baseloadHydroEnergy = totalDailyHydroEnergy * 0.40;
                let flexibleHydroEnergy = totalDailyHydroEnergy * 0.60;

                const deficitHours = netLoad.map((load, hour) => load > 0.01 ? hour : -1).filter(hour => hour !== -1);
                if (deficitHours.length > 0) {
                    const hourlyBaseloadHydro = baseloadHydroEnergy / deficitHours.length;
                    deficitHours.forEach(i => {
                        const hydroToDispatch = Math.min(hourlyBaseloadHydro, netLoad[i], maxHourlyHydroOutput - finalGeneration.hydro[i]);
                        finalGeneration.hydro[i] += hydroToDispatch;
                        netLoad[i] -= hydroToDispatch;
                    });
                }

                while (flexibleHydroEnergy > 0.01) {
                    let maxPriority = -Infinity, maxPriorityHour = -1;
                    for (let i = 0; i < 24; i++) {
                        if (netLoad[i] > 0.01 && netLoad[i] > maxPriority) {
                            maxPriority = netLoad[i];
                            maxPriorityHour = i;
                        }
                    }
                    if (maxPriorityHour === -1) break;

                    const hydroToDispatch = Math.min(0.1, flexibleHydroEnergy, netLoad[maxPriorityHour], maxHourlyHydroOutput - finalGeneration.hydro[maxPriorityHour]);
                    if (hydroToDispatch < 0.001) break;

                    finalGeneration.hydro[maxPriorityHour] += hydroToDispatch;
                    netLoad[maxPriorityHour] -= hydroToDispatch;
                    flexibleHydroEnergy -= hydroToDispatch;
                }
                
                const { gasGenDetails, hourlyMarginalPrice, thermalGeneration } = calculateThermalDispatchAndPrice(netLoad, inputs, currentPotential);
                finalGeneration.naturalGas = thermalGeneration.naturalGas;
                finalGeneration.coal = thermalGeneration.coal;
                
                // FIX 2: Override price with export price during curtailment hours
                for (let i = 0; i < 24; i++) {
                    if (finalGeneration.curtailment[i] > 0.01) {
                        hourlyMarginalPrice[i] = inputs.incentives.exportPrice;
                    }
                }

                const newEmissions = calculateEmissions(finalGeneration, inputs.capacity.dac);
                const newSystemCost = calculateTotalAnnualSystemCost(finalGeneration, inputs.capacity, inputs.incentives, finalGeneration.curtailment, currentCountryInstalledCapacity, baselineStorageGWh, gasGenDetails);
                
                return {
                    generation: finalGeneration,
                    emissions: newEmissions,
                    systemCost: newSystemCost,
                    demand: modifiedDemand,
                    curtailmentBySource: curtailmentBySource,
                    hourlyMarginalPrice: hourlyMarginalPrice 
                };
            }
            
            function calculateThermalDispatchAndPrice(netLoad, inputs, currentPotential) {
                const gasGenDetails = { ccgt: { generation: 0, cost: 0 }, ct: { generation: 0, cost: 0 } };
                const hourlyMarginalPrice = Array(24).fill(0);
                const thermalGeneration = { naturalGas: Array(24).fill(0), coal: Array(24).fill(0) };
                
                const totalNGCapacity = (currentCountryInstalledCapacity.naturalGas || 0) + (inputs.capacity.naturalGas || 0);
                const ccgtCapacity = totalNGCapacity * 0.7;
                const ctCapacity = totalNGCapacity * 0.3;

                for (let i = 0; i < 24; i++) {
                    let remainingLoad = netLoad[i];
                    let hourlyPrice = 0;

                    if (remainingLoad <= 0.01) {
                        hourlyMarginalPrice[i] = 0;
                        continue;
                    }

                    if (ccgtCapacity > 0) {
                        const ccgtToDispatch = Math.min(remainingLoad, ccgtCapacity);
                        if (ccgtToDispatch > 0) {
                            thermalGeneration.naturalGas[i] += ccgtToDispatch;
                            remainingLoad -= ccgtToDispatch;
                            const costStart = COST_DATA.variable_om.naturalGasCCGT.start;
                            const costEnd = COST_DATA.variable_om.naturalGasCCGT.end;
                            const priceAtDispatch = costStart + (costEnd - costStart) * (ccgtToDispatch / ccgtCapacity);
                            hourlyPrice = Math.max(hourlyPrice, priceAtDispatch);
                            const avgCost = (costStart + priceAtDispatch) / 2;
                            gasGenDetails.ccgt.cost += ccgtToDispatch * 1000 * avgCost;
                        }
                    }

                    if (remainingLoad > 0.01 && ctCapacity > 0) {
                        const ctToDispatch = Math.min(remainingLoad, ctCapacity);
                        if (ctToDispatch > 0) {
                            thermalGeneration.naturalGas[i] += ctToDispatch;
                            remainingLoad -= ctToDispatch;
                            const costStart = COST_DATA.variable_om.naturalGasCT.start;
                            const costEnd = COST_DATA.variable_om.naturalGasCT.end;
                            const priceAtDispatch = costStart + (costEnd - costStart) * (ctToDispatch / ctCapacity);
                            hourlyPrice = Math.max(hourlyPrice, priceAtDispatch);
                            const avgCost = (costStart + priceAtDispatch) / 2;
                            gasGenDetails.ct.cost += ctToDispatch * 1000 * avgCost;
                        }
                    }
                    
                    if (remainingLoad > 0.01 && currentPotential.coal[i] > 0) {
                        const coalToDispatch = Math.min(remainingLoad, currentPotential.coal[i]);
                        thermalGeneration.coal[i] += coalToDispatch;
                        remainingLoad -= coalToDispatch;
                        hourlyPrice = Math.max(hourlyPrice, COST_DATA.variable_om.coal);
                    }
                    hourlyMarginalPrice[i] = hourlyPrice;
                }
                return { gasGenDetails, hourlyMarginalPrice, thermalGeneration };
            }

            function dispatchStorageEconomically(initialNetLoad, inputs, baselineStorageGWh, currentPotential) {
                const storageTypes = ['battery4hr', 'battery8hr', 'longduration'];
                const storageCapacityGWh = {};
                const storagePowerGW = {};
                let totalStorageEnergyGWh = 0;

                storageTypes.forEach(type => {
                    if (enabledTechnologies[type]) {
                        const capacity = (baselineStorageGWh[type] || 0) + inputs.capacity[type];
                        storageCapacityGWh[type] = capacity;
                        totalStorageEnergyGWh += capacity;
                        const duration = type === 'longduration' ? 24 : parseInt(type.match(/\d+/)[0]);
                        storagePowerGW[type] = capacity / duration;
                    } else {
                        storageCapacityGWh[type] = 0;
                        storagePowerGW[type] = 0;
                    }
                });

                if (totalStorageEnergyGWh === 0) {
                    return { charge: Array(24).fill(0), discharge: Array(24).fill(0) };
                }

                let netLoad = [...initialNetLoad];
                let hourlyCharge = Array(24).fill(0);
                let hourlyDischarge = Array(24).fill(0);
                let totalChargedGWh = 0;
                const storageEfficiency = 0.85;
                const DISPATCH_INCREMENT = 0.1; // GWh
                const PROFIT_THRESHOLD = 20; // $20/MWh

                while (true) {
                    const { hourlyMarginalPrice } = calculateThermalDispatchAndPrice(netLoad, inputs, currentPotential);
                    
                    let maxPrice = -Infinity, minPrice = Infinity;
                    let maxPriceHour = -1, minPriceHour = -1;

                    for (let i = 0; i < 24; i++) {
                        if (hourlyMarginalPrice[i] > maxPrice) {
                            maxPrice = hourlyMarginalPrice[i];
                            maxPriceHour = i;
                        }
                        if (hourlyMarginalPrice[i] < minPrice) {
                            minPrice = hourlyMarginalPrice[i];
                            minPriceHour = i;
                        }
                    }

                    if ((maxPrice * storageEfficiency) - minPrice <= PROFIT_THRESHOLD || maxPriceHour === -1 || minPriceHour === -1) {
                        break;
                    }

                    let availableChargePower = 0;
                    let availableDischargePower = 0;
                    storageTypes.forEach(type => {
                        availableChargePower += storagePowerGW[type];
                        availableDischargePower += storagePowerGW[type];
                    });

                    const chargeHeadroom = availableChargePower - hourlyCharge[minPriceHour];
                    const dischargeHeadroom = availableDischargePower - hourlyDischarge[maxPriceHour];
                    const energyHeadroom = totalStorageEnergyGWh - totalChargedGWh;

                    const dispatchAmount = Math.min(DISPATCH_INCREMENT, chargeHeadroom, dischargeHeadroom, energyHeadroom);

                    if (dispatchAmount < 0.01) {
                        break; 
                    }

                    const chargeAmount = dispatchAmount / storageEfficiency;
                    hourlyCharge[minPriceHour] += chargeAmount;
                    hourlyDischarge[maxPriceHour] += dispatchAmount;
                    totalChargedGWh += chargeAmount;
                    
                    netLoad[minPriceHour] += chargeAmount;
                    netLoad[maxPriceHour] -= dispatchAmount;
                }

                return { charge: hourlyCharge, discharge: hourlyDischarge };
            }


            function runSimulation() {
                const currentValues = {};
                for (const key in sliders) {
                    currentValues[key] = parseFloat(sliders[key].value);
                }
                
                const selectedCountry = countrySelect.value;
                const baseSolarProfile = (countryProfiles[selectedCountry] || countryProfiles.default).solar;
                const baseWindProfile = (countryProfiles[selectedCountry] || countryProfiles.default).wind;
                const baseOffshoreWindProfile = (countryProfiles[selectedCountry] || countryProfiles.default).offshoreWind;
                
                const baseSeason = currentDemandProfileName.split(' ')[0].toLowerCase();
                const seasonalMultipliers = SEASONAL_MULTIPLIERS[baseSeason] || { solar: 1.0, wind: 1.0, offshoreWind: 1.0 };
                const seasonalSolarProfile = currentSolarCFProfile.length > 0 ? currentSolarCFProfile : baseSolarProfile.map(cf => Math.min(1, cf * seasonalMultipliers.solar));
                const seasonalWindProfile = currentWindCFProfile.length > 0 ? currentWindCFProfile : baseWindProfile.map(cf => Math.min(1, cf * seasonalMultipliers.wind));
                const seasonalOffshoreWindProfile = currentOffshoreWindCFProfile.length > 0 ? currentOffshoreWindCFProfile : baseOffshoreWindProfile.map(cf => Math.min(1, cf * seasonalMultipliers.offshoreWind));


                let activePotentialGeneration = JSON.parse(JSON.stringify(BASELINE_POTENTIAL_GENERATION));
                for (const tech in enabledTechnologies) {
                    if (!enabledTechnologies[tech]) {
                        activePotentialGeneration[tech] = Array(24).fill(0);
                    }
                }
                
                const inputsForSim = {
                    capacity: {
                        solar: currentValues.solar, wind: currentValues.wind, offshoreWind: currentValues.offshoreWind,
                        geothermal: currentValues.geothermal, nuclear: currentValues.nuclear,
                        biomass: currentValues.biomass, rng: currentValues.rng,
                        battery4hr: currentValues.battery4hr, battery8hr: currentValues.battery8hr,
                        longduration: currentValues.longduration, dac: currentValues.dac,
                        demandflex: currentValues.demandflex,
                    },
                    incentives: {
                        solar: currentValues.solarIncentive, wind: currentValues.windIncentive, offshoreWind: currentValues.offshoreWindIncentive,
                        geothermal: currentValues.geothermalIncentive, nuclear: currentValues.nuclearIncentive,
                        biomass: currentValues.biomassIncentive, rng: currentValues.rngIncentive,
                        storage: currentValues.storageIncentive, dac: currentValues.dacIncentive,
                        carbonTax: currentValues.carbonTax,
                        exportPrice: currentValues.exportPrice,
                    }
                };

                const result = getSimulationResult(
                    inputsForSim,
                    seasonalSolarProfile, seasonalWindProfile, seasonalOffshoreWindProfile,
                    activePotentialGeneration, currentBaselineStorage, currentHydroCF, selectedCountry
                );

                const resultWithoutStorage = getSimulationResult(
                    inputsForSim,
                    seasonalSolarProfile, seasonalWindProfile, seasonalOffshoreWindProfile,
                    activePotentialGeneration, currentBaselineStorage, currentHydroCF, selectedCountry,
                    true // storageOverrideDisabled = true
                );

                const totalDailyCO2 = result.emissions.reduce((a, b) => a + b, 0);
                
                const newConsumerCost = calculateAnnualConsumerCost(result.hourlyMarginalPrice, result.demand);
                const totalAnnualDemandMWh = result.demand.reduce((a,b) => a+b, 0) * 1000 * 365;
                const newAvgMarginalPrice = totalAnnualDemandMWh > 0 ? newConsumerCost / totalAnnualDemandMWh : 0;

                const baselineTotalAnnualDemandMWh = currentDemand.reduce((a,b) => a+b, 0) * 1000 * 365;
                const baselineAvgMarginalPrice = baselineTotalAnnualDemandMWh > 0 ? customBaselineConsumerCost / baselineTotalAnnualDemandMWh : 0;
                
                const billPercentageChange = baselineAvgMarginalPrice > 0 ? ((newAvgMarginalPrice - baselineAvgMarginalPrice) / baselineAvgMarginalPrice) * 100 : 0;

                const newTotalAnnualCO2 = result.emissions.reduce((a, b) => a + b, 0) * 365;
                const co2Avoided = customBaselineTotalAnnualCO2 - newTotalAnnualCO2;
                const costDifference = result.systemCost - customBaselineSystemCost;
                const systemCostPercentageChange = customBaselineSystemCost > 0 ? (costDifference / customBaselineSystemCost) * 100 : 0;


                let abatementCost = 0;
                if (co2Avoided > 0) {
                    abatementCost = costDifference / co2Avoided;
                }

                updateCharts(result.generation, result.emissions, result.demand, totalDailyCO2, seasonalSolarProfile, seasonalWindProfile, seasonalOffshoreWindProfile, result.hourlyMarginalPrice, resultWithoutStorage.hourlyMarginalPrice);
                updateGridMixSlider(currentCountryInstalledCapacity, defaultCapacityMix);
                updateGenerationMixSlider(result.generation, defaultGenerationMix, result.curtailmentBySource);
                
                billImpactEl.textContent = `${billPercentageChange > 0 ? '+' : ''}${billPercentageChange.toFixed(0)}%`;
                systemCostImpactEl.textContent = `${systemCostPercentageChange > 0 ? '+' : ''}${systemCostPercentageChange.toFixed(0)}%`;

                // Update colors based on positive/negative change
                [billImpactEl, systemCostImpactEl].forEach((el, index) => {
                    const change = index === 0 ? billPercentageChange : systemCostPercentageChange;
                    if(change > 0) {
                        el.className = 'text-5xl font-bold text-red-600 mt-2';
                    } else if (change < 0) {
                        el.className = 'text-5xl font-bold text-green-600 mt-2';
                    } else {
                        el.className = 'text-5xl font-bold text-blue-600 mt-2';
                    }
                });


                const baselineDailyCO2 = customBaselineTotalAnnualCO2 / 365;
                const dailyCO2Avoided = baselineDailyCO2 - totalDailyCO2;

                if (Math.abs(dailyCO2Avoided) < 0.01) {
                    co2AvoidedEl.textContent = `CO2 avoided: 0 tons (0%)`;
                    co2AvoidedEl.className = 'text-md font-medium text-gray-700';
                } else {
                    const co2AvoidedPercent = baselineDailyCO2 > 0 ? (dailyCO2Avoided / baselineDailyCO2) * 100 : 0;
                    let text = `CO2 avoided: ${dailyCO2Avoided.toLocaleString('en-US', {maximumFractionDigits: 0})} tons (${co2AvoidedPercent.toFixed(0)}%)`;
                    if (co2Avoided > 0) {
                        text += ` at $${abatementCost.toFixed(0)}/ton`;
                    }
                    co2AvoidedEl.textContent = text;
                    co2AvoidedEl.className = dailyCO2Avoided > 0 ? 'text-md font-medium text-green-600' : 'text-md font-medium text-red-600';
                }
            }
            
            function calculateEmissions(generation, dacRate) {
                const co2 = [];
                for (let i = 0; i < 24; i++) {
                    let hourlyEmission = 0;
                    hourlyEmission += (generation.naturalGas[i] || 0) * EMISSION_FACTORS.naturalGas;
                    hourlyEmission += (generation.coal[i] || 0) * EMISSION_FACTORS.coal;
                    hourlyEmission += (generation.biomass[i] || 0) * EMISSION_FACTORS.biomass; // Added biomass
                    hourlyEmission -= dacRate;
                    co2.push(Math.max(0, hourlyEmission));
                }
                return co2;
            }

            function updateCharts(generation, emissions, demand, totalCO2, solarProfile, windProfile, offshoreWindProfile, hourlyMarginalPrice, priceWithoutStorage) {
                const chartData = generationChart.data.datasets;
                
                const techMap = {
                    nuclear: 0, geothermal: 1, biomass: 2, rng: 3, hydro: 3: 4, 
                    wind: 5, offshoreWind: 6, solar: 7, 
                    naturalGas: 8, coal: 9, storage: 10, curtailment: 11,
                    solarToStorage: 12, windToStorage: 13, offshoreWindToStorage: 14
                };

                for (const tech in techMap) {
                    if (generation[tech]) {
                        chartData[techMap[tech]].data = generation[tech];
                    }
                }
                chartData[15].data = demand;

                generationChart.update('none');
                
                // NEW: Update marginal price chart
                marginalPriceChart.data.datasets[0].data = hourlyMarginalPrice;
                marginalPriceChart.data.datasets[1].data = priceWithoutStorage;
                marginalPriceChart.update('none');

                co2Chart.data.datasets[0].data = emissions;
                co2Chart.options.plugins.annotation.annotations.totalCO2.content = `Total Daily CO2: ${totalCO2.toLocaleString(undefined, {maximumFractionDigits: 0})} tons`;
                co2Chart.update('none');

                capacityFactorChart.data.datasets[0].data = solarProfile;
                capacityFactorChart.data.datasets[1].data = windProfile;
                capacityFactorChart.data.datasets[2].data = offshoreWindProfile;
                capacityFactorChart.update('none');
            }

            function updateGridMixSlider(installedCapacity, defaultMix) {
                const capacities = {};
                let totalCapacity = 0;

                for (const tech in COST_DATA.capacity_factor) {
                    const baselineCapacity = installedCapacity[tech] || 0;
                    let newCapacity = 0;
                    if (sliders[tech]) {
                        newCapacity = parseFloat(sliders[tech].value);
                    }
                    capacities[tech] = baselineCapacity + newCapacity;
                    totalCapacity += capacities[tech];
                }

                if (totalCapacity > 0) {
                    for (const tech in capacities) {
                        if (COST_DATA.capacity_factor[tech]) { // Only for generators
                            const percentage = (capacities[tech] / totalCapacity) * 100;
                            const fillEl = document.getElementById(`mix-fill-${tech}`);
                            const valueEl = document.getElementById(`mix-value-${tech}`);
                            const outlineEl = document.getElementById(`mix-default-outline-${tech}`);
                            
                            if (fillEl && valueEl) {
                                fillEl.style.width = `${percentage}%`;
                                valueEl.textContent = `${percentage.toFixed(1)}%`;
                            }
                            if (outlineEl && defaultMix[tech] !== undefined) {
                                outlineEl.style.width = `${defaultMix[tech]}%`;
                            }
                        }
                    }
                }

                // Update storage display
                ['battery4hr', 'battery8hr', 'longduration'].forEach(type => {
                    const baselineGWh = currentBaselineStorage[type] || 0;
                    const newGWh = parseFloat(sliders[type].value);
                    const totalGWh = baselineGWh + newGWh;
                    const duration = type === 'longduration' ? 24 : parseInt(type.match(/\d+/)[0]);
                    const totalGW = totalGWh / duration;
                    const displayEl = document.getElementById(`storage-capacity-${type}`);
                    if (displayEl) {
                        displayEl.textContent = `${totalGW.toFixed(2)} GW / ${totalGWh.toFixed(2)} GWh`;
                    }
                });
            }
            
            function createGridMixSliders() {
                const techOrder = ['coal', 'naturalGas', 'solar', 'hydro', 'wind', 'offshoreWind', 'nuclear', 'geothermal', 'biomass'];
                techOrder.forEach(tech => {
                    let name = tech.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
                    if (tech === 'wind') name = 'Onshore Wind';
                    if (tech === 'offshoreWind') name = 'Offshore Wind';

                    const color = COLORS[tech] || '#ccc';

                    const wrapper = document.createElement('div');
                    wrapper.className = 'grid grid-cols-6 gap-2 items-center mix-slider-row';
                    wrapper.dataset.tech = tech;

                    const checkboxContainer = document.createElement('div');
                    checkboxContainer.className = "flex items-center justify-center";
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `toggle-${tech}`;
                    checkbox.checked = true;
                    checkbox.className = "form-checkbox h-5 w-5 text-blue-600 rounded";
                    checkbox.addEventListener('change', () => {
                        enabledTechnologies[tech] = checkbox.checked;
                        runSimulation();
                        saveState();
                    });
                    checkboxContainer.appendChild(checkbox);
                    wrapper.appendChild(checkboxContainer);

                    const label = document.createElement('label');
                    label.textContent = name;
                    label.className = 'col-span-1 text-sm font-medium text-gray-700';
                    wrapper.appendChild(label);

                    const sliderContainer = document.createElement('div');
                    sliderContainer.className = 'col-span-3';
                    const track = document.createElement('div');
                    track.className = 'mix-slider-track';
                    const fill = document.createElement('div');
                    fill.id = `mix-fill-${tech}`;
                    fill.className = 'mix-slider-fill';
                    fill.style.backgroundColor = color;
                    const outline = document.createElement('div');
                    outline.id = `mix-default-outline-${tech}`;
                    outline.className = 'mix-slider-default-outline';
                    track.appendChild(fill);
                    track.appendChild(outline);
                    sliderContainer.appendChild(track);
                    wrapper.appendChild(sliderContainer);

                    const value = document.createElement('span');
                    value.id = `mix-value-${tech}`;
                    value.className = 'col-span-1 text-sm font-semibold text-right';
                    value.textContent = '0.0%';
                    wrapper.appendChild(value);

                    gridMixSlidersContainer.appendChild(wrapper);
                });

                // Create storage section
                const storageHeader = document.createElement('h3');
                storageHeader.className = 'text-lg font-lora font-semibold mt-6 mb-2 text-gray-800';
                storageHeader.textContent = 'Installed Storage Capacity';
                storageCapacityDisplayContainer.appendChild(storageHeader);

                const storageTypes = [
                    { id: 'battery4hr', name: '4-hr Battery' },
                    { id: 'battery8hr', name: '8-hr Battery' },
                    { id: 'longduration', name: '24-hr Storage' }
                ];

                storageTypes.forEach(type => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'grid grid-cols-6 gap-2 items-center';
                    
                    const checkboxContainer = document.createElement('div');
                    checkboxContainer.className = "flex items-center justify-center";
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `toggle-${type.id}`;
                    checkbox.checked = true;
                    checkbox.className = "form-checkbox h-5 w-5 text-blue-600 rounded";
                    checkbox.addEventListener('change', () => {
                        enabledTechnologies[type.id] = checkbox.checked;
                        runSimulation();
                        saveState();
                    });
                    checkboxContainer.appendChild(checkbox);
                    wrapper.appendChild(checkboxContainer);

                    const label = document.createElement('label');
                    label.textContent = type.name;
                    label.className = 'col-span-2 text-sm font-medium text-gray-700';
                    wrapper.appendChild(label);

                    const value = document.createElement('span');
                    value.id = `storage-capacity-${type.id}`;
                    value.className = 'col-span-3 text-sm font-semibold text-right';
                    value.textContent = '0.00 GW / 0.00 GWh';
                    wrapper.appendChild(value);

                    storageCapacityDisplayContainer.appendChild(wrapper);
                });
            }

            // --- GENERATION MIX SLIDER ---
            function updateGenerationMixSlider(generation, defaultMix, curtailmentBySource) {
                dailyGenerationTotalsGWh = {}; // Clear previous totals
                let totalGeneration = 0;

                const gridTechs = ['coal', 'naturalGas', 'hydro', 'geothermal', 'biomass', 'nuclear', 'solar', 'wind', 'offshoreWind', 'storage'];
                gridTechs.forEach(tech => {
                    const techTotal = (generation[tech] || []).reduce((a, b) => a + b, 0);
                    dailyGenerationTotalsGWh[tech] = techTotal;
                    totalGeneration += techTotal;
                });

                if (totalGeneration > 0) {
                    gridTechs.forEach(tech => {
                        const percentage = (dailyGenerationTotalsGWh[tech] / totalGeneration) * 100;
                        const fillEl = document.getElementById(`gen-mix-fill-${tech}`);
                        const valueEl = document.getElementById(`gen-mix-value-${tech}`);
                        const outlineEl = document.getElementById(`gen-mix-default-outline-${tech}`);

                        if (fillEl && valueEl) {
                            fillEl.style.width = `${percentage}%`;
                            valueEl.textContent = `${percentage.toFixed(1)}%`;
                        }
                        if (outlineEl && defaultMix[tech] !== undefined) {
                            outlineEl.style.width = `${defaultMix[tech]}%`;
                        }
                    });
                } else { 
                     gridTechs.forEach(tech => {
                        const fillEl = document.getElementById(`gen-mix-fill-${tech}`);
                        const valueEl = document.getElementById(`gen-mix-value-${tech}`);
                        if(fillEl && valueEl) {
                            fillEl.style.width = '0%';
                            valueEl.textContent = '0.0%';
                        }
                    });
                }

                const curtailmentTrack = document.getElementById('gen-mix-track-curtailment');
                const curtailmentValue = document.getElementById('gen-mix-value-curtailment');
                curtailmentTrack.innerHTML = ''; 

                let totalCurtailed = (generation.curtailment || []).reduce((a, b) => a + b, 0);
                dailyGenerationTotalsGWh['curtailment'] = totalCurtailed;
                let totalPotentialGeneration = totalGeneration + totalCurtailed + (generation.solarToStorage || []).reduce((a,b)=>a+b,0) + (generation.windToStorage || []).reduce((a,b)=>a+b,0) + (generation.offshoreWindToStorage || []).reduce((a,b)=>a+b,0);
                
                if (totalPotentialGeneration > 0) {
                    const overallCurtailmentPercent = (totalCurtailed / totalPotentialGeneration) * 100;
                    curtailmentValue.textContent = `${overallCurtailmentPercent.toFixed(1)}%`;

                    if (totalCurtailed > 0) {
                        const solarCurtail = (curtailmentBySource.solar || []).reduce((a,b)=>a+b,0) || 0;
                        const windCurtail = (curtailmentBySource.wind || []).reduce((a,b)=>a+b,0) || 0;
                        const offshoreWindCurtail = (curtailmentBySource.offshoreWind || []).reduce((a,b)=>a+b,0) || 0;

                        const techWithCurtailment = [{tech: 'solar', val: solarCurtail}, {tech: 'wind', val: windCurtail}, {tech: 'offshoreWind', val: offshoreWindCurtail}];

                        techWithCurtailment.forEach(item => {
                             if (item.val > 0) {
                                const contributionPercent = (item.val / totalCurtailed);
                                const segmentWidth = 100 * contributionPercent; 

                                const segment = document.createElement('div');
                                segment.className = 'h-full';
                                segment.style.backgroundColor = COLORS[item.tech];
                                segment.style.width = `${segmentWidth}%`;
                                segment.style.float = 'left';
                                curtailmentTrack.appendChild(segment);
                            }
                        });
                        curtailmentTrack.parentElement.style.width = `${overallCurtailmentPercent}%`;
                    } else {
                        curtailmentTrack.parentElement.style.width = `0%`;
                    }
                } else {
                    curtailmentValue.textContent = '0.0%';
                    curtailmentTrack.parentElement.style.width = `0%`;
                }
            }

            function createGenerationMixSliders() {
                const techOrder = ['coal', 'naturalGas', 'solar', 'hydro', 'wind', 'offshoreWind', 'nuclear', 'geothermal', 'biomass', 'storage'];
                techOrder.forEach(tech => {
                    let name = tech.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
                    if (tech === 'wind') name = 'Onshore Wind';
                    if (tech === 'offshoreWind') name = 'Offshore Wind';
                    const color = COLORS[tech] || '#ccc';

                    const wrapper = document.createElement('div');
                    wrapper.className = 'grid grid-cols-5 gap-2 items-center mix-slider-row';
                    wrapper.dataset.tech = tech;

                    const label = document.createElement('label');
                    label.textContent = name;
                    label.className = 'col-span-1 text-sm font-medium text-gray-700';
                    wrapper.appendChild(label);

                    const sliderContainer = document.createElement('div');
                    sliderContainer.className = 'col-span-3';
                    const track = document.createElement('div');
                    track.className = 'mix-slider-track';
                    const fill = document.createElement('div');
                    fill.id = `gen-mix-fill-${tech}`;
                    fill.className = 'mix-slider-fill';
                    fill.style.backgroundColor = color;
                    const outline = document.createElement('div');
                    outline.id = `gen-mix-default-outline-${tech}`;
                    outline.className = 'mix-slider-default-outline';
                    track.appendChild(fill);
                    track.appendChild(outline);
                    sliderContainer.appendChild(track);
                    wrapper.appendChild(sliderContainer);

                    const value = document.createElement('span');
                    value.id = `gen-mix-value-${tech}`;
                    value.className = 'col-span-1 text-sm font-semibold text-right';
                    value.textContent = '0.0%';
                    wrapper.appendChild(value);

                    generationMixSlidersContainer.appendChild(wrapper);
                });

                const wrapper = document.createElement('div');
                wrapper.className = 'grid grid-cols-5 gap-2 items-center mix-slider-row';
                wrapper.dataset.tech = 'curtailment';
                const label = document.createElement('label');
                label.textContent = 'Curtailment';
                label.className = 'col-span-1 text-sm font-medium text-gray-700';
                wrapper.appendChild(label);
                const sliderContainer = document.createElement('div');
                sliderContainer.className = 'col-span-3';
                const outerTrack = document.createElement('div');
                outerTrack.className = 'mix-slider-track';
                const innerTrack = document.createElement('div');
                innerTrack.id = 'gen-mix-track-curtailment';
                innerTrack.className = 'h-full w-full';
                outerTrack.appendChild(innerTrack);
                sliderContainer.appendChild(outerTrack);
                wrapper.appendChild(sliderContainer);
                const value = document.createElement('span');
                value.id = `gen-mix-value-curtailment`;
                value.className = 'col-span-1 text-sm font-semibold text-right';
                value.textContent = '0.0%';
                wrapper.appendChild(value);
                generationMixSlidersContainer.appendChild(wrapper);
            }

            // --- DEMAND EDIT MODE ---
            function setDemandEditMode(enabled) {
                isDemandEditMode = enabled;
                const demandDatasetIndex = generationChart.data.datasets.findIndex(ds => ds.label === 'Demand');

                if (enabled) {
                    editDemandBtn.classList.add('hidden');
                    confirmDemandBtn.classList.remove('hidden');
                    revertDemandBtn.classList.remove('hidden');
                    demandPresetsDiv.classList.remove('hidden');

                    document.querySelectorAll('#demand-presets button').forEach(btn => {
                        btn.classList.remove('preset-active');
                        if (btn.id === `preset-demand-${currentDemandProfileName.toLowerCase().replace(' ', '-')}`) {
                            btn.classList.add('preset-active');
                        }
                    });

                    generationChart.data.datasets.forEach((dataset, index) => {
                        if (index !== demandDatasetIndex) {
                            dataset.hidden = true;
                        } else {
                            dataset.borderWidth = 4;
                            dataset.pointRadius = 6;
                            dataset.pointHoverRadius = 8;
                            dataset.pointBackgroundColor = 'rgba(17, 24, 39, 1)';
                            dataset.pointBorderColor = 'white';
                            dataset.pointBorderWidth = 2;
                        }
                    });

                    generationChart.options.plugins.dragData = {
                        round: 1,
                        showTooltip: true,
                        onDragEnd: function(e, datasetIndex, index, value) {
                            generationChart.update('none');
                        }
                    };
                    generationChart.options.plugins.dragData.enabled = true;
                    generationChart.options.scales.y.stacked = false;
                    generationChart.update();

                } else {
                    editDemandBtn.classList.remove('hidden');
                    confirmDemandBtn.classList.add('hidden');
                    revertDemandBtn.classList.add('hidden');
                    demandPresetsDiv.classList.add('hidden');

                    generationChart.data.datasets.forEach((dataset, index) => {
                        dataset.hidden = false;
                        if (index === demandDatasetIndex) {
                            dataset.borderWidth = 3;
                            dataset.pointRadius = 0;
                            dataset.pointHoverRadius = 0;
                        }
                    });

                    if (generationChart.options.plugins.dragData) {
                        generationChart.options.plugins.dragData.enabled = false;
                        generationChart.options.plugins.dragData.onDragEnd = null;
                    }
                    generationChart.options.scales.y.stacked = true;
                    generationChart.update();
                }
            }

            // --- CF EDIT MODE ---
            function setCFEditMode(enabled) {
                isCFEditMode = enabled;
                
                if (enabled) {
                    editCFBtn.classList.add('hidden');
                    confirmCFBtn.classList.remove('hidden');
                    revertCFBtn.classList.remove('hidden');
                    cfPresetsDiv.classList.remove('hidden');

                    document.querySelectorAll('#cf-presets button').forEach(btn => {
                        btn.classList.remove('preset-active');
                        if (btn.id === `preset-cf-${currentCFProfileName.toLowerCase()}`) {
                            btn.classList.add('preset-active');
                        }
                    });

                    capacityFactorChart.data.datasets.forEach(dataset => {
                        dataset.pointRadius = 6;
                        dataset.pointHoverRadius = 8;
                        dataset.pointBorderColor = 'white';
                        dataset.pointBorderWidth = 2;
                        dataset.dragData = true;
                    });

                } else {
                    editCFBtn.classList.remove('hidden');
                    confirmCFBtn.classList.add('hidden');
                    revertCFBtn.classList.add('hidden');
                    cfPresetsDiv.classList.add('hidden');
                    
                    capacityFactorChart.data.datasets.forEach(dataset => {
                        dataset.pointRadius = 0;
                        dataset.dragData = false;
                    });
                }
                capacityFactorChart.update();
            }
            
            // --- NEW: Function to set the baseline from the current state ---
            function setNewBaselineFromCurrentState() {
                const currentValues = {};
                for (const key in sliders) {
                    currentValues[key] = parseFloat(sliders[key].value);
                }
                
                let activePotentialGeneration = JSON.parse(JSON.stringify(BASELINE_POTENTIAL_GENERATION));
                for (const tech in enabledTechnologies) {
                    if (!enabledTechnologies[tech]) {
                        activePotentialGeneration[tech] = Array(24).fill(0);
                    }
                }

                const newBaselineResult = getSimulationResult(
                    {
                        capacity: {
                            solar: currentValues.solar, wind: currentValues.wind, offshoreWind: currentValues.offshoreWind,
                            geothermal: currentValues.geothermal, nuclear: currentValues.nuclear,
                            biomass: currentValues.biomass, rng: currentValues.rng,
                            battery4hr: currentValues.battery4hr, battery8hr: currentValues.battery8hr,
                            longduration: currentValues.longduration, dac: currentValues.dac,
                            demandflex: currentValues.demandflex,
                        },
                        incentives: {
                            solar: currentValues.solarIncentive, wind: currentValues.windIncentive, offshoreWind: currentValues.offshoreWindIncentive,
                            geothermal: currentValues.geothermalIncentive, nuclear: currentValues.nuclearIncentive,
                            biomass: currentValues.biomassIncentive, rng: currentValues.rngIncentive,
                            storage: currentValues.storageIncentive, dac: currentValues.dacIncentive,
                            carbonTax: currentValues.carbonTax,
                            exportPrice: currentValues.exportPrice,
                        }
                    },
                    currentSolarCFProfile,
                    currentWindCFProfile,
                    currentOffshoreWindCFProfile,
                    activePotentialGeneration,
                    currentBaselineStorage,
                    currentHydroCF,
                    countrySelect.value
                );
                
                customBaselineSystemCost = newBaselineResult.systemCost;
                customBaselineConsumerCost = calculateAnnualConsumerCost(newBaselineResult.hourlyMarginalPrice, newBaselineResult.demand);
                customBaselineTotalAnnualCO2 = newBaselineResult.emissions.reduce((a, b) => a + b, 0) * 365;
            }

            // --- EVENT LISTENERS ---
            function updateUndoRedoButtons() {
                undoButton.disabled = historyIndex <= 0;
                redoButton.disabled = historyIndex >= stateHistory.length - 1;
            }

            function saveState() {
                const currentState = {};
                for (const key in sliders) {
                    currentState[key] = sliders[key].value;
                }
                currentState.enabledTech = { ...enabledTechnologies };
                currentState.demandProfile = [...currentDemand];
                currentState.solarCFProfile = [...currentSolarCFProfile];
                currentState.windCFProfile = [...currentWindCFProfile];
                currentState.offshoreWindCFProfile = [...currentOffshoreWindCFProfile];
                currentState.demandProfileName = currentDemandProfileName;
                currentState.cfProfileName = currentCFProfileName;
                currentState.hydroCF = currentHydroCF;

                stateHistory = stateHistory.slice(0, historyIndex + 1);
                stateHistory.push(currentState);
                historyIndex++;
                updateUndoRedoButtons();
            }
            
            function syncInputs(sourceElement, targetElement) {
                targetElement.value = sourceElement.value;
            }

            function setupInputSyncing() {
                for (const key in sliders) {
                    const slider = sliders[key];
                    const input = inputs[key];

                    // --- MODIFICATION: Special handling for carbon tax ---
                    if (key === 'carbonTax') {
                         slider.addEventListener('input', () => {
                            syncInputs(slider, input);
                            setNewBaselineFromCurrentState(); // Recalculate baseline on change
                            runSimulation();
                        });
                        
                        input.addEventListener('input', () => {
                            let value = parseFloat(input.value);
                            const min = parseFloat(slider.min);
                            const max = parseFloat(slider.max);
                            if (isNaN(value)) value = min;
                            if (value > max) value = max;
                            if (value < min) value = min;
                            input.value = value;
                            syncInputs(input, slider);
                            setNewBaselineFromCurrentState(); // Recalculate baseline on change
                            runSimulation();
                        });
                    } else {
                        // Original behavior for all other sliders
                        slider.addEventListener('input', () => {
                            syncInputs(slider, input);
                            runSimulation();
                        });
                        
                        input.addEventListener('input', () => {
                            let value = parseFloat(input.value);
                            const min = parseFloat(slider.min);
                            const max = parseFloat(slider.max);
                            if (isNaN(value)) value = min;
                            if (value > max) value = max;
                            if (value < min) value = min;
                            input.value = value;
                            syncInputs(input, slider);
                            runSimulation();
                        });
                    }

                    slider.addEventListener('change', saveState);
                    input.addEventListener('change', saveState);
                }
            }

            function applySeason(profileName) {
                currentSystemDefaultProfileName = profileName;
                const nameParts = profileName.split('-');
                const baseSeason = nameParts[0];
                const profileDisplayName = nameParts.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ');

                currentDemandProfileName = profileDisplayName;
                currentDemandProfileText.textContent = currentDemandProfileName;

                const cfProfileDisplayName = baseSeason.charAt(0).toUpperCase() + baseSeason.slice(1);
                const seasonalMultipliers = SEASONAL_MULTIPLIERS[baseSeason];
                const baseSolarProfile = (countryProfiles[countrySelect.value] || countryProfiles.default).solar;
                const baseWindProfile = (countryProfiles[countrySelect.value] || countryProfiles.default).wind;
                const baseOffshoreWindProfile = (countryProfiles[countrySelect.value] || countryProfiles.default).offshoreWind;
                currentSolarCFProfile = baseSolarProfile.map(cf => Math.min(1, cf * seasonalMultipliers.solar));
                currentWindCFProfile = baseWindProfile.map(cf => Math.min(1, cf * seasonalMultipliers.wind));
                currentOffshoreWindCFProfile = baseOffshoreWindProfile.map(cf => Math.min(1, cf * seasonalMultipliers.offshoreWind));
                currentHydroCF = SEASONAL_HYDRO_CF[baseSeason];
                currentCFProfileName = cfProfileDisplayName;
                currentCFProfileText.textContent = currentCFProfileName;

                updateBaselineForCountry(countrySelect.value, profileName); 
                
                setDemandEditMode(false);
                setCFEditMode(false);
                saveState();
            }

            editDemandBtn.addEventListener('click', () => {
                originalDemandBeforeEdit = [...currentDemand];
                setDemandEditMode(true);
            });

            revertDemandBtn.addEventListener('click', () => {
                generationChart.data.datasets.find(ds => ds.label === 'Demand').data = [...originalDemandBeforeEdit];
                generationChart.update('none');
            });

            confirmDemandBtn.addEventListener('click', () => {
                currentDemand = [...generationChart.data.datasets.find(ds => ds.label === 'Demand').data];
                currentDemandProfileName = "User Defined";
                currentDemandProfileText.textContent = currentDemandProfileName;
                setDemandEditMode(false);
                runSimulation();
                saveState();
            });
            
            const demandProfiles = [
                'spring-typical', 'spring-high', 'summer-typical', 'summer-high', 
                'fall-typical', 'fall-high', 'winter-typical', 'winter-high'
            ];
            demandProfiles.forEach(profile => {
                document.getElementById(`preset-demand-${profile}`).addEventListener('click', () => applySeason(profile));
            });

            ['spring', 'summer', 'fall', 'winter'].forEach(season => {
                document.getElementById(`preset-cf-${season}`).addEventListener('click', () => {
                    applySeason(`${season}-typical`);
                });
            });

            editCFBtn.addEventListener('click', () => {
                originalSolarCFBeforeEdit = [...capacityFactorChart.data.datasets[0].data];
                originalWindCFBeforeEdit = [...capacityFactorChart.data.datasets[1].data];
                originalOffshoreWindCFBeforeEdit = [...capacityFactorChart.data.datasets[2].data];
                setCFEditMode(true);
            });

            revertCFBtn.addEventListener('click', () => {
                capacityFactorChart.data.datasets[0].data = [...originalSolarCFBeforeEdit];
                capacityFactorChart.data.datasets[1].data = [...originalWindCFBeforeEdit];
                capacityFactorChart.data.datasets[2].data = [...originalOffshoreWindCFBeforeEdit];
                capacityFactorChart.update('none');
            });

            confirmCFBtn.addEventListener('click', () => {
                currentSolarCFProfile = [...capacityFactorChart.data.datasets[0].data];
                currentWindCFProfile = [...capacityFactorChart.data.datasets[1].data];
                currentOffshoreWindCFProfile = [...capacityFactorChart.data.datasets[2].data];
                currentCFProfileName = "User Defined";
                currentCFProfileText.textContent = currentCFProfileName;
                
                const lastDemandProfile = currentDemandProfileName.toLowerCase().replace(' ', '-');
                updateBaselineForCountry(countrySelect.value, lastDemandProfile);

                setCFEditMode(false);
                runSimulation();
                saveState();
            });


            resetToZeroButton.addEventListener('click', () => {
                Object.keys(sliders).forEach(key => {
                    if (key === 'exportPrice') {
                         sliders[key].value = 20;
                         inputs[key].value = 20;
                    } else {
                        sliders[key].value = 0;
                        inputs[key].value = 0;
                    }
                });
                runSimulation();
                saveState();
            });
            
            makeDefaultButton.addEventListener('click', () => {
                userDefaultState = {};
                for (const key in sliders) {
                    userDefaultState[key] = sliders[key].value;
                }
                userDefaultState.enabledTech = { ...enabledTechnologies };
                userDefaultState.demandProfile = [...currentDemand];
                userDefaultState.solarCFProfile = [...currentSolarCFProfile];
                userDefaultState.windCFProfile = [...currentWindCFProfile];
                userDefaultState.offshoreWindCFProfile = [...currentOffshoreWindCFProfile];
                userDefaultState.demandProfileName = currentDemandProfileName;
                userDefaultState.cfProfileName = currentCFProfileName;
                userDefaultState.hydroCF = currentHydroCF;

                setNewBaselineFromCurrentState(); // Use the new function
                
                userDefaultState.baselineCost = customBaselineSystemCost;
                userDefaultState.baselineCO2 = customBaselineTotalAnnualCO2;

                runSimulation();
                
                const modal = document.createElement('div');
                modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50';
                modal.innerHTML = `
                    <div class="bg-white p-6 rounded-lg shadow-2xl text-center">
                        <p class="text-lg font-semibold text-gray-800">Current settings saved as user default.</p>
                    </div>
                `;
                document.body.appendChild(modal);
                setTimeout(() => modal.remove(), 2000);
            });

            resetToDefaultButton.addEventListener('click', () => {
                const isUserDefaultAvailable = Object.keys(userDefaultState).length > 0;

                if (isUserDefaultAvailable) {
                    restoreState(userDefaultState);
                    saveState();
                } else {
                    applySeason(currentSystemDefaultProfileName);
                }
            });

            function restoreState(state) {
                currentDemand = [...state.demandProfile];
                currentSolarCFProfile = [...state.solarCFProfile];
                currentWindCFProfile = [...state.windCFProfile];
                currentOffshoreWindCFProfile = [...state.offshoreWindCFProfile];
                currentDemandProfileName = state.demandProfileName;
                currentCFProfileName = state.cfProfileName;
                currentHydroCF = state.hydroCF;
                currentDemandProfileText.textContent = currentDemandProfileName;
                currentCFProfileText.textContent = currentCFProfileName;

                for (const key in state) {
                    if (sliders[key] && inputs[key]) {
                        sliders[key].value = state[key];
                        inputs[key].value = state[key];
                    }
                }
                if (state.enabledTech) {
                    for (const tech in state.enabledTech) {
                        const checkbox = document.getElementById(`toggle-${tech}`);
                        if (checkbox) {
                            checkbox.checked = state.enabledTech[tech];
                            enabledTechnologies[tech] = state.enabledTech[tech];
                        }
                    }
                }
                runSimulation();
                updateUndoRedoButtons();
            }

            undoButton.addEventListener('click', () => {
                if (historyIndex > 0) {
                    historyIndex--;
                    restoreState(stateHistory[historyIndex]);
                }
            });

            redoButton.addEventListener('click', () => {
                if (historyIndex < stateHistory.length - 1) {
                    historyIndex++;
                    restoreState(stateHistory[historyIndex]);
                }
            });
            
            // --- INITIALIZATION & DYNAMIC CONTENT ---

            function populateCountryDropdown() {
                countrySelect.innerHTML = '';
                const caOption = document.createElement('option');
                caOption.value = "California";
                caOption.textContent = "California";
                countrySelect.appendChild(caOption);

                for(const country in countryGridMixData) {
                    if (country !== "California") {
                        const option = document.createElement('option');
                        option.value = country;
                        option.textContent = country;
                        countrySelect.appendChild(option);
                    }
                }
                countrySelect.value = "California";
            }

            function updateBaselineForCountry(countryName, profileName) { 
                const TYPICAL_DAY_SCALING_FACTORS = {
                    summer: 0.82, fall: 0.77, winter: 0.73, spring: 0.79
                };

                let newCarbonTax = 0;
                let countryData = countryGridMixData[countryName];
                
                if (!countryData) {
                    console.error(`No data for country: ${countryName}`);
                    return;
                }
                
                newCarbonTax = carbonTaxes[countryName] || 0;

                const nameParts = profileName.split('-');
                const baseSeason = nameParts[0];
                const profileType = nameParts[1];

                if (currentDemandProfileName !== 'User Defined') {
                    const baseProfile = SEASONAL_DEMAND_PROFILES[`${baseSeason}-high`];
                    const basePeak = Math.max(...baseProfile);
                    
                    const countryHighPeakMW = countryData.peakLoadsMW[baseSeason];
                    let targetPeakGW = countryHighPeakMW / 1000;

                    if (profileType === 'typical') {
                        targetPeakGW *= TYPICAL_DAY_SCALING_FACTORS[baseSeason];
                    }

                    const finalScalingFactor = targetPeakGW / basePeak;
                    currentDemand = baseProfile.map(val => val * finalScalingFactor);
                }
                
                currentCountryInstalledCapacity = {};
                for(const tech in COST_DATA.capacity_factor) {
                    const techCapacityGW = (countryData.totalCapacityMW / 1000) * ((countryData.mix[tech] || 0) / 100);
                    currentCountryInstalledCapacity[tech] = techCapacityGW;
                }
                
                currentBaselineStorage = countryData.storageGWh || {};

                const potentialGeneration = {};
                for(const tech in currentCountryInstalledCapacity) {
                    potentialGeneration[tech] = Array(24).fill(0);
                    const cf = COST_DATA.capacity_factor[tech];
                    let capacity = currentCountryInstalledCapacity[tech];

                    if (tech === 'solar') {
                        for (let i = 0; i < 24; i++) potentialGeneration.solar[i] = capacity * currentSolarCFProfile[i];
                    } else if (tech === 'wind') {
                        for (let i = 0; i < 24; i++) potentialGeneration.wind[i] = capacity * currentWindCFProfile[i];
                    } else if (tech === 'offshoreWind') {
                        for (let i = 0; i < 24; i++) potentialGeneration.offshoreWind[i] = capacity * currentOffshoreWindCFProfile[i];
                    } else if (tech === 'hydro') {
                        for (let i = 0; i < 24; i++) potentialGeneration.hydro[i] = capacity;
                    } else if (tech === 'naturalGas' || tech === 'coal') {
                        for (let i = 0; i < 24; i++) potentialGeneration[tech][i] = capacity * 1.0;
                    } else {
                        for (let i = 0; i < 24; i++) potentialGeneration[tech][i] = capacity * cf;
                    }
                }
                BASELINE_POTENTIAL_GENERATION = potentialGeneration;

                Object.keys(sliders).forEach(key => {
                    sliders[key].value = 0;
                    inputs[key].value = 0;
                });
                
                sliders.carbonTax.value = newCarbonTax;
                inputs.carbonTax.value = newCarbonTax;

                const newExportPrice = countryData.defaultExportPrice ?? 20;
                sliders.exportPrice.value = newExportPrice;
                inputs.exportPrice.value = newExportPrice;
                
                const allTechs = [...Object.keys(COST_DATA.capacity_factor), 'battery4hr', 'battery8hr', 'longduration'];
                allTechs.forEach(tech => {
                    const checkbox = document.getElementById(`toggle-${tech}`);
                    if(checkbox) {
                       checkbox.checked = true;
                       enabledTechnologies[tech] = true;
                    }
                });

                const baselineResult = getSimulationResult(
                    { 
                        capacity: { solar: 0, wind: 0, offshoreWind: 0, geothermal: 0, nuclear: 0, biomass: 0, rng: 0, battery4hr: 0, battery8hr: 0, longduration: 0, dac: 0, demandflex: 0 },
                        incentives: { solar: 0, wind: 0, offshoreWind: 0, geothermal: 0, nuclear: 0, biomass: 0, rng: 0, storage: 0, dac: 0, carbonTax: newCarbonTax, exportPrice: newExportPrice }
                    },
                    currentSolarCFProfile,
                    currentWindCFProfile,
                    currentOffshoreWindCFProfile,
                    BASELINE_POTENTIAL_GENERATION,
                    currentBaselineStorage,
                    currentHydroCF,
                    countryName
                );
                customBaselineSystemCost = baselineResult.systemCost;
                customBaselineConsumerCost = calculateAnnualConsumerCost(baselineResult.hourlyMarginalPrice, baselineResult.demand); // NEW
                customBaselineTotalAnnualCO2 = baselineResult.emissions.reduce((a, b) => a + b, 0) * 365;
                
                systemDefaultState = {};
                for (const key in sliders) {
                    systemDefaultState[key] = sliders[key].value;
                }
                systemDefaultState.enabledTech = { ...enabledTechnologies };
                userDefaultState = {};
                
                let totalDefaultCapacity = 0;
                for (const tech in currentCountryInstalledCapacity) {
                    defaultCapacityMix[tech] = currentCountryInstalledCapacity[tech];
                    totalDefaultCapacity += currentCountryInstalledCapacity[tech];
                }

                if (totalDefaultCapacity > 0) {
                    for (const tech in defaultCapacityMix) {
                        defaultCapacityMix[tech] = (defaultCapacityMix[tech] / totalDefaultCapacity) * 100;
                    }
                }

                let totalDefaultGeneration = 0;
                for (const tech in baselineResult.generation) {
                    if (tech !== 'curtailment' && !tech.includes('ToStorage')) {
                        const gen = baselineResult.generation[tech].reduce((a, b) => a + b, 0);
                        defaultGenerationMix[tech] = gen;
                        totalDefaultGeneration += gen;
                    }
                }
                 if (totalDefaultGeneration > 0) {
                    for (const tech in defaultGenerationMix) {
                        defaultGenerationMix[tech] = (defaultGenerationMix[tech] / totalDefaultGeneration) * 100;
                    }
                }
                runSimulation();
            }

            countrySelect.addEventListener('change', (e) => {
                applySeason(currentSystemDefaultProfileName);
            });
            
            document.addEventListener('mousemove', (e) => {
                hoverTooltip.style.left = e.pageX + 15 + 'px';
                hoverTooltip.style.top = e.pageY + 15 + 'px';
            });

            gridMixSlidersContainer.addEventListener('mouseover', (e) => {
                const row = e.target.closest('.mix-slider-row');
                if (!row) return;
                const tech = row.dataset.tech;
                if (!tech) return;

                const baselineCapacity = currentCountryInstalledCapacity[tech] || 0;
                const newCapacity = (sliders[tech] ? parseFloat(sliders[tech].value) : 0) || 0;
                const totalCapacity = baselineCapacity + newCapacity;

                hoverTooltip.innerHTML = `Total Capacity: ${totalCapacity.toFixed(2)} GW`;
                hoverTooltip.classList.remove('hidden');
            });
            gridMixSlidersContainer.addEventListener('mouseout', () => {
                hoverTooltip.classList.add('hidden');
            });
            
            generationMixSlidersContainer.addEventListener('mouseover', (e) => {
                const row = e.target.closest('.mix-slider-row');
                if (!row) return;
                const tech = row.dataset.tech;
                if (!tech || dailyGenerationTotalsGWh[tech] === undefined) return;

                const totalGWh = dailyGenerationTotalsGWh[tech];
                const label = tech === 'curtailment' ? 'Total Daily Curtailment' : 'Total Daily Generation';
                hoverTooltip.innerHTML = `${label}: ${totalGWh.toFixed(2)} GWh`;
                hoverTooltip.classList.remove('hidden');
            });
             generationMixSlidersContainer.addEventListener('mouseout', () => {
                hoverTooltip.classList.add('hidden');
            });


            // --- TUTORIAL LOGIC ---
            const tutorialSteps = [
                {
                    title: 'Welcome to the Grid Simulator!',
                    text: 'This interactive tool lets you explore pathways to a zero-carbon electricity grid. Let\'s take a quick tour of the main features.',
                    position: 'center'
                },
                {
                    element: '#tutorial-step-2',
                    title: 'Live Simulation Charts',
                    text: 'These charts show the real-time results of your decisions. See how the generation mix and CO2 emissions change as you adjust the levers.',
                    position: 'right',
                    highlightClass: 'rounded-lg'
                },
                {
                    element: '#tutorial-step-3',
                    title: 'Your Control Panel',
                    text: 'This is where you make things happen! Use these sliders to deploy new technologies, set government incentives, and choose a starting grid mix.',
                    position: 'left',
                    highlightClass: 'rounded-lg'
                },
                {
                    element: '#tutorial-step-4',
                    title: 'Manage Existing Resources',
                    text: 'Use these checkboxes to turn off an existing resource type and watch the impact it has on emissions and costs.',
                    position: 'right',
                    highlightClass: 'rounded-lg'
                },
                {
                    element: '#make-default-button',
                    title: 'Save Your Scenario',
                    text: 'Once you find a set of policies you like, you can save them as your new default. The cost metrics will then be calculated relative to this new baseline.',
                    position: 'top',
                    highlightClass: 'rounded-full'
                },
                {
                    element: '#tutorial-step-5',
                    title: 'Key Outcome Metrics',
                    text: 'Your goal is to get CO2 emissions to zero while keeping costs low. These cards show the impact on electricity bills and the cost of avoiding CO2.',
                    position: 'bottom',
                    highlightClass: 'rounded-lg'
                },
                {
                    element: '#edit-demand-btn',
                    title: 'Customize Demand',
                    text: 'Click the edit icon to create your own custom daily demand profile, or select a seasonal preset.',
                    position: 'left',
                    highlightClass: 'rounded-full'
                },
                {
                    element: '#edit-cf-btn',
                    title: 'Customize Weather',
                    text: 'Click this edit icon to change the hourly performance of solar and wind to simulate different weather conditions.',
                    position: 'top',
                    highlightClass: 'rounded-full'
                }
            ];

            let currentStep = 0;
            const overlay = document.getElementById('tutorial-overlay');
            const popover = document.getElementById('tutorial-popover');
            const titleEl = document.getElementById('tutorial-title');
            const textEl = document.getElementById('tutorial-text');
            const prevBtn = document.getElementById('tutorial-prev');
            const nextBtn = document.getElementById('tutorial-next');
            const skipBtn = document.getElementById('tutorial-skip');
            let highlightedElement = null;

            function startTutorial() {
                if (localStorage.getItem('gridSimulatorTutorialSeen')) {
                    return;
                }
                document.body.classList.add('tutorial-active');
                currentStep = 0;
                showTutorialStep(currentStep);
            }

            function endTutorial() {
                document.body.classList.remove('tutorial-active');
                overlay.style.display = 'none';
                popover.style.display = 'none';
                if (highlightedElement) {
                    highlightedElement.classList.remove('tutorial-highlight-active', 'rounded-full', 'rounded-lg');
                }
                localStorage.setItem('gridSimulatorTutorialSeen', 'true');
            }
            
            function positionPopover(targetElement, popoverEl, position) {
                popoverEl.style.visibility = 'hidden';
                popoverEl.style.display = 'block';

                const popoverRect = popoverEl.getBoundingClientRect();
                const margin = 15;

                if (position === 'center' || !targetElement) {
                    popoverEl.style.left = '50%';
                    popoverEl.style.top = '50%';
                    popoverEl.style.transform = 'translate(-50%, -50%)';
                    popoverEl.style.visibility = 'visible';
                    return;
                }

                const targetRect = targetElement.getBoundingClientRect();
                let top, left;

                switch (position) {
                    case 'top':
                        top = targetRect.top - popoverRect.height - margin;
                        left = targetRect.left + (targetRect.width / 2) - (popoverRect.width / 2);
                        break;
                    case 'bottom':
                        top = targetRect.bottom + margin;
                        left = targetRect.left + (targetRect.width / 2) - (popoverRect.width / 2);
                        break;
                    case 'left':
                        top = targetRect.left - popoverRect.width - margin;
                        left = targetRect.top + (targetRect.height / 2) - (popoverRect.height / 2);
                        break;
                    case 'right':
                    default:
                        top = targetRect.top + (targetRect.height / 2) - (popoverRect.height / 2);
                        left = targetRect.right + margin;
                        break;
                }

                if (top < margin) top = margin;
                if (left < margin) left = margin;
                if (left + popoverRect.width > window.innerWidth - margin) {
                    left = window.innerWidth - popoverRect.width - margin;
                }
                if (top + popoverRect.height > window.innerHeight - margin) {
                    top = window.innerHeight - popoverRect.height - margin;
                }

                popoverEl.style.top = `${top}px`;
                popoverEl.style.left = `${left}px`;
                popoverEl.style.transform = 'none';
                popoverEl.style.visibility = 'visible';
            }

            function showTutorialStep(stepIndex) {
                if (stepIndex < 0 || stepIndex >= tutorialSteps.length) {
                    endTutorial();
                    return;
                }

                const step = tutorialSteps[stepIndex];

                if (highlightedElement) {
                    highlightedElement.classList.remove('tutorial-highlight-active', 'rounded-full', 'rounded-lg');
                    highlightedElement = null;
                }

                titleEl.textContent = step.title;
                textEl.textContent = step.text;

                let targetElement;
                if (step.element) {
                    targetElement = document.querySelector(step.element);
                }

                if (targetElement) {
                    overlay.style.display = 'none';
                    highlightedElement = targetElement;
                    highlightedElement.classList.add('tutorial-highlight-active');
                    if (step.highlightClass) {
                        highlightedElement.classList.add(step.highlightClass);
                    }
                    
                    highlightedElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });

                    setTimeout(() => {
                        positionPopover(highlightedElement, popover, step.position);
                    }, 400); 
                } else {
                    overlay.style.display = 'block';
                    positionPopover(null, popover, 'center');
                }

                prevBtn.style.display = stepIndex === 0 ? 'none' : 'inline-block';
                nextBtn.textContent = stepIndex === tutorialSteps.length - 1 ? 'Finish' : 'Next';
            }

            nextBtn.addEventListener('click', () => {
                currentStep++;
                showTutorialStep(currentStep);
            });

            prevBtn.addEventListener('click', () => {
                currentStep--;
                showTutorialStep(currentStep);
            });

            skipBtn.addEventListener('click', endTutorial);
            
            startTutorialBtn.addEventListener('click', () => {
                localStorage.removeItem('gridSimulatorTutorialSeen');
                startTutorial();
            });


            // --- MAIN INITIALIZATION FUNCTION ---
            async function initialize() {
                try {
                    await signInAnonymously(auth);
                    console.log("Firebase authentication successful.");
                } catch (error) {
                    console.error("Firebase authentication failed:", error);
                    visitorCountEl.textContent = "Auth Failed";
                    return;
                }

                const counterRef = doc(db, `artifacts/${appId}/public/data/counters/visitor_counter`);
                try {
                    const newCount = await runTransaction(db, async (transaction) => {
                        const counterDoc = await transaction.get(counterRef);
                        if (!counterDoc.exists()) {
                            transaction.set(counterRef, { count: 1 });
                            return 1;
                        }
                        const newCount = counterDoc.data().count + 1;
                        transaction.update(counterRef, { count: newCount });
                        return newCount;
                    });
                    visitorCountEl.textContent = newCount.toLocaleString();
                } catch (e) {
                    console.error("Firestore transaction failed: ", e);
                    visitorCountEl.textContent = "DB Error";
                }

                createGridMixSliders();
                createGenerationMixSliders();
                populateCountryDropdown();
                applySeason('spring-typical');
                setupInputSyncing();
                
                setTimeout(startTutorial, 500);
            }

            await initialize();
        });
