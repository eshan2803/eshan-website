// --- 1. GET REFERENCES TO HTML ELEMENTS ---
const ctx = document.getElementById('gridChart').getContext('2d');
const cfCtx = document.getElementById('capacityFactorChart').getContext('2d');
const startButton = document.getElementById('startButton');
const pauseButtons = document.getElementById('pauseButtons');
const resumeButton = document.getElementById('resumeButton');
const restartButton = document.getElementById('restartButton');
const showScheduleBtn = document.getElementById('showScheduleBtn');
const showScheduleButtonContainer = document.getElementById('showScheduleButtonContainer');
const endGameButtons = document.getElementById('endGameButtons');
const newGameButton = document.getElementById('newGameButton');
const retryWithScheduleButton = document.getElementById('retryWithScheduleButton');

// Leaderboard elements
const usernameModal = document.getElementById('usernameModal');
const usernameInput = document.getElementById('usernameInput');
const submitUsernameBtn = document.getElementById('submitUsernameBtn');
const leaderboardBtn = document.getElementById('leaderboardBtn');
const leaderboardModal = document.getElementById('leaderboardModal');
const closeLeaderboardBtn = document.getElementById('closeLeaderboardBtn');
const leaderboardLoading = document.getElementById('leaderboardLoading');
const leaderboardContent = document.getElementById('leaderboardContent');
const leaderboardList = document.getElementById('leaderboardList');
const leaderboardEmpty = document.getElementById('leaderboardEmpty');
const currentUsernameSpan = document.getElementById('currentUsername');

// API Configuration
const API_BASE_URL = 'https://grid-operator-game.onrender.com/api';

// Battery controls
const batterySlider = document.getElementById('batterySlider');
const batteryInput = document.getElementById('batteryInput');

// CCGT unit dispatch controls
const ccgtCommitBtn = document.getElementById('ccgtCommitBtn');
const ccgtShutdownBtn = document.getElementById('ccgtShutdownBtn');
const ccgtPowerSlider = document.getElementById('ccgtPowerSlider');
const ccgtOutputDisplay = document.getElementById('ccgtOutputDisplay');
const ccgtOnlineCount = document.getElementById('ccgtOnlineCount');
const ccgtOnlineMW = document.getElementById('ccgtOnlineMW');
const ccgtStartingCount = document.getElementById('ccgtStartingCount');
const ccgtNextOnline = document.getElementById('ccgtNextOnline');

// CT unit dispatch controls
const ctCommitBtn = document.getElementById('ctCommitBtn');
const ctShutdownBtn = document.getElementById('ctShutdownBtn');
const ctPowerSlider = document.getElementById('ctPowerSlider');
const ctOutputDisplay = document.getElementById('ctOutputDisplay');
const ctOnlineCount = document.getElementById('ctOnlineCount');
const ctOnlineMW = document.getElementById('ctOnlineMW');
const ctStartingCount = document.getElementById('ctStartingCount');
const ctNextOnline = document.getElementById('ctNextOnline');

// Hydro controls
const hydroSlider = document.getElementById('hydroSlider');
const hydroInput = document.getElementById('hydroInput');
const hydroCondition = document.getElementById('hydroCondition');
const hydroMaxDisplay = document.getElementById('hydroMaxDisplay');

// Solar Curtailment controls
const solarCurtailmentSlider = document.getElementById('solarCurtailmentSlider');
const solarCurtailmentInput = document.getElementById('solarCurtailmentInput');
const solarCurtailmentMaxDisplay = document.getElementById('solarCurtailmentMaxDisplay');

// Wind Curtailment controls
const windCurtailmentSlider = document.getElementById('windCurtailmentSlider');
const windCurtailmentInput = document.getElementById('windCurtailmentInput');
const windCurtailmentMaxDisplay = document.getElementById('windCurtailmentMaxDisplay');

// RNG unit dispatch controls
const rngCommitBtn = document.getElementById('rngCommitBtn');
const rngShutdownBtn = document.getElementById('rngShutdownBtn');
const rngPowerSlider = document.getElementById('rngPowerSlider');
const rngOutputDisplay = document.getElementById('rngOutputDisplay');
const rngOnlineCount = document.getElementById('rngOnlineCount');
const rngOnlineMW = document.getElementById('rngOnlineMW');
const rngStartingCount = document.getElementById('rngStartingCount');
const rngNextOnline = document.getElementById('rngNextOnline');

// Hydrogen unit dispatch controls
const hydrogenCommitBtn = document.getElementById('hydrogenCommitBtn');
const hydrogenShutdownBtn = document.getElementById('hydrogenShutdownBtn');
const hydrogenPowerSlider = document.getElementById('hydrogenPowerSlider');
const hydrogenOutputDisplay = document.getElementById('hydrogenOutputDisplay');
const hydrogenOnlineCount = document.getElementById('hydrogenOnlineCount');
const hydrogenOnlineMW = document.getElementById('hydrogenOnlineMW');
const hydrogenStartingCount = document.getElementById('hydrogenStartingCount');
const hydrogenNextOnline = document.getElementById('hydrogenNextOnline');
const hydrogenFuelCost = document.getElementById('hydrogenFuelCost');
const hydrogenCostDisplay = document.getElementById('hydrogenCostDisplay');

const totalSupplyValueSpan = document.getElementById('totalSupplyValue');

// Battery state of charge elements
const batterySOCDiv = document.getElementById('batterySOC');
const batterySOCText = document.getElementById('batterySOCText');
const batterySOCDisplay = document.getElementById('batterySOCDisplay');

const demandValueSpan = document.getElementById('demandValue');
const deltaValueSpan = document.getElementById('deltaValue');
const currentCostValueSpan = document.getElementById('currentCostValue');
const totalCostValueSpan = document.getElementById('totalCostValue');
const nextDemandPreview = document.getElementById('nextDemandPreview');
const nextDemandValue = document.getElementById('nextDemandValue');
const nextDemandChange = document.getElementById('nextDemandChange');
const editProfileButton = document.getElementById('editProfileButton');
const confirmEditButton = document.getElementById('confirmEditButton');
const revertEditButton = document.getElementById('revertEditButton');
const loadPresetsDiv = document.getElementById('load-presets');
const currentLoadProfileText = document.getElementById('current-load-profile-text');

// CF Chart elements
const editCFBtn = document.getElementById('edit-cf-btn');
const confirmCFBtn = document.getElementById('confirm-cf-btn');
const revertCFBtn = document.getElementById('revert-cf-btn');
const cfPresetsDiv = document.getElementById('cf-presets');
const currentCFProfileText = document.getElementById('current-cf-profile-text');

// Current season/profile selection
let currentSeason = 'spring-typical';
let isLoadProfileModified = false;
let isCFProfileModified = false;

// Event buttons removed - events now trigger randomly

// Gauge elements
const deltaNeedle = document.getElementById('deltaNeedle');
const frequencyNeedle = document.getElementById('frequencyNeedle');
const deltaGaugeValue = document.getElementById('deltaGaugeValue');
const frequencyGaugeValue = document.getElementById('frequencyGaugeValue');

// Status banner and counters
const statusBanner = document.getElementById('statusBanner');
const tipsBanner = document.getElementById('tipsBanner');
const emergencyCountSpan = document.getElementById('emergencyCount');
const blackoutCountSpan = document.getElementById('blackoutCount');

const currentTimeValue = document.getElementById('currentTimeValue');

// Game speed controls
const gameSpeedSlider = document.getElementById('gameSpeedSlider');
const gameSpeedTime = document.getElementById('gameSpeedTime');

// Header buttons
const documentationBtn = document.getElementById('documentationBtn');
const showTutorialBtn = document.getElementById('showTutorialBtn');

// --- 2. DEFINE GLOBAL VARIABLES ---
let myChart;
let cfChart;
let deltaHistoryChart;
let gameInterval;
let forecastData = [];
let hourlyForecastData = []; // Hourly forecast (24 points) for pre-game display
let gameTick = 0;
let gameStarted = false; // Track whether game has started
let gamePaused = false; // Track whether game is paused
let gameSpeed = 1.0; // Game speed multiplier (seconds per tick)
let seasonalProfilesData = null;
let originalSeasonalProfilesData = null; // Pristine copy of presets
let isEditMode = false;
let isCFEditMode = false;
let originalDemandBeforeEdit = [];
let originalSolarCFBeforeEdit = [];
let originalWindCFBeforeEdit = [];
let currentCFProfileName = 'Summer';

// Battery state variables (will be updated dynamically from planner data)
let BATTERY_CAPACITY_MWH = 52000; // Default: 52 GWh capacity (4-hour battery at 13 GW)
let BATTERY_POWER_MW = 13000; // Default: 13 GW power capacity
let batterySOC = 0.2; // State of charge (0 to 1), start at 20%

// Ramp rate limits (MW per 5 minutes, since game ticks are 5-minute intervals)
const CCGT_RAMP_RATE_MW_PER_5MIN = (150 * 60) / 12; // 750 MW/5min (9,000 MW/hr ÷ 12)
const CT_RAMP_RATE_MW_PER_5MIN = (500 * 60) / 12;   // 2,500 MW/5min (30,000 MW/hr ÷ 12)
const HYDRO_RAMP_RATE_MW_PER_5MIN = (1000 * 60) / 12; // 5,000 MW/5min (60,000 MW/hr ÷ 12) - very fast
// Battery has no ramp limit (near-instantaneous)

// Track previous power output for ramp rate calculations
let prevCCGT = 0;
let prevCT = 0;
let prevHydro = 0;

// Operating costs in $/MWh (mainly fuel costs for thermal plants)
const BATTERY_OPCOST = 6;   // Battery storage (minimal O&M, efficiency losses)
const HYDRO_OPCOST = 2;     // Hydro (minimal O&M, no fuel cost)
const SOLAR_CURTAILMENT_OPCOST = 20;   // Solar curtailment (opportunity cost of wasted energy)
const WIND_CURTAILMENT_OPCOST = 20;  // Wind curtailment (opportunity cost of wasted energy)

// Linear cost function parameters for CCGT and CT (simulating heat rate degradation)
// CCGT: starts at $32/MWh for first 500MW, then increases by $1/MWh for each additional 500MW
const CCGT_BASE_COST = 32;
const CCGT_STEP_MW = 500;
const CCGT_COST_INCREMENT = 1;

// CT: starts at $50/MWh for first 200MW, then increases by $2/MWh for each additional 200MW
const CT_BASE_COST = 50;
const CT_STEP_MW = 200;
const CT_COST_INCREMENT = 2;

// Helper function to calculate linear cost for CCGT
function calculateCCGTCost(mw) {
    if (mw <= 0) return 0;

    let totalCost = 0;
    let remainingMW = mw;
    let stepIndex = 0;

    while (remainingMW > 0) {
        const stepMW = Math.min(remainingMW, CCGT_STEP_MW);
        const costPerMWh = CCGT_BASE_COST + (stepIndex * CCGT_COST_INCREMENT);
        totalCost += stepMW * costPerMWh;
        remainingMW -= stepMW;
        stepIndex++;
    }

    return totalCost;
}

// Helper function to calculate linear cost for CT
function calculateCTCost(mw) {
    if (mw <= 0) return 0;

    let totalCost = 0;
    let remainingMW = mw;
    let stepIndex = 0;

    while (remainingMW > 0) {
        const stepMW = Math.min(remainingMW, CT_STEP_MW);
        const costPerMWh = CT_BASE_COST + (stepIndex * CT_COST_INCREMENT);
        totalCost += stepMW * costPerMWh;
        remainingMW -= stepMW;
        stepIndex++;
    }

    return totalCost;
}

// Helper function to calculate linear cost for RNG
function calculateRNGCost(mw) {
    if (mw <= 0) return 0;

    let totalCost = 0;
    let remainingMW = mw;
    let stepIndex = 0;

    while (remainingMW > 0) {
        const stepMW = Math.min(remainingMW, RNG_STEP_MW);
        const costPerMWh = RNG_BASE_COST + (stepIndex * RNG_COST_INCREMENT);
        totalCost += stepMW * costPerMWh;
        remainingMW -= stepMW;
        stepIndex++;
    }

    return totalCost;
}

// Helper function to calculate linear cost for Hydrogen
function calculateHydrogenCost(mw) {
    if (mw <= 0) return 0;

    let totalCost = 0;
    let remainingMW = mw;
    let stepIndex = 0;

    while (remainingMW > 0) {
        const stepMW = Math.min(remainingMW, HYDROGEN_STEP_MW);
        const costPerMWh = currentHydrogenBaseCost + (stepIndex * HYDROGEN_COST_INCREMENT);
        totalCost += stepMW * costPerMWh;
        remainingMW -= stepMW;
        stepIndex++;
    }

    return totalCost;
}

// Cost tracking
let totalCost = 0; // Total accumulated cost in dollars

// Emergency and Blackout counters
let emergencyAlertCount = 0;
let blackoutCount = 0;

// Hydro capacity mapping (MW) based on year type
const HYDRO_CAPACITY = {
    wet: 6000,
    normal: 4000,
    dry: 3000
};
let currentHydroMaxMW = HYDRO_CAPACITY.normal; // Default to normal

// --- LOAD CAPACITY DATA FROM GRID PLANNER ---
let plannerCapacityData = null;
let selectedCountry = 'california'; // Default to California
let selectedCountryDisplayName = 'California'; // For UI display
try {
    const storedData = localStorage.getItem('gridDispatchCapacities');
    if (storedData) {
        plannerCapacityData = JSON.parse(storedData);
        console.log('Loaded capacity data from Grid Planner:', plannerCapacityData);

        // Extract country/region information
        if (plannerCapacityData.country) {
            selectedCountryDisplayName = plannerCapacityData.country;
            // Convert country name to lowercase key for seasonal profiles
            selectedCountry = plannerCapacityData.country.toLowerCase().replace(/\s+/g, '');
            console.log('Selected country from planner:', selectedCountry, '(display:', selectedCountryDisplayName + ')');
        }
    }
} catch (error) {
    console.error('Error loading capacity data:', error);
}

// Global capacities object for easy access
const capacities = {
    rng: plannerCapacityData?.totalCapacityMW?.rng || 0,
    hydrogen: plannerCapacityData?.totalCapacityMW?.hydrogen || 0
};

// Unit Dispatch Constants
const CCGT_UNIT_SIZE_MW = 500;
const CCGT_MAX_UNITS = 30;
const CCGT_MIN_LOAD_PERCENT = 0.5; // 50% minimum stable load
const CCGT_STARTUP_TIME_MIN = 75; // 60-90 min, using midpoint for game time
const CCGT_RAMP_RATE_MW_PER_MIN = 12.5; // 10-15 MW/min per unit

const CT_UNIT_SIZE_MW = 200;
const CT_MAX_UNITS = 50;
const CT_MIN_LOAD_PERCENT = 0; // 0% minimum - can run at any level
const CT_STARTUP_TIME_MIN = 15; // 10-20 min, using midpoint
const CT_RAMP_RATE_MW_PER_MIN = 25; // 20-30 MW/min per unit

// RNG Unit Constants
const RNG_UNIT_SIZE_MW = 100;
let RNG_MAX_UNITS = 20; // Will be dynamically calculated based on planner capacity
const RNG_MIN_LOAD_PERCENT = 0.3; // 30% minimum stable load
const RNG_STARTUP_TIME_MIN = 30; // 30 min startup time
const RNG_RAMP_RATE_MW_PER_MIN = 10; // 10 MW/min per unit
const RNG_BASE_COST = 255; // $/MWh base cost
const RNG_COST_INCREMENT = 3; // $/MWh per 100MW step
const RNG_STEP_MW = 100;

// Hydrogen Unit Constants
const HYDROGEN_UNIT_SIZE_MW = 150;
let HYDROGEN_MAX_UNITS = 15; // Will be dynamically calculated based on planner capacity
const HYDROGEN_MIN_LOAD_PERCENT = 0.2; // 20% minimum stable load
const HYDROGEN_STARTUP_TIME_MIN = 45; // 45 min startup time
const HYDROGEN_RAMP_RATE_MW_PER_MIN = 8; // 8 MW/min per unit

// Hydrogen fuel cost options ($/MWh base cost for different H2 prices)
const HYDROGEN_FUEL_COST = {
    '3': 278,  // 3 $/kg H2
    '4': 362,  // 4 $/kg H2
    '5': 455,  // 5 $/kg H2
    '6': 540   // 6 $/kg H2 (default)
};
let currentHydrogenBaseCost = HYDROGEN_FUEL_COST['6']; // Default to 6 $/kg
const HYDROGEN_COST_INCREMENT = 5; // $/MWh per 150MW step
const HYDROGEN_STEP_MW = 150;

// Unit state arrays - each element represents one unit
// Unit states: 'offline', 'starting' (with startupTicksRemaining), 'online'
let ccgtUnits = [];
let ctUnits = [];
let rngUnits = [];
let hydrogenUnits = [];

// Function to initialize unit arrays (called after planner data is loaded)
function initializeUnitArrays() {
    // Clear existing arrays
    ccgtUnits = [];
    ctUnits = [];
    rngUnits = [];
    hydrogenUnits = [];

    // Initialize CCGT units
    for (let i = 0; i < CCGT_MAX_UNITS; i++) {
        ccgtUnits.push({ state: 'offline', startupTicksRemaining: 0, outputMW: 0 });
    }

    // Initialize CT units
    for (let i = 0; i < CT_MAX_UNITS; i++) {
        ctUnits.push({ state: 'offline', startupTicksRemaining: 0, outputMW: 0 });
    }

    // Initialize RNG units (may be dynamically sized based on planner capacity)
    for (let i = 0; i < RNG_MAX_UNITS; i++) {
        rngUnits.push({ state: 'offline', startupTicksRemaining: 0, outputMW: 0 });
    }

    // Initialize Hydrogen units (may be dynamically sized based on planner capacity)
    for (let i = 0; i < HYDROGEN_MAX_UNITS; i++) {
        hydrogenUnits.push({ state: 'offline', startupTicksRemaining: 0, outputMW: 0 });
    }
}

// Helper function to calculate actual MW for a given number of RNG units (accounts for fractional last unit)
function calculateRNGMW(unitCount) {
    if (unitCount === 0) return 0;
    const totalInstalledCapacityMW = capacities.rng || 0;
    const fractionalAmount = totalInstalledCapacityMW % RNG_UNIT_SIZE_MW;

    if (fractionalAmount > 0 && unitCount === RNG_MAX_UNITS) {
        // Last unit is fractional
        return (unitCount - 1) * RNG_UNIT_SIZE_MW + fractionalAmount;
    }
    return unitCount * RNG_UNIT_SIZE_MW;
}

// Helper function to calculate actual MW for a given number of Hydrogen units (accounts for fractional last unit)
function calculateHydrogenMW(unitCount) {
    if (unitCount === 0) return 0;
    const totalInstalledCapacityMW = capacities.hydrogen || 0;
    const fractionalAmount = totalInstalledCapacityMW % HYDROGEN_UNIT_SIZE_MW;

    if (fractionalAmount > 0 && unitCount === HYDROGEN_MAX_UNITS) {
        // Last unit is fractional
        return (unitCount - 1) * HYDROGEN_UNIT_SIZE_MW + fractionalAmount;
    }
    return unitCount * HYDROGEN_UNIT_SIZE_MW;
}

// --- UNIT DISPATCH FUNCTIONS ---

// Helper: Get count of units by state
function getUnitCounts(units) {
    let offline = 0, starting = 0, online = 0;
    units.forEach(unit => {
        if (unit.state === 'offline') offline++;
        else if (unit.state === 'starting') starting++;
        else if (unit.state === 'online') online++;
    });
    return { offline, starting, online };
}

// Helper: Get total MW from online units
function getTotalOnlineMW(units) {
    return units.filter(u => u.state === 'online').reduce((sum, u) => sum + u.outputMW, 0);
}

// Helper: Get min/max MW for online units
function getOnlineCapacity(units, unitSize, minLoadPercent) {
    const onlineCount = units.filter(u => u.state === 'online').length;
    // Cumulative formula: previous units at full capacity + newest unit at min/max
    const minMW = (onlineCount - 1 + minLoadPercent) * unitSize;
    const maxMW = onlineCount * unitSize;
    return { minMW, maxMW, onlineCount };
}

// Helper: Get next unit coming online and its countdown
function getNextUnitCountdown(units) {
    const startingUnits = units.filter(u => u.state === 'starting');
    if (startingUnits.length === 0) return null;

    // Find the unit with the smallest startupTicksRemaining (coming online soonest)
    const nextUnit = startingUnits.reduce((min, unit) =>
        unit.startupTicksRemaining < min.startupTicksRemaining ? unit : min
    );

    // Convert ticks to minutes (each tick is 5 minutes)
    const minutesRemaining = nextUnit.startupTicksRemaining * 5;
    return minutesRemaining;
}

// CCGT: Commit a unit (start the startup timer or bring online instantly if pre-game)
function commitCCGTUnit() {
    const offlineUnit = ccgtUnits.find(u => u.state === 'offline');
    if (!offlineUnit) return false;

    if (!gameStarted) {
        // Before game starts: bring unit online instantly at max capacity
        offlineUnit.state = 'online';
        offlineUnit.outputMW = CCGT_UNIT_SIZE_MW; // Start at full capacity
        offlineUnit.startupTicksRemaining = 0;
        updateCCGTPowerSlider();

        // Distribute power according to slider value
        const targetMW = parseFloat(ccgtPowerSlider.value);
        distributePowerToUnits(ccgtUnits, targetMW, CCGT_UNIT_SIZE_MW);
    } else {
        // During game: normal startup timer
        offlineUnit.state = 'starting';
        // Convert minutes to ticks (5-minute resolution)
        offlineUnit.startupTicksRemaining = Math.ceil(CCGT_STARTUP_TIME_MIN / 5);
    }

    updateCCGTDisplay();
    updateSupplyValues(); // Update supply display immediately
    return true;
}

// CCGT: Shutdown a unit (if online)
function shutdownCCGTUnit() {
    const onlineUnit = ccgtUnits.find(u => u.state === 'online');
    if (!onlineUnit) return false;

    onlineUnit.state = 'offline';
    onlineUnit.outputMW = 0;
    onlineUnit.startupTicksRemaining = 0;

    updateCCGTDisplay();
    updateCCGTPowerSlider();
    updateSupplyValues(); // Update supply display and chart immediately
    return true;
}

// CT: Commit a unit (start the startup timer or bring online instantly if pre-game)
function commitCTUnit() {
    const offlineUnit = ctUnits.find(u => u.state === 'offline');
    if (!offlineUnit) return false;

    if (!gameStarted) {
        // Before game starts: bring unit online instantly at max capacity
        offlineUnit.state = 'online';
        offlineUnit.outputMW = CT_UNIT_SIZE_MW; // Start at full capacity
        offlineUnit.startupTicksRemaining = 0;
        updateCTPowerSlider();

        // Distribute power according to slider value
        const targetMW = parseFloat(ctPowerSlider.value);
        distributePowerToUnits(ctUnits, targetMW, CT_UNIT_SIZE_MW);
    } else {
        // During game: normal startup timer
        offlineUnit.state = 'starting';
        // Convert minutes to ticks (5-minute resolution)
        offlineUnit.startupTicksRemaining = Math.ceil(CT_STARTUP_TIME_MIN / 5);
    }

    updateCTDisplay();
    updateSupplyValues(); // Update supply display immediately
    return true;
}

// CT: Shutdown a unit (if online)
function shutdownCTUnit() {
    const onlineUnit = ctUnits.find(u => u.state === 'online');
    if (!onlineUnit) return false;

    onlineUnit.state = 'offline';
    onlineUnit.outputMW = 0;
    onlineUnit.startupTicksRemaining = 0;

    updateCTDisplay();
    updateCTPowerSlider();
    updateSupplyValues(); // Update supply display and chart immediately
    return true;
}

// RNG: Commit a unit
function commitRNGUnit() {
    console.log('=== commitRNGUnit called ===');
    const offlineUnit = rngUnits.find(u => u.state === 'offline');
    if (!offlineUnit) {
        console.log('No offline unit found');
        return false;
    }

    if (!gameStarted) {
        console.log('Game not started - instant startup');
        offlineUnit.state = 'online';
        offlineUnit.outputMW = RNG_UNIT_SIZE_MW;
        offlineUnit.startupTicksRemaining = 0;
        console.log(`Unit state set to online with outputMW: ${offlineUnit.outputMW}`);

        updateRNGPowerSlider();
        const targetMW = parseFloat(rngPowerSlider.value);
        console.log(`Slider value after update: ${targetMW}`);

        distributePowerToUnits(rngUnits, targetMW, RNG_UNIT_SIZE_MW);
        console.log(`After distributePowerToUnits, total online MW: ${getTotalOnlineMW(rngUnits)}`);
    } else {
        offlineUnit.state = 'starting';
        offlineUnit.startupTicksRemaining = Math.ceil(RNG_STARTUP_TIME_MIN / 5);
    }

    console.log('Calling updateRNGDisplay...');
    updateRNGDisplay();
    console.log('Calling updateSupplyValues...');
    updateSupplyValues();
    console.log('=== commitRNGUnit complete ===\n');
    return true;
}

// RNG: Shutdown a unit
function shutdownRNGUnit() {
    const onlineUnit = rngUnits.find(u => u.state === 'online');
    if (!onlineUnit) return false;

    onlineUnit.state = 'offline';
    onlineUnit.outputMW = 0;
    onlineUnit.startupTicksRemaining = 0;

    updateRNGPowerSlider();
    // Redistribute power among remaining online units
    const targetMW = parseFloat(rngPowerSlider.value);
    distributePowerToUnits(rngUnits, targetMW, RNG_UNIT_SIZE_MW);

    updateRNGDisplay();
    updateSupplyValues();
    return true;
}

// Hydrogen: Commit a unit
function commitHydrogenUnit() {
    const offlineUnit = hydrogenUnits.find(u => u.state === 'offline');
    if (!offlineUnit) return false;

    if (!gameStarted) {
        offlineUnit.state = 'online';
        offlineUnit.outputMW = HYDROGEN_UNIT_SIZE_MW;
        offlineUnit.startupTicksRemaining = 0;
        updateHydrogenPowerSlider();
        const targetMW = parseFloat(hydrogenPowerSlider.value);
        distributePowerToUnits(hydrogenUnits, targetMW, HYDROGEN_UNIT_SIZE_MW);
    } else {
        offlineUnit.state = 'starting';
        offlineUnit.startupTicksRemaining = Math.ceil(HYDROGEN_STARTUP_TIME_MIN / 5);
    }

    updateHydrogenDisplay();
    updateSupplyValues();
    return true;
}

// Hydrogen: Shutdown a unit
function shutdownHydrogenUnit() {
    const onlineUnit = hydrogenUnits.find(u => u.state === 'online');
    if (!onlineUnit) return false;

    onlineUnit.state = 'offline';
    onlineUnit.outputMW = 0;
    onlineUnit.startupTicksRemaining = 0;

    updateHydrogenPowerSlider();
    // Redistribute power among remaining online units
    const targetMW = parseFloat(hydrogenPowerSlider.value);
    distributePowerToUnits(hydrogenUnits, targetMW, HYDROGEN_UNIT_SIZE_MW);

    updateHydrogenDisplay();
    updateSupplyValues();
    return true;
}

// Process startup timers and bring units online
function processStartupTimers() {
    // Process CCGT units
    ccgtUnits.forEach(unit => {
        if (unit.state === 'starting') {
            unit.startupTicksRemaining--;
            if (unit.startupTicksRemaining <= 0) {
                unit.state = 'online';
                // Bring unit online at minimum stable load
                unit.outputMW = CCGT_UNIT_SIZE_MW * CCGT_MIN_LOAD_PERCENT;
            }
        }
    });

    // Process CT units
    ctUnits.forEach(unit => {
        if (unit.state === 'starting') {
            unit.startupTicksRemaining--;
            if (unit.startupTicksRemaining <= 0) {
                unit.state = 'online';
                // CT can start at 0 MW
                unit.outputMW = 0;
            }
        }
    });

    // Process RNG units
    rngUnits.forEach(unit => {
        if (unit.state === 'starting') {
            unit.startupTicksRemaining--;
            if (unit.startupTicksRemaining <= 0) {
                unit.state = 'online';
                // Bring unit online at minimum stable load
                unit.outputMW = RNG_UNIT_SIZE_MW * RNG_MIN_LOAD_PERCENT;
            }
        }
    });

    // Process Hydrogen units
    hydrogenUnits.forEach(unit => {
        if (unit.state === 'starting') {
            unit.startupTicksRemaining--;
            if (unit.startupTicksRemaining <= 0) {
                unit.state = 'online';
                // Bring unit online at minimum stable load
                unit.outputMW = HYDROGEN_UNIT_SIZE_MW * HYDROGEN_MIN_LOAD_PERCENT;
            }
        }
    });

    updateCCGTDisplay();
    updateCCGTPowerSlider();
    updateCTDisplay();
    updateCTPowerSlider();
    updateRNGDisplay();
    updateRNGPowerSlider();
    updateHydrogenDisplay();
    updateHydrogenPowerSlider();

    // Distribute power according to slider values for newly online units
    const ccgtTargetMW = parseFloat(ccgtPowerSlider.value);
    distributePowerToUnits(ccgtUnits, ccgtTargetMW, CCGT_UNIT_SIZE_MW);

    const ctTargetMW = parseFloat(ctPowerSlider.value);
    distributePowerToUnits(ctUnits, ctTargetMW, CT_UNIT_SIZE_MW);

    const rngTargetMW = parseFloat(rngPowerSlider.value);
    distributePowerToUnits(rngUnits, rngTargetMW, RNG_UNIT_SIZE_MW);

    const hydrogenTargetMW = parseFloat(hydrogenPowerSlider.value);
    distributePowerToUnits(hydrogenUnits, hydrogenTargetMW, HYDROGEN_UNIT_SIZE_MW);
}

// Update CCGT display
function updateCCGTDisplay() {
    const counts = getUnitCounts(ccgtUnits);
    const totalMW = getTotalOnlineMW(ccgtUnits);

    ccgtOnlineCount.textContent = counts.online;
    ccgtOnlineMW.textContent = Math.round(totalMW);
    ccgtStartingCount.textContent = counts.starting;
    ccgtOutputDisplay.textContent = `${Math.round(totalMW)} MW`;

    // Update countdown for next unit coming online
    const minutesRemaining = getNextUnitCountdown(ccgtUnits);
    if (minutesRemaining !== null) {
        ccgtNextOnline.textContent = `Next: ${minutesRemaining} min`;
    } else {
        ccgtNextOnline.textContent = '';
    }

    // Enable/disable buttons
    ccgtCommitBtn.disabled = counts.offline === 0;
    ccgtShutdownBtn.disabled = counts.online === 0;
}

// Update CT display
function updateCTDisplay() {
    const counts = getUnitCounts(ctUnits);
    const totalMW = getTotalOnlineMW(ctUnits);

    ctOnlineCount.textContent = counts.online;
    ctOnlineMW.textContent = Math.round(totalMW);
    ctStartingCount.textContent = counts.starting;
    ctOutputDisplay.textContent = `${Math.round(totalMW)} MW`;

    // Update countdown for next unit coming online
    const minutesRemaining = getNextUnitCountdown(ctUnits);
    if (minutesRemaining !== null) {
        ctNextOnline.textContent = `Next: ${minutesRemaining} min`;
    } else {
        ctNextOnline.textContent = '';
    }

    // Enable/disable buttons
    ctCommitBtn.disabled = counts.offline === 0;
    ctShutdownBtn.disabled = counts.online === 0;
}

// Update CCGT power slider range based on online units
function updateCCGTPowerSlider() {
    // At Hour 0 (before game starts), no minimum load requirement
    const minLoadPercent = gameStarted ? CCGT_MIN_LOAD_PERCENT : 0;
    const capacity = getOnlineCapacity(ccgtUnits, CCGT_UNIT_SIZE_MW, minLoadPercent);

    ccgtPowerSlider.min = Math.round(capacity.minMW);
    ccgtPowerSlider.max = Math.round(capacity.maxMW);
    // Set slider to max when units are committed, or current total if already adjusted
    ccgtPowerSlider.value = Math.round(capacity.maxMW);
    ccgtPowerSlider.disabled = capacity.onlineCount === 0;
}

// Update CT power slider range based on online units
function updateCTPowerSlider() {
    // At Hour 0 (before game starts), no minimum load requirement
    const minLoadPercent = gameStarted ? CT_MIN_LOAD_PERCENT : 0;
    const capacity = getOnlineCapacity(ctUnits, CT_UNIT_SIZE_MW, minLoadPercent);

    ctPowerSlider.min = Math.round(capacity.minMW);
    ctPowerSlider.max = Math.round(capacity.maxMW);
    // Set slider to max when units are committed, or current total if already adjusted
    ctPowerSlider.value = Math.round(capacity.maxMW);
    ctPowerSlider.disabled = capacity.onlineCount === 0;
}

// Update RNG display
function updateRNGDisplay() {
    console.log('--- updateRNGDisplay called ---');
    const counts = getUnitCounts(rngUnits);
    const totalMW = getTotalOnlineMW(rngUnits);
    console.log(`RNG counts: online=${counts.online}, starting=${counts.starting}, offline=${counts.offline}`);
    console.log(`RNG totalMW: ${totalMW}`);

    rngOnlineCount.textContent = counts.online;
    rngOnlineMW.textContent = Math.round(getTotalOnlineMW(rngUnits.filter(u => u.state === 'online')));
    rngStartingCount.textContent = counts.starting;
    rngOutputDisplay.textContent = `${Math.round(totalMW)} MW`;
    console.log(`Set rngOutputDisplay to: "${Math.round(totalMW)} MW"`);

    const minutesRemaining = getNextUnitCountdown(rngUnits);
    if (minutesRemaining !== null) {
        rngNextOnline.textContent = `Next: ${minutesRemaining} min`;
    } else {
        rngNextOnline.textContent = '';
    }

    rngCommitBtn.disabled = counts.offline === 0;
    rngShutdownBtn.disabled = counts.online === 0;
    console.log('--- updateRNGDisplay complete ---');
}

// Update RNG power slider range based on online units
function updateRNGPowerSlider() {
    const onlineCount = rngUnits.filter(u => u.state === 'online').length;
    const totalInstalledCapacityMW = capacities.rng || 0;

    if (onlineCount === 0) {
        rngPowerSlider.min = 0;
        rngPowerSlider.max = 0;
        rngPowerSlider.value = 0;
        rngPowerSlider.disabled = true;
        return;
    }

    // At Hour 0 (before game starts), no minimum load requirement
    const minLoadPercent = gameStarted ? RNG_MIN_LOAD_PERCENT : 0;

    // Cumulative min: previous units at full + newest unit at min load
    const minMW = (onlineCount - 1 + minLoadPercent) * RNG_UNIT_SIZE_MW;

    // Cumulative max: sum of all online units (handle fractional last unit)
    const fractionalAmount = totalInstalledCapacityMW % RNG_UNIT_SIZE_MW;
    let maxMW;

    if (fractionalAmount > 0 && onlineCount === RNG_MAX_UNITS) {
        // Last unit is fractional and it's online
        maxMW = (onlineCount - 1) * RNG_UNIT_SIZE_MW + fractionalAmount;
    } else {
        // All online units are full size
        maxMW = onlineCount * RNG_UNIT_SIZE_MW;
    }

    rngPowerSlider.min = Math.round(minMW);
    rngPowerSlider.max = Math.round(maxMW);
    rngPowerSlider.value = Math.round(maxMW);
    rngPowerSlider.disabled = false;
}

// Update Hydrogen display
function updateHydrogenDisplay() {
    const counts = getUnitCounts(hydrogenUnits);
    const totalMW = getTotalOnlineMW(hydrogenUnits);

    hydrogenOnlineCount.textContent = counts.online;
    hydrogenOnlineMW.textContent = Math.round(getTotalOnlineMW(hydrogenUnits.filter(u => u.state === 'online')));
    hydrogenStartingCount.textContent = counts.starting;
    hydrogenOutputDisplay.textContent = `${Math.round(totalMW)} MW`;

    const minutesRemaining = getNextUnitCountdown(hydrogenUnits);
    if (minutesRemaining !== null) {
        hydrogenNextOnline.textContent = `Next: ${minutesRemaining} min`;
    } else {
        hydrogenNextOnline.textContent = '';
    }

    hydrogenCommitBtn.disabled = counts.offline === 0;
    hydrogenShutdownBtn.disabled = counts.online === 0;
}

// Update Hydrogen power slider range based on online units
function updateHydrogenPowerSlider() {
    const onlineCount = hydrogenUnits.filter(u => u.state === 'online').length;
    const totalInstalledCapacityMW = capacities.hydrogen || 0;

    if (onlineCount === 0) {
        hydrogenPowerSlider.min = 0;
        hydrogenPowerSlider.max = 0;
        hydrogenPowerSlider.value = 0;
        hydrogenPowerSlider.disabled = true;
        return;
    }

    // At Hour 0 (before game starts), no minimum load requirement
    const minLoadPercent = gameStarted ? HYDROGEN_MIN_LOAD_PERCENT : 0;

    // Cumulative min: previous units at full + newest unit at min load
    const minMW = (onlineCount - 1 + minLoadPercent) * HYDROGEN_UNIT_SIZE_MW;

    // Cumulative max: sum of all online units (handle fractional last unit)
    const fractionalAmount = totalInstalledCapacityMW % HYDROGEN_UNIT_SIZE_MW;
    let maxMW;

    if (fractionalAmount > 0 && onlineCount === HYDROGEN_MAX_UNITS) {
        // Last unit is fractional and it's online
        maxMW = (onlineCount - 1) * HYDROGEN_UNIT_SIZE_MW + fractionalAmount;
    } else {
        // All online units are full size
        maxMW = onlineCount * HYDROGEN_UNIT_SIZE_MW;
    }

    hydrogenPowerSlider.min = Math.round(minMW);
    hydrogenPowerSlider.max = Math.round(maxMW);
    hydrogenPowerSlider.value = Math.round(maxMW);
    hydrogenPowerSlider.disabled = false;
}

// Distribute target power across online units
function distributePowerToUnits(units, targetMW, unitSize) {
    const onlineUnits = units.filter(u => u.state === 'online');
    if (onlineUnits.length === 0) return;

    // Sequential fill: fill units to their max capacity before moving to next unit
    // This properly handles fractional units (e.g., 356 MW = 100+100+100+56)
    let remainingMW = targetMW;

    for (let i = 0; i < onlineUnits.length; i++) {
        const unit = onlineUnits[i];
        const unitCapacity = Math.min(unitSize, remainingMW);
        unit.outputMW = unitCapacity;
        remainingMW -= unitCapacity;

        if (remainingMW <= 0) {
            // Fill any remaining units with 0
            for (let j = i + 1; j < onlineUnits.length; j++) {
                onlineUnits[j].outputMW = 0;
            }
            break;
        }
    }
}

// --- 3. GENERATE FORECAST DATA FROM SEASONAL PROFILE ---
// Helper function: Cubic Hermite spline interpolation (smooth curves)
// This creates smooth, natural-looking curves between hourly points
function cubicInterpolate(p0, p1, p2, p3, t) {
    // Catmull-Rom spline: uses 4 points to create smooth curve between p1 and p2
    // t is the fraction between p1 and p2 (0 to 1)
    const t2 = t * t;
    const t3 = t2 * t;

    // Catmull-Rom coefficients (tension = 0.5 for balanced smoothness)
    const v0 = (p2 - p0) * 0.5;
    const v1 = (p3 - p1) * 0.5;

    return (2 * p1 - 2 * p2 + v0 + v1) * t3 +
           (-3 * p1 + 3 * p2 - 2 * v0 - v1) * t2 +
           v0 * t + p1;
}

// Helper function: Generate smooth interpolation for array of hourly values
// Returns array with 288 values (24 hours * 12 five-minute intervals)
function smoothInterpolate(hourlyValues) {
    const result = [];
    const n = hourlyValues.length; // Should be 24

    // Find min and max values for clamping (prevent overshoot)
    const minValue = Math.min(...hourlyValues);
    const maxValue = Math.max(...hourlyValues);

    for (let hour = 0; hour < 24; hour++) {
        // Get 4 points for cubic interpolation (wrap around for edges)
        const p0 = hourlyValues[(hour - 1 + n) % n];
        const p1 = hourlyValues[hour];
        const p2 = hourlyValues[(hour + 1) % n];
        const p3 = hourlyValues[(hour + 2) % n];

        // Generate 12 five-minute intervals within this hour
        for (let interval = 0; interval < 12; interval++) {
            const t = interval / 12; // Fraction within the hour (0 to 11/12)
            let value = cubicInterpolate(p0, p1, p2, p3, t);

            // Clamp to prevent overshoot (especially important for capacity factors)
            // Allow slight overshoot for smoother curves, but prevent negative values
            value = Math.max(0, Math.min(maxValue * 1.05, value));

            result.push(value);
        }
    }

    return result;
}

// Helper function: Random walk for demand constrained around smooth curve
function generateRandomWalkDemand(hourlyDemands, peakMW) {
    const fiveMinDemands = [];
    const maxStepMW = 50; // Maximum ±50 MW per 5-minute step
    const maxDeviationFromCurve = 200; // Maximum ±200 MW from smooth curve

    // First, generate smooth baseline curve using cubic interpolation
    const smoothBaseline = smoothInterpolate(hourlyDemands);

    // Start at first hour value
    let currentValue = hourlyDemands[0];

    // Generate random walk around the smooth baseline
    for (let i = 0; i < 288; i++) {
        const baselineValue = smoothBaseline[i];

        // Random step constrained by maxStepMW
        const randomStep = (Math.random() * 2 - 1) * maxStepMW;
        let newValue = currentValue + randomStep;

        // Constrain to stay within band around smooth baseline
        const minAllowed = baselineValue - maxDeviationFromCurve;
        const maxAllowed = baselineValue + maxDeviationFromCurve;
        newValue = Math.max(minAllowed, Math.min(maxAllowed, newValue));

        // Also ensure we don't go negative
        newValue = Math.max(0, newValue);

        fiveMinDemands.push(newValue);
        currentValue = newValue;
    }

    return fiveMinDemands;
}

// Helper function to extract hourly forecast points from 5-min data
function extractHourlyForecast(fiveMinData) {
    if (!fiveMinData || fiveMinData.length === 0) {
        console.error("extractHourlyForecast: fiveMinData is empty or undefined");
        return [];
    }

    const hourlyData = [];
    // Extract data at the start of each hour (indices 0, 12, 24, ... 276)
    for (let hour = 0; hour < 24; hour++) {
        const index = hour * 12; // Each hour has 12 five-minute intervals
        if (index >= fiveMinData.length) {
            console.error(`extractHourlyForecast: index ${index} out of bounds (length: ${fiveMinData.length})`);
            break;
        }
        hourlyData.push({
            timestamp: fiveMinData[index].timestamp,
            total_demand_mw: fiveMinData[index].total_demand_mw,
            net_demand_mw: fiveMinData[index].net_demand_mw,
            biomass_mw: fiveMinData[index].biomass_mw,
            geothermal_mw: fiveMinData[index].geothermal_mw,
            nuclear_mw: fiveMinData[index].nuclear_mw,
            wind_mw: fiveMinData[index].wind_mw,
            solar_mw: fiveMinData[index].solar_mw
        });
    }
    return hourlyData;
}

function generateForecastFromProfile(season) {
    const profile = seasonalProfilesData[selectedCountry].profiles[season];
    const peakMW = profile.peakMW;
    const hourlyPercentages = profile.hourlyPercentages;

    // Get season-specific renewable capacity factors (24 hourly values)
    const solarCF = profile.solarCF;
    const windCF = profile.windCF;
    const nuclearCF = profile.nuclearCF;
    const geothermalCF = profile.geothermalCF;
    const biomassCF = profile.biomassCF;

    const solarCapacity = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW.solar;
    const windCapacity = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW.wind;
    const nuclearCapacity = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW.nuclear;
    const geothermalCapacity = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW.geothermal;
    const biomassCapacity = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW.biomass;

    // Convert hourly percentages to MW values
    const hourlyDemandsMW = hourlyPercentages.map(pct => (pct / 100) * peakMW);

    // Generate 5-minute demand with random walk
    const fiveMinDemands = generateRandomWalkDemand(hourlyDemandsMW, peakMW);

    // Generate 5-minute capacity factors using smooth cubic interpolation
    const fiveMinSolarCF = smoothInterpolate(solarCF);
    const fiveMinWindCF = smoothInterpolate(windCF);

    const data = [];
    const today = new Date();

    // Generate 288 five-minute intervals (24 hours * 12 intervals per hour)
    for (let i = 0; i < 288; i++) {
        const hour = Math.floor(i / 12);
        const minute = (i % 12) * 5;

        // Get demand for this interval
        const totalDemandMW = fiveMinDemands[i];

        // Calculate renewable generation using interpolated capacity factors
        const solarMW = solarCapacity * fiveMinSolarCF[i];
        const windMW = windCapacity * fiveMinWindCF[i];
        const nuclearMW = nuclearCapacity * nuclearCF; // Constant
        const geothermalMW = geothermalCapacity * geothermalCF; // Constant
        const biomassMW = biomassCapacity * biomassCF; // Constant
        const totalRenewablesMW = solarMW + windMW + nuclearMW + geothermalMW + biomassMW;

        // Calculate net demand
        const netDemandMW = totalDemandMW - totalRenewablesMW;

        // Create timestamp
        const timestamp = new Date(today);
        timestamp.setHours(hour, minute, 0, 0);

        data.push({
            timestamp: timestamp.toISOString(),
            total_demand_mw: totalDemandMW,
            solar_mw: solarMW,
            wind_mw: windMW,
            nuclear_mw: nuclearMW,
            geothermal_mw: geothermalMW,
            biomass_mw: biomassMW,
            total_renewables_mw: totalRenewablesMW,
            net_demand_mw: netDemandMW
        });
    }

    return data;
}

// Function to update capacity display
function updateCapacityDisplay() {
    const capacities = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW;

    document.getElementById('solarCapacity').textContent = Math.round(capacities.solar).toLocaleString();
    document.getElementById('windCapacity').textContent = Math.round(capacities.wind).toLocaleString();
    document.getElementById('offshoreWindCapacity').textContent = Math.round(capacities.offshoreWind || 0).toLocaleString();
    document.getElementById('nuclearCapacity').textContent = Math.round(capacities.nuclear).toLocaleString();
    document.getElementById('geothermalCapacity').textContent = Math.round(capacities.geothermal).toLocaleString();
    document.getElementById('biomassCapacity').textContent = Math.round(capacities.biomass).toLocaleString();
    document.getElementById('rngCapacity').textContent = Math.round(capacities.rng || 0).toLocaleString();
    document.getElementById('hydrogenCapacity').textContent = Math.round(capacities.hydrogen || 0).toLocaleString();

    // Display battery capacity from planner data (convert GWh to MWh)
    if (plannerCapacityData && plannerCapacityData.storage) {
        const totalBatteryGWh = (plannerCapacityData.storage.battery4hr || 0) + (plannerCapacityData.storage.battery8hr || 0);
        const totalBatteryMWh = Math.round(totalBatteryGWh * 1000);
        document.getElementById('batteryCapacity').textContent = totalBatteryMWh.toLocaleString();
    } else {
        document.getElementById('batteryCapacity').textContent = '0';
    }
}

// --- 4. FETCH DATA AND INITIALIZE THE APP ---
async function initialize() {
    try {
        const response = await fetch('seasonal_profiles.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        seasonalProfilesData = await response.json();

        // Create deep copy of pristine preset data
        originalSeasonalProfilesData = JSON.parse(JSON.stringify(seasonalProfilesData));

        // Check if selected country exists in profiles, if not fall back to California profiles
        if (!seasonalProfilesData[selectedCountry]) {
            console.log(`Country '${selectedCountry}' not found in profiles, using California profiles with custom demand data`);
            selectedCountry = 'california';
        }

        // Override capacities if planner data exists
        if (plannerCapacityData && plannerCapacityData.totalCapacityMW) {
            console.log('Overriding capacities with Grid Planner data');
            const capacities = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW;

            // Update capacities from planner (already in MW)
            if (plannerCapacityData.totalCapacityMW.solar) capacities.solar = plannerCapacityData.totalCapacityMW.solar;
            if (plannerCapacityData.totalCapacityMW.wind) capacities.wind = plannerCapacityData.totalCapacityMW.wind;
            if (plannerCapacityData.totalCapacityMW.offshoreWind) capacities.offshoreWind = plannerCapacityData.totalCapacityMW.offshoreWind;
            if (plannerCapacityData.totalCapacityMW.nuclear) capacities.nuclear = plannerCapacityData.totalCapacityMW.nuclear;
            if (plannerCapacityData.totalCapacityMW.geothermal) capacities.geothermal = plannerCapacityData.totalCapacityMW.geothermal;
            if (plannerCapacityData.totalCapacityMW.biomass) capacities.biomass = plannerCapacityData.totalCapacityMW.biomass;
            if (plannerCapacityData.totalCapacityMW.rng) capacities.rng = plannerCapacityData.totalCapacityMW.rng;
            if (plannerCapacityData.totalCapacityMW.hydrogen) capacities.hydrogen = plannerCapacityData.totalCapacityMW.hydrogen;

            // Calculate dynamic max units for RNG and Hydrogen based on planner capacity
            if (plannerCapacityData.totalCapacityMW.rng && plannerCapacityData.totalCapacityMW.rng > 0) {
                RNG_MAX_UNITS = Math.ceil(plannerCapacityData.totalCapacityMW.rng / RNG_UNIT_SIZE_MW);
                console.log(`RNG capacity from planner: ${plannerCapacityData.totalCapacityMW.rng} MW, setting max units to ${RNG_MAX_UNITS}`);
            } else {
                RNG_MAX_UNITS = 0;
                console.log(`No RNG capacity from planner, setting max units to 0`);
            }
            if (plannerCapacityData.totalCapacityMW.hydrogen && plannerCapacityData.totalCapacityMW.hydrogen > 0) {
                HYDROGEN_MAX_UNITS = Math.ceil(plannerCapacityData.totalCapacityMW.hydrogen / HYDROGEN_UNIT_SIZE_MW);
                console.log(`Hydrogen capacity from planner: ${plannerCapacityData.totalCapacityMW.hydrogen} MW, setting max units to ${HYDROGEN_MAX_UNITS}`);
            } else {
                HYDROGEN_MAX_UNITS = 0;
                console.log(`No Hydrogen capacity from planner, setting max units to 0`);
            }

            // Calculate battery capacity and power from planner storage data
            if (plannerCapacityData.storage) {
                // Storage is in GWh, need to calculate power capacity (MW) and energy capacity (MWh)
                const battery4hrGWh = plannerCapacityData.storage.battery4hr || 0;
                const battery8hrGWh = plannerCapacityData.storage.battery8hr || 0;
                const longdurationGWh = plannerCapacityData.storage.longduration || 0;

                // Total energy capacity in MWh
                BATTERY_CAPACITY_MWH = (battery4hrGWh + battery8hrGWh + longdurationGWh) * 1000;

                // Power capacity = energy / duration for each storage type
                // 4-hr battery: power = energy / 4
                // 8-hr battery: power = energy / 8
                // 24-hr storage: power = energy / 24
                const power4hr = battery4hrGWh * 1000 / 4;  // GWh * 1000 / 4 = MW
                const power8hr = battery8hrGWh * 1000 / 8;
                const powerLongduration = longdurationGWh * 1000 / 24;

                BATTERY_POWER_MW = power4hr + power8hr + powerLongduration;

                console.log(`Battery from planner: ${BATTERY_CAPACITY_MWH} MWh capacity, ${BATTERY_POWER_MW} MW power`);

                // Set battery slider limits (negative for charging, positive for discharging)
                batterySlider.setAttribute('min', -BATTERY_POWER_MW);
                batterySlider.setAttribute('max', BATTERY_POWER_MW);
                batteryInput.setAttribute('min', -BATTERY_POWER_MW);
                batteryInput.setAttribute('max', BATTERY_POWER_MW);

                // Update battery display text
                document.getElementById('batteryPowerDisplay').textContent = Math.round(BATTERY_POWER_MW).toLocaleString();
                document.getElementById('batteryCapacityDisplay').textContent = Math.round(BATTERY_CAPACITY_MWH).toLocaleString();
                document.getElementById('batteryCapacityDisplaySOC').textContent = Math.round(BATTERY_CAPACITY_MWH).toLocaleString();
            }

            // Override capacity factor profiles from planner if available
            if (plannerCapacityData.solarCF || plannerCapacityData.windCF || plannerCapacityData.offshoreWindCF) {
                console.log('Overriding capacity factor profiles with Grid Planner data');
                const profiles = seasonalProfilesData[selectedCountry].profiles;

                // Apply to all seasonal profiles
                for (const seasonKey in profiles) {
                    if (plannerCapacityData.solarCF) {
                        profiles[seasonKey].solarCF = plannerCapacityData.solarCF;
                        console.log(`Updated ${seasonKey} solar CF profile`);
                    }
                    if (plannerCapacityData.windCF) {
                        profiles[seasonKey].windCF = plannerCapacityData.windCF;
                        console.log(`Updated ${seasonKey} wind CF profile`);
                    }
                    if (plannerCapacityData.offshoreWindCF) {
                        // Note: offshore wind CF not currently used in forecast generation
                        profiles[seasonKey].offshoreWindCF = plannerCapacityData.offshoreWindCF;
                        console.log(`Updated ${seasonKey} offshore wind CF profile`);
                    }
                }
            }
        }

        // Initialize unit arrays with calculated max units
        initializeUnitArrays();

        // Update max units display
        document.getElementById('rngMaxUnits').textContent = RNG_MAX_UNITS;
        document.getElementById('hydrogenMaxUnits').textContent = HYDROGEN_MAX_UNITS;

        // Set RNG and Hydrogen power slider max to match installed capacity from planner
        if (plannerCapacityData && plannerCapacityData.totalCapacityMW) {
            if (plannerCapacityData.totalCapacityMW.rng && plannerCapacityData.totalCapacityMW.rng > 0) {
                const rngCapacityMW = plannerCapacityData.totalCapacityMW.rng;
                rngPowerSlider.setAttribute('max', rngCapacityMW);
                rngPowerSlider.disabled = false;
                document.querySelector('[data-action="commit_rng"]').disabled = false;
                document.querySelector('[data-action="shutdown_rng"]').disabled = false;
                console.log(`Set RNG power slider max to ${rngCapacityMW} MW`);
            } else {
                rngPowerSlider.setAttribute('max', 0);
                rngPowerSlider.value = 0;
                rngPowerSlider.disabled = true;
                document.querySelector('[data-action="commit_rng"]').disabled = true;
                document.querySelector('[data-action="shutdown_rng"]').disabled = true;
                rngCommitBtn.disabled = true;
                rngShutdownBtn.disabled = true;
                console.log(`No RNG capacity, disabling RNG controls`);
            }
            if (plannerCapacityData.totalCapacityMW.hydrogen && plannerCapacityData.totalCapacityMW.hydrogen > 0) {
                const hydrogenCapacityMW = plannerCapacityData.totalCapacityMW.hydrogen;
                hydrogenPowerSlider.setAttribute('max', hydrogenCapacityMW);
                hydrogenPowerSlider.disabled = false;
                document.querySelector('[data-action="commit_hydrogen"]').disabled = false;
                document.querySelector('[data-action="shutdown_hydrogen"]').disabled = false;
                console.log(`Set Hydrogen power slider max to ${hydrogenCapacityMW} MW`);
            } else {
                hydrogenPowerSlider.setAttribute('max', 0);
                hydrogenPowerSlider.value = 0;
                hydrogenPowerSlider.disabled = true;
                document.querySelector('[data-action="commit_hydrogen"]').disabled = true;
                document.querySelector('[data-action="shutdown_hydrogen"]').disabled = true;
                hydrogenCommitBtn.disabled = true;
                hydrogenShutdownBtn.disabled = true;
                console.log(`No Hydrogen capacity, disabling Hydrogen controls`);
            }
        }

        // Update capacity display
        updateCapacityDisplay();

        // Hide CCGT/CT generators if natural gas generation is 0% in planner
        if (plannerCapacityData && plannerCapacityData.dailyGenerationPercent) {
            const naturalGasGeneration = plannerCapacityData.dailyGenerationPercent.naturalGas || 0;
            if (naturalGasGeneration === 0) {
                console.log('Hiding CCGT and CT generators (natural gas generation is 0%)');
                // Hide CCGT controls
                const ccgtContainer = document.querySelector('.p-4.bg-blue-50.rounded-lg');
                if (ccgtContainer && ccgtContainer.textContent.includes('CCGT')) {
                    ccgtContainer.style.display = 'none';
                }
                // Hide CT controls
                const ctContainer = document.querySelector('.p-4.bg-orange-50.rounded-lg');
                if (ctContainer && ctContainer.textContent.includes('CT Peakers')) {
                    ctContainer.style.display = 'none';
                }
            }
        }

        // Load demand profile from planner data if available
        if (plannerCapacityData && plannerCapacityData.demandProfile) {
            const plannerProfile = plannerCapacityData.demandProfile;
            console.log(`Loading demand profile from planner: ${plannerProfile}`);
            // Convert planner naming to tester naming if necessary
            // Planner uses: "Spring Typical", "Winter High", etc.
            // Tester uses: "spring-typical", "winter-high", etc.
            const normalizedProfile = plannerProfile.toLowerCase().replace(' ', '-');

            // If all seasonal demands are provided (for non-California countries), populate all season presets
            if (plannerCapacityData.allSeasonalDemands &&
                Object.keys(plannerCapacityData.allSeasonalDemands).length > 0 &&
                selectedCountryDisplayName !== 'California') {
                console.log(`Creating all seasonal profiles for ${selectedCountryDisplayName} with planner demand data`);

                // Create profiles for all seasons provided by the planner
                for (const [seasonKey, demandDataMW] of Object.entries(plannerCapacityData.allSeasonalDemands)) {
                    if (demandDataMW && demandDataMW.length === 24) {
                        const peakMW = Math.max(...demandDataMW);
                        const hourlyPercentages = demandDataMW.map(mw => (mw / peakMW) * 100);

                        // Use the closest matching California season's CF profiles as base
                        const baseSeason = seasonKey.includes('spring') ? 'spring-typical' :
                                           seasonKey.includes('summer') ? 'summer-typical' :
                                           seasonKey.includes('fall') ? 'fall-typical' :
                                           seasonKey.includes('winter') ? 'winter-typical' : 'spring-typical';

                        const baseProfile = seasonalProfilesData[selectedCountry].profiles[baseSeason];

                        // Create profile with country-specific demand but California CF patterns
                        seasonalProfilesData[selectedCountry].profiles[seasonKey] = {
                            name: seasonKey.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
                            peakMW: peakMW,
                            hourlyPercentages: hourlyPercentages,
                            solarCF: baseProfile.solarCF,
                            windCF: baseProfile.windCF,
                            nuclearCF: baseProfile.nuclearCF,
                            geothermalCF: baseProfile.geothermalCF,
                            biomassCF: baseProfile.biomassCF,
                            seasonalMultipliers: baseProfile.seasonalMultipliers
                        };

                        console.log(`Created profile '${seasonKey}' with peak ${peakMW.toFixed(0)} MW`);
                    }
                }

                // Update the pristine copy to include these new profiles
                originalSeasonalProfilesData[selectedCountry] = JSON.parse(JSON.stringify(seasonalProfilesData[selectedCountry]));

                // Set current season to the one from planner
                if (seasonalProfilesData[selectedCountry].profiles[normalizedProfile]) {
                    currentSeason = normalizedProfile;
                    console.log(`Set current season to: ${currentSeason}`);
                } else {
                    console.warn(`Profile ${normalizedProfile} not created, using spring-typical`);
                    currentSeason = 'spring-typical';
                }
            } else if (seasonalProfilesData[selectedCountry].profiles[normalizedProfile]) {
                // For California or when no seasonal demands data, use preset profile
                currentSeason = normalizedProfile;
                console.log(`Set current season to: ${currentSeason}`);
            } else {
                console.warn(`Profile ${normalizedProfile} not found and no seasonal demand data provided, using default`);
            }
        }

        loadSeasonalProfile(currentSeason);
        updateLoadProfileDisplay();

        createChart();
        createCFChart();
        createDeltaHistoryChart();

        // Start/Pause/Reset button handler
        startButton.addEventListener('click', () => {
            if (startButton.textContent === 'Reset') {
                resetGame();
            } else if (!gameStarted) {
                startGame();
            } else if (!gamePaused) {
                pauseGame();
            }
        });

        // Resume and Restart button handlers
        resumeButton.addEventListener('click', resumeGame);
        restartButton.addEventListener('click', resetGame);

        // Show Schedule button handler
        showScheduleBtn.addEventListener('click', () => {
            schedulerModal.classList.remove('hidden');
            if (!schedulerChart) {
                createSchedulerChart();
            }
            updateSchedulerChart();
        });

        // End game button handlers
        newGameButton.addEventListener('click', () => {
            // Clear schedule and reset game
            scheduledEvents = [];
            resetGame();
        });

        retryWithScheduleButton.addEventListener('click', () => {
            // Keep schedule and reset game
            resetGame();
        });

        // Battery, Hydro, and Curtailment slider event listeners
        batterySlider.addEventListener('input', updateSupplyValues);
        hydroSlider.addEventListener('input', updateSupplyValues);
        solarCurtailmentSlider.addEventListener('input', updateSupplyValues);
        windCurtailmentSlider.addEventListener('input', updateSupplyValues);

        // Battery and Hydro input field event listeners
        batteryInput.addEventListener('input', () => {
            const value = parseFloat(batteryInput.value) || 0;
            const clamped = Math.max(-13000, Math.min(13000, value));
            batterySlider.value = clamped;
            updateSupplyValues();
        });
        hydroInput.addEventListener('input', () => {
            const value = parseFloat(hydroInput.value) || 0;
            const clamped = Math.max(0, Math.min(currentHydroMaxMW, value));
            hydroSlider.value = clamped;
            updateSupplyValues();
        });
        solarCurtailmentInput.addEventListener('input', () => {
            const value = parseFloat(solarCurtailmentInput.value) || 0;
            const maxCurtailment = parseFloat(solarCurtailmentSlider.max);
            const clamped = Math.max(0, Math.min(maxCurtailment, value));
            solarCurtailmentSlider.value = clamped;
            updateSupplyValues();
        });
        windCurtailmentInput.addEventListener('input', () => {
            const value = parseFloat(windCurtailmentInput.value) || 0;
            const maxCurtailment = parseFloat(windCurtailmentSlider.max);
            const clamped = Math.max(0, Math.min(maxCurtailment, value));
            windCurtailmentSlider.value = clamped;
            updateSupplyValues();
        });

        // CCGT unit dispatch button listeners
        ccgtCommitBtn.addEventListener('click', commitCCGTUnit);
        ccgtShutdownBtn.addEventListener('click', shutdownCCGTUnit);
        ccgtPowerSlider.addEventListener('input', () => {
            const targetMW = parseFloat(ccgtPowerSlider.value);
            distributePowerToUnits(ccgtUnits, targetMW, CCGT_UNIT_SIZE_MW);
            updateCCGTDisplay();
            updateSupplyValues(); // Update supply display and chart
        });

        // CT unit dispatch button listeners
        ctCommitBtn.addEventListener('click', commitCTUnit);
        ctShutdownBtn.addEventListener('click', shutdownCTUnit);
        ctPowerSlider.addEventListener('input', () => {
            const targetMW = parseFloat(ctPowerSlider.value);
            distributePowerToUnits(ctUnits, targetMW, CT_UNIT_SIZE_MW);
            updateCTDisplay();
            updateSupplyValues(); // Update supply display and chart
        });

        // RNG unit dispatch button listeners
        rngCommitBtn.addEventListener('click', commitRNGUnit);
        rngShutdownBtn.addEventListener('click', shutdownRNGUnit);
        rngPowerSlider.addEventListener('input', () => {
            const targetMW = parseFloat(rngPowerSlider.value);
            distributePowerToUnits(rngUnits, targetMW, RNG_UNIT_SIZE_MW);
            updateRNGDisplay();
            updateSupplyValues();
        });

        // Hydrogen unit dispatch button listeners
        hydrogenCommitBtn.addEventListener('click', commitHydrogenUnit);
        hydrogenShutdownBtn.addEventListener('click', shutdownHydrogenUnit);
        hydrogenPowerSlider.addEventListener('input', () => {
            const targetMW = parseFloat(hydrogenPowerSlider.value);
            distributePowerToUnits(hydrogenUnits, targetMW, HYDROGEN_UNIT_SIZE_MW);
            updateHydrogenDisplay();
            updateSupplyValues();
        });

        // Load Profile edit controls
        editProfileButton.addEventListener('click', enterEditMode);
        confirmEditButton.addEventListener('click', confirmEdit);
        revertEditButton.addEventListener('click', revertEdit);

        // Load Profile preset buttons
        document.getElementById('preset-load-spring-typical').addEventListener('click', () => applyLoadSeasonPreset('spring-typical'));
        document.getElementById('preset-load-spring-high').addEventListener('click', () => applyLoadSeasonPreset('spring-high'));
        document.getElementById('preset-load-summer-typical').addEventListener('click', () => applyLoadSeasonPreset('summer-typical'));
        document.getElementById('preset-load-summer-high').addEventListener('click', () => applyLoadSeasonPreset('summer-high'));
        document.getElementById('preset-load-fall-typical').addEventListener('click', () => applyLoadSeasonPreset('fall-typical'));
        document.getElementById('preset-load-fall-high').addEventListener('click', () => applyLoadSeasonPreset('fall-high'));
        document.getElementById('preset-load-winter-typical').addEventListener('click', () => applyLoadSeasonPreset('winter-typical'));
        document.getElementById('preset-load-winter-high').addEventListener('click', () => applyLoadSeasonPreset('winter-high'));

        // CF Chart event listeners
        editCFBtn.addEventListener('click', enterCFEditMode);
        confirmCFBtn.addEventListener('click', confirmCFEdit);
        revertCFBtn.addEventListener('click', revertCFEdit);

        // CF Preset buttons
        document.getElementById('preset-cf-spring-typical').addEventListener('click', () => applyCFSeasonPreset('spring-typical'));
        document.getElementById('preset-cf-spring-high').addEventListener('click', () => applyCFSeasonPreset('spring-high'));
        document.getElementById('preset-cf-summer-typical').addEventListener('click', () => applyCFSeasonPreset('summer-typical'));
        document.getElementById('preset-cf-summer-high').addEventListener('click', () => applyCFSeasonPreset('summer-high'));
        document.getElementById('preset-cf-fall-typical').addEventListener('click', () => applyCFSeasonPreset('fall-typical'));
        document.getElementById('preset-cf-fall-high').addEventListener('click', () => applyCFSeasonPreset('fall-high'));
        document.getElementById('preset-cf-winter-typical').addEventListener('click', () => applyCFSeasonPreset('winter-typical'));
        document.getElementById('preset-cf-winter-high').addEventListener('click', () => applyCFSeasonPreset('winter-high'));

        // Enable controls before game starts
        batterySlider.disabled = false;
        batteryInput.disabled = false;
        hydroSlider.disabled = false;
        hydroInput.disabled = false;
        solarCurtailmentSlider.disabled = false;
        solarCurtailmentInput.disabled = false;
        windCurtailmentSlider.disabled = false;
        windCurtailmentInput.disabled = false;
        ccgtCommitBtn.disabled = false;
        ctCommitBtn.disabled = false;
        rngCommitBtn.disabled = false;
        hydrogenCommitBtn.disabled = false;

        // Initialize unit displays
        updateCCGTDisplay();
        updateCTDisplay();
        updateRNGDisplay();
        updateHydrogenDisplay();

        // Hydro condition dropdown listener
        hydroCondition.addEventListener('change', updateHydroCapacity);

        // Hydrogen fuel cost dropdown listener
        hydrogenFuelCost.addEventListener('change', updateHydrogenCost);

        const speedSteps = [0.1, 1, 5, 10, 20, 30];
        const gameSpeedSlider = document.getElementById("gameSpeedSlider");
        const gameSpeedTime = document.getElementById("gameSpeedTime");
        const defaultIndex = 2;
        gameSpeedSlider.value = defaultIndex;
        gameSpeed = speedSteps[defaultIndex];
        gameSpeedTime.textContent = gameSpeed.toFixed(1);        
        gameSpeedSlider.addEventListener("input", function () {
            const index = parseInt(this.value);
            const selectedSpeed = speedSteps[index];
            gameSpeed = selectedSpeed;
            gameSpeedTime.textContent = selectedSpeed.toFixed(1);
        
            if (gameStarted && !gamePaused) {
                clearInterval(gameInterval);
                gameInterval = setInterval(gameLoop, gameSpeed * 1000);
            }
        });
        
        // Documentation button listener
        documentationBtn.addEventListener('click', () => {
            window.open('operator-documentation.html', '_blank');
        });

        // Initialize hydro capacity based on default dropdown value
        updateHydroCapacity();

        // Show initial demand for tick 0
        showInitialDemand();
    } catch (e) {
        console.error("Failed to initialize game:", e);
        console.error("Error stack:", e.stack);
        console.error("Error message:", e.message);
        alert("Failed to load game data. Error: " + e.message + "\nCheck the console for details.");
    }
}

// Update curtailment slider ranges based on current solar/wind generation
function updateCurtailmentRanges(tick = 0) {
    if (forecastData.length === 0) return;

    const currentData = forecastData[tick];
    const maxSolarCurtailment = Math.max(0, Math.round(currentData.solar_mw));
    const maxWindCurtailment = Math.max(0, Math.round(currentData.wind_mw));

    // Format the time for the current tick
    const hour = Math.floor(tick / 12);
    const minute = (tick % 12) * 5;
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    const timeString = `${displayHour}:${minute.toString().padStart(2, '0')} ${period}`;

    // Update solar curtailment slider
    solarCurtailmentSlider.max = maxSolarCurtailment;
    solarCurtailmentInput.max = maxSolarCurtailment;
    solarCurtailmentMaxDisplay.textContent = `Max: ${maxSolarCurtailment.toLocaleString()} MW (at ${timeString})`;

    // Clamp current value if it exceeds new max
    const currentSolarCurtailment = parseFloat(solarCurtailmentSlider.value);
    if (currentSolarCurtailment > maxSolarCurtailment) {
        solarCurtailmentSlider.value = maxSolarCurtailment;
        solarCurtailmentInput.value = maxSolarCurtailment;
    }

    // Update wind curtailment slider
    windCurtailmentSlider.max = maxWindCurtailment;
    windCurtailmentInput.max = maxWindCurtailment;
    windCurtailmentMaxDisplay.textContent = `Max: ${maxWindCurtailment.toLocaleString()} MW (at ${timeString})`;

    // Clamp current value if it exceeds new max
    const currentWindCurtailment = parseFloat(windCurtailmentSlider.value);
    if (currentWindCurtailment > maxWindCurtailment) {
        windCurtailmentSlider.value = maxWindCurtailment;
        windCurtailmentInput.value = maxWindCurtailment;
    }
}

// Show initial demand before game starts
function showInitialDemand() {
    if (forecastData.length > 0) {
        const initialNetDemand = forecastData[0].net_demand_mw;
        demandValueSpan.textContent = Math.round(initialNetDemand);

        // Update curtailment ranges for tick 0
        updateCurtailmentRanges(0);

        // Update delta based on current supply (units + battery + hydro)
        const totalSupply = parseFloat(batterySlider.value) + getTotalOnlineMW(ccgtUnits) +
                           getTotalOnlineMW(ctUnits) + parseFloat(hydroSlider.value);
        const delta = totalSupply - initialNetDemand;
        deltaValueSpan.textContent = Math.round(delta);

        // Color code the delta
        const deltaElement = deltaValueSpan.parentElement;
        const absDelta = Math.abs(delta);
        if (absDelta < 500) {
            deltaElement.className = 'text-2xl font-bold text-green-600';
        } else if (absDelta < 1000) {
            deltaElement.className = 'text-2xl font-bold text-yellow-600';
        } else {
            deltaElement.className = 'text-2xl font-bold text-red-600';
        }

        // Enable/disable Start button based on grid stability
        // Grid is stable if delta is within ±500 MW (green zone)
        if (!gameStarted) {
            if (absDelta < 500) {
                startButton.disabled = false;
                startButton.classList.remove('bg-gray-400', 'cursor-not-allowed');
                startButton.classList.add('bg-gradient-to-r', 'from-blue-600', 'to-purple-600', 'hover:from-blue-700', 'hover:to-purple-700');
                startButton.removeAttribute('title'); // Remove tooltip when enabled
            } else {
                startButton.disabled = true;
                startButton.classList.add('bg-gray-400', 'cursor-not-allowed');
                startButton.classList.remove('bg-gradient-to-r', 'from-blue-600', 'to-purple-600', 'hover:from-blue-700', 'hover:to-purple-700');
                startButton.setAttribute('title', 'Match the Net Demand with Generation at 12:00 AM to start the game.'); // Show tooltip when disabled
            }
        }

        // Update gauges (delta and frequency) during pre-game
        updateGauges(delta, totalSupply);
    }
}

// --- 5. LOAD SEASONAL PROFILE ---
function loadSeasonalProfile(season) {
    forecastData = generateForecastFromProfile(season);
    hourlyForecastData = extractHourlyForecast(forecastData);

    if (myChart) {
        updateChartData();
    }
}

// --- HELPER: Calculate minimum demand based on inflexible baseload ---
function calculateMinimumDemandMW() {
    const INFLEXIBLE_SOURCES = ['nuclear', 'geothermal', 'biomass', 'rng', 'hydrogen'];
    const capacities = seasonalProfilesData[selectedCountry].renewables.installedCapacityMW;

    let minDemandMW = 0;
    INFLEXIBLE_SOURCES.forEach(tech => {
        const capacity = capacities[tech] || 0;
        // Approximate capacity factors for inflexible sources
        const cf = tech === 'nuclear' ? 0.9 :
                   tech === 'geothermal' ? 0.9 :
                   tech === 'biomass' ? 0.8 :
                   tech === 'rng' ? 0.85 :
                   tech === 'hydrogen' ? 0.2 : 0.9;
        minDemandMW += capacity * cf;
    });

    return minDemandMW;
}

// --- 6. CREATE THE CHART ---
function createChart() {
    // Ensure hourlyForecastData exists before creating chart
    if (!hourlyForecastData || hourlyForecastData.length === 0) {
        console.error("Cannot create chart: hourlyForecastData is empty");
        throw new Error("No forecast data available");
    }

    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: forecastData.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })),
            datasets: [
                {
                    label: 'Biomass',
                    type: 'line',
                    data: forecastData.map(d => d.biomass_mw),
                    borderColor: 'rgba(101, 67, 33, 1)',
                    backgroundColor: 'rgba(101, 67, 33, 0.6)',
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 5
                },
                {
                    label: 'Geothermal',
                    type: 'line',
                    data: forecastData.map(d => d.geothermal_mw),
                    borderColor: 'rgba(239, 68, 68, 1)',
                    backgroundColor: 'rgba(239, 68, 68, 0.6)',
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 5
                },
                {
                    label: 'Nuclear',
                    type: 'line',
                    data: forecastData.map(d => d.nuclear_mw),
                    borderColor: 'rgba(168, 85, 247, 1)',
                    backgroundColor: 'rgba(168, 85, 247, 0.6)',
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 5
                },
                {
                    label: 'Wind',
                    type: 'line',
                    data: forecastData.map(d => d.wind_mw),
                    borderColor: 'rgba(52, 211, 153, 1)',
                    backgroundColor: 'rgba(52, 211, 153, 0.6)',
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 5
                },
                {
                    label: 'Solar',
                    type: 'line',
                    data: forecastData.map(d => d.solar_mw),
                    borderColor: 'rgba(251, 191, 36, 1)',
                    backgroundColor: 'rgba(251, 191, 36, 0.6)',
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 5
                },
                {
                    label: 'Total Demand (Forecast)',
                    type: 'line',
                    data: forecastData.map((d, i) => (i % 12 === 0) ? d.total_demand_mw : null),
                    borderColor: 'rgba(150, 150, 150, 0.9)',
                    borderDash: [5, 5],
                    borderWidth: 0, // No line initially (just dots)
                    fill: false,
                    showLine: false, // Don't connect the dots
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointStyle: 'circle',
                    pointBorderWidth: 2,
                    pointBackgroundColor: 'rgba(150, 150, 150, 0.7)',
                    pointBorderColor: 'rgba(150, 150, 150, 1)',
                    order: 3
                },
                {
                    label: 'Net Demand (Forecast)',
                    type: 'line',
                    data: forecastData.map((d, i) => (i % 12 === 0) ? d.net_demand_mw : null),
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 0, // No line initially (just dots)
                    fill: false,
                    showLine: false, // Don't connect the dots
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointStyle: 'circle',
                    pointBorderWidth: 2,
                    pointBackgroundColor: 'rgba(255, 99, 132, 0.7)',
                    pointBorderColor: 'rgba(255, 99, 132, 1)',
                    order: 1
                },
                {
                    label: 'Battery',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(34, 197, 94, 1)',
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 4
                },
                {
                    label: 'CCGT',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(59, 130, 246, 1)',
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 4
                },
                {
                    label: 'CT',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(249, 115, 22, 1)',
                    backgroundColor: 'rgba(249, 115, 22, 0.7)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 4
                },
                {
                    label: 'RNG',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(132, 204, 22, 1)',
                    backgroundColor: 'rgba(132, 204, 22, 0.7)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 4
                },
                {
                    label: 'Hydrogen',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(99, 102, 241, 1)',
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 4
                },
                {
                    label: 'Hydro',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(6, 182, 212, 1)',
                    backgroundColor: 'rgba(6, 182, 212, 0.7)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 4
                },
                {
                    label: 'Solar Curtailment',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(245, 158, 11, 1)',
                    backgroundColor: 'rgba(245, 158, 11, 0.5)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 6
                },
                {
                    label: 'Wind Curtailment',
                    type: 'line',
                    data: [],
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.5)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    stack: 'renewable',
                    order: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Power (GW)'
                    },
                    ticks: {
                        callback: function(value) {
                            return Math.round(value / 1000);
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time of Day (Hour)'
                    },
                    min: 0,
                    max: 287, // 288 data points (0-287) representing 24 hours
                    ticks: {
                        // Show ticks every hour (0, 1, 2, ..., 24)
                        callback: function(value, index, ticks) {
                            const totalDataPoints = ticks.length;

                            // If we have 24 data points (hourly mode), show all hours
                            if (totalDataPoints === 24) {
                                return index.toString();
                            }
                            // If we have 288 data points (5-min mode), show every 12th tick (hourly)
                            else if (totalDataPoints === 288) {
                                if (index % 12 === 0) {
                                    const hour = Math.floor(index / 12);
                                    return hour.toString();
                                }
                                // Show hour 24 at the end (index 288 would be out of bounds, so show at 287)
                                if (index === 287) {
                                    return '24';
                                }
                                return '';
                            }
                            return index.toString();
                        },
                        autoSkip: false,
                        maxRotation: 0,
                        minRotation: 0,
                        stepSize: 12 // One tick every 12 data points (hourly)
                    },
                    grid: {
                        display: true,
                        color: function(context) {
                            // Only show grid lines every hour (every 12 data points)
                            if (context.tick && context.tick.label !== '') {
                                return 'rgba(0, 0, 0, 0.1)';
                            }
                            return 'rgba(0, 0, 0, 0)';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        filter: function(legendItem, chartData) {
                            // During gameplay, hide the forecast dot datasets from legend
                            // Also hide Total Demand and Net Demand lines (they're obvious in the chart)
                            const totalDatasets = chartData.datasets.length;

                            // If we have more than 11 datasets, game has started (actual lines added)
                            if (totalDatasets > 11) {
                                // Hide forecast dots (indices 5 and 6) during gameplay
                                // Hide Total Demand and Net Demand lines (indices 7 and 8)
                                if (legendItem.datasetIndex === 5 || legendItem.datasetIndex === 6 ||
                                    legendItem.datasetIndex === 7 || legendItem.datasetIndex === 8) {
                                    return false;
                                }
                            }

                            return true;
                        },
                        generateLabels: function(chart) {
                            // Use Chart.js default label generation
                            const datasets = chart.data.datasets;
                            const labels = datasets.map((dataset, i) => {
                                // For demand datasets (scatter plots), use pointBorderColor
                                // For other datasets (filled areas), use backgroundColor
                                const usePointColor = dataset.pointBorderColor && dataset.showLine === false;

                                return {
                                    text: dataset.label,
                                    fillStyle: usePointColor ? dataset.pointBorderColor : dataset.backgroundColor,
                                    strokeStyle: usePointColor ? dataset.pointBorderColor : dataset.borderColor,
                                    lineWidth: dataset.borderWidth,
                                    hidden: !chart.isDatasetVisible(i),
                                    datasetIndex: i
                                };
                            });

                            // Define custom order: Demand first, then renewables, then flexible, then curtailment
                            const order = [
                                'Total Demand', 'Net Demand',  // Row 1
                                'Solar', 'Wind', 'Geothermal', 'Nuclear', 'Biomass',  // Row 2
                                'CCGT', 'CT', 'Hydro', 'Battery', 'Solar Curtailment', 'Wind Curtailment'  // Row 3 & 4
                            ];

                            // Remove "(Forecast)" and "(Actual)" suffixes from labels
                            labels.forEach(label => {
                                label.text = label.text.replace(' (Forecast)', '').replace(' (Actual)', '');
                            });

                            // Sort labels based on custom order
                            labels.sort((a, b) => {
                                const aIndex = order.indexOf(a.text);
                                const bIndex = order.indexOf(b.text);
                                return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
                            });

                            return labels;
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    axis: 'x',
                    callbacks: {
                        title: function(tooltipItems) {
                            if (tooltipItems.length === 0) return '';

                            const index = tooltipItems[0].dataIndex;

                            // In edit mode, data points are hourly (indices 0-23)
                            if (isEditMode) {
                                return `Hour ${index}`;
                            }

                            // In pre-game, snap to nearest hour
                            if (!gameStarted) {
                                const hour = Math.round(index / 12);
                                return `Hour ${hour}`;
                            }

                            // During game - check if this is future time (beyond gameTick)
                            if (gameStarted && index > gameTick) {
                                // For future time, snap to nearest hour
                                const hour = Math.round(index / 12);
                                return `Hour ${hour} (Forecast)`;
                            }

                            // During game - past/current time, show hour and minute
                            const hour = Math.floor(index / 12);
                            const minute = (index % 12) * 5;
                            return `Time: ${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
                        },
                        label: function(context) {
                            const currentIndex = context.dataIndex;
                            const datasetIndex = context.datasetIndex;
                            const dataset = context.chart.data.datasets[datasetIndex];

                            // In pre-game mode OR future time during gameplay, snap values to nearest hour
                            if ((!gameStarted && !isEditMode) || (gameStarted && currentIndex > gameTick)) {
                                const nearestHourIndex = Math.round(currentIndex / 12) * 12;

                                // Get the value at the nearest hour
                                const value = dataset.data[nearestHourIndex];

                                if (value === null || value === undefined) {
                                    return null;
                                }

                                return `${dataset.label}: ${Math.round(value)} MW`;
                            }

                            // Default behavior for edit mode and past/current game time
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += Math.round(context.parsed.y) + ' MW';
                            }
                            return label;
                        }
                    }
                },
                dragData: {
                    enabled: false,
                    round: 0,
                    showTooltip: true,
                    dragX: false,
                    onDrag: function(e, datasetIndex, index, value) {
                        if (isEditMode && datasetIndex === 5) {
                            // Enforce constraints DURING dragging for real-time feedback
                            const minDemandMW = calculateMinimumDemandMW();

                            if (value < minDemandMW) {
                                return minDemandMW;
                            }
                            if (value < 0) {
                                return 0;
                            }
                            return value;
                        }
                        return value;
                    },
                    onDragEnd: function(e, datasetIndex, index, value) {
                        if (isEditMode && datasetIndex === 5) {
                            let updatedValue = value;

                            // Calculate minimum demand based on inflexible baseload
                            const minDemandMW = calculateMinimumDemandMW();

                            // Enforce minimum demand constraint
                            if (updatedValue < minDemandMW) {
                                updatedValue = minDemandMW;
                            }

                            // Enforce non-negative constraint
                            if (updatedValue < 0) {
                                updatedValue = 0;
                            }

                            // Update hourly percentage when dragging in edit mode
                            const profile = seasonalProfilesData[selectedCountry].profiles[currentSeason];
                            const peakMW = profile.peakMW;
                            const newPercentage = (updatedValue / peakMW) * 100;
                            profile.hourlyPercentages[index] = Math.max(0, Math.round(newPercentage));

                            // Update chart data
                            e.chart.data.datasets[datasetIndex].data[index] = updatedValue;
                            e.chart.update('none');

                            // Mark profile as modified
                            isLoadProfileModified = true;
                            updateLoadProfileDisplay();
                        }
                    }
                }
            }
        }
    });
}

// --- 7. UPDATE CHART DATA ---
function updateChartData() {
    // Use 5-minute forecast data for smooth curves (288 points)
    // But show demand as hourly dots only
    myChart.data.labels = forecastData.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }));

    // Renewable generation (smooth curves)
    myChart.data.datasets[0].data = forecastData.map(d => d.biomass_mw);
    myChart.data.datasets[1].data = forecastData.map(d => d.geothermal_mw);
    myChart.data.datasets[2].data = forecastData.map(d => d.nuclear_mw);
    myChart.data.datasets[3].data = forecastData.map(d => d.wind_mw);
    myChart.data.datasets[4].data = forecastData.map(d => d.solar_mw);

    // Demand datasets (hourly dots only)
    myChart.data.datasets[5].data = forecastData.map((d, i) => (i % 12 === 0) ? d.total_demand_mw : null);
    myChart.data.datasets[6].data = forecastData.map((d, i) => (i % 12 === 0) ? d.net_demand_mw : null);

    // Flexible generation (empty pre-game)
    myChart.data.datasets[7].data = []; // Battery
    myChart.data.datasets[8].data = []; // CCGT
    myChart.data.datasets[9].data = []; // CT
    myChart.data.datasets[10].data = []; // RNG
    myChart.data.datasets[11].data = []; // Hydrogen
    myChart.data.datasets[12].data = []; // Hydro
    myChart.data.datasets[13].data = []; // Solar Curtailment
    myChart.data.datasets[14].data = []; // Wind Curtailment
    myChart.update();

    // Update demand and gauges after chart data changes
    showInitialDemand();
}

// --- 8. EDIT MODE FUNCTIONS ---
// Helper function to format season name for display
function formatSeasonName(seasonKey) {
    // Handle custom profiles
    if (seasonKey === 'custom') {
        return 'User Defined';
    }
    // Convert "spring-typical" to "Spring Typical" and "winter-high" to "Winter High"
    return seasonKey
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Helper function to update load profile display text
function updateLoadProfileDisplay() {
    if (isLoadProfileModified) {
        currentLoadProfileText.textContent = 'User Defined';
    } else {
        const seasonName = formatSeasonName(currentSeason);
        currentLoadProfileText.textContent = seasonName;
    }
}

// Helper function to apply load season preset
function applyLoadSeasonPreset(season) {
    // Restore original preset data for this season from pristine copy
    seasonalProfilesData[selectedCountry].profiles[season] =
        JSON.parse(JSON.stringify(originalSeasonalProfilesData[selectedCountry].profiles[season]));

    currentSeason = season;
    isLoadProfileModified = false; // Reset modified flag when applying preset
    isCFProfileModified = false; // Also reset CF profile modified flag

    if (isEditMode) {
        // If in edit mode, stay in hourly editing mode
        const profile = seasonalProfilesData[selectedCountry].profiles[season];
        const peakMW = profile.peakMW;
        const hourlyDemandMW = profile.hourlyPercentages.map(pct => (pct / 100) * peakMW);
        myChart.data.datasets[5].data = hourlyDemandMW;
        myChart.update('none');

        // Update original backup for revert
        originalDemandBeforeEdit = [...profile.hourlyPercentages];

        // Also update CF chart to match the season
        updateCFChart();
    } else {
        // Not in edit mode, normal load
        loadSeasonalProfile(season);
        updateCFChart();
        resetGame();
        showInitialDemand();
    }

    updateLoadProfileDisplay();
}

function enterEditMode() {
    isEditMode = true;

    const profile = seasonalProfilesData[selectedCountry].profiles[currentSeason];
    originalDemandBeforeEdit = [...profile.hourlyPercentages];

    editProfileButton.classList.add('hidden');
    loadPresetsDiv.classList.remove('hidden');
    confirmEditButton.classList.remove('hidden');
    revertEditButton.classList.remove('hidden');

    startButton.disabled = true;

    const demandDataset = myChart.data.datasets[5];

    // Hide all other datasets
    myChart.data.datasets[0].hidden = true; // Biomass
    myChart.data.datasets[1].hidden = true; // Geothermal
    myChart.data.datasets[2].hidden = true; // Nuclear
    myChart.data.datasets[3].hidden = true; // Wind
    myChart.data.datasets[4].hidden = true; // Solar
    myChart.data.datasets[6].hidden = true; // Net Demand
    myChart.data.datasets[7].hidden = true; // Battery Supply
    myChart.data.datasets[8].hidden = true; // CCGT Supply
    myChart.data.datasets[9].hidden = true; // CT Supply
    myChart.data.datasets[10].hidden = true; // RNG Supply
    myChart.data.datasets[11].hidden = true; // Hydrogen Supply
    myChart.data.datasets[12].hidden = true; // Hydro Supply
    myChart.data.datasets[13].hidden = true; // Solar Curtailment
    myChart.data.datasets[14].hidden = true; // Wind Curtailment

    // Switch to hourly data for editing (24 points instead of 288)
    const peakMW = profile.peakMW;
    const hourlyDemandMW = profile.hourlyPercentages.map(pct => (pct / 100) * peakMW);
    const HOURS = Array.from({ length: 24 }, (_, i) => `${i}:00`);

    myChart.data.labels = HOURS;
    demandDataset.data = hourlyDemandMW;

    demandDataset.borderWidth = 4;
    demandDataset.pointRadius = 6;
    demandDataset.pointHoverRadius = 8;
    demandDataset.pointBackgroundColor = 'rgba(150, 150, 150, 1)';
    demandDataset.pointBorderColor = 'white';
    demandDataset.pointBorderWidth = 2;

    // Update x-axis for hourly grid lines (every hour instead of every 12 intervals)
    myChart.options.scales.x.ticks.callback = function(value, index, ticks) {
        return index.toString();
    };
    myChart.options.scales.x.ticks.autoSkip = false;
    myChart.options.scales.x.grid.color = function(context) {
        return 'rgba(0, 0, 0, 0.1)'; // Show all grid lines in edit mode (24 hours)
    };

    myChart.options.plugins.dragData.enabled = true;
    myChart.options.onHover = function(e) {
        const points = myChart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
        if (points.length && points[0].datasetIndex === 5) {
            e.native.target.style.cursor = 'grab';
        } else {
            e.native.target.style.cursor = 'default';
        }
    };

    myChart.update();
}

function confirmEdit() {
    isEditMode = false;

    editProfileButton.classList.remove('hidden');
    loadPresetsDiv.classList.add('hidden');
    confirmEditButton.classList.add('hidden');
    revertEditButton.classList.add('hidden');

    startButton.disabled = false;

    // Unhide all datasets
    myChart.data.datasets[0].hidden = false; // Biomass
    myChart.data.datasets[1].hidden = false; // Geothermal
    myChart.data.datasets[2].hidden = false; // Nuclear
    myChart.data.datasets[3].hidden = false; // Wind
    myChart.data.datasets[4].hidden = false; // Solar
    myChart.data.datasets[6].hidden = false; // Net Demand
    myChart.data.datasets[7].hidden = false; // Battery Supply
    myChart.data.datasets[8].hidden = false; // CCGT Supply
    myChart.data.datasets[9].hidden = false; // CT Supply
    myChart.data.datasets[10].hidden = false; // RNG Supply
    myChart.data.datasets[11].hidden = false; // Hydrogen Supply
    myChart.data.datasets[12].hidden = false; // Hydro Supply
    myChart.data.datasets[13].hidden = false; // Solar Curtailment
    myChart.data.datasets[14].hidden = false; // Wind Curtailment

    // Restore Total Demand dataset to pre-game dot style (not lines)
    const demandDataset = myChart.data.datasets[5];
    demandDataset.showLine = false; // Don't connect dots in pre-game
    demandDataset.borderWidth = 0; // No line border
    demandDataset.pointRadius = 5; // Visible dots
    demandDataset.pointHoverRadius = 7;
    demandDataset.pointBackgroundColor = 'rgba(150, 150, 150, 0.7)';
    demandDataset.pointBorderColor = 'rgba(150, 150, 150, 1)';
    demandDataset.pointBorderWidth = 2;

    // Restore Net Demand dataset to pre-game dot style
    const netDemandDataset = myChart.data.datasets[6];
    netDemandDataset.showLine = false; // Don't connect dots in pre-game
    netDemandDataset.borderWidth = 0; // No line border
    netDemandDataset.pointRadius = 5; // Visible dots
    netDemandDataset.pointHoverRadius = 7;

    myChart.options.plugins.dragData.enabled = false;
    myChart.options.onHover = null;

    // Restore x-axis configuration for hourly intervals (24 points in pre-game)
    myChart.options.scales.x.ticks.callback = function(value, index, ticks) {
        const totalDataPoints = ticks.length;

        // If we have 24 data points (hourly mode), show all hours
        if (totalDataPoints === 24) {
            return index.toString();
        }
        // If we have 288 data points (5-min mode), show every 12th tick (hourly)
        else if (totalDataPoints === 288) {
            if (index % 12 === 0) {
                const hour = Math.floor(index / 12);
                return hour.toString();
            }
            return '';
        }
        return index.toString();
    };
    myChart.options.scales.x.ticks.autoSkip = false;
    myChart.options.scales.x.grid.color = function(context) {
        if (context.tick && context.tick.label !== '') {
            return 'rgba(0, 0, 0, 0.1)';
        }
        return 'rgba(0, 0, 0, 0)';
    };

    // Regenerate full 288-point forecast from edited hourly percentages
    forecastData = generateForecastFromProfile(currentSeason);
    hourlyForecastData = extractHourlyForecast(forecastData);

    // Restore hourly pre-game view using updateChartData()
    updateChartData();
}

function revertEdit() {
    const profile = seasonalProfilesData[selectedCountry].profiles[currentSeason];
    profile.hourlyPercentages = [...originalDemandBeforeEdit];

    // Update the hourly chart display in edit mode
    const peakMW = profile.peakMW;
    const hourlyDemandMW = profile.hourlyPercentages.map(pct => (pct / 100) * peakMW);
    myChart.data.datasets[5].data = hourlyDemandMW;
    myChart.update('none');
}

// --- 9. HELPER FUNCTIONS FOR SUPPLY AND BATTERY ---
function updateSupplyValues() {
    console.log('--- updateSupplyValues called ---');
    const battery = parseFloat(batterySlider.value);
    const ccgt = getTotalOnlineMW(ccgtUnits);
    const ct = getTotalOnlineMW(ctUnits);
    const rng = getTotalOnlineMW(rngUnits);
    const hydrogen = getTotalOnlineMW(hydrogenUnits);
    const hydro = parseFloat(hydroSlider.value);
    const solarCurtailment = parseFloat(solarCurtailmentSlider.value);
    const windCurtailment = parseFloat(windCurtailmentSlider.value);

    console.log(`Supply values: battery=${battery}, ccgt=${ccgt}, ct=${ct}, rng=${rng}, hydrogen=${hydrogen}, hydro=${hydro}`);
    console.log(`Curtailment: solar=${solarCurtailment}, wind=${windCurtailment}`);

    // Curtailment acts as negative supply (reduces renewable generation)
    // So total supply = flexible resources - curtailment
    const total = battery + ccgt + ct + rng + hydrogen + hydro - solarCurtailment - windCurtailment;
    console.log(`Calculated total supply: ${total}`);

    // Update input fields to match sliders
    batteryInput.value = Math.round(battery);
    hydroInput.value = Math.round(hydro);
    solarCurtailmentInput.value = Math.round(solarCurtailment);
    windCurtailmentInput.value = Math.round(windCurtailment);
    totalSupplyValueSpan.textContent = Math.round(total);
    console.log(`Set totalSupplyValueSpan to: ${Math.round(total)}`);

    // Update delta display and chart if game hasn't started yet
    console.log(`Checking chart update condition: gameTick=${gameTick}, forecastData.length=${forecastData.length}`);
    if (gameTick === 0 && forecastData.length > 0) {
        console.log('Entering chart update block...');
        const initialNetDemand = forecastData[0].net_demand_mw;
        const delta = total - initialNetDemand;
        deltaValueSpan.textContent = Math.round(delta);
        console.log(`Delta: ${delta} (Total: ${total}, Net Demand: ${initialNetDemand})`);

        // Color code the delta
        const deltaElement = deltaValueSpan.parentElement;
        const absDelta = Math.abs(delta);
        if (absDelta < 500) {
            deltaElement.className = 'text-2xl font-bold text-green-600';
        } else if (absDelta < 1000) {
            deltaElement.className = 'text-2xl font-bold text-yellow-600';
        } else {
            deltaElement.className = 'text-2xl font-bold text-red-600';
        }

        // Enable/disable Start button based on grid stability
        // Grid is stable if delta is within ±500 MW (green zone)
        if (!gameStarted && !isEditMode) {
            if (absDelta < 500) {
                startButton.disabled = false;
                startButton.classList.remove('bg-gray-400', 'cursor-not-allowed');
                startButton.classList.add('bg-gradient-to-r', 'from-blue-600', 'to-purple-600', 'hover:from-blue-700', 'hover:to-purple-700');
                startButton.removeAttribute('title'); // Remove tooltip when enabled
            } else {
                startButton.disabled = true;
                startButton.classList.add('bg-gray-400', 'cursor-not-allowed');
                startButton.classList.remove('bg-gradient-to-r', 'from-blue-600', 'to-purple-600', 'hover:from-blue-700', 'hover:to-purple-700');
                startButton.setAttribute('title', 'Match the Net Demand with Generation at 12:00 AM to start the game.'); // Show tooltip when disabled
            }
        }

        // Calculate battery SOC change for tick 0
        const energyChangeMWh = -battery * (1/12); // 5-minute intervals = 1/12 hour
        const socChange = energyChangeMWh / BATTERY_CAPACITY_MWH;
        const projectedSOC = Math.max(0, Math.min(1, batterySOC + socChange));

        // Update battery SOC display for tick 0 (horizontal tank)
        const socPercent = Math.round(projectedSOC * 100);
        batterySOCDiv.style.width = `${socPercent}%`;  // Horizontal tank uses width
        batterySOCText.textContent = `${socPercent}%`;

        // Change tank color based on projected SOC level (horizontal gradient)
        if (projectedSOC < 0.2) {
            batterySOCDiv.className = 'absolute left-0 top-0 h-full bg-gradient-to-r from-red-500 to-red-300 transition-all duration-300';
        } else if (projectedSOC < 0.5) {
            batterySOCDiv.className = 'absolute left-0 top-0 h-full bg-gradient-to-r from-yellow-500 to-yellow-300 transition-all duration-300';
        } else {
            batterySOCDiv.className = 'absolute left-0 top-0 h-full bg-gradient-to-r from-green-500 to-green-300 transition-all duration-300';
        }

        // Calculate cost for tick 0
        const batteryCost = Math.abs(battery) * BATTERY_OPCOST * (1/12);
        const ccgtCost = calculateCCGTCost(ccgt) * (1/12);
        const ctCost = calculateCTCost(ct) * (1/12);
        const hydroCost = hydro * HYDRO_OPCOST * (1/12);
        const solarCurtailmentCost = solarCurtailment * SOLAR_CURTAILMENT_OPCOST * (1/12);
        const windCurtailmentCost = windCurtailment * WIND_CURTAILMENT_OPCOST * (1/12);
        const currentIntervalCost = batteryCost + ccgtCost + ctCost + hydroCost + solarCurtailmentCost + windCurtailmentCost;

        // Before game starts, total cost is just tick 0 cost (not extrapolated)
        const totalCostBeforeGame = currentIntervalCost;

        // Update cost displays
        currentCostValueSpan.textContent = Math.round(currentIntervalCost).toLocaleString();
        totalCostValueSpan.textContent = Math.round(totalCostBeforeGame).toLocaleString();

        // Color code current interval cost
        const currentCostElement = currentCostValueSpan.parentElement;
        if (currentIntervalCost < 2500) {
            currentCostElement.className = 'text-2xl font-bold text-green-600';
        } else if (currentIntervalCost < 5000) {
            currentCostElement.className = 'text-2xl font-bold text-yellow-600';
        } else {
            currentCostElement.className = 'text-2xl font-bold text-red-600';
        }

        // Color code total cost (same thresholds as current interval before game starts)
        const totalCostElement = totalCostValueSpan.parentElement;
        if (totalCostBeforeGame < 2500) {
            totalCostElement.className = 'text-2xl font-bold text-green-600';
        } else if (totalCostBeforeGame < 5000) {
            totalCostElement.className = 'text-2xl font-bold text-yellow-600';
        } else {
            totalCostElement.className = 'text-2xl font-bold text-red-600';
        }

        // Update chart datasets for tick 0 (first data point only)
        console.log(`Checking chart update: myChart exists=${!!myChart}, dataset[7] exists=${myChart && !!myChart.data.datasets[7]}`);
        if (myChart && myChart.data.datasets[7]) {
            const rngMW = getTotalOnlineMW(rngUnits);
            const hydrogenMW = getTotalOnlineMW(hydrogenUnits);
            console.log(`Updating chart datasets: battery=${battery}, ccgt=${ccgt}, ct=${ct}, rng=${rngMW}, hydrogen=${hydrogenMW}, hydro=${hydro}`);

            myChart.data.datasets[7].data[0] = battery;  // Battery
            myChart.data.datasets[8].data[0] = ccgt;     // CCGT
            myChart.data.datasets[9].data[0] = ct;       // CT
            myChart.data.datasets[10].data[0] = rngMW;  // RNG
            myChart.data.datasets[11].data[0] = hydrogenMW;  // Hydrogen
            myChart.data.datasets[12].data[0] = hydro;   // Hydro
            myChart.data.datasets[13].data[0] = -solarCurtailment;   // Solar Curtailment (negative)
            myChart.data.datasets[14].data[0] = -windCurtailment;    // Wind Curtailment (negative)
            console.log('Calling myChart.update()...');
            myChart.update('none'); // Update without animation
            console.log('Chart update complete');
        } else {
            console.log('WARNING: Chart or datasets not available for update!');
        }

        // Update gauges before game starts
        updateGauges(delta, total);
    } else {
        console.log('Skipped chart update block (condition not met)');
    }
    console.log('--- updateSupplyValues complete ---\n');
}

function updateBatterySOCDisplay() {
    const socPercent = Math.round(batterySOC * 100);
    batterySOCDiv.style.width = `${socPercent}%`;  // Horizontal tank uses width
    batterySOCText.textContent = `${socPercent}%`;

    // Change tank color based on SOC level (horizontal gradient)
    if (batterySOC < 0.2) {
        batterySOCDiv.className = 'absolute left-0 top-0 h-full bg-gradient-to-r from-red-500 to-red-300 transition-all duration-300';
    } else if (batterySOC < 0.5) {
        batterySOCDiv.className = 'absolute left-0 top-0 h-full bg-gradient-to-r from-yellow-500 to-yellow-300 transition-all duration-300';
    } else {
        batterySOCDiv.className = 'absolute left-0 top-0 h-full bg-gradient-to-r from-green-500 to-green-300 transition-all duration-300';
    }
}

// Update contextual tips banner based on game state
function updateTipsBanner() {
    if (!gameStarted) {
        // Pre-game tip
        tipsBanner.textContent = '💡 Match the Net Demand with Generation at 12:00 AM to start the game.';
        tipsBanner.className = 'mb-4 px-4 py-2 rounded-lg text-center text-sm font-medium transition-all duration-300 bg-blue-50 text-blue-800 border border-blue-200';
        return;
    }

    // Get current game state
    const currentHour = Math.floor(gameTick / 12); // 12 ticks per hour (5-min intervals)
    const socPercent = batterySOC * 100;
    const ccgtStarting = getUnitCounts(ccgtUnits).starting;
    const ctStarting = getUnitCounts(ctUnits).starting;
    const ccgtOnline = getUnitCounts(ccgtUnits).online;
    const ctOnline = getUnitCounts(ctUnits).online;

    let message = '';
    let bgClass = '';
    let textClass = '';
    let borderClass = '';

    // Priority order: Critical warnings > Important tips > Informational

    // CRITICAL: Battery critically low
    if (socPercent < 15) {
        message = '⚠️ Battery critically low! Deploy gas generators or risk blackouts';
        bgClass = 'bg-red-50';
        textClass = 'text-red-800';
        borderClass = 'border-red-200';
    }
    // WARNING: Battery low during daytime with solar
    else if (socPercent < 18 && currentHour >= 6 && currentHour < 18) {
        message = '☀️ Battery running low - solar generation can help recharge';
        bgClass = 'bg-yellow-50';
        textClass = 'text-yellow-800';
        borderClass = 'border-yellow-200';
    }
    // WARNING: Evening peak approaching
    else if (currentHour >= 16 && currentHour < 18) {
        message = '🌆 Evening peak approaching! Solar fading, demand rising - prepare resources';
        bgClass = 'bg-orange-50';
        textClass = 'text-orange-800';
        borderClass = 'border-orange-200';
    }
    // CRITICAL: Evening peak
    else if (currentHour >= 18 && currentHour < 21) {
        message = '⚡ Evening peak! Maximum demand, no solar - use all resources';
        bgClass = 'bg-red-50';
        textClass = 'text-red-800';
        borderClass = 'border-red-200';
    }
    // TIP: Morning ramp
    else if (currentHour >= 6 && currentHour < 9) {
        message = '🌅 Morning ramp-up: Demand rising, solar coming online';
        bgClass = 'bg-blue-50';
        textClass = 'text-blue-800';
        borderClass = 'border-blue-200';
    }
    // TIP: Peak solar hours
    else if (currentHour >= 11 && currentHour < 14) {
        message = '☀️ Peak solar hours - great time to charge batteries!';
        bgClass = 'bg-green-50';
        textClass = 'text-green-800';
        borderClass = 'border-green-200';
    }
    // TIP: Overnight period
    else if (currentHour >= 22 || currentHour < 6) {
        message = '🌙 Overnight period - maintain baseload efficiently';
        bgClass = 'bg-indigo-50';
        textClass = 'text-indigo-800';
        borderClass = 'border-indigo-200';
    }
    // TIP: Battery well charged
    else if (socPercent > 80) {
        message = '✓ Battery well charged - consider reducing expensive generators';
        bgClass = 'bg-green-50';
        textClass = 'text-green-800';
        borderClass = 'border-green-200';
    }
    // TIP: Expensive CT peakers online
    else if (ctOnline >= 5) {
        message = '💰 Multiple CT peakers online - expensive! Consider CCGT for sustained load';
        bgClass = 'bg-yellow-50';
        textClass = 'text-yellow-800';
        borderClass = 'border-yellow-200';
    }
    // INFO: Units starting
    else if (ccgtStarting > 0) {
        const nextTime = getNextUnitCountdown(ccgtUnits);
        message = `⏰ CCGT units starting - will be online in ${nextTime} min`;
        bgClass = 'bg-blue-50';
        textClass = 'text-blue-800';
        borderClass = 'border-blue-200';
    }
    else if (ctStarting > 0) {
        const nextTime = getNextUnitCountdown(ctUnits);
        message = `⏰ CT peakers starting - will be online in ${nextTime} min`;
        bgClass = 'bg-blue-50';
        textClass = 'text-blue-800';
        borderClass = 'border-blue-200';
    }
    // DEFAULT: General tip
    else {
        message = '💡 Monitor battery levels and plan ahead for demand changes';
        bgClass = 'bg-blue-50';
        textClass = 'text-blue-800';
        borderClass = 'border-blue-200';
    }

    tipsBanner.textContent = message;
    tipsBanner.className = `mb-4 px-4 py-2 rounded-lg text-center text-sm font-medium transition-all duration-300 ${bgClass} ${textClass} border ${borderClass}`;
}

// Update hydro capacity based on dropdown selection
function updateHydroCapacity() {
    const condition = hydroCondition.value;
    currentHydroMaxMW = HYDRO_CAPACITY[condition];

    // Update slider and input max values
    hydroSlider.max = currentHydroMaxMW;
    hydroInput.max = currentHydroMaxMW;

    // Clamp current value if it exceeds new max
    const currentValue = parseFloat(hydroSlider.value);
    if (currentValue > currentHydroMaxMW) {
        hydroSlider.value = currentHydroMaxMW;
        hydroInput.value = currentHydroMaxMW;
        updateSupplyValues();
    }

    // Update display text
    hydroMaxDisplay.textContent = `Max: ${currentHydroMaxMW.toLocaleString()} MW`;
}

function updateHydrogenCost() {
    const fuelCostKey = hydrogenFuelCost.value;
    currentHydrogenBaseCost = HYDROGEN_FUEL_COST[fuelCostKey];

    // Update cost display text
    hydrogenCostDisplay.textContent = currentHydrogenBaseCost;
}

// --- 10. STATUS BANNER UPDATE FUNCTION ---
function updateStatusBanner(delta) {
    const absDelta = Math.abs(delta);

    // Check if we're in initial state (no resources configured yet)
    const battery = parseFloat(batterySlider.value);
    const ccgt = getTotalOnlineMW(ccgtUnits);
    const ct = getTotalOnlineMW(ctUnits);
    const hydro = parseFloat(hydroSlider.value);
    const totalSupply = battery + ccgt + ct + hydro;
    const isInitialState = !gameStarted && totalSupply === 0;

    if (isInitialState) {
        // Initial state - show instruction to match delta
        statusBanner.className = 'mb-4 px-4 py-3 rounded-lg text-center font-semibold text-lg transition-all duration-300 bg-blue-100 text-blue-800';
        statusBanner.textContent = '⚙️ Grid Unstable: Match Net Demand with Resources';
    } else if (absDelta >= 1500) {
        // Blackout
        statusBanner.className = 'mb-4 px-4 py-3 rounded-lg text-center font-semibold text-lg transition-all duration-300 bg-red-100 text-red-800 animate-pulse';
        statusBanner.textContent = '⚠️ BLACKOUT';
    } else if (absDelta >= 500) {
        // Emergency Alert
        statusBanner.className = 'mb-4 px-4 py-3 rounded-lg text-center font-semibold text-lg transition-all duration-300 bg-yellow-100 text-yellow-800';
        statusBanner.textContent = '⚡ Emergency Alert';
    } else {
        // Grid Stable
        statusBanner.className = 'mb-4 px-4 py-3 rounded-lg text-center font-semibold text-lg transition-all duration-300 bg-green-100 text-green-800';
        statusBanner.textContent = '✓ Grid Stable';
    }
}

// --- 11. GAUGE UPDATE FUNCTIONS ---
function updateGauges(delta, totalSupply) {
    // Update Delta Gauge
    // Range: -2000 MW to +2000 MW mapped to -90° to +90° (180° arc)
    const deltaAngle = Math.max(-90, Math.min(90, (delta / 2000) * 90));
    const deltaX2 = 110 + 65 * Math.sin((deltaAngle * Math.PI) / 180);
    const deltaY2 = 120 - 65 * Math.cos((deltaAngle * Math.PI) / 180);
    deltaNeedle.setAttribute('x2', deltaX2);
    deltaNeedle.setAttribute('y2', deltaY2);
    deltaGaugeValue.textContent = Math.round(delta);

    // Update Grid Frequency Gauge
    // Formula based on grid frequency response to power imbalance
    // delta = supply - demand (positive = oversupply, negative = undersupply)
    // Undersupply (delta < 0) → lower frequency
    // Oversupply (delta > 0) → higher frequency

    // Realistic frequency response based on game thresholds:
    // ±500 MW (Emergency Alert) → ~59.7/60.3 Hz (0.3 Hz deviation)
    // ±1500 MW (Blackout) → ~59.0/61.0 Hz (1.0 Hz deviation)
    // Beyond ±1500 MW → increasingly severe (can go below 58 Hz for catastrophic undersupply)

    // Use frequency droop: Δf (Hz) = delta (MW) / droop_constant
    // Calibrated so ±1500 MW gives ±1.0 Hz deviation
    const droopConstant = 1500; // MW per Hz deviation
    const frequency = 60 + (delta / droopConstant);

    // Typical grid frequency range: 59.5 Hz to 60.5 Hz
    // Map 59 Hz to -90°, 60 Hz to 0°, 61 Hz to +90°
    const freqAngle = Math.max(-90, Math.min(90, (frequency - 60) * 90));
    const freqX2 = 110 + 65 * Math.sin((freqAngle * Math.PI) / 180);
    const freqY2 = 120 - 65 * Math.cos((freqAngle * Math.PI) / 180);
    frequencyNeedle.setAttribute('x2', freqX2);
    frequencyNeedle.setAttribute('y2', freqY2);
    frequencyGaugeValue.textContent = frequency.toFixed(2);
}

// --- 11. ANIMATION CONTROLLER ---
const AnimationController = {
    // Confetti celebration animation (for zero alerts/blackouts)
    playConfetti() {
        const duration = 4000; // 4 seconds
        const animationEnd = Date.now() + duration;
        const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 9999 };

        function randomInRange(min, max) {
            return Math.random() * (max - min) + min;
        }

        const interval = setInterval(function() {
            const timeLeft = animationEnd - Date.now();

            if (timeLeft <= 0) {
                return clearInterval(interval);
            }

            const particleCount = 50 * (timeLeft / duration);

            // Multiple origin points for confetti
            confetti(Object.assign({}, defaults, {
                particleCount,
                origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 }
            }));
            confetti(Object.assign({}, defaults, {
                particleCount,
                origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 }
            }));
        }, 250);
    },

    // Cloud cover animation
    playCloudCover() {
        const overlay = document.getElementById('animation-overlay');
        const cloudContainer = document.getElementById('cloud-animation');

        // Show overlay
        overlay.style.display = 'block';
        cloudContainer.classList.remove('hidden');

        // Create darkening overlay effect
        const darkenOverlay = document.createElement('div');
        darkenOverlay.className = 'cloud-darken-overlay';
        cloudContainer.appendChild(darkenOverlay);

        // Create multiple large clouds covering the screen
        const cloudPositions = [
            { left: '15%', delay: 0 },
            { left: '35%', delay: 0.2 },
            { left: '55%', delay: 0.4 },
            { left: '75%', delay: 0.6 }
        ];

        cloudPositions.forEach((pos) => {
            const cloud = document.createElement('div');
            cloud.textContent = '☁️';
            cloud.className = 'cloud-element';
            cloud.style.left = pos.left;
            cloud.style.animationDelay = `${pos.delay}s`;
            cloudContainer.appendChild(cloud);
        });

        // Clean up after animation completes
        setTimeout(() => {
            cloudContainer.innerHTML = '';
            cloudContainer.classList.add('hidden');
            overlay.style.display = 'none';
        }, 4000);
    },

    // Demand spike animation
    playDemandSpike() {
        const overlay = document.getElementById('animation-overlay');
        const spikeContainer = document.getElementById('demand-spike-animation');

        // Show overlay
        overlay.style.display = 'block';
        spikeContainer.classList.remove('hidden');

        // Create lightning bolt
        const lightning = document.createElement('div');
        lightning.textContent = '⚡';
        lightning.className = 'lightning-element';
        spikeContainer.appendChild(lightning);

        // Create flash effect
        const flash = document.createElement('div');
        flash.className = 'flash-overlay';
        spikeContainer.appendChild(flash);

        // Clean up after animation completes
        setTimeout(() => {
            spikeContainer.innerHTML = '';
            spikeContainer.classList.add('hidden');
            overlay.style.display = 'none';
        }, 2000);
    }
};

// --- 12. EVENT FUNCTIONS ---
function triggerCloudCoverEvent() {
    if (gameTick >= forecastData.length - 1) return; // Don't trigger on last tick

    // Play cloud cover animation
    AnimationController.playCloudCover();

    // Apply steep reduction to solar generation for next tick only
    // Random reduction between 50-90% of solar output
    const reductionFactor = 0.5 + Math.random() * 0.4; // 0.5 to 0.9
    const nextTick = gameTick + 1;

    // Get current solar output and reduce it
    const currentSolarMW = forecastData[nextTick].solar_mw;
    const reducedSolarMW = currentSolarMW * (1 - reductionFactor);

    // Update the forecast data for next tick
    forecastData[nextTick].solar_mw = reducedSolarMW;
    forecastData[nextTick].total_renewables_mw =
        reducedSolarMW +
        forecastData[nextTick].wind_mw +
        forecastData[nextTick].nuclear_mw +
        forecastData[nextTick].geothermal_mw +
        forecastData[nextTick].biomass_mw;
    forecastData[nextTick].net_demand_mw =
        forecastData[nextTick].total_demand_mw - forecastData[nextTick].total_renewables_mw;

    // Update chart data for that tick
    myChart.data.datasets[4].data[nextTick] = reducedSolarMW;
    myChart.update('none');

    console.log(`Cloud Cover Event! Solar reduced by ${Math.round(reductionFactor * 100)}% for next tick`);
}

function triggerDemandSpikeEvent() {
    if (gameTick >= forecastData.length - 1) return; // Don't trigger on last tick

    // Play demand spike animation
    AnimationController.playDemandSpike();

    // Apply steep increase to total demand for next tick only
    // Random spike between 1000-3000 MW
    const spikeMW = 1000 + Math.random() * 2000;
    const nextTick = gameTick + 1;

    // Update the forecast data for next tick
    forecastData[nextTick].total_demand_mw += spikeMW;
    forecastData[nextTick].net_demand_mw += spikeMW; // Net demand increases by same amount

    // Update chart data for that tick
    // During gameplay, we have both forecast dots (5-6) and actual lines (7-8)
    if (myChart.data.datasets.length > 11) {
        // Game is running - update both forecast and actual
        if ((nextTick % 12) === 0) {
            // Update forecast dot if it's an hourly point
            myChart.data.datasets[5].data[nextTick] = forecastData[nextTick].total_demand_mw;
            myChart.data.datasets[6].data[nextTick] = forecastData[nextTick].net_demand_mw;
        }
        // Update actual line data
        myChart.data.datasets[7].data[nextTick] = forecastData[nextTick].total_demand_mw;
        myChart.data.datasets[8].data[nextTick] = forecastData[nextTick].net_demand_mw;
    } else {
        // Pre-game - just update forecast
        myChart.data.datasets[5].data[nextTick] = forecastData[nextTick].total_demand_mw;
        myChart.data.datasets[6].data[nextTick] = forecastData[nextTick].net_demand_mw;
    }
    myChart.update('none');

    console.log(`Demand Spike Event! Demand increased by ${Math.round(spikeMW)} MW for next tick`);
}

// --- RANDOM EVENT SCHEDULING ---
let scheduledCloudCoverTicks = [];
let scheduledDemandSpikeTicks = [];

function scheduleRandomEvents() {
    // Clear any previously scheduled events
    scheduledCloudCoverTicks = [];
    scheduledDemandSpikeTicks = [];

    // Determine solar hours (hours where solar generation is significant)
    // Typically hours 6-18 (ticks 72-216 in 5-min intervals)
    // But we'll be more precise and check actual solar output
    const solarHours = [];
    for (let i = 0; i < forecastData.length; i++) {
        if (forecastData[i].solar_mw > 100) { // Only count hours with meaningful solar output
            solarHours.push(i);
        }
    }

    // Randomly select 0-2 cloud cover events during solar hours
    const numCloudEvents = Math.floor(Math.random() * 3); // 0, 1, or 2
    if (numCloudEvents > 0 && solarHours.length > 0) {
        for (let i = 0; i < numCloudEvents; i++) {
            // Pick a random tick during solar hours, avoiding the last few ticks
            const randomIndex = Math.floor(Math.random() * Math.max(1, solarHours.length - 12));
            const scheduledTick = solarHours[randomIndex];

            // Ensure we don't schedule duplicates at the same tick
            if (!scheduledCloudCoverTicks.includes(scheduledTick)) {
                scheduledCloudCoverTicks.push(scheduledTick);
            }
        }
    }

    // Randomly select 0-2 demand spike events anytime during the day
    const numDemandEvents = Math.floor(Math.random() * 3); // 0, 1, or 2
    const maxTick = forecastData.length - 12; // Avoid scheduling too close to end
    if (numDemandEvents > 0 && maxTick > 0) {
        for (let i = 0; i < numDemandEvents; i++) {
            const scheduledTick = Math.floor(Math.random() * maxTick);

            // Ensure we don't schedule duplicates at the same tick
            if (!scheduledDemandSpikeTicks.includes(scheduledTick)) {
                scheduledDemandSpikeTicks.push(scheduledTick);
            }
        }
    }

    // Events are scheduled but not revealed to maintain surprise element
    // console.log(`Scheduled Random Events - Cloud Cover at ticks: ${scheduledCloudCoverTicks.join(', ') || 'none'}`);
    // console.log(`Scheduled Random Events - Demand Spike at ticks: ${scheduledDemandSpikeTicks.join(', ') || 'none'}`);
}

function checkAndTriggerScheduledEvents(currentTick) {
    // Check if current tick should trigger a cloud cover event
    if (scheduledCloudCoverTicks.includes(currentTick)) {
        triggerCloudCoverEvent();
        // Remove this tick from scheduled list
        scheduledCloudCoverTicks = scheduledCloudCoverTicks.filter(t => t !== currentTick);
    }

    // Check if current tick should trigger a demand spike event
    if (scheduledDemandSpikeTicks.includes(currentTick)) {
        triggerDemandSpikeEvent();
        // Remove this tick from scheduled list
        scheduledDemandSpikeTicks = scheduledDemandSpikeTicks.filter(t => t !== currentTick);
    }
}

// --- 13. GAME LOGIC ---
function gameLoop() {
    if (gameTick >= forecastData.length) {
        clearInterval(gameInterval);

        // Calculate minutes from counts (each tick = 5 minutes)
        const emergencyMinutes = emergencyAlertCount * 5;
        const blackoutMinutes = blackoutCount * 5;

        // Check for perfect game (zero alerts and blackouts)
        if (emergencyAlertCount === 0 && blackoutCount === 0) {
            // Play confetti animation for perfect game!
            AnimationController.playConfetti();
        }

        alert(`Day complete! You suffered ${emergencyMinutes} mins of Emergency Alerts and ${blackoutMinutes} minutes of Blackouts.`);

        // Submit score to leaderboard if perfect game
        if (emergencyAlertCount === 0 && blackoutCount === 0) {
            submitScore();
        }

        // Show appropriate buttons based on whether there's a schedule
        pauseButtons.classList.add('hidden');

        if (scheduledEvents.length > 0) {
            // Game ended with schedule - show New Game/Retry buttons and Show Schedule button
            startButton.classList.add('hidden');
            endGameButtons.classList.remove('hidden');
            showScheduleButtonContainer.classList.remove('hidden');
        } else {
            // Game ended without schedule - show regular Reset button
            startButton.textContent = 'Reset';
            startButton.classList.remove('hidden');
            endGameButtons.classList.add('hidden');
            showScheduleButtonContainer.classList.add('hidden');
        }

        return;
    }

    // Process unit startup timers at the beginning of each tick
    processStartupTimers();

    // Execute scheduled events from scheduler (Phase 2)
    executeScheduledEvents(gameTick);

    // Check and trigger any scheduled random events for this tick
    checkAndTriggerScheduledEvents(gameTick);

    const currentNetDemand = forecastData[gameTick].net_demand_mw;

    // Get current supply from all sources (units + battery + hydro + curtailment)
    const batteryMW = parseFloat(batterySlider.value);
    const ccgtMW = getTotalOnlineMW(ccgtUnits);
    const ctMW = getTotalOnlineMW(ctUnits);
    const rngMW = getTotalOnlineMW(rngUnits);
    const hydrogenMW = getTotalOnlineMW(hydrogenUnits);
    let hydroMW = parseFloat(hydroSlider.value);
    const solarCurtailmentMW = parseFloat(solarCurtailmentSlider.value);
    const windCurtailmentMW = parseFloat(windCurtailmentSlider.value);

    // Update curtailment ranges for next tick
    updateCurtailmentRanges(gameTick);

    // Apply ramp rate constraints for Hydro only (units handle their own ramping)
    const hydroRampChange = hydroMW - prevHydro;

    // Constrain Hydro to ramp rate
    if (Math.abs(hydroRampChange) > HYDRO_RAMP_RATE_MW_PER_5MIN) {
        if (hydroRampChange > 0) {
            hydroMW = prevHydro + HYDRO_RAMP_RATE_MW_PER_5MIN; // Ramp up limited
        } else {
            hydroMW = prevHydro - HYDRO_RAMP_RATE_MW_PER_5MIN; // Ramp down limited
        }
        hydroSlider.value = hydroMW;
    }

    // Update previous value for next tick
    prevHydro = hydroMW;

    // Update displays after ramp constraints applied
    updateSupplyValues();

    // Curtailment acts as negative supply (reduces net demand effectively)
    // Constrain battery power based on SOC BEFORE applying it
    let actualBatteryMW = batteryMW;
    if (batterySOC <= 0.01 && batteryMW > 0) {
        // Battery empty, cannot discharge
        console.log(`[GameLoop] Cannot discharge ${batteryMW} MW - battery empty (SOC: ${(batterySOC * 100).toFixed(1)}%)`);
        actualBatteryMW = 0;
        batterySlider.value = 0;
        updateSupplyValues();
    } else if (batterySOC >= 0.99 && batteryMW < 0) {
        // Battery full, cannot charge
        console.log(`[GameLoop] Cannot charge at ${batteryMW} MW - battery full (SOC: ${(batterySOC * 100).toFixed(1)}%)`);
        actualBatteryMW = 0;
        batterySlider.value = 0;
        updateSupplyValues();
    }

    const totalSupply = actualBatteryMW + ccgtMW + ctMW + rngMW + hydrogenMW + hydroMW - solarCurtailmentMW - windCurtailmentMW;

    // Update battery state of charge
    // Negative battery value = charging (increasing SOC)
    // Positive battery value = discharging (decreasing SOC)
    const energyChangeMWh = -actualBatteryMW * (1/12); // 5-minute intervals = 1/12 hour, MW to MWh
    const socChange = energyChangeMWh / BATTERY_CAPACITY_MWH;
    batterySOC = Math.max(0, Math.min(1, batterySOC + socChange));

    updateBatterySOCDisplay();
    updateTipsBanner();

    // Calculate cost for this 5-minute interval
    // Cost = (Power in MW) * (Operating Cost in $/MWh) * (Duration in hours)
    // For 5-minute intervals, duration = 1/12 hour
    // For battery, we use absolute value since both charging and discharging have efficiency losses
    const batteryCost = Math.abs(actualBatteryMW) * BATTERY_OPCOST * (1/12);
    const ccgtCost = calculateCCGTCost(ccgtMW) * (1/12);  // Linear cost function * time
    const ctCost = calculateCTCost(ctMW) * (1/12);        // Linear cost function * time
    const rngCost = calculateRNGCost(rngMW) * (1/12);     // Linear cost function * time
    const hydrogenCost = calculateHydrogenCost(hydrogenMW) * (1/12); // Linear cost function * time
    const hydroCost = hydroMW * HYDRO_OPCOST * (1/12);
    const solarCurtailmentCost = solarCurtailmentMW * SOLAR_CURTAILMENT_OPCOST * (1/12);
    const windCurtailmentCost = windCurtailmentMW * WIND_CURTAILMENT_OPCOST * (1/12);
    const currentIntervalCost = batteryCost + ccgtCost + ctCost + rngCost + hydrogenCost + hydroCost + solarCurtailmentCost + windCurtailmentCost;

    // Accumulate total cost
    totalCost += currentIntervalCost;

    // Update cost displays with color coding
    currentCostValueSpan.textContent = Math.round(currentIntervalCost).toLocaleString();
    totalCostValueSpan.textContent = Math.round(totalCost).toLocaleString();

    // Color code current interval cost (thresholds adjusted for 5-min: <2.5k=green, 2.5k-5k=yellow, >5k=red)
    const currentCostElement = currentCostValueSpan.parentElement;
    if (currentIntervalCost < 2500) {
        currentCostElement.className = 'text-2xl font-bold text-green-600';
    } else if (currentIntervalCost < 5000) {
        currentCostElement.className = 'text-2xl font-bold text-yellow-600';
    } else {
        currentCostElement.className = 'text-2xl font-bold text-red-600';
    }

    // Color code total cost (thresholds: <500k=green, 500k-1M=yellow, >1M=red)
    const totalCostElement = totalCostValueSpan.parentElement;
    if (totalCost < 500000) {
        totalCostElement.className = 'text-2xl font-bold text-green-600';
    } else if (totalCost < 1000000) {
        totalCostElement.className = 'text-2xl font-bold text-yellow-600';
    } else {
        totalCostElement.className = 'text-2xl font-bold text-red-600';
    }

    // Update chart data
    // Note: After switchToActualData(), datasets 7-8 are actual demand lines, 9-16 are supply/curtailment
    myChart.data.datasets[9].data.push(batteryMW);  // Battery
    myChart.data.datasets[10].data.push(ccgtMW);     // CCGT
    myChart.data.datasets[11].data.push(ctMW);       // CT
    myChart.data.datasets[12].data.push(rngMW);     // RNG
    myChart.data.datasets[13].data.push(hydrogenMW); // Hydrogen
    myChart.data.datasets[14].data.push(hydroMW);   // Hydro
    myChart.data.datasets[15].data.push(-solarCurtailmentMW);   // Solar Curtailment (negative)
    myChart.data.datasets[16].data.push(-windCurtailmentMW);    // Wind Curtailment (negative)

    // Update the ACTUAL demand lines for the CURRENT tick
    // This ensures the array has valid data up to the point being rendered
    if (myChart.data.datasets[7] && myChart.data.datasets[8]) {
        myChart.data.datasets[7].data[gameTick] = forecastData[gameTick].total_demand_mw;
        myChart.data.datasets[8].data[gameTick] = forecastData[gameTick].net_demand_mw;
    }

    myChart.update('none');

    demandValueSpan.textContent = Math.round(currentNetDemand);
    const delta = totalSupply - currentNetDemand;
    deltaValueSpan.textContent = Math.round(delta);

    // Update next demand preview (if not on last tick)
    if (gameTick + 1 < forecastData.length) {
        const nextNetDemand = forecastData[gameTick + 1].net_demand_mw;
        const demandChange = nextNetDemand - currentNetDemand;

        nextDemandPreview.classList.remove('hidden');
        nextDemandValue.textContent = Math.round(nextNetDemand);

        if (demandChange > 0) {
            // Increase (harder to meet)
            nextDemandChange.textContent = `(↑${Math.round(demandChange)} MW)`;
            if (demandChange > 500) {
                nextDemandChange.className = 'font-semibold text-red-600';
            } else if (demandChange > 100) {
                nextDemandChange.className = 'font-semibold text-orange-600';
            } else {
                nextDemandChange.className = 'font-semibold text-yellow-600';
            }
        } else if (demandChange < 0) {
            // Decrease (easier to meet)
            nextDemandChange.textContent = `(↓${Math.round(Math.abs(demandChange))} MW)`;
            if (Math.abs(demandChange) > 500) {
                nextDemandChange.className = 'font-semibold text-green-600';
            } else if (Math.abs(demandChange) > 100) {
                nextDemandChange.className = 'font-semibold text-teal-600';
            } else {
                nextDemandChange.className = 'font-semibold text-blue-600';
            }
        } else {
            // Exactly 0 change (rare but possible)
            nextDemandChange.textContent = '(0 MW)';
            nextDemandChange.className = 'font-semibold text-gray-600';
        }
    } else {
        // Last tick - hide preview
        nextDemandPreview.classList.add('hidden');
    }

    // Color code delta (thresholds: within ±500MW=green, ±500-1000MW=yellow, >±1000MW=red)
    const deltaElement = deltaValueSpan.parentElement;
    const absDelta = Math.abs(delta);
    if (absDelta < 500) {
        deltaElement.className = 'text-2xl font-bold text-green-600';
    } else if (absDelta < 1000) {
        deltaElement.className = 'text-2xl font-bold text-yellow-600';
    } else {
        deltaElement.className = 'text-2xl font-bold text-red-600';
    }

    // Check for Emergency Alerts and Blackouts
    if (absDelta >= 1500) {
        // Blackout (delta exceeds ±1500 MW)
        blackoutCount++;
        blackoutCountSpan.textContent = blackoutCount;
    } else if (absDelta >= 500) {
        // Emergency Alert (delta between ±500 and ±1500 MW)
        emergencyAlertCount++;
        emergencyCountSpan.textContent = emergencyAlertCount;
    }

    // Update status banner
    updateStatusBanner(delta);

    // Update gauges during gameplay
    updateGauges(delta, totalSupply);

    // Update current time display
    currentTimeValue.textContent = formatGameTime(gameTick);

    // Update delta history chart
    deltaHistoryChart.data.labels.push(formatGameTime(gameTick));
    deltaHistoryChart.data.datasets[0].data.push(Math.round(delta));
    deltaHistoryChart.update('none');

    gameTick++;
}

// Switch from hourly forecast dots to 5-min actual data when game starts
function switchToActualData() {
    // Keep all 288 labels for proper x-axis scale
    myChart.data.labels = forecastData.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }));

    // Keep renewable generation visible (known upfront)
    myChart.data.datasets[0].data = forecastData.map(d => d.biomass_mw);
    myChart.data.datasets[1].data = forecastData.map(d => d.geothermal_mw);
    myChart.data.datasets[2].data = forecastData.map(d => d.nuclear_mw);
    myChart.data.datasets[3].data = forecastData.map(d => d.wind_mw);
    myChart.data.datasets[4].data = forecastData.map(d => d.solar_mw);

    // Show all hourly forecast dots (known upfront)
    const totalDemandForecastDataset = myChart.data.datasets[5];
    totalDemandForecastDataset.label = 'Total Demand (Forecast)';
    totalDemandForecastDataset.data = forecastData.map((d, i) => (i % 12 === 0) ? d.total_demand_mw : null);
    totalDemandForecastDataset.showLine = false;
    totalDemandForecastDataset.pointRadius = 4;
    totalDemandForecastDataset.pointHoverRadius = 6;

    const netDemandForecastDataset = myChart.data.datasets[6];
    netDemandForecastDataset.label = 'Net Demand (Forecast)';
    netDemandForecastDataset.data = forecastData.map((d, i) => (i % 12 === 0) ? d.net_demand_mw : null);
    netDemandForecastDataset.showLine = false;
    netDemandForecastDataset.pointRadius = 4;
    netDemandForecastDataset.pointHoverRadius = 6;

    // Add new datasets for actual demand lines (progressively revealed)
    // Create sparse arrays - will be filled as game progresses
    const actualTotalDemand = new Array(288);
    const actualNetDemand = new Array(288);

    myChart.data.datasets.splice(7, 0, {
        label: 'Total Demand',
        type: 'line',
        data: actualTotalDemand,
        borderColor: 'rgba(150, 150, 150, 1)',
        borderDash: [5, 5],
        borderWidth: 2,
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0,
        order: 2,
        spanGaps: true,  // Skip over undefined values
        hidden: false
    });

    myChart.data.datasets.splice(8, 0, {
        label: 'Net Demand',
        type: 'line',
        data: actualNetDemand,
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 3,
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0,
        order: 1,
        spanGaps: true,  // Skip over undefined values
        hidden: false
    });

    myChart.update('none'); // Update without animation
}

// Switch back to hourly forecast dots when game resets
function switchToForecastData() {
    // Remove the actual demand line datasets if they exist (indices 7 and 8)
    if (myChart.data.datasets.length > 11) {
        myChart.data.datasets.splice(7, 2); // Remove the 2 actual demand datasets
    }

    // Update chart labels to show 5-minute intervals (smooth curves)
    myChart.data.labels = forecastData.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }));

    // Update renewable generation to 5-minute smooth data
    myChart.data.datasets[0].data = forecastData.map(d => d.biomass_mw);
    myChart.data.datasets[1].data = forecastData.map(d => d.geothermal_mw);
    myChart.data.datasets[2].data = forecastData.map(d => d.nuclear_mw);
    myChart.data.datasets[3].data = forecastData.map(d => d.wind_mw);
    myChart.data.datasets[4].data = forecastData.map(d => d.solar_mw);

    // Update Total Demand dataset to show hourly forecast dots (null for non-hourly points)
    const totalDemandDataset = myChart.data.datasets[5];
    totalDemandDataset.label = 'Total Demand (Forecast)';
    totalDemandDataset.data = forecastData.map((d, i) => (i % 12 === 0) ? d.total_demand_mw : null);
    totalDemandDataset.showLine = false; // Don't connect dots
    totalDemandDataset.borderWidth = 0;
    totalDemandDataset.pointRadius = 5;
    totalDemandDataset.pointHoverRadius = 7;

    // Update Net Demand dataset to show hourly forecast dots (null for non-hourly points)
    const netDemandDataset = myChart.data.datasets[6];
    netDemandDataset.label = 'Net Demand (Forecast)';
    netDemandDataset.data = forecastData.map((d, i) => (i % 12 === 0) ? d.net_demand_mw : null);
    netDemandDataset.showLine = false; // Don't connect dots
    netDemandDataset.borderWidth = 0;
    netDemandDataset.pointRadius = 5;
    netDemandDataset.pointHoverRadius = 7;

    myChart.update('none');
}

function startGame() {
    gameStarted = true; // Mark game as started
    gamePaused = false; // Mark game as not paused

    // Change button to "Pause" with distinct gradient (yellow to orange - less distracting)
    startButton.textContent = 'Pause';
    startButton.disabled = false;
    startButton.className = 'w-full px-6 py-3 text-lg font-medium text-white bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 rounded-full transition-colors shadow-md';

    // Hide scheduler button during gameplay
    hideSchedulerButton();

    // Show active schedule indicator if events are scheduled
    showActiveScheduleIndicator();
    if (scheduledEvents.length > 0) {
        updateUpcomingEventsList(0);
        updateNextEventTicker(0);
    }

    editProfileButton.disabled = true;
    gameTick = 0;
    batterySOC = 0.2; // Reset to 20%

    // Set initial ramp tracking for hydro
    prevHydro = parseFloat(hydroSlider.value);

    totalCost = 0; // Reset cost tracking
    updateBatterySOCDisplay();
    updateTipsBanner();
    currentCostValueSpan.textContent = '0';
    totalCostValueSpan.textContent = '0';

    // Schedule random events for this game session
    scheduleRandomEvents();

    // Switch from hourly forecast to 5-min actual data
    switchToActualData();

    gameInterval = setInterval(gameLoop, gameSpeed * 1000);
}

function pauseGame() {
    gamePaused = true;
    clearInterval(gameInterval);

    // Hide "Pause" button and show "Resume" and "Restart" buttons
    startButton.classList.add('hidden');
    pauseButtons.classList.remove('hidden');

    // Show "Show Schedule" button if there are scheduled events
    if (scheduledEvents.length > 0) {
        showScheduleButtonContainer.classList.remove('hidden');
    }
}

function resumeGame() {
    gamePaused = false;

    // Hide "Resume" and "Restart" buttons, show "Pause" button
    pauseButtons.classList.add('hidden');
    endGameButtons.classList.add('hidden');
    showScheduleButtonContainer.classList.add('hidden');
    startButton.classList.remove('hidden');

    // Resume the game loop
    gameInterval = setInterval(gameLoop, gameSpeed * 1000);
}

function resetGame() {
    gameStarted = false; // Mark game as not started
    gamePaused = false; // Mark game as not paused
    clearInterval(gameInterval);

    // Reset button states and restore initial styling
    startButton.textContent = 'Start The Day';
    startButton.disabled = true; // Will be enabled when grid is stable
    startButton.className = 'w-full px-6 py-3 text-lg font-medium text-white bg-gray-400 cursor-not-allowed rounded-full transition-colors shadow-md';
    startButton.classList.remove('hidden');
    pauseButtons.classList.add('hidden');
    endGameButtons.classList.add('hidden');
    showScheduleButtonContainer.classList.add('hidden');

    batterySlider.disabled = true;
    batteryInput.disabled = true;
    hydroSlider.disabled = true;
    hydroInput.disabled = true;
    editProfileButton.disabled = false;
    gameTick = 0;
    batterySOC = 0.2; // Reset to 20%
    prevHydro = 0; // Reset ramp tracking
    totalCost = 0; // Reset cost tracking

    // Clear scheduled random events
    scheduledCloudCoverTicks = [];
    scheduledDemandSpikeTicks = [];

    // Regenerate forecast data to clear any random event modifications
    forecastData = generateForecastFromProfile(currentSeason);
    hourlyForecastData = extractHourlyForecast(forecastData);

    // Update chart to show clean forecast data
    updateChartData();

    // Hide active schedule indicator and next event ticker
    hideActiveScheduleIndicator();
    document.getElementById('nextEventTicker').classList.add('hidden');

    // Reset game speed to default (index 2 = 5s/tick)
    const speedSteps = [0.1, 1, 5, 10, 20, 30];
    const defaultIndex = 2;
    gameSpeed = speedSteps[defaultIndex];
    gameSpeedSlider.value = defaultIndex;
    gameSpeedTime.textContent = gameSpeed.toFixed(1);

    // Reset all units to offline
    ccgtUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
        unit.startupTicksRemaining = 0;
    });
    ctUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
        unit.startupTicksRemaining = 0;
    });
    rngUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
        unit.startupTicksRemaining = 0;
    });
    hydrogenUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
        unit.startupTicksRemaining = 0;
    });

    // Reset sliders and inputs
    batterySlider.value = 0;
    hydroSlider.value = 0;
    batteryInput.value = 0;
    hydroInput.value = 0;
    solarCurtailmentSlider.value = 0;
    solarCurtailmentInput.value = 0;
    windCurtailmentSlider.value = 0;
    windCurtailmentInput.value = 0;
    updateSupplyValues();
    updateBatterySOCDisplay();
    updateCCGTDisplay();
    updateCCGTPowerSlider();
    updateCTDisplay();
    updateCTPowerSlider();
    updateRNGDisplay();
    updateRNGPowerSlider();
    updateHydrogenDisplay();
    updateHydrogenPowerSlider();
    updateTipsBanner();

    demandValueSpan.textContent = '--';
    deltaValueSpan.textContent = '--';
    currentCostValueSpan.textContent = '0';
    totalCostValueSpan.textContent = '0';

    // Hide next demand preview
    nextDemandPreview.classList.add('hidden');

    // Reset emergency and blackout counters
    emergencyAlertCount = 0;
    blackoutCount = 0;
    emergencyCountSpan.textContent = '0';
    blackoutCountSpan.textContent = '0';

    // Reset status banner to initial unstable state
    statusBanner.className = 'mb-4 px-4 py-3 rounded-lg text-center font-semibold text-lg transition-all duration-300 bg-blue-100 text-blue-800';
    statusBanner.textContent = '⚙️ Grid Unstable: Match Net Demand with Resources';

    // Show scheduler button for pre-game planning
    showSchedulerButton();

    // Re-enable controls for pre-game setup
    batterySlider.disabled = false;
    batteryInput.disabled = false;
    hydroSlider.disabled = false;
    hydroInput.disabled = false;
    solarCurtailmentSlider.disabled = false;
    solarCurtailmentInput.disabled = false;
    windCurtailmentSlider.disabled = false;
    windCurtailmentInput.disabled = false;
    ccgtCommitBtn.disabled = false;
    ctCommitBtn.disabled = false;

    // Clear supply chart data BEFORE switching back to forecast
    // During game, actual demand datasets are at 7-8, pushing supply to 9-16
    // We need to clear 9-16 if they exist, or 7-14 if game never started
    if (myChart.data.datasets.length > 15) {
        // Game was running: clear datasets at indices 9-16 (Battery, CCGT, CT, RNG, Hydrogen, Hydro, Solar Curtailment, Wind Curtailment)
        myChart.data.datasets[9].data = []; // Battery
        myChart.data.datasets[10].data = []; // CCGT
        myChart.data.datasets[11].data = []; // CT
        myChart.data.datasets[12].data = []; // RNG
        myChart.data.datasets[13].data = []; // Hydrogen
        myChart.data.datasets[14].data = []; // Hydro
        myChart.data.datasets[15].data = []; // Solar Curtailment
        myChart.data.datasets[16].data = []; // Wind Curtailment
    } else {
        // Game never started: clear datasets at indices 7-14
        myChart.data.datasets[7].data = []; // Battery
        myChart.data.datasets[8].data = []; // CCGT
        myChart.data.datasets[9].data = []; // CT
        myChart.data.datasets[10].data = []; // RNG
        myChart.data.datasets[11].data = []; // Hydrogen
        myChart.data.datasets[12].data = []; // Hydro
        myChart.data.datasets[13].data = []; // Solar Curtailment
        myChart.data.datasets[14].data = []; // Wind Curtailment
    }

    // Switch back to hourly forecast dots (removes actual demand datasets 7-8)
    switchToForecastData();

    // Now clear supply data at their reset positions (7-14)
    myChart.data.datasets[7].data = []; // Battery
    myChart.data.datasets[8].data = []; // CCGT
    myChart.data.datasets[9].data = []; // CT
    myChart.data.datasets[10].data = []; // RNG
    myChart.data.datasets[11].data = []; // Hydrogen
    myChart.data.datasets[12].data = []; // Hydro
    myChart.data.datasets[13].data = []; // Solar Curtailment
    myChart.data.datasets[14].data = []; // Wind Curtailment

    myChart.update();

    // Clear delta history chart
    deltaHistoryChart.data.labels = [];
    deltaHistoryChart.data.datasets[0].data = [];
    deltaHistoryChart.update('none');

    // Reset current time display
    currentTimeValue.textContent = '12:00 AM';

    // Show initial demand for tick 0
    showInitialDemand();
}

// --- 10. DELTA HISTORY CHART FUNCTIONS ---
function createDeltaHistoryChart() {
    const deltaHistoryCtx = document.getElementById('deltaHistoryChart').getContext('2d');

    deltaHistoryChart = new Chart(deltaHistoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Delta (MW)',
                data: [],
                borderColor: 'rgba(59, 130, 246, 1)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: {
                y: {
                    title: {
                        display: false
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    display: false
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += Math.round(context.parsed.y) + ' MW';
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

// Helper function to format time from game tick
function formatGameTime(tick) {
    const hour = Math.floor(tick / 12);
    const minute = (tick % 12) * 5;
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}:${minute.toString().padStart(2, '0')} ${period}`;
}

// --- 11. CAPACITY FACTOR CHART FUNCTIONS ---
function createCFChart() {
    const HOURS = Array.from({ length: 24 }, (_, i) => i.toString());
    const profile = seasonalProfilesData[selectedCountry].profiles[currentSeason];

    cfChart = new Chart(cfCtx, {
        type: 'line',
        data: {
            labels: HOURS,
            datasets: [
                {
                    label: 'Solar',
                    data: profile.solarCF.map(cf => cf * 100),
                    borderColor: 'rgba(251, 191, 36, 1)',
                    backgroundColor: 'rgba(251, 191, 36, 0.1)',
                    borderWidth: 3,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Wind',
                    data: profile.windCF.map(cf => cf * 100),
                    borderColor: 'rgba(52, 211, 153, 1)',
                    backgroundColor: 'rgba(52, 211, 153, 0.1)',
                    borderWidth: 3,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: {
                    position: 'bottom'
                },
                dragData: {
                    enabled: false,
                    round: 1,
                    showTooltip: true,
                    dragX: false,
                    onDrag: function(e, datasetIndex, index, value) {
                        // Enforce constraints DURING dragging for real-time feedback
                        if (value < 0) return 0;
                        if (value > 1) return 1;
                        return value;
                    },
                    onDragEnd: function(e, datasetIndex, index, value) {
                        let updatedValue = value;
                        // Capacity factors should be between 0 and 1 (0% to 100%)
                        if (value < 0) updatedValue = 0;
                        if (value > 1) updatedValue = 1;
                        cfChart.data.datasets[datasetIndex].data[index] = updatedValue;
                        cfChart.update('none');

                        // Mark CF profile as modified
                        isCFProfileModified = true;
                        if (isCFEditMode) {
                            currentCFProfileText.textContent = 'User Defined';
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time of Day (Hour)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Capacity Factor (%)'
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });

    currentCFProfileText.textContent = formatSeasonName(currentSeason);
}

function updateCFChart() {
    const profile = seasonalProfilesData[selectedCountry].profiles[currentSeason];

    cfChart.data.datasets[0].data = profile.solarCF.map(cf => cf * 100);
    cfChart.data.datasets[1].data = profile.windCF.map(cf => cf * 100);
    cfChart.update();

    // Update CF profile text
    if (isCFProfileModified) {
        currentCFProfileText.textContent = 'User Defined';
    } else {
        currentCFProfileText.textContent = formatSeasonName(currentSeason);
    }
    currentCFProfileName = formatSeasonName(currentSeason);
}

function enterCFEditMode() {
    isCFEditMode = true;

    // Save original CF values
    originalSolarCFBeforeEdit = [...cfChart.data.datasets[0].data];
    originalWindCFBeforeEdit = [...cfChart.data.datasets[1].data];

    // Show/hide buttons
    editCFBtn.classList.add('hidden');
    confirmCFBtn.classList.remove('hidden');
    revertCFBtn.classList.remove('hidden');
    cfPresetsDiv.classList.remove('hidden');

    // Enable drag on CF chart
    cfChart.data.datasets.forEach(dataset => {
        dataset.pointRadius = 6;
        dataset.pointHoverRadius = 8;
        dataset.pointBorderColor = 'white';
        dataset.pointBorderWidth = 2;
    });

    cfChart.options.plugins.dragData.enabled = true;
    cfChart.options.onHover = function(e) {
        const points = cfChart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
        if (points.length) {
            e.native.target.style.cursor = 'grab';
        } else {
            e.native.target.style.cursor = 'default';
        }
    };

    cfChart.update();
}

function confirmCFEdit() {
    isCFEditMode = false;

    // Save edited CF values back to profile
    const profile = seasonalProfilesData[selectedCountry].profiles[currentSeason];
    profile.solarCF = cfChart.data.datasets[0].data.map(cf => cf / 100);
    profile.windCF = cfChart.data.datasets[1].data.map(cf => cf / 100);

    // Regenerate forecast with new CF values
    forecastData = generateForecastFromProfile(currentSeason);
    updateChartData();

    // Update the Load Profile display text to match current season
    updateLoadProfileDisplay();

    // Show/hide buttons
    editCFBtn.classList.remove('hidden');
    confirmCFBtn.classList.add('hidden');
    revertCFBtn.classList.add('hidden');
    cfPresetsDiv.classList.add('hidden');

    // Disable drag on CF chart
    cfChart.data.datasets.forEach(dataset => {
        dataset.pointRadius = 0;
        dataset.pointHoverRadius = 0;
    });

    cfChart.options.plugins.dragData.enabled = false;
    cfChart.options.onHover = null;

    cfChart.update();
}

function revertCFEdit() {
    cfChart.data.datasets[0].data = [...originalSolarCFBeforeEdit];
    cfChart.data.datasets[1].data = [...originalWindCFBeforeEdit];
    cfChart.update('none');
}

function applyCFSeasonPreset(presetSeason) {
    // Restore original preset data for this season from pristine copy
    seasonalProfilesData[selectedCountry].profiles[presetSeason] =
        JSON.parse(JSON.stringify(originalSeasonalProfilesData[selectedCountry].profiles[presetSeason]));

    // Update current season
    currentSeason = presetSeason;
    isCFProfileModified = false; // Reset modified flag when applying preset

    // Load the new season's data
    const profile = seasonalProfilesData[selectedCountry].profiles[presetSeason];
    cfChart.data.datasets[0].data = profile.solarCF.map(cf => cf * 100);
    cfChart.data.datasets[1].data = profile.windCF.map(cf => cf * 100);
    cfChart.update('none');

    // Update the CF profile display text
    currentCFProfileText.textContent = presetSeason.charAt(0).toUpperCase() + presetSeason.slice(1);
}

// --- TUTORIAL LOGIC ---
const tutorialSteps = [
    {
        title: '🎮 Welcome to Grid Operator!',
        text: () => {
            // Use the display name from planner for proper country name
            return `You're in charge of ${selectedCountryDisplayName}'s electricity grid for 24 hours. Your mission: Match supply to net demand exactly while minimizing costs and avoiding blackouts. Perfect games qualify for the global leaderboard!`;
        },
        position: 'center'
    },
    {
        element: '#tutorial-step-2',
        title: '📊 Understanding the Chart',
        text: 'This chart shows 24-hour demand and generation. Renewable sources (solar, wind, nuclear, geothermal, biomass) are shown as colored areas. The RED LINE is Net Demand - what you need to match with flexible resources!',
        position: 'right',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-4',
        title: '⚡ Fast-Starting Gas Units',
        text: 'CCGT Units: 500 MW each, 75-min startup, 50% minimum load, $35+/MWh. CT Peakers: 200 MW each, 15-min startup, no minimum load, $65+/MWh. Click "Commit Unit" to start them up. These are expensive but reliable!',
        position: 'left',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-4',
        title: '🔋 Fast-Response Resources',
        text: 'Battery: ±13 GW, instant response, $5/MWh, 52 GWh capacity (watch SOC!). Hydro: 0-6 GW, very fast ramp, $2/MWh (cheapest!). Use these to follow rapid changes in demand and smooth out renewable variability.',
        position: 'left',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-4',
        title: '☀️ Renewable Curtailment',
        text: 'Solar & Wind Curtailment: When renewables exceed demand and your battery is full, curtail excess generation to avoid oversupply. Cost: $20/MWh. Range adjusts each tick based on actual generation. Use sparingly!',
        position: 'left',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-gauges',
        title: '📈 Live Gauges - Monitor Grid Health',
        text: 'Delta Gauge: Keep this NEAR ZERO!\n• Green (< 500 MW) = Grid Stable ✓\n• Yellow (500-1500 MW) = Emergency ⚠️\n• Red (> 1500 MW) = Blackout ⚠️⚠️\n\nFrequency Gauge: 60 Hz = perfect balance. Too low (undersupply) or too high (oversupply) means instability. Both gauges update in real-time!',
        position: 'right',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-5',
        title: '💰 Cost Tracking',
        text: 'Every resource has an operating cost. Minimize your total cost while maintaining stability! Costs per MWh: Hydro ($2), Battery ($5), Curtailment ($20), CCGT ($35+), CT ($65+). Strategy matters!',
        position: 'bottom',
        highlightClass: 'rounded-lg'
    },
    {
        title: '🎲 Random Events',
        text: 'Expect the unexpected! Cloud cover can suddenly reduce solar generation. Demand spikes can hit without warning. The game schedules 0-2 random events during your 24-hour shift. Stay alert and keep backup capacity ready!',
        position: 'center',
        onShow: () => {
            // Play both animations to demonstrate random events
            AnimationController.playCloudCover();
            setTimeout(() => {
                AnimationController.playDemandSpike();
            }, 2000); // Stagger the second animation
        }
    },
    {
        element: '#tutorial-step-game-speed',
        title: '⏱️ Game Speed Control',
        text: 'Adjust game speed from 0.1s to 30s per tick (each tick = 5 real-world minutes). Start slow to learn, then speed up for faster gameplay. You can pause anytime to plan your next moves!',
        position: 'bottom',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#openSchedulerBtn',
        title: '📅 Unit Commitment Scheduler (OPTIONAL)',
        text: 'Want to plan ahead? Schedule your entire day\'s dispatch BEFORE starting the game. Click to open the scheduler, plan your commits, shutdowns, and MW setpoints at 5-minute precision. When ready, hit "Apply Schedule" and watch the game execute your strategy automatically! Perfect for mastering those tricky morning ramps and evening demand peaks.',
        position: 'bottom',
        highlightClass: 'rounded-full'
    },
    {
        title: '🚦 Starting the Game',
        text: 'IMPORTANT: The "Start The Day" button is DISABLED until you achieve grid stability (delta < 500 MW). Set up your resources for 12:00 AM, watch the delta turn GREEN, then click start. This prevents starting with an unbalanced grid!',
        position: 'center'
    },
    {
        title: '💡 Pro Tips',
        text: 'Strategy: Plan ahead! CCGT takes 75 min to start. Anticipate the evening peak (18-21h) when solar fades and demand spikes. Charge battery during solar hours (11-14h). Use cheap hydro for baseload. Save expensive CT peakers for emergencies!',
        position: 'center'
    },
    {
        title: '🏆 Global Leaderboard',
        text: 'Perfect games (0 Emergency Alerts + 0 Blackouts) automatically qualify for the leaderboard! Compete globally for the LOWEST COST. Only the top 10 most efficient operators are displayed. Can you make it to the top?',
        position: 'center'
    },
    {
        title: '🎯 Ready to Operate!',
        text: 'You\'re now ready to run the grid! Balance supply and demand, minimize costs, avoid blackouts, and aim for a perfect game. Remember: Every decision counts. Good luck, Operator!',
        position: 'center'
    }
];

let currentTutorialStep = 0;
const tutorialOverlay = document.getElementById('tutorial-overlay');
const tutorialPopover = document.getElementById('tutorial-popover');
const tutorialTitleEl = document.getElementById('tutorial-title');
const tutorialTextEl = document.getElementById('tutorial-text');
const tutorialPrevBtn = document.getElementById('tutorial-prev');
const tutorialNextBtn = document.getElementById('tutorial-next');
const tutorialSkipBtn = document.getElementById('tutorial-skip');
let highlightedTutorialElement = null;

function startTutorial() {
    if (localStorage.getItem('gridOperatorTutorialSeen')) {
        return;
    }
    document.body.classList.add('tutorial-active');
    currentTutorialStep = 0;
    showTutorialStep(currentTutorialStep);
}

function endTutorial() {
    document.body.classList.remove('tutorial-active');
    tutorialOverlay.style.display = 'none';
    tutorialPopover.style.display = 'none';
    if (highlightedTutorialElement) {
        // Remove tutorial-highlight-active
        highlightedTutorialElement.classList.remove('tutorial-highlight-active');
        // Only remove the highlight class if we added it (not if it was already there)
        const addedClass = highlightedTutorialElement.getAttribute('data-tutorial-added-class');
        if (addedClass) {
            highlightedTutorialElement.classList.remove(addedClass);
            highlightedTutorialElement.removeAttribute('data-tutorial-added-class');
        }
        // Reset inline styles
        highlightedTutorialElement.style.position = '';
        highlightedTutorialElement.style.zIndex = '';
        highlightedTutorialElement = null;
    }
    localStorage.setItem('gridOperatorTutorialSeen', 'true');
}

function positionTutorialPopover(targetElement, popoverEl, position) {
    popoverEl.style.visibility = 'hidden';
    popoverEl.style.display = 'block';

    const rect = targetElement ? targetElement.getBoundingClientRect() : null;
    const popoverRect = popoverEl.getBoundingClientRect();
    let top, left;

    if (position === 'center') {
        top = window.innerHeight / 2 - popoverRect.height / 2;
        left = window.innerWidth / 2 - popoverRect.width / 2;
    } else if (position === 'right') {
        top = rect.top + rect.height / 2 - popoverRect.height / 2;
        left = rect.right + 20;
        if (left + popoverRect.width > window.innerWidth) {
            left = rect.left - popoverRect.width - 20;
        }
    } else if (position === 'left') {
        top = rect.top + rect.height / 2 - popoverRect.height / 2;
        left = rect.left - popoverRect.width - 20;
        if (left < 0) {
            left = rect.right + 20;
        }
    } else if (position === 'bottom') {
        top = rect.bottom + 20;
        left = rect.left + rect.width / 2 - popoverRect.width / 2;
        if (top + popoverRect.height > window.innerHeight) {
            top = rect.top - popoverRect.height - 20;
        }
    } else if (position === 'top') {
        top = rect.top - popoverRect.height - 20;
        left = rect.left + rect.width / 2 - popoverRect.width / 2;
        if (top < 0) {
            top = rect.bottom + 20;
        }
    }

    if (left < 10) left = 10;
    if (left + popoverRect.width > window.innerWidth - 10) {
        left = window.innerWidth - popoverRect.width - 10;
    }
    if (top < 10) top = 10;
    if (top + popoverRect.height > window.innerHeight - 10) {
        top = window.innerHeight - popoverRect.height - 10;
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

    if (highlightedTutorialElement) {
        // Remove tutorial-highlight-active
        highlightedTutorialElement.classList.remove('tutorial-highlight-active');
        // Only remove the highlight class if we added it (not if it was already there)
        const addedClass = highlightedTutorialElement.getAttribute('data-tutorial-added-class');
        if (addedClass) {
            highlightedTutorialElement.classList.remove(addedClass);
            highlightedTutorialElement.removeAttribute('data-tutorial-added-class');
        }
        // Reset inline styles that may have been added
        highlightedTutorialElement.style.position = '';
        highlightedTutorialElement.style.zIndex = '';
        highlightedTutorialElement = null;
    }

    tutorialTitleEl.textContent = step.title;
    // Handle text as either string or function
    tutorialTextEl.textContent = typeof step.text === 'function' ? step.text() : step.text;

    // Execute onShow callback if provided
    if (step.onShow && typeof step.onShow === 'function') {
        step.onShow();
    }

    if (step.element) {
        const targetElement = document.querySelector(step.element);
        if (targetElement) {
            tutorialOverlay.style.display = 'none';
            highlightedTutorialElement = targetElement;

            // Force positioning for highlight to work properly
            const currentPosition = window.getComputedStyle(targetElement).position;
            if (currentPosition === 'static') {
                highlightedTutorialElement.style.position = 'relative';
            }
            highlightedTutorialElement.style.zIndex = '9999';

            highlightedTutorialElement.classList.add('tutorial-highlight-active');
            // Store if the element already had the highlight class
            if (step.highlightClass && !highlightedTutorialElement.classList.contains(step.highlightClass)) {
                highlightedTutorialElement.classList.add(step.highlightClass);
                highlightedTutorialElement.setAttribute('data-tutorial-added-class', step.highlightClass);
            }

            highlightedTutorialElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
            setTimeout(() => {
                positionTutorialPopover(targetElement, tutorialPopover, step.position);
            }, 300);
        } else {
            // If element not found, show as center popup instead
            console.warn(`Tutorial element not found: ${step.element}`);
            tutorialOverlay.style.display = 'block';
            positionTutorialPopover(null, tutorialPopover, 'center');
        }
    } else {
        tutorialOverlay.style.display = 'block';
        positionTutorialPopover(null, tutorialPopover, 'center');
    }

    tutorialPrevBtn.style.display = stepIndex === 0 ? 'none' : 'inline-block';
    tutorialNextBtn.textContent = stepIndex === tutorialSteps.length - 1 ? 'Finish' : 'Next';
}

tutorialNextBtn.addEventListener('click', () => {
    currentTutorialStep++;
    showTutorialStep(currentTutorialStep);
});

tutorialPrevBtn.addEventListener('click', () => {
    currentTutorialStep--;
    showTutorialStep(currentTutorialStep);
});

tutorialSkipBtn.addEventListener('click', endTutorial);

showTutorialBtn.addEventListener('click', () => {
    localStorage.removeItem('gridOperatorTutorialSeen');
    startTutorial();
});

// --- LEADERBOARD FUNCTIONS ---
let playerUsername = localStorage.getItem('gridOperatorUsername') || '';

// Show username modal if no username is saved
function checkUsername() {
    if (!playerUsername) {
        usernameModal.classList.remove('hidden');
    } else {
        currentUsernameSpan.textContent = playerUsername;
    }
}

// Submit username
submitUsernameBtn.addEventListener('click', () => {
    const username = usernameInput.value.trim();
    if (username.length < 3) {
        alert('Username must be at least 3 characters long');
        return;
    }

    playerUsername = username;
    localStorage.setItem('gridOperatorUsername', username);
    currentUsernameSpan.textContent = username;
    usernameModal.classList.add('hidden');

    // Start tutorial after username is submitted (for new users)
    setTimeout(startTutorial, 500);
});

// Allow Enter key to submit username
usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitUsernameBtn.click();
    }
});

// Fetch and display leaderboard
async function fetchLeaderboard() {
    try {
        leaderboardLoading.classList.remove('hidden');
        leaderboardContent.classList.add('hidden');

        const response = await fetch(`${API_BASE_URL}/leaderboard`);
        const data = await response.json();

        leaderboardLoading.classList.add('hidden');
        leaderboardContent.classList.remove('hidden');

        if (data.success && data.leaderboard.length > 0) {
            displayLeaderboard(data.leaderboard);
            leaderboardEmpty.classList.add('hidden');
        } else {
            leaderboardList.innerHTML = '';
            leaderboardEmpty.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error fetching leaderboard:', error);
        leaderboardLoading.classList.add('hidden');
        leaderboardContent.classList.remove('hidden');
        leaderboardList.innerHTML = '<p class="text-center text-red-500">Failed to load leaderboard. Make sure the backend server is running.</p>';
    }
}

// Display leaderboard entries
function displayLeaderboard(entries) {
    leaderboardList.innerHTML = entries.map((entry, index) => {
        const rank = index + 1;
        const isCurrentPlayer = entry.username === playerUsername;
        const rankEmoji = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;

        return `
            <div class="flex items-center justify-between p-4 rounded-lg ${
                isCurrentPlayer ? 'bg-blue-50 border-2 border-blue-500' : 'bg-gray-50'
            } transition-all hover:shadow-md">
                <div class="flex items-center gap-4">
                    <span class="text-2xl font-bold ${rank <= 3 ? '' : 'text-gray-600'}">${rankEmoji}</span>
                    <div>
                        <p class="font-semibold text-gray-800 ${isCurrentPlayer ? 'text-blue-600' : ''}">
                            ${entry.username} ${isCurrentPlayer ? '(You!)' : ''}
                        </p>
                        <p class="text-xs text-gray-500">
                            ${new Date(entry.timestamp).toLocaleDateString()} • ${entry.season}
                        </p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="font-bold text-green-600">$${entry.totalCost.toLocaleString()}</p>
                    <p class="text-xs text-gray-500">Total Cost</p>
                </div>
            </div>
        `;
    }).join('');
}

// Submit score to leaderboard
async function submitScore() {
    if (!playerUsername) {
        alert('Please set a username first!');
        usernameModal.classList.remove('hidden');
        return;
    }

    // Only submit perfect games
    if (emergencyAlertCount !== 0 || blackoutCount !== 0) {
        return; // Don't submit imperfect games
    }

    try {
        const response = await fetch(`${API_BASE_URL}/leaderboard`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: playerUsername,
                totalCost: totalCost,
                emergencyAlerts: emergencyAlertCount,
                blackouts: blackoutCount,
                season: currentSeason
            })
        });

        const data = await response.json();

        if (data.success && data.rank) {
            // Show congratulations message
            alert(`🎉 ${data.message}\n\nYour cost: $${Math.round(totalCost).toLocaleString()}\n\nClick OK to view the leaderboard!`);
            showLeaderboard();
        }
    } catch (error) {
        console.error('Error submitting score:', error);
        alert('Failed to submit score to leaderboard. Make sure the backend server is running.');
    }
}

// Show leaderboard modal
function showLeaderboard() {
    leaderboardModal.classList.remove('hidden');
    fetchLeaderboard();
}

// Close leaderboard modal
closeLeaderboardBtn.addEventListener('click', () => {
    leaderboardModal.classList.add('hidden');
});

// Leaderboard button click
leaderboardBtn.addEventListener('click', showLeaderboard);

// Close modal when clicking outside
leaderboardModal.addEventListener('click', (e) => {
    if (e.target === leaderboardModal) {
        leaderboardModal.classList.add('hidden');
    }
});

// --- SCHEDULER MODULE ---
let schedulerChart = null;
let scheduledEvents = [];
let selectedScheduleTick = null;

// Scheduler DOM elements
const schedulerModal = document.getElementById('schedulerModal');
const openSchedulerBtn = document.getElementById('openSchedulerBtn');
const closeSchedulerBtn = document.getElementById('closeSchedulerBtn');
const applyScheduleBtn = document.getElementById('applyScheduleBtn');
const clearScheduleBtn = document.getElementById('clearScheduleBtn');
const schedulerButtonContainer = document.getElementById('schedulerButtonContainer');
const scheduledEventsList = document.getElementById('scheduledEventsList');
const resourceSelectionPanel = document.getElementById('resourceSelectionPanel');
const selectedTimeSpan = document.getElementById('selectedTime');
const totalScheduledMWSpan = document.getElementById('totalScheduledMW');

// Open scheduler modal
openSchedulerBtn.addEventListener('click', () => {
    schedulerModal.classList.remove('hidden');
    if (!schedulerChart) {
        createSchedulerChart();
    }

    // Hide CCGT/CT in scheduler if natural gas generation is 0% in planner
    if (plannerCapacityData && plannerCapacityData.dailyGenerationPercent) {
        const naturalGasGeneration = plannerCapacityData.dailyGenerationPercent.naturalGas || 0;
        if (naturalGasGeneration === 0) {
            // Hide CCGT section in scheduler
            const ccgtSchedulerContainer = document.querySelector('#schedulerModal .p-3.bg-blue-50.rounded-lg.border-blue-200');
            if (ccgtSchedulerContainer && ccgtSchedulerContainer.textContent.includes('CCGT')) {
                ccgtSchedulerContainer.style.display = 'none';
            }
            // Hide CT section in scheduler
            const ctSchedulerContainer = document.querySelector('#schedulerModal .p-3.bg-orange-50.rounded-lg.border-orange-200');
            if (ctSchedulerContainer && ctSchedulerContainer.textContent.includes('CT Peakers')) {
                ctSchedulerContainer.style.display = 'none';
            }
        }
    }

    // Set default selected time to 12:00 AM (tick 0) for easy start
    selectedScheduleTick = 0;
    selectedTimeSpan.textContent = '12:00 AM';

    // Update panel to show current state at 12:00 AM
    updateResourcePanelValues();
    updateShutdownButtonStates();

    // Initialize battery icon overlay
    updateBatteryIconOverlay();

    // Show scheduler tutorial on first visit
    const schedulerTutorialSeen = localStorage.getItem('gridOperatorSchedulerTutorialSeen');
    if (!schedulerTutorialSeen) {
        setTimeout(() => {
            showSchedulerQuickGuide();
        }, 500);
    }
});

// Show scheduler tutorial button event listener
document.getElementById('showSchedulerTutorialBtn').addEventListener('click', () => {
    showSchedulerQuickGuide();
});

// Scheduler quick guide
function showSchedulerQuickGuide() {
    const guide = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10000; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 500px; border: 3px solid #8b5cf6;">
            <h2 style="font-size: 1.5rem; font-weight: bold; color: #8b5cf6; margin-bottom: 1rem;">📅 Quick Scheduler Guide</h2>
            <div style="color: #374151; line-height: 1.6; margin-bottom: 1.5rem;">
                <p style="margin-bottom: 0.75rem;"><strong>1. Click Timeline</strong> - Select any 5-minute interval</p>
                <p style="margin-bottom: 0.75rem;"><strong>2. Add Resources</strong> - Commit/shutdown units or set MW levels</p>
                <p style="margin-bottom: 0.75rem;"><strong>3. Watch Chart</strong> - See your schedule visualized in real-time</p>
                <p style="margin-bottom: 0.75rem;"><strong>4. Apply Schedule</strong> - Lock it in and watch it execute automatically!</p>
                <p style="margin-top: 1rem; padding: 0.75rem; background: #f3f4f6; border-radius: 6px; font-size: 0.875rem;">
                    <strong>💡 Pro Tip:</strong> Hour 0 (12:00 AM) units start instantly. All other times respect startup delays (CCGT: 75 min, CT: 15 min).
                </p>
            </div>
            <button id="closeSchedulerGuide" style="width: 100%; padding: 0.75rem; background: linear-gradient(to right, #8b5cf6, #7c3aed); color: white; font-weight: 600; border-radius: 8px; border: none; cursor: pointer; font-size: 1rem;">
                Got it! Let's Schedule 🚀
            </button>
        </div>
        <div id="guideOverlay" style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); z-index: 9999;"></div>
    `;

    const guideContainer = document.createElement('div');
    guideContainer.id = 'schedulerGuideContainer';
    guideContainer.innerHTML = guide;
    document.body.appendChild(guideContainer);

    document.getElementById('closeSchedulerGuide').addEventListener('click', () => {
        document.getElementById('schedulerGuideContainer').remove();
        localStorage.setItem('gridOperatorSchedulerTutorialSeen', 'true');
    });

    document.getElementById('guideOverlay').addEventListener('click', () => {
        document.getElementById('schedulerGuideContainer').remove();
        localStorage.setItem('gridOperatorSchedulerTutorialSeen', 'true');
    });
}

// Close scheduler modal
closeSchedulerBtn.addEventListener('click', () => {
    schedulerModal.classList.add('hidden');
});

// Clear all scheduled events
clearScheduleBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to clear all scheduled events?')) {
        scheduledEvents = [];
        // Reset selected time to 12:00 AM (tick 0)
        selectedScheduleTick = 0;
        selectedTimeSpan.textContent = '12:00 AM';
        updateScheduledEventsList();
        updateSchedulerChartVisuals(); // This also updates battery overlay
        updateResourcePanelValues();
        updateShutdownButtonStates();
    }
});

// Apply schedule
applyScheduleBtn.addEventListener('click', applySchedule);

// Calculate end-of-day battery SOC based on schedule
function calculateEndOfDayBatterySOC() {
    const INITIAL_SOC_PERCENT = 0.2; // Start with 20% charge
    const TICK_DURATION_HOURS = 5 / 60; // 5 minutes = 1/12 hour

    let currentSOC = BATTERY_CAPACITY_MWH * INITIAL_SOC_PERCENT; // Starting energy in MWh
    let currentBatteryMW = 0; // Battery starts at 0 MW
    let lastEventTick = 0;

    // Sort events by tick
    const sortedEvents = [...scheduledEvents].sort((a, b) => a.tick - b.tick);

    for (const event of sortedEvents) {
        if (event.action === 'set_battery') {
            // Process the time period from last event to this event with current battery MW
            const ticksElapsed = event.tick - lastEventTick;
            // Note: Positive MW = discharging (decreases SOC), Negative MW = charging (increases SOC)
            const energyChange = -currentBatteryMW * TICK_DURATION_HOURS * ticksElapsed;
            currentSOC += energyChange;

            // Clamp SOC to valid range [0, BATTERY_CAPACITY_MWH]
            currentSOC = Math.max(0, Math.min(BATTERY_CAPACITY_MWH, currentSOC));

            // Update current battery MW for next period
            currentBatteryMW = event.value;
            lastEventTick = event.tick;
        }
    }

    // Process from last event to end of day (tick 287)
    if (lastEventTick < 287) {
        const ticksElapsed = 287 - lastEventTick;
        const energyChange = -currentBatteryMW * TICK_DURATION_HOURS * ticksElapsed;
        currentSOC += energyChange;

        // Clamp SOC to valid range [0, BATTERY_CAPACITY_MWH]
        currentSOC = Math.max(0, Math.min(BATTERY_CAPACITY_MWH, currentSOC));
    }

    // Return SOC as percentage (0-100)
    return (currentSOC / BATTERY_CAPACITY_MWH) * 100;
}

// Update battery icon overlay
function updateBatteryIconOverlay() {
    const overlay = document.getElementById('batteryIconOverlay');
    if (!overlay) return;

    const socPercent = calculateEndOfDayBatterySOC();
    const socText = overlay.querySelector('.battery-soc-text');
    const batteryFill = overlay.querySelector('.battery-fill');

    if (socText) {
        socText.textContent = `${Math.round(socPercent)}%`;
    }

    if (batteryFill) {
        batteryFill.style.height = `${socPercent}%`;

        // Change color based on SOC level
        if (socPercent < 20) {
            batteryFill.style.background = 'linear-gradient(to top, #ef4444, #f87171)'; // Red
        } else if (socPercent < 50) {
            batteryFill.style.background = 'linear-gradient(to top, #eab308, #fbbf24)'; // Yellow
        } else {
            batteryFill.style.background = 'linear-gradient(to top, #22c55e, #4ade80)'; // Green
        }
    }
}

// Create scheduler chart
function createSchedulerChart() {
    const canvas = document.getElementById('schedulerChart');
    const ctx = canvas.getContext('2d');

    // Generate 289 labels (0 to 288 inclusive, so we show 24:00)
    const labels = Array.from({ length: 289 }, (_, i) => {
        const hour = Math.floor(i / 12);
        const minute = (i % 12) * 5;
        return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
    });

    // Get net demand data from forecast - only hourly values (every 12th tick)
    const hourlyNetDemand = forecastData.filter((d, i) => i % 12 === 0).map(d => d.net_demand_mw);

    // Create sparse array with null values for non-hourly points, extend to 289
    const sparseNetDemand = Array.from({ length: 289 }, (_, i) => {
        if (i >= 288) return null; // No data for 24:00
        return i % 12 === 0 ? forecastData[i].net_demand_mw : null;
    });

    schedulerChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Net Demand (Hourly Forecast)',
                    data: sparseNetDemand,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.6)',
                    borderWidth: 0,
                    fill: false,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    showLine: false,  // Only show points, no connecting lines
                    spanGaps: false
                },
                // CCGT scheduled generation dataset
                {
                    label: 'CCGT',
                    data: Array(289).fill(0),
                    borderColor: 'rgba(59, 130, 246, 1)',
                    backgroundColor: 'rgba(59, 130, 246, 0.3)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true,
                    stack: 'generation'
                },
                // CT scheduled generation dataset
                {
                    label: 'CT',
                    data: Array(289).fill(0),
                    borderColor: 'rgba(249, 115, 22, 1)',
                    backgroundColor: 'rgba(249, 115, 22, 0.3)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true,
                    stack: 'generation'
                },
                // Battery scheduled output dataset
                {
                    label: 'Battery',
                    data: Array(289).fill(0),
                    borderColor: 'rgba(34, 197, 94, 1)',
                    backgroundColor: 'rgba(34, 197, 94, 0.3)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true,
                    stack: 'generation'
                },
                // Hydro scheduled output dataset
                {
                    label: 'Hydro',
                    data: Array(289).fill(0),
                    borderColor: 'rgba(6, 182, 212, 1)',
                    backgroundColor: 'rgba(6, 182, 212, 0.3)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true,
                    stack: 'generation'
                },
                // RNG scheduled generation dataset
                {
                    label: 'RNG',
                    data: Array(289).fill(0),
                    borderColor: 'rgba(132, 204, 22, 1)',
                    backgroundColor: 'rgba(132, 204, 22, 0.3)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true,
                    stack: 'generation'
                },
                // Hydrogen scheduled generation dataset
                {
                    label: 'Hydrogen',
                    data: Array(289).fill(0),
                    borderColor: 'rgba(99, 102, 241, 1)',
                    backgroundColor: 'rgba(99, 102, 241, 0.3)',
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true,
                    stack: 'generation'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: handleSchedulerChartClick,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += Math.round(context.parsed.y) + ' MW';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time of Day'
                    },
                    grid: {
                        color: function(context) {
                            // Make hour boundaries more visible
                            return context.index % 12 === 0 ? 'rgba(0, 0, 0, 0.15)' : 'rgba(0, 0, 0, 0.05)';
                        }
                    },
                    ticks: {
                        callback: function(value, index) {
                            // Show every 2 hours (24 ticks = every 12*2 = 24)
                            return index % 24 === 0 ? labels[index] : '';
                        },
                        maxRotation: 0,
                        autoSkip: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'MW'
                    },
                    stacked: true
                }
            }
        }
    });
}

// Handle click on scheduler chart
function handleSchedulerChartClick(event) {
    // Get the chart area and calculate the clicked position
    const chartArea = schedulerChart.chartArea;
    const canvasPosition = Chart.helpers.getRelativePosition(event, schedulerChart);

    // Only proceed if click was within chart area (with some tolerance on edges)
    if (canvasPosition.x >= (chartArea.left - 10) && canvasPosition.x <= (chartArea.right + 10) &&
        canvasPosition.y >= (chartArea.top - 10) && canvasPosition.y <= (chartArea.bottom + 10)) {

        // Calculate which tick was clicked based on x position
        const xScale = schedulerChart.scales.x;
        const xValue = xScale.getValueForPixel(canvasPosition.x);

        // Round to nearest tick and ensure it's within valid range
        selectedScheduleTick = Math.round(xValue);

        // Clamp to valid range: 0 to 287 (don't allow 288 which is 24:00)
        selectedScheduleTick = Math.max(0, Math.min(287, selectedScheduleTick));


        // Format time
        const hour = Math.floor(selectedScheduleTick / 12);
        const minute = (selectedScheduleTick % 12) * 5;
        const period = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
        const timeString = `${displayHour}:${minute.toString().padStart(2, '0')} ${period}`;

        selectedTimeSpan.textContent = timeString;

        // Update right panel to show currently scheduled values at this time
        updateResourcePanelValues();

        // Update shutdown button states based on current committed units
        updateShutdownButtonStates();
    }
}

// Add event listeners for resource action buttons
document.querySelectorAll('.resource-action-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const action = this.getAttribute('data-action');
        addScheduledEvent(action);
    });
});

// Add click-and-hold feature for commit buttons (rapid unit addition)
let holdInterval = null;
let holdTimeout = null;

document.querySelectorAll('.resource-action-btn').forEach(btn => {
    const action = btn.getAttribute('data-action');

    // Only add hold feature to commit buttons
    if (action && (action === 'commit_ccgt' || action === 'commit_ct' || action === 'commit_rng' || action === 'commit_hydrogen')) {
        btn.addEventListener('mousedown', function() {
            // Clear any existing intervals
            if (holdInterval) clearInterval(holdInterval);
            if (holdTimeout) clearTimeout(holdTimeout);

            // Start adding units after a short delay (500ms)
            holdTimeout = setTimeout(() => {
                holdInterval = setInterval(() => {
                    const success = addScheduledEvent(action);
                    // Stop interval if validation fails (reached capacity limit)
                    if (!success) {
                        if (holdInterval) clearInterval(holdInterval);
                        if (holdTimeout) clearTimeout(holdTimeout);
                        holdInterval = null;
                        holdTimeout = null;
                    }
                }, 150); // Add a unit every 150ms while holding
            }, 500);
        });

        btn.addEventListener('mouseup', function() {
            if (holdInterval) clearInterval(holdInterval);
            if (holdTimeout) clearTimeout(holdTimeout);
            holdInterval = null;
            holdTimeout = null;
        });

        btn.addEventListener('mouseleave', function() {
            if (holdInterval) clearInterval(holdInterval);
            if (holdTimeout) clearTimeout(holdTimeout);
            holdInterval = null;
            holdTimeout = null;
        });
    }
});

// Add Enter key listeners for Battery and Hydro inputs
document.getElementById('batteryMW').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        // Trigger the "Set MW Level" button for battery
        const batterySetBtn = document.querySelector('[data-action="set_battery"]');
        if (batterySetBtn) {
            batterySetBtn.click();
        }
    }
});

document.getElementById('hydroMW').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        // Trigger the "Set MW Level" button for hydro
        const hydroSetBtn = document.querySelector('[data-action="set_hydro"]');
        if (hydroSetBtn) {
            hydroSetBtn.click();
        }
    }
});

// Validate battery State of Charge (SOC) with new scheduled value
function validateBatterySOC(newBatteryMW, atTick) {
    const INITIAL_SOC_PERCENT = 0.2; // Start with 20% charge
    const TICK_DURATION_HOURS = 5 / 60; // 5 minutes = 1/12 hour

    let currentSOC = BATTERY_CAPACITY_MWH * INITIAL_SOC_PERCENT; // Starting energy in MWh

    // Create a temporary schedule including the new value
    const tempSchedule = [...scheduledEvents];

    // Add the new battery event to temp schedule
    tempSchedule.push({
        tick: atTick,
        action: 'set_battery',
        value: newBatteryMW
    });

    // Sort by tick
    tempSchedule.sort((a, b) => a.tick - b.tick);

    // Simulate battery SOC from tick 0 to tick 287 (24 hours)
    let currentBatteryMW = 0; // Battery starts at 0 MW
    let lastEventTick = 0;

    for (const event of tempSchedule) {
        if (event.action === 'set_battery') {
            // Process the time period from last event to this event with current battery MW
            const ticksElapsed = event.tick - lastEventTick;
            // Note: Positive MW = discharging (decreases SOC), Negative MW = charging (increases SOC)
            const energyChange = -currentBatteryMW * TICK_DURATION_HOURS * ticksElapsed;
            const previousSOC = currentSOC;
            currentSOC += energyChange;

            // Check if SOC went out of bounds during this period
            if (currentSOC < 0) {
                // Calculate exact tick where battery would reach 0%
                // Energy removed per tick = currentBatteryMW × TICK_DURATION_HOURS (when discharging, currentBatteryMW > 0)
                const ticksToEmpty = Math.floor(previousSOC / (currentBatteryMW * TICK_DURATION_HOURS));
                const stopTick = Math.min(287, Math.max(lastEventTick + ticksToEmpty, lastEventTick + 1));
                const timeStr = formatGameTime(stopTick);

                // Determine if the violation is due to charging or discharging
                const actionType = currentBatteryMW > 0 ? "discharging" : "charging";

                return {
                    valid: false,
                    stopTick: stopTick,
                    message: `Schedule conflict: Battery would fully discharge at ${timeStr} (due to ${actionType} at ${Math.abs(currentBatteryMW)} MW).\n\nAutomatically adding stop event to set battery to 0 MW at ${timeStr}.`
                };
            }
            if (currentSOC > BATTERY_CAPACITY_MWH) {
                // Calculate exact tick where battery would reach 100%
                // Energy added per tick = -currentBatteryMW × TICK_DURATION_HOURS (when charging, currentBatteryMW < 0)
                const remainingCapacity = BATTERY_CAPACITY_MWH - previousSOC;
                const ticksToFull = Math.floor(remainingCapacity / (-currentBatteryMW * TICK_DURATION_HOURS));
                const stopTick = Math.min(287, Math.max(lastEventTick + ticksToFull, lastEventTick + 1));
                const timeStr = formatGameTime(stopTick);

                return {
                    valid: false,
                    stopTick: stopTick,
                    message: `Battery would reach full capacity (100%) at ${timeStr} while charging at ${Math.abs(currentBatteryMW)} MW.\n\nAutomatically adding stop event to set battery to 0 MW at ${timeStr}.`
                };
            }

            // Update current battery MW for next period
            currentBatteryMW = event.value;
            lastEventTick = event.tick;
        }
    }

    // Check from last event to end of day (tick 287)
    if (lastEventTick < 287) {
        const ticksElapsed = 287 - lastEventTick;
        const energyChange = -currentBatteryMW * TICK_DURATION_HOURS * ticksElapsed;
        const previousSOC = currentSOC;
        currentSOC += energyChange;

        if (currentSOC < 0) {
            // Calculate exact tick where battery would reach 0%
            const ticksToEmpty = Math.floor(previousSOC / (currentBatteryMW * TICK_DURATION_HOURS));
            const stopTick = Math.min(287, Math.max(lastEventTick + ticksToEmpty, lastEventTick + 1));
            const timeStr = formatGameTime(stopTick);

            // Determine if the violation is due to charging or discharging
            const actionType = currentBatteryMW > 0 ? "discharging" : "charging";

            return {
                valid: false,
                stopTick: stopTick,
                message: `Schedule conflict: Battery would fully discharge at ${timeStr} (due to ${actionType} at ${Math.abs(currentBatteryMW)} MW).\n\nAutomatically adding stop event to set battery to 0 MW at ${timeStr}.`
            };
        }
        if (currentSOC > BATTERY_CAPACITY_MWH) {
            // Calculate exact tick where battery would reach 100%
            const remainingCapacity = BATTERY_CAPACITY_MWH - previousSOC;
            const ticksToFull = Math.floor(remainingCapacity / (-currentBatteryMW * TICK_DURATION_HOURS));
            const stopTick = Math.min(287, Math.max(lastEventTick + ticksToFull, lastEventTick + 1));
            const timeStr = formatGameTime(stopTick);

            return {
                valid: false,
                stopTick: stopTick,
                message: `Battery would reach full capacity (100%) at ${timeStr} while charging at ${Math.abs(currentBatteryMW)} MW.\n\nAutomatically adding stop event to set battery to 0 MW at ${timeStr}.`
            };
        }
    }

    return { valid: true };
}

// Add scheduled event (returns true if successful, false if validation failed)
function addScheduledEvent(action) {
    if (selectedScheduleTick === null) {
        alert('Please select a time on the timeline first');
        return false;
    }

    let eventData = {
        tick: selectedScheduleTick,
        action: action,
        time: selectedTimeSpan.textContent
    };

    // Get specific values based on action
    switch(action) {
        case 'commit_ccgt':
            eventData.count = 1; // Always commit 1 unit per click
            // Hour 0 (tick 0) has instant startup, otherwise 75 min delay
            eventData.effectiveTick = selectedScheduleTick === 0 ? 0 : selectedScheduleTick + 15;
            break;
        case 'shutdown_ccgt':
            // Check if there are CCGT units online to shut down
            {
                let currentCCGTOnline = 0;
                scheduledEvents.forEach(event => {
                    if (event.action === 'commit_ccgt' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
                        currentCCGTOnline += event.count;
                    } else if (event.action === 'shutdown_ccgt' && event.tick <= selectedScheduleTick) {
                        currentCCGTOnline = Math.max(0, currentCCGTOnline - event.count);
                    }
                });

                if (currentCCGTOnline === 0) {
                    alert('No CCGT units are currently online to shut down at this time.');
                    return false;
                }
            }
            eventData.count = 1; // Always shutdown 1 unit per click
            break;
        case 'commit_ct':
            eventData.count = 1; // Always commit 1 unit per click
            // Hour 0 (tick 0) has instant startup, otherwise 15 min delay
            eventData.effectiveTick = selectedScheduleTick === 0 ? 0 : selectedScheduleTick + 3;
            break;
        case 'shutdown_ct':
            // Check if there are CT units online to shut down
            {
                let currentCTOnline = 0;
                scheduledEvents.forEach(event => {
                    if (event.action === 'commit_ct' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
                        currentCTOnline += event.count;
                    } else if (event.action === 'shutdown_ct' && event.tick <= selectedScheduleTick) {
                        currentCTOnline = Math.max(0, currentCTOnline - event.count);
                    }
                });

                if (currentCTOnline === 0) {
                    alert('No CT units are currently online to shut down at this time.');
                    return false;
                }
            }
            eventData.count = 1; // Always shutdown 1 unit per click
            break;
        case 'commit_rng':
            // Check if we can commit another RNG unit
            {
                if (RNG_MAX_UNITS === 0) {
                    alert('No RNG capacity available. Please configure RNG capacity in the Grid Planner.');
                    return false;
                }

                // Calculate the effective tick for this new commit
                const newEffectiveTick = selectedScheduleTick === 0 ? 0 : selectedScheduleTick + 6;

                // Count units online at the effective tick (when this new unit would come online)
                let currentRNGOnline = 0;
                scheduledEvents.forEach(event => {
                    if (event.action === 'commit_rng' && event.effectiveTick !== undefined && event.effectiveTick <= newEffectiveTick) {
                        currentRNGOnline += event.count;
                    } else if (event.action === 'shutdown_rng' && event.tick <= newEffectiveTick) {
                        currentRNGOnline = Math.max(0, currentRNGOnline - event.count);
                    }
                });

                // Check unit count limit
                if (currentRNGOnline >= RNG_MAX_UNITS) {
                    const totalCapacityMW = plannerCapacityData?.totalCapacityMW?.rng || (RNG_MAX_UNITS * RNG_UNIT_SIZE_MW);
                    alert(`Cannot commit more RNG units. Maximum capacity is ${RNG_MAX_UNITS} units (${Math.round(totalCapacityMW)} MW).`);
                    return false;
                }

                // Additional safety check: validate total MW doesn't exceed planner capacity
                const currentRNGMW = calculateRNGMW(currentRNGOnline);
                const newRNGMW = calculateRNGMW(currentRNGOnline + 1);
                const totalCapacityMW = plannerCapacityData?.totalCapacityMW?.rng || (RNG_MAX_UNITS * RNG_UNIT_SIZE_MW);
                if (newRNGMW > totalCapacityMW) {
                    alert(`Cannot commit more RNG units. This would exceed maximum capacity.\n\nCurrent: ${Math.round(currentRNGMW)} MW\nRequested: ${Math.round(newRNGMW)} MW\nMaximum: ${Math.round(totalCapacityMW)} MW`);
                    return false;
                }

                eventData.effectiveTick = newEffectiveTick;
            }
            eventData.count = 1; // Always commit 1 unit per click
            break;
        case 'shutdown_rng':
            // Check if there are RNG units online to shut down
            {
                let currentRNGOnline = 0;
                scheduledEvents.forEach(event => {
                    if (event.action === 'commit_rng' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
                        currentRNGOnline += event.count;
                    } else if (event.action === 'shutdown_rng' && event.tick <= selectedScheduleTick) {
                        currentRNGOnline = Math.max(0, currentRNGOnline - event.count);
                    }
                });

                if (currentRNGOnline === 0) {
                    alert('No RNG units are currently online to shut down at this time.');
                    return false;
                }
            }
            eventData.count = 1; // Always shutdown 1 unit per click
            break;
        case 'commit_hydrogen':
            // Check if we can commit another Hydrogen unit
            {
                if (HYDROGEN_MAX_UNITS === 0) {
                    alert('No Hydrogen capacity available. Please configure Hydrogen capacity in the Grid Planner.');
                    return false;
                }

                // Calculate the effective tick for this new commit
                const newEffectiveTick = selectedScheduleTick === 0 ? 0 : selectedScheduleTick + 9;

                // Count units online at the effective tick (when this new unit would come online)
                let currentHydrogenOnline = 0;
                scheduledEvents.forEach(event => {
                    if (event.action === 'commit_hydrogen' && event.effectiveTick !== undefined && event.effectiveTick <= newEffectiveTick) {
                        currentHydrogenOnline += event.count;
                    } else if (event.action === 'shutdown_hydrogen' && event.tick <= newEffectiveTick) {
                        currentHydrogenOnline = Math.max(0, currentHydrogenOnline - event.count);
                    }
                });

                // Check unit count limit
                if (currentHydrogenOnline >= HYDROGEN_MAX_UNITS) {
                    const totalCapacityMW = plannerCapacityData?.totalCapacityMW?.hydrogen || (HYDROGEN_MAX_UNITS * HYDROGEN_UNIT_SIZE_MW);
                    alert(`Cannot commit more Hydrogen units. Maximum capacity is ${HYDROGEN_MAX_UNITS} units (${Math.round(totalCapacityMW)} MW).`);
                    return false;
                }

                // Additional safety check: validate total MW doesn't exceed planner capacity
                const currentHydrogenMW = calculateHydrogenMW(currentHydrogenOnline);
                const newHydrogenMW = calculateHydrogenMW(currentHydrogenOnline + 1);
                const totalCapacityMW = plannerCapacityData?.totalCapacityMW?.hydrogen || (HYDROGEN_MAX_UNITS * HYDROGEN_UNIT_SIZE_MW);
                if (newHydrogenMW > totalCapacityMW) {
                    alert(`Cannot commit more Hydrogen units. This would exceed maximum capacity.\n\nCurrent: ${Math.round(currentHydrogenMW)} MW\nRequested: ${Math.round(newHydrogenMW)} MW\nMaximum: ${Math.round(totalCapacityMW)} MW`);
                    return false;
                }

                eventData.effectiveTick = newEffectiveTick;
            }
            eventData.count = 1; // Always commit 1 unit per click
            break;
        case 'shutdown_hydrogen':
            // Check if there are Hydrogen units online to shut down
            {
                let currentHydrogenOnline = 0;
                scheduledEvents.forEach(event => {
                    if (event.action === 'commit_hydrogen' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
                        currentHydrogenOnline += event.count;
                    } else if (event.action === 'shutdown_hydrogen' && event.tick <= selectedScheduleTick) {
                        currentHydrogenOnline = Math.max(0, currentHydrogenOnline - event.count);
                    }
                });

                if (currentHydrogenOnline === 0) {
                    alert('No Hydrogen units are currently online to shut down at this time.');
                    return false;
                }
            }
            eventData.count = 1; // Always shutdown 1 unit per click
            break;
        case 'set_battery':
            {
                let batteryMW = parseInt(document.getElementById('batteryMW').value);

                // Validation 1: Auto-cap battery power to maximum capacity
                if (Math.abs(batteryMW) > BATTERY_POWER_MW) {
                    const cappedValue = batteryMW > 0 ? BATTERY_POWER_MW : -BATTERY_POWER_MW;
                    alert(`Battery power cannot exceed ${BATTERY_POWER_MW} MW.\n\nRequested: ${batteryMW} MW\nScheduling at maximum: ${cappedValue} MW`);
                    batteryMW = cappedValue;
                }

                // Remove ALL existing auto-generated battery stop events before recalculating
                scheduledEvents = scheduledEvents.filter(e => !(e.action === 'set_battery' && e.autoGenerated === true));

                // CONSOLIDATION: Remove any existing battery event at the same tick (to avoid redundancy)
                // Also remove their linked events
                const existingBatteryEventsAtTick = scheduledEvents.filter(e =>
                    e.action === 'set_battery' &&
                    e.tick === selectedScheduleTick
                );

                for (const existingEvent of existingBatteryEventsAtTick) {
                    // If this event is linked, remove all events with the same linkedEventId
                    if (existingEvent.linkedEventId) {
                        scheduledEvents = scheduledEvents.filter(e => e.linkedEventId !== existingEvent.linkedEventId);
                    } else {
                        // Just remove this single event
                        const index = scheduledEvents.indexOf(existingEvent);
                        if (index !== -1) {
                            scheduledEvents.splice(index, 1);
                        }
                    }
                }

                // Validation 2: Check battery energy capacity (SOC tracking) and auto-add stop events
                const socValidation = validateBatterySOC(batteryMW, selectedScheduleTick);
                if (!socValidation.valid) {
                    // Auto-add stop event at the time battery would reach limit
                    if (socValidation.stopTick !== undefined) {
                        alert(socValidation.message);

                        // Generate unique ID for linking the two events
                        const linkId = `battery_${Date.now()}_${Math.random()}`;

                        eventData.value = batteryMW;
                        eventData.linkedEventId = linkId;

                        // Add the initial event
                        scheduledEvents.push(eventData);

                        // Add automatic stop event
                        const stopEventData = {
                            tick: socValidation.stopTick,
                            action: 'set_battery',
                            time: formatGameTime(socValidation.stopTick),
                            value: 0,
                            autoGenerated: true,
                            linkedEventId: linkId
                        };
                        scheduledEvents.push(stopEventData);
                        scheduledEvents.sort((a, b) => a.tick - b.tick);

                        updateScheduledEventsList();
                        updateSchedulerChartVisuals();
                        updateResourcePanelValues();
                        updateShutdownButtonStates();
                        return true; // Successfully added battery schedule with auto-stop
                    }
                }

                eventData.value = batteryMW;
            }
            break;
        case 'set_hydro':
            {
                let hydroMW = parseInt(document.getElementById('hydroMW').value);

                // Validation 1: Auto-cap hydro to 0 if negative
                if (hydroMW < 0) {
                    alert(`Hydro power cannot be negative.\n\nRequested: ${hydroMW} MW\nScheduling at minimum: 0 MW`);
                    hydroMW = 0;
                }

                // Validation 2: Auto-cap hydro to maximum capacity
                if (hydroMW > currentHydroMaxMW) {
                    alert(`Hydro power cannot exceed maximum capacity.\n\nRequested: ${hydroMW} MW\nScheduling at maximum: ${currentHydroMaxMW} MW (${Object.keys(HYDRO_CAPACITY).find(key => HYDRO_CAPACITY[key] === currentHydroMaxMW)} year)`);
                    hydroMW = currentHydroMaxMW;
                }

                // CONSOLIDATION: Remove any existing hydro event at the same tick (to avoid redundancy)
                const existingHydroAtTick = scheduledEvents.find(e =>
                    e.action === 'set_hydro' &&
                    e.tick === selectedScheduleTick
                );
                if (existingHydroAtTick) {
                    const existingIndex = scheduledEvents.indexOf(existingHydroAtTick);
                    scheduledEvents.splice(existingIndex, 1);
                }

                eventData.value = hydroMW;
            }
            break;
    }

    scheduledEvents.push(eventData);
    scheduledEvents.sort((a, b) => a.tick - b.tick); // Keep sorted by tick

    updateScheduledEventsList();
    updateSchedulerChartVisuals();
    updateResourcePanelValues();
    updateShutdownButtonStates();
    return true; // Success
}

// Update scheduled events list display
function updateScheduledEventsList() {
    if (scheduledEvents.length === 0) {
        scheduledEventsList.innerHTML = '<p class="text-sm text-gray-400 italic">No events scheduled yet. Click on the timeline to add events.</p>';
        return;
    }

    const eventIcons = {
        'commit_ccgt': '⚡',
        'shutdown_ccgt': '⛔',
        'commit_ct': '🔥',
        'shutdown_ct': '⛔',
        'commit_rng': '🌱',
        'shutdown_rng': '⛔',
        'commit_hydrogen': '⚗️',
        'shutdown_hydrogen': '⛔',
        'set_battery': '🔋',
        'set_hydro': '💧'
    };

    const eventNames = {
        'commit_ccgt': 'Commit CCGT',
        'shutdown_ccgt': 'Shutdown CCGT',
        'commit_ct': 'Commit CT',
        'shutdown_ct': 'Shutdown CT',
        'commit_rng': 'Commit RNG',
        'shutdown_rng': 'Shutdown RNG',
        'commit_hydrogen': 'Commit Hydrogen',
        'shutdown_hydrogen': 'Shutdown Hydrogen',
        'set_battery': 'Set Battery',
        'set_hydro': 'Set Hydro'
    };

    const renderedCards = [];
    const processedLinkIds = new Set();

    scheduledEvents.forEach((event, index) => {
        // Skip auto-generated events - they'll be shown with their parent
        if (event.autoGenerated) {
            return;
        }

        // Skip if we already processed this link
        if (event.linkedEventId && processedLinkIds.has(event.linkedEventId)) {
            return;
        }

        let details = '';
        if (event.count) {
            details = `${event.count} unit(s)`;
        } else if (event.value !== undefined) {
            details = `${event.value} MW`;
        }

        let effectiveInfo = '';
        if (event.effectiveTick !== undefined) {
            if (event.effectiveTick === event.tick) {
                effectiveInfo = `<span class="text-xs text-green-600 font-semibold">⚡ Instant</span>`;
            } else {
                const effHour = Math.floor(event.effectiveTick / 12);
                const effMinute = (event.effectiveTick % 12) * 5;
                const effPeriod = effHour >= 12 ? 'PM' : 'AM';
                const effDisplayHour = effHour === 0 ? 12 : effHour > 12 ? effHour - 12 : effHour;
                effectiveInfo = `<span class="text-xs text-gray-500">→ Online: ${effDisplayHour}:${effMinute.toString().padStart(2, '0')} ${effPeriod}</span>`;
            }
        }

        // Check if this event has a linked auto-stop event
        let autoStopInfo = '';
        if (event.linkedEventId) {
            const linkedEvent = scheduledEvents.find(e =>
                e.linkedEventId === event.linkedEventId &&
                e.autoGenerated === true
            );
            if (linkedEvent) {
                autoStopInfo = `
                    <div class="text-xs text-purple-700 ml-7 mt-1 bg-purple-50 px-2 py-1 rounded inline-block">
                        <span class="font-semibold">AUTO-STOP</span> @ ${linkedEvent.time}
                    </div>
                `;
                processedLinkIds.add(event.linkedEventId);
            }
        }

        const card = `
            <div class="flex items-center justify-between p-2 bg-white rounded border border-gray-200 hover:border-blue-400 transition-colors">
                <div class="flex-1">
                    <div class="flex items-center gap-2">
                        <span class="text-lg">${eventIcons[event.action]}</span>
                        <span class="text-sm font-medium">${eventNames[event.action]}</span>
                        <span class="text-sm text-gray-600">${details}</span>
                    </div>
                    <div class="text-xs text-gray-500 ml-7">@ ${event.time} ${effectiveInfo}</div>
                    ${autoStopInfo}
                </div>
                <button onclick="deleteScheduledEvent(${index})" class="text-red-500 hover:text-red-700 px-2 self-center" title="${event.linkedEventId ? 'Delete both events' : 'Delete event'}">
                    🗑️
                </button>
            </div>
        `;
        renderedCards.push(card);
    });

    scheduledEventsList.innerHTML = renderedCards.join('');
}

// Delete scheduled event
function deleteScheduledEvent(index) {
    const eventToDelete = scheduledEvents[index];

    // If this event is linked to another event, delete both
    if (eventToDelete.linkedEventId) {
        const linkId = eventToDelete.linkedEventId;
        // Remove all events with this linkedEventId
        scheduledEvents = scheduledEvents.filter(e => e.linkedEventId !== linkId);
    } else {
        // Just delete this single event
        scheduledEvents.splice(index, 1);
    }

    updateScheduledEventsList();
    updateSchedulerChartVisuals();
    updateResourcePanelValues();
    updateShutdownButtonStates();
}

// Update chart visuals to show scheduled generation
function updateSchedulerChartVisuals() {
    // Initialize arrays for each resource type (289 to include 24:00)
    const ccgtData = Array(289).fill(0);
    const ctData = Array(289).fill(0);
    const batteryData = Array(289).fill(0);
    const hydroData = Array(289).fill(0);
    const rngData = Array(289).fill(0);
    const hydrogenData = Array(289).fill(0);

    // Track current committed units throughout the day
    let currentCCGT = 0;
    let currentCT = 0;
    let currentBattery = 0;
    let currentHydro = 0;
    let currentRNG = 0;
    let currentHydrogen = 0;

    // Track battery SOC to enforce physical constraints in visualization
    const INITIAL_SOC_PERCENT = 0.2;
    const TICK_DURATION_HOURS = 5 / 60; // 5 minutes = 1/12 hour
    let batterySOC = BATTERY_CAPACITY_MWH * INITIAL_SOC_PERCENT;

    // Process each tick and apply scheduled events
    for (let tick = 0; tick < 289; tick++) {
        // Only process actual ticks (0-287)
        if (tick < 288) {
            // Check for events that become effective at this tick
            scheduledEvents.forEach(event => {
                if (event.action === 'commit_ccgt' && event.effectiveTick === tick) {
                    currentCCGT += event.count;
                } else if (event.action === 'shutdown_ccgt' && event.tick === tick) {
                    currentCCGT = Math.max(0, currentCCGT - event.count);
                } else if (event.action === 'commit_ct' && event.effectiveTick === tick) {
                    currentCT += event.count;
                } else if (event.action === 'shutdown_ct' && event.tick === tick) {
                    currentCT = Math.max(0, currentCT - event.count);
                } else if (event.action === 'set_battery' && event.tick === tick) {
                    currentBattery = event.value;
                } else if (event.action === 'set_hydro' && event.tick === tick) {
                    currentHydro = event.value;
                } else if (event.action === 'commit_rng' && event.effectiveTick === tick) {
                    currentRNG += event.count;
                } else if (event.action === 'shutdown_rng' && event.tick === tick) {
                    currentRNG = Math.max(0, currentRNG - event.count);
                } else if (event.action === 'commit_hydrogen' && event.effectiveTick === tick) {
                    currentHydrogen += event.count;
                } else if (event.action === 'shutdown_hydrogen' && event.tick === tick) {
                    currentHydrogen = Math.max(0, currentHydrogen - event.count);
                }
            });

            // Enforce battery SOC constraints BEFORE applying to chart
            let actualBatteryMW = currentBattery;
            if (batterySOC <= 0.01 && currentBattery > 0) {
                // Battery empty, cannot discharge
                actualBatteryMW = 0;
            } else if (batterySOC >= BATTERY_CAPACITY_MWH * 0.99 && currentBattery < 0) {
                // Battery full, cannot charge
                actualBatteryMW = 0;
            }

            // Update battery SOC for next tick based on actual battery MW
            const energyChangeMWh = -actualBatteryMW * TICK_DURATION_HOURS;
            batterySOC = Math.max(0, Math.min(BATTERY_CAPACITY_MWH, batterySOC + energyChangeMWh));

            // Use actual battery MW (after SOC constraints) for chart
            currentBattery = actualBatteryMW;
        }

        // Set data for this tick (carry forward to 24:00)
        ccgtData[tick] = currentCCGT * CCGT_UNIT_SIZE_MW;
        ctData[tick] = currentCT * CT_UNIT_SIZE_MW;
        batteryData[tick] = currentBattery;
        hydroData[tick] = currentHydro;
        rngData[tick] = calculateRNGMW(currentRNG);
        hydrogenData[tick] = calculateHydrogenMW(currentHydrogen);
    }

    // Update chart datasets
    schedulerChart.data.datasets[1].data = ccgtData;  // CCGT
    schedulerChart.data.datasets[2].data = ctData;    // CT
    schedulerChart.data.datasets[3].data = batteryData; // Battery
    schedulerChart.data.datasets[4].data = hydroData;  // Hydro
    schedulerChart.data.datasets[5].data = rngData;    // RNG
    schedulerChart.data.datasets[6].data = hydrogenData; // Hydrogen
    schedulerChart.update('none');

    // Update battery icon overlay
    updateBatteryIconOverlay();
}

// Update resource panel to show currently scheduled values at selected time
function updateResourcePanelValues() {
    if (selectedScheduleTick === null) return;

    // Calculate what resources are scheduled at the selected tick
    let ccgtOnline = 0;
    let ctOnline = 0;
    let batteryMW = 0;
    let hydroMW = 0;
    let rngOnline = 0;
    let hydrogenOnline = 0;

    // Process all events up to and including the selected tick
    scheduledEvents.forEach(event => {
        if (event.action === 'commit_ccgt' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
            ccgtOnline += event.count;
        } else if (event.action === 'shutdown_ccgt' && event.tick <= selectedScheduleTick) {
            ccgtOnline = Math.max(0, ccgtOnline - event.count);
        } else if (event.action === 'commit_ct' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
            ctOnline += event.count;
        } else if (event.action === 'shutdown_ct' && event.tick <= selectedScheduleTick) {
            ctOnline = Math.max(0, ctOnline - event.count);
        } else if (event.action === 'set_battery' && event.tick <= selectedScheduleTick) {
            batteryMW = event.value;
        } else if (event.action === 'set_hydro' && event.tick <= selectedScheduleTick) {
            hydroMW = event.value;
        } else if (event.action === 'commit_rng' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
            rngOnline += event.count;
        } else if (event.action === 'shutdown_rng' && event.tick <= selectedScheduleTick) {
            rngOnline = Math.max(0, rngOnline - event.count);
        } else if (event.action === 'commit_hydrogen' && event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
            hydrogenOnline += event.count;
        } else if (event.action === 'shutdown_hydrogen' && event.tick <= selectedScheduleTick) {
            hydrogenOnline = Math.max(0, hydrogenOnline - event.count);
        }
    });

    // Update the input values in the panel (only for Battery and Hydro)
    document.getElementById('batteryMW').value = batteryMW;
    document.getElementById('hydroMW').value = hydroMW;

    // Calculate total scheduled generation MW at this tick
    const totalMW = (ccgtOnline * CCGT_UNIT_SIZE_MW) + (ctOnline * CT_UNIT_SIZE_MW) + batteryMW + hydroMW + calculateRNGMW(rngOnline) + calculateHydrogenMW(hydrogenOnline);
    totalScheduledMWSpan.textContent = Math.round(totalMW).toLocaleString();

    // Add visual indicators showing current scheduled values
    const ccgtLabel = document.querySelector('[data-action="commit_ccgt"]').closest('.p-3').querySelector('label');
    const ctLabel = document.querySelector('[data-action="commit_ct"]').closest('.p-3').querySelector('label');
    const batteryLabel = document.querySelector('[data-action="set_battery"]').closest('.p-3').querySelector('label');
    const hydroLabel = document.querySelector('[data-action="set_hydro"]').closest('.p-3').querySelector('label');
    const rngLabel = document.querySelector('[data-action="commit_rng"]').closest('.p-3').querySelector('label');
    const hydrogenLabel = document.querySelector('[data-action="commit_hydrogen"]').closest('.p-3').querySelector('label');

    if (ccgtOnline > 0) {
        ccgtLabel.innerHTML = `⚡ CCGT Units (500 MW each) <span class="text-xs text-blue-600 font-semibold">(${ccgtOnline} online @ ${ccgtOnline * CCGT_UNIT_SIZE_MW} MW)</span>`;
    } else {
        ccgtLabel.innerHTML = '⚡ CCGT Units (500 MW each)';
    }

    if (ctOnline > 0) {
        ctLabel.innerHTML = `🔥 CT Peakers (200 MW each) <span class="text-xs text-orange-600 font-semibold">(${ctOnline} online @ ${ctOnline * CT_UNIT_SIZE_MW} MW)</span>`;
    } else {
        ctLabel.innerHTML = '🔥 CT Peakers (200 MW each)';
    }

    if (batteryMW !== 0) {
        batteryLabel.innerHTML = `🔋 Battery <span class="text-xs text-green-600 font-semibold">(${Math.round(batteryMW)} MW scheduled)</span>`;
    } else {
        batteryLabel.innerHTML = '🔋 Battery';
    }

    if (hydroMW !== 0) {
        hydroLabel.innerHTML = `💧 Hydro <span class="text-xs text-cyan-600 font-semibold">(${Math.round(hydroMW)} MW scheduled)</span>`;
    } else {
        hydroLabel.innerHTML = '💧 Hydro';
    }

    if (rngOnline > 0) {
        rngLabel.innerHTML = `🌱 RNG (100 MW each) <span class="text-xs text-lime-600 font-semibold">(${rngOnline} online @ ${Math.round(calculateRNGMW(rngOnline))} MW)</span>`;
    } else {
        rngLabel.innerHTML = '🌱 RNG (100 MW each)';
    }

    if (hydrogenOnline > 0) {
        hydrogenLabel.innerHTML = `⚗️ Hydrogen (150 MW each) <span class="text-xs text-indigo-600 font-semibold">(${hydrogenOnline} online @ ${Math.round(calculateHydrogenMW(hydrogenOnline))} MW)</span>`;
    } else {
        hydrogenLabel.innerHTML = '⚗️ Hydrogen (150 MW each)';
    }
}

// Update shutdown button states based on currently committed units
function updateShutdownButtonStates() {
    if (selectedScheduleTick === null) return;

    // Calculate what units are online at the selected tick
    let ccgtOnline = 0;
    let ctOnline = 0;
    let rngOnline = 0;
    let hydrogenOnline = 0;

    scheduledEvents.forEach(event => {
        if (event.effectiveTick !== undefined && event.effectiveTick <= selectedScheduleTick) {
            if (event.action === 'commit_ccgt') {
                ccgtOnline += event.count;
            } else if (event.action === 'commit_ct') {
                ctOnline += event.count;
            } else if (event.action === 'commit_rng') {
                rngOnline += event.count;
            } else if (event.action === 'commit_hydrogen') {
                hydrogenOnline += event.count;
            }
        }
        if (event.tick <= selectedScheduleTick) {
            if (event.action === 'shutdown_ccgt') {
                ccgtOnline = Math.max(0, ccgtOnline - event.count);
            } else if (event.action === 'shutdown_ct') {
                ctOnline = Math.max(0, ctOnline - event.count);
            } else if (event.action === 'shutdown_rng') {
                rngOnline = Math.max(0, rngOnline - event.count);
            } else if (event.action === 'shutdown_hydrogen') {
                hydrogenOnline = Math.max(0, hydrogenOnline - event.count);
            }
        }
    });

    // Update button states
    const shutdownCCGTBtns = document.querySelectorAll('[data-action="shutdown_ccgt"]');
    const shutdownCTBtns = document.querySelectorAll('[data-action="shutdown_ct"]');
    const shutdownRNGBtns = document.querySelectorAll('[data-action="shutdown_rng"]');
    const shutdownHydrogenBtns = document.querySelectorAll('[data-action="shutdown_hydrogen"]');

    shutdownCCGTBtns.forEach(btn => {
        if (ccgtOnline > 0) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    });

    shutdownCTBtns.forEach(btn => {
        if (ctOnline > 0) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    });

    shutdownRNGBtns.forEach(btn => {
        if (rngOnline > 0) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    });

    shutdownHydrogenBtns.forEach(btn => {
        if (hydrogenOnline > 0) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    });
}

// Apply schedule and close modal
function applySchedule() {
    if (scheduledEvents.length === 0) {
        alert('No events scheduled. Add events to the timeline first.');
        return;
    }

    // Calculate Hour 0 state from schedule
    const hour0State = calculateHour0StateFromSchedule();

    // Apply Hour 0 state to sliders
    applyHour0State(hour0State);

    // Close modal
    schedulerModal.classList.add('hidden');

    // Check if game has ended (gameStarted is true but game has finished)
    if (gameStarted && gameTick >= forecastData.length) {
        alert(`Schedule updated! ${scheduledEvents.length} events saved.\n\nClick "Retry with Schedule" to use this updated schedule in your next game.`);
    } else {
        alert(`Schedule applied! ${scheduledEvents.length} events will execute during gameplay.`);
    }
}

// Calculate what the Hour 0 state should be based on schedule
function calculateHour0StateFromSchedule() {
    const state = {
        ccgtOnline: 0,
        ctOnline: 0,
        battery: 0,
        hydro: 0,
        rngOnline: 0,
        hydrogenOnline: 0
    };

    // Process events that would be effective by tick 0
    scheduledEvents.forEach(event => {
        if (event.tick === 0 || (event.effectiveTick && event.effectiveTick <= 0)) {
            switch(event.action) {
                case 'commit_ccgt':
                    state.ccgtOnline += event.count;
                    break;
                case 'shutdown_ccgt':
                    // Shutdowns at Hour 0 reduce the count
                    state.ccgtOnline = Math.max(0, state.ccgtOnline - event.count);
                    break;
                case 'commit_ct':
                    state.ctOnline += event.count;
                    break;
                case 'shutdown_ct':
                    // Shutdowns at Hour 0 reduce the count
                    state.ctOnline = Math.max(0, state.ctOnline - event.count);
                    break;
                case 'set_battery':
                    state.battery = event.value;
                    break;
                case 'set_hydro':
                    state.hydro = event.value;
                    break;
                case 'commit_rng':
                    state.rngOnline += event.count;
                    break;
                case 'shutdown_rng':
                    // Shutdowns at Hour 0 reduce the count
                    state.rngOnline = Math.max(0, state.rngOnline - event.count);
                    break;
                case 'commit_hydrogen':
                    state.hydrogenOnline += event.count;
                    break;
                case 'shutdown_hydrogen':
                    // Shutdowns at Hour 0 reduce the count
                    state.hydrogenOnline = Math.max(0, state.hydrogenOnline - event.count);
                    break;
            }
        }
    });

    return state;
}

// Apply Hour 0 state to the game controls
function applyHour0State(state) {
    // Reset all units first
    ccgtUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
    });
    ctUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
    });
    rngUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
    });
    hydrogenUnits.forEach(unit => {
        unit.state = 'offline';
        unit.outputMW = 0;
    });

    // Commit required units
    for (let i = 0; i < state.ccgtOnline && i < ccgtUnits.length; i++) {
        ccgtUnits[i].state = 'online';
        ccgtUnits[i].outputMW = CCGT_UNIT_SIZE_MW;
    }
    for (let i = 0; i < state.ctOnline && i < ctUnits.length; i++) {
        ctUnits[i].state = 'online';
        ctUnits[i].outputMW = CT_UNIT_SIZE_MW;
    }
    for (let i = 0; i < state.rngOnline && i < rngUnits.length; i++) {
        rngUnits[i].state = 'online';
        rngUnits[i].outputMW = RNG_UNIT_SIZE_MW;
    }
    for (let i = 0; i < state.hydrogenOnline && i < hydrogenUnits.length; i++) {
        hydrogenUnits[i].state = 'online';
        hydrogenUnits[i].outputMW = HYDROGEN_UNIT_SIZE_MW;
    }

    // Set battery and hydro
    batterySlider.value = state.battery;
    hydroSlider.value = state.hydro;

    // Update displays
    updateCCGTDisplay();
    updateCTDisplay();
    updateRNGDisplay();
    updateHydrogenDisplay();

    // Update power sliders for RNG and Hydrogen to reflect committed units
    updateRNGPowerSlider();
    updateHydrogenPowerSlider();

    updateSupplyValues();
}

// Show active schedule indicator during gameplay
function showActiveScheduleIndicator() {
    const activeScheduleIndicator = document.getElementById('activeScheduleIndicator');
    const scheduledEventsCount = document.getElementById('scheduledEventsCount');

    if (scheduledEvents.length > 0) {
        activeScheduleIndicator.classList.remove('hidden');
        scheduledEventsCount.textContent = `${scheduledEvents.length} event${scheduledEvents.length !== 1 ? 's' : ''}`;
    } else {
        activeScheduleIndicator.classList.add('hidden');
    }
}

// Hide active schedule indicator
function hideActiveScheduleIndicator() {
    const activeScheduleIndicator = document.getElementById('activeScheduleIndicator');
    activeScheduleIndicator.classList.add('hidden');
}

// Update upcoming events list in Game Metrics
function updateUpcomingEventsList(currentTick) {
    const upcomingEventsList = document.getElementById('upcomingEventsList');

    if (scheduledEvents.length === 0) {
        upcomingEventsList.innerHTML = '<p class="text-gray-400 italic">No scheduled events</p>';
        return;
    }

    // Get upcoming events
    const upcomingEvents = scheduledEvents.filter(event => {
        const executionTick = (event.action === 'commit_ccgt' || event.action === 'commit_ct' || event.action === 'commit_rng' || event.action === 'commit_hydrogen')
            ? event.effectiveTick
            : event.tick;
        return executionTick >= currentTick;
    });

    if (upcomingEvents.length === 0) {
        upcomingEventsList.innerHTML = '<p class="text-gray-400 italic">All events executed</p>';
        return;
    }

    // Group events by time
    const eventsByTime = {};
    upcomingEvents.forEach(event => {
        if (!eventsByTime[event.time]) {
            eventsByTime[event.time] = [];
        }
        eventsByTime[event.time].push(event);
    });

    // Get first 5 time slots
    const timeSlots = Object.keys(eventsByTime).slice(0, 5);

    upcomingEventsList.innerHTML = timeSlots.map(time => {
        const events = eventsByTime[time];

        // Consolidate same event types
        const consolidated = {};
        let totalMWImpact = 0;

        events.forEach(event => {
            if (!consolidated[event.action]) {
                consolidated[event.action] = { count: 0, value: 0 };
            }

            if (event.count) {
                consolidated[event.action].count += event.count;
                // Calculate MW impact
                if (event.action === 'commit_ccgt') {
                    totalMWImpact += event.count * CCGT_UNIT_SIZE_MW;
                } else if (event.action === 'shutdown_ccgt') {
                    totalMWImpact -= event.count * CCGT_UNIT_SIZE_MW;
                } else if (event.action === 'commit_ct') {
                    totalMWImpact += event.count * CT_UNIT_SIZE_MW;
                } else if (event.action === 'shutdown_ct') {
                    totalMWImpact -= event.count * CT_UNIT_SIZE_MW;
                } else if (event.action === 'commit_rng') {
                    totalMWImpact += event.count * RNG_UNIT_SIZE_MW;
                } else if (event.action === 'shutdown_rng') {
                    totalMWImpact -= event.count * RNG_UNIT_SIZE_MW;
                } else if (event.action === 'commit_hydrogen') {
                    totalMWImpact += event.count * HYDROGEN_UNIT_SIZE_MW;
                } else if (event.action === 'shutdown_hydrogen') {
                    totalMWImpact -= event.count * HYDROGEN_UNIT_SIZE_MW;
                }
            } else if (event.value !== undefined) {
                consolidated[event.action].value = event.value; // Latest value
                // Battery and Hydro contribute directly
                if (event.action === 'set_battery') {
                    totalMWImpact += event.value;
                } else if (event.action === 'set_hydro') {
                    totalMWImpact += event.value;
                }
            }
        });

        const eventIcons = {
            'commit_ccgt': '⚡',
            'shutdown_ccgt': '⛔',
            'commit_ct': '🔥',
            'shutdown_ct': '⛔',
            'commit_rng': '🌱',
            'shutdown_rng': '⛔',
            'commit_hydrogen': '⚗️',
            'shutdown_hydrogen': '⛔',
            'set_battery': '🔋',
            'set_hydro': '💧'
        };

        const eventNames = {
            'commit_ccgt': 'CCGT',
            'shutdown_ccgt': 'CCGT Down',
            'commit_ct': 'CT',
            'shutdown_ct': 'CT Down',
            'commit_rng': 'RNG',
            'shutdown_rng': 'RNG Down',
            'commit_hydrogen': 'Hydrogen',
            'shutdown_hydrogen': 'Hydrogen Down',
            'set_battery': 'Battery',
            'set_hydro': 'Hydro'
        };

        // Build event summary
        const eventSummaries = Object.keys(consolidated).map(action => {
            const data = consolidated[action];
            if (data.count > 0) {
                return `${eventIcons[action]} ${eventNames[action]} ${data.count}x`;
            } else if (data.value !== 0) {
                return `${eventIcons[action]} ${eventNames[action]} ${Math.round(data.value)}MW`;
            }
            return '';
        }).filter(s => s).join(', ');

        // Format MW impact
        const impactColor = totalMWImpact >= 0 ? 'text-green-600' : 'text-red-600';
        const impactSign = totalMWImpact >= 0 ? '+' : '';
        const impactText = `${impactSign}${Math.round(totalMWImpact).toLocaleString()} MW`;

        return `
            <div class="px-2 py-2 bg-gray-50 rounded border-l-4 border-purple-400">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-semibold text-gray-700">${time}</span>
                    <span class="text-xs font-bold ${impactColor}">${impactText}</span>
                </div>
                <div class="text-xs text-gray-600">${eventSummaries}</div>
            </div>
        `;
    }).join('');
}

// Update next event ticker
function updateNextEventTicker(currentTick) {
    const nextEventTicker = document.getElementById('nextEventTicker');
    const nextEventText = document.getElementById('nextEventText');

    if (scheduledEvents.length === 0) {
        nextEventTicker.classList.add('hidden');
        return;
    }

    // Find the very next event
    const nextEvent = scheduledEvents.find(event => {
        const executionTick = (event.action === 'commit_ccgt' || event.action === 'commit_ct' || event.action === 'commit_rng' || event.action === 'commit_hydrogen')
            ? event.effectiveTick
            : event.tick;
        return executionTick >= currentTick;
    });

    if (!nextEvent) {
        nextEventTicker.classList.add('hidden');
        return;
    }

    const eventIcons = {
        'commit_ccgt': '⚡',
        'shutdown_ccgt': '⛔',
        'commit_ct': '🔥',
        'shutdown_ct': '⛔',
        'commit_rng': '🌱',
        'shutdown_rng': '⛔',
        'commit_hydrogen': '⚗️',
        'shutdown_hydrogen': '⛔',
        'set_battery': '🔋',
        'set_hydro': '💧'
    };

    const eventNames = {
        'commit_ccgt': 'CCGT Commit',
        'shutdown_ccgt': 'CCGT Shutdown',
        'commit_ct': 'CT Commit',
        'shutdown_ct': 'CT Shutdown',
        'commit_rng': 'RNG Commit',
        'shutdown_rng': 'RNG Shutdown',
        'commit_hydrogen': 'Hydrogen Commit',
        'shutdown_hydrogen': 'Hydrogen Shutdown',
        'set_battery': 'Battery',
        'set_hydro': 'Hydro'
    };

    let details = '';
    let mwImpact = 0;
    if (nextEvent.count) {
        details = `${nextEvent.count}x`;
        if (nextEvent.action === 'commit_ccgt') mwImpact = nextEvent.count * CCGT_UNIT_SIZE_MW;
        else if (nextEvent.action === 'shutdown_ccgt') mwImpact = -nextEvent.count * CCGT_UNIT_SIZE_MW;
        else if (nextEvent.action === 'commit_ct') mwImpact = nextEvent.count * CT_UNIT_SIZE_MW;
        else if (nextEvent.action === 'shutdown_ct') mwImpact = -nextEvent.count * CT_UNIT_SIZE_MW;
        else if (nextEvent.action === 'commit_rng') mwImpact = nextEvent.count * RNG_UNIT_SIZE_MW;
        else if (nextEvent.action === 'shutdown_rng') mwImpact = -nextEvent.count * RNG_UNIT_SIZE_MW;
        else if (nextEvent.action === 'commit_hydrogen') mwImpact = nextEvent.count * HYDROGEN_UNIT_SIZE_MW;
        else if (nextEvent.action === 'shutdown_hydrogen') mwImpact = -nextEvent.count * HYDROGEN_UNIT_SIZE_MW;
    } else if (nextEvent.value !== undefined) {
        details = `${Math.round(nextEvent.value)}MW`;
        mwImpact = nextEvent.value;
    }

    const mwText = mwImpact !== 0 ? ` (${mwImpact >= 0 ? '+' : ''}${Math.round(mwImpact).toLocaleString()} MW)` : '';

    nextEventText.innerHTML = `${eventIcons[nextEvent.action]} ${eventNames[nextEvent.action]} ${details} @ ${nextEvent.time}${mwText}`;
    nextEventTicker.classList.remove('hidden');
}

// Execute scheduled events during gameplay (Phase 2)
function executeScheduledEvents(currentTick) {
    if (scheduledEvents.length === 0) return;

    // Update the upcoming events display and next event ticker
    updateUpcomingEventsList(currentTick);
    updateNextEventTicker(currentTick);

    // Filter events that should execute at this tick
    // IMPORTANT: Skip tick 0 events as they're already applied via applyHour0State
    const eventsToExecute = scheduledEvents.filter(event => {
        // Skip Hour 0 events - they're handled by applyHour0State
        if (event.tick === 0 || (event.effectiveTick !== undefined && event.effectiveTick === 0)) {
            return false;
        }

        // For commits, check effectiveTick (when unit becomes online)
        if (event.action === 'commit_ccgt' || event.action === 'commit_ct' || event.action === 'commit_rng' || event.action === 'commit_hydrogen') {
            return event.effectiveTick === currentTick;
        }
        // For shutdowns and setpoints, check tick (when action is initiated)
        return event.tick === currentTick;
    });

    eventsToExecute.forEach(event => {
        switch(event.action) {
            case 'commit_ccgt':
                // Find offline units and commit them
                // Note: scheduled commits should bring units online immediately
                // since effectiveTick already accounts for startup delay
                let ccgtCommitted = 0;
                for (let unit of ccgtUnits) {
                    if (unit.state === 'offline' && ccgtCommitted < event.count) {
                        // Bring unit online immediately (no additional startup delay)
                        unit.state = 'online';
                        unit.outputMW = CCGT_UNIT_SIZE_MW;
                        unit.startupTicksRemaining = 0;
                        ccgtCommitted++;
                    }
                }
                // Update displays after committing units
                if (ccgtCommitted > 0) {
                    updateCCGTDisplay();
                    updateCCGTPowerSlider();
                    const targetMW = parseFloat(ccgtPowerSlider.value);
                    distributePowerToUnits(ccgtUnits, targetMW, CCGT_UNIT_SIZE_MW);
                    updateSupplyValues();
                }
                break;

            case 'shutdown_ccgt':
                // Find online units and shut them down
                let ccgtShutdown = 0;
                for (let i = ccgtUnits.length - 1; i >= 0; i--) {
                    if (ccgtUnits[i].state === 'online' && ccgtShutdown < event.count) {
                        shutdownCCGTUnit(ccgtUnits[i]);
                        ccgtShutdown++;
                    }
                }
                break;

            case 'commit_ct':
                // Find offline units and commit them
                // Note: scheduled commits should bring units online immediately
                // since effectiveTick already accounts for startup delay
                let ctCommitted = 0;
                for (let unit of ctUnits) {
                    if (unit.state === 'offline' && ctCommitted < event.count) {
                        // Bring unit online immediately (no additional startup delay)
                        unit.state = 'online';
                        unit.outputMW = CT_UNIT_SIZE_MW;
                        unit.startupTicksRemaining = 0;
                        ctCommitted++;
                    }
                }
                // Update displays after committing units
                if (ctCommitted > 0) {
                    updateCTDisplay();
                    updateCTPowerSlider();
                    const targetMW = parseFloat(ctPowerSlider.value);
                    distributePowerToUnits(ctUnits, targetMW, CT_UNIT_SIZE_MW);
                    updateSupplyValues();
                }
                break;

            case 'shutdown_ct':
                // Find online units and shut them down
                let ctShutdown = 0;
                for (let i = ctUnits.length - 1; i >= 0; i--) {
                    if (ctUnits[i].state === 'online' && ctShutdown < event.count) {
                        shutdownCTUnit(ctUnits[i]);
                        ctShutdown++;
                    }
                }
                break;

            case 'commit_rng':
                // Find offline units and commit them
                // Note: scheduled commits should bring units online immediately
                // since effectiveTick already accounts for startup delay
                let rngCommitted = 0;
                for (let unit of rngUnits) {
                    if (unit.state === 'offline' && rngCommitted < event.count) {
                        // Bring unit online immediately (no additional startup delay)
                        unit.state = 'online';
                        unit.outputMW = RNG_UNIT_SIZE_MW;
                        unit.startupTicksRemaining = 0;
                        rngCommitted++;
                    }
                }
                // Update displays after committing units
                if (rngCommitted > 0) {
                    updateRNGDisplay();
                    updateRNGPowerSlider();
                    const targetMW = parseFloat(rngPowerSlider.value);
                    distributePowerToUnits(rngUnits, targetMW, RNG_UNIT_SIZE_MW);
                    updateSupplyValues();
                }
                break;

            case 'shutdown_rng':
                // Find online units and shut them down
                let rngShutdown = 0;
                for (let i = rngUnits.length - 1; i >= 0; i--) {
                    if (rngUnits[i].state === 'online' && rngShutdown < event.count) {
                        shutdownRNGUnit(rngUnits[i]);
                        rngShutdown++;
                    }
                }
                break;

            case 'commit_hydrogen':
                // Find offline units and commit them
                // Note: scheduled commits should bring units online immediately
                // since effectiveTick already accounts for startup delay
                let hydrogenCommitted = 0;
                for (let unit of hydrogenUnits) {
                    if (unit.state === 'offline' && hydrogenCommitted < event.count) {
                        // Bring unit online immediately (no additional startup delay)
                        unit.state = 'online';
                        unit.outputMW = HYDROGEN_UNIT_SIZE_MW;
                        unit.startupTicksRemaining = 0;
                        hydrogenCommitted++;
                    }
                }
                // Update displays after committing units
                if (hydrogenCommitted > 0) {
                    updateHydrogenDisplay();
                    updateHydrogenPowerSlider();
                    const targetMW = parseFloat(hydrogenPowerSlider.value);
                    distributePowerToUnits(hydrogenUnits, targetMW, HYDROGEN_UNIT_SIZE_MW);
                    updateSupplyValues();
                }
                break;

            case 'shutdown_hydrogen':
                // Find online units and shut them down
                let hydrogenShutdown = 0;
                for (let i = hydrogenUnits.length - 1; i >= 0; i--) {
                    if (hydrogenUnits[i].state === 'online' && hydrogenShutdown < event.count) {
                        shutdownHydrogenUnit(hydrogenUnits[i]);
                        hydrogenShutdown++;
                    }
                }
                break;

            case 'set_battery':
                // Check battery SOC constraints before applying scheduled value
                let requestedBatteryMW = event.value;

                // If battery is empty (SOC <= 0) and trying to discharge (positive MW), prevent discharge
                if (batterySOC <= 0.01 && requestedBatteryMW > 0) {
                    console.log(`[Scheduled Battery] Cannot discharge ${requestedBatteryMW} MW - battery empty (SOC: ${(batterySOC * 100).toFixed(1)}%)`);
                    requestedBatteryMW = 0; // Force to 0 MW
                }

                // If battery is full (SOC >= 1) and trying to charge (negative MW), prevent charging
                if (batterySOC >= 0.99 && requestedBatteryMW < 0) {
                    console.log(`[Scheduled Battery] Cannot charge at ${requestedBatteryMW} MW - battery full (SOC: ${(batterySOC * 100).toFixed(1)}%)`);
                    requestedBatteryMW = 0; // Force to 0 MW
                }

                batterySlider.value = requestedBatteryMW;
                updateSupplyValues();
                break;

            case 'set_hydro':
                hydroSlider.value = event.value;
                updateSupplyValues();
                break;
        }
    });

    // Update displays if any events were executed
    if (eventsToExecute.length > 0) {
        updateCCGTDisplay();
        updateCTDisplay();
        updateRNGDisplay();
        updateHydrogenDisplay();
        updateSupplyValues();
    }
}

// Hide scheduler button when game starts
function hideSchedulerButton() {
    schedulerButtonContainer.classList.add('hidden');
}

// Show scheduler button when game resets
function showSchedulerButton() {
    schedulerButtonContainer.classList.remove('hidden');
}

// --- 11. KICK EVERYTHING OFF ---
initialize().then(() => {
    // Check for username
    checkUsername();

    // Start tutorial after a short delay, but only if user already has a username
    // (new users will see tutorial after entering username)
    if (playerUsername) {
        setTimeout(startTutorial, 500);
    }
});




