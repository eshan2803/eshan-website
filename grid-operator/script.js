// --- 1. GET REFERENCES TO HTML ELEMENTS ---
const ctx = document.getElementById('gridChart').getContext('2d');
const cfCtx = document.getElementById('capacityFactorChart').getContext('2d');
const startButton = document.getElementById('startButton');
const pauseButtons = document.getElementById('pauseButtons');
const resumeButton = document.getElementById('resumeButton');
const restartButton = document.getElementById('restartButton');

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

// CT unit dispatch controls
const ctCommitBtn = document.getElementById('ctCommitBtn');
const ctShutdownBtn = document.getElementById('ctShutdownBtn');
const ctPowerSlider = document.getElementById('ctPowerSlider');
const ctOutputDisplay = document.getElementById('ctOutputDisplay');
const ctOnlineCount = document.getElementById('ctOnlineCount');
const ctOnlineMW = document.getElementById('ctOnlineMW');
const ctStartingCount = document.getElementById('ctStartingCount');

// Hydro controls
const hydroSlider = document.getElementById('hydroSlider');
const hydroInput = document.getElementById('hydroInput');
const hydroCondition = document.getElementById('hydroCondition');
const hydroMaxDisplay = document.getElementById('hydroMaxDisplay');

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
let currentSeason = 'spring';
let isLoadProfileModified = false;
let isCFProfileModified = false;

// Event buttons
const cloudCoverBtn = document.getElementById('cloudCoverBtn');
const demandSpikeBtn = document.getElementById('demandSpikeBtn');

// Gauge elements
const deltaNeedle = document.getElementById('deltaNeedle');
const frequencyNeedle = document.getElementById('frequencyNeedle');
const deltaGaugeValue = document.getElementById('deltaGaugeValue');
const frequencyGaugeValue = document.getElementById('frequencyGaugeValue');

// Status banner and counters
const statusBanner = document.getElementById('statusBanner');
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

// Battery state variables
const BATTERY_CAPACITY_MWH = 52000; // 52 GWh capacity (4-hour battery at 13 GW)
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
const BATTERY_OPCOST = 5;   // Battery storage (minimal O&M, efficiency losses)
const HYDRO_OPCOST = 2;     // Hydro (minimal O&M, no fuel cost)

// Linear cost function parameters for CCGT and CT (simulating heat rate degradation)
// CCGT: starts at $35/MWh for first 500MW, then increases by $5/MWh for each additional 500MW
const CCGT_BASE_COST = 35;
const CCGT_STEP_MW = 500;
const CCGT_COST_INCREMENT = 5;

// CT: starts at $65/MWh for first 200MW, then increases by $5/MWh for each additional 200MW
const CT_BASE_COST = 65;
const CT_STEP_MW = 200;
const CT_COST_INCREMENT = 5;

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

// Unit state arrays - each element represents one unit
// Unit states: 'offline', 'starting' (with startupTicksRemaining), 'online'
let ccgtUnits = [];
let ctUnits = [];

// Initialize unit arrays
for (let i = 0; i < CCGT_MAX_UNITS; i++) {
    ccgtUnits.push({ state: 'offline', startupTicksRemaining: 0, outputMW: 0 });
}
for (let i = 0; i < CT_MAX_UNITS; i++) {
    ctUnits.push({ state: 'offline', startupTicksRemaining: 0, outputMW: 0 });
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
    const minMW = onlineCount * unitSize * minLoadPercent;
    const maxMW = onlineCount * unitSize;
    return { minMW, maxMW, onlineCount };
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

    updateCCGTDisplay();
    updateCCGTPowerSlider();
    updateCTDisplay();
    updateCTPowerSlider();

    // Distribute power according to slider values for newly online units
    const ccgtTargetMW = parseFloat(ccgtPowerSlider.value);
    distributePowerToUnits(ccgtUnits, ccgtTargetMW, CCGT_UNIT_SIZE_MW);

    const ctTargetMW = parseFloat(ctPowerSlider.value);
    distributePowerToUnits(ctUnits, ctTargetMW, CT_UNIT_SIZE_MW);
}

// Update CCGT display
function updateCCGTDisplay() {
    const counts = getUnitCounts(ccgtUnits);
    const totalMW = getTotalOnlineMW(ccgtUnits);

    ccgtOnlineCount.textContent = counts.online;
    ccgtOnlineMW.textContent = Math.round(totalMW);
    ccgtStartingCount.textContent = counts.starting;
    ccgtOutputDisplay.textContent = `${Math.round(totalMW)} MW`;

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

    // Enable/disable buttons
    ctCommitBtn.disabled = counts.offline === 0;
    ctShutdownBtn.disabled = counts.online === 0;
}

// Update CCGT power slider range based on online units
function updateCCGTPowerSlider() {
    const capacity = getOnlineCapacity(ccgtUnits, CCGT_UNIT_SIZE_MW, CCGT_MIN_LOAD_PERCENT);

    ccgtPowerSlider.min = Math.round(capacity.minMW);
    ccgtPowerSlider.max = Math.round(capacity.maxMW);
    // Set slider to max when units are committed, or current total if already adjusted
    ccgtPowerSlider.value = Math.round(capacity.maxMW);
    ccgtPowerSlider.disabled = capacity.onlineCount === 0;
}

// Update CT power slider range based on online units
function updateCTPowerSlider() {
    const capacity = getOnlineCapacity(ctUnits, CT_UNIT_SIZE_MW, CT_MIN_LOAD_PERCENT);

    ctPowerSlider.min = Math.round(capacity.minMW);
    ctPowerSlider.max = Math.round(capacity.maxMW);
    // Set slider to max when units are committed, or current total if already adjusted
    ctPowerSlider.value = Math.round(capacity.maxMW);
    ctPowerSlider.disabled = capacity.onlineCount === 0;
}

// Distribute target power across online units
function distributePowerToUnits(units, targetMW, unitSize) {
    const onlineUnits = units.filter(u => u.state === 'online');
    if (onlineUnits.length === 0) return;

    // Simple proportional distribution: divide target equally among units
    const perUnitMW = targetMW / onlineUnits.length;

    onlineUnits.forEach(unit => {
        unit.outputMW = Math.max(0, Math.min(unitSize, perUnitMW));
    });
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
    const profile = seasonalProfilesData.california.profiles[season];
    const peakMW = profile.peakMW;
    const hourlyPercentages = profile.hourlyPercentages;

    // Get season-specific renewable capacity factors (24 hourly values)
    const solarCF = profile.solarCF;
    const windCF = profile.windCF;
    const nuclearCF = profile.nuclearCF;
    const geothermalCF = profile.geothermalCF;
    const biomassCF = profile.biomassCF;

    const solarCapacity = seasonalProfilesData.california.renewables.installedCapacityMW.solar;
    const windCapacity = seasonalProfilesData.california.renewables.installedCapacityMW.wind;
    const nuclearCapacity = seasonalProfilesData.california.renewables.installedCapacityMW.nuclear;
    const geothermalCapacity = seasonalProfilesData.california.renewables.installedCapacityMW.geothermal;
    const biomassCapacity = seasonalProfilesData.california.renewables.installedCapacityMW.biomass;

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

// --- 4. FETCH DATA AND INITIALIZE THE APP ---
async function initialize() {
    try {
        const response = await fetch('seasonal_profiles.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        seasonalProfilesData = await response.json();

        // Create deep copy of pristine preset data
        originalSeasonalProfilesData = JSON.parse(JSON.stringify(seasonalProfilesData));

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

        // Battery and Hydro slider event listeners
        batterySlider.addEventListener('input', updateSupplyValues);
        hydroSlider.addEventListener('input', updateSupplyValues);

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

        // Load Profile edit controls
        editProfileButton.addEventListener('click', enterEditMode);
        confirmEditButton.addEventListener('click', confirmEdit);
        revertEditButton.addEventListener('click', revertEdit);

        // Load Profile preset buttons
        document.getElementById('preset-load-spring').addEventListener('click', () => applyLoadSeasonPreset('spring'));
        document.getElementById('preset-load-summer').addEventListener('click', () => applyLoadSeasonPreset('summer'));
        document.getElementById('preset-load-fall').addEventListener('click', () => applyLoadSeasonPreset('fall'));
        document.getElementById('preset-load-winter').addEventListener('click', () => applyLoadSeasonPreset('winter'));

        // CF Chart event listeners
        editCFBtn.addEventListener('click', enterCFEditMode);
        confirmCFBtn.addEventListener('click', confirmCFEdit);
        revertCFBtn.addEventListener('click', revertCFEdit);

        // CF Preset buttons
        document.getElementById('preset-cf-spring').addEventListener('click', () => applyCFSeasonPreset('spring'));
        document.getElementById('preset-cf-summer').addEventListener('click', () => applyCFSeasonPreset('summer'));
        document.getElementById('preset-cf-fall').addEventListener('click', () => applyCFSeasonPreset('fall'));
        document.getElementById('preset-cf-winter').addEventListener('click', () => applyCFSeasonPreset('winter'));

        // Enable controls before game starts
        batterySlider.disabled = false;
        batteryInput.disabled = false;
        hydroSlider.disabled = false;
        hydroInput.disabled = false;
        ccgtCommitBtn.disabled = false;
        ctCommitBtn.disabled = false;

        // Initialize unit displays
        updateCCGTDisplay();
        updateCTDisplay();

        // Event button listeners
        cloudCoverBtn.addEventListener('click', triggerCloudCoverEvent);
        demandSpikeBtn.addEventListener('click', triggerDemandSpikeEvent);

        // Hydro condition dropdown listener
        hydroCondition.addEventListener('change', updateHydroCapacity);

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

// Show initial demand before game starts
function showInitialDemand() {
    if (forecastData.length > 0) {
        const initialNetDemand = forecastData[0].net_demand_mw;
        demandValueSpan.textContent = Math.round(initialNetDemand);

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
                            // Only show the actual line datasets
                            const totalDatasets = chartData.datasets.length;

                            // If we have more than 11 datasets, game has started (actual lines added)
                            if (totalDatasets > 11) {
                                // Hide forecast dots (indices 5 and 6) during gameplay
                                // The actual demand lines are at indices 7 and 8
                                if (legendItem.datasetIndex === 5 || legendItem.datasetIndex === 6) {
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

                            // Define custom order: Demand first, then renewables, then flexible
                            const order = [
                                'Total Demand', 'Net Demand',  // Row 1
                                'Solar', 'Wind', 'Geothermal', 'Nuclear', 'Biomass',  // Row 2
                                'CCGT', 'CT', 'Hydro', 'Battery'  // Row 3
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

                                return `${dataset.label}: ${value.toFixed(2)} GW`;
                            }

                            // Default behavior for edit mode and past/current game time
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(2) + ' GW';
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
                    onDragEnd: function(e, datasetIndex, index, value) {
                        if (isEditMode && datasetIndex === 5) {
                            // Update hourly percentage when dragging in edit mode
                            const profile = seasonalProfilesData.california.profiles[currentSeason];
                            const peakMW = profile.peakMW;
                            const newPercentage = (value / peakMW) * 100;
                            profile.hourlyPercentages[index] = Math.max(0, Math.round(newPercentage));

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
    myChart.data.datasets[10].data = []; // Hydro
    myChart.update();

    // Update demand and gauges after chart data changes
    showInitialDemand();
}

// --- 8. EDIT MODE FUNCTIONS ---
// Helper function to update load profile display text
function updateLoadProfileDisplay() {
    if (isLoadProfileModified) {
        currentLoadProfileText.textContent = 'User Defined';
    } else {
        const seasonName = currentSeason.charAt(0).toUpperCase() + currentSeason.slice(1);
        currentLoadProfileText.textContent = seasonName;
    }
}

// Helper function to apply load season preset
function applyLoadSeasonPreset(season) {
    // Restore original preset data for this season from pristine copy
    seasonalProfilesData.california.profiles[season] =
        JSON.parse(JSON.stringify(originalSeasonalProfilesData.california.profiles[season]));

    currentSeason = season;
    isLoadProfileModified = false; // Reset modified flag when applying preset
    isCFProfileModified = false; // Also reset CF profile modified flag

    if (isEditMode) {
        // If in edit mode, stay in hourly editing mode
        const profile = seasonalProfilesData.california.profiles[season];
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

    const profile = seasonalProfilesData.california.profiles[currentSeason];
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
    myChart.data.datasets[10].hidden = true; // Hydro Supply

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
    myChart.data.datasets[10].hidden = false; // Hydro Supply

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
    const profile = seasonalProfilesData.california.profiles[currentSeason];
    profile.hourlyPercentages = [...originalDemandBeforeEdit];

    // Update the hourly chart display in edit mode
    const peakMW = profile.peakMW;
    const hourlyDemandMW = profile.hourlyPercentages.map(pct => (pct / 100) * peakMW);
    myChart.data.datasets[5].data = hourlyDemandMW;
    myChart.update('none');
}

// --- 9. HELPER FUNCTIONS FOR SUPPLY AND BATTERY ---
function updateSupplyValues() {
    const battery = parseFloat(batterySlider.value);
    const ccgt = getTotalOnlineMW(ccgtUnits);
    const ct = getTotalOnlineMW(ctUnits);
    const hydro = parseFloat(hydroSlider.value);
    const total = battery + ccgt + ct + hydro;

    // Update input fields to match sliders
    batteryInput.value = Math.round(battery);
    hydroInput.value = Math.round(hydro);
    totalSupplyValueSpan.textContent = Math.round(total);

    // Update delta display and chart if game hasn't started yet
    if (gameTick === 0 && forecastData.length > 0) {
        const initialNetDemand = forecastData[0].net_demand_mw;
        const delta = total - initialNetDemand;
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
        const currentIntervalCost = batteryCost + ccgtCost + ctCost + hydroCost;

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
        if (myChart && myChart.data.datasets[7]) {
            myChart.data.datasets[7].data[0] = battery;  // Battery
            myChart.data.datasets[8].data[0] = ccgt;     // CCGT
            myChart.data.datasets[9].data[0] = ct;       // CT
            myChart.data.datasets[10].data[0] = hydro;   // Hydro
            myChart.update('none'); // Update without animation
        }

        // Update gauges before game starts
        updateGauges(delta, total);
    }
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

// --- 10. STATUS BANNER UPDATE FUNCTION ---
function updateStatusBanner(delta) {
    const absDelta = Math.abs(delta);

    if (absDelta >= 1500) {
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

        // Create 4 clouds at different heights
        const cloudPositions = [15, 35, 55, 75]; // Y positions in %

        cloudPositions.forEach((yPos, index) => {
            const cloud = document.createElement('div');
            cloud.textContent = '☁️';
            cloud.className = 'cloud-element';
            cloud.style.top = `${yPos}%`;
            cloud.style.animationDelay = `${index * 0.3}s`;
            cloud.style.animationDuration = `${3 + index * 0.5}s`;
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

    // Disable button temporarily
    cloudCoverBtn.disabled = true;
    cloudCoverBtn.textContent = '☁️ Cloud Active!';

    // Re-enable after event passes (after next tick)
    setTimeout(() => {
        cloudCoverBtn.disabled = false;
        cloudCoverBtn.textContent = '☁️ Cloud Cover';
    }, 1000);

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

    // Disable button temporarily
    demandSpikeBtn.disabled = true;
    demandSpikeBtn.textContent = '⚡ Spike Active!';

    // Re-enable after event passes (after next tick)
    setTimeout(() => {
        demandSpikeBtn.disabled = false;
        demandSpikeBtn.textContent = '⚡ Demand Spike';
    }, 1000);

    console.log(`Demand Spike Event! Demand increased by ${Math.round(spikeMW)} MW for next tick`);
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

        // Change button to "Reset" after user clicks OK
        // Keep game in "started" state so button knows to call resetGame
        startButton.textContent = 'Reset';
        startButton.classList.remove('hidden');
        pauseButtons.classList.add('hidden');

        return;
    }

    // Process unit startup timers at the beginning of each tick
    processStartupTimers();

    const currentNetDemand = forecastData[gameTick].net_demand_mw;

    // Get current supply from all sources (units + battery + hydro)
    const batteryMW = parseFloat(batterySlider.value);
    const ccgtMW = getTotalOnlineMW(ccgtUnits);
    const ctMW = getTotalOnlineMW(ctUnits);
    let hydroMW = parseFloat(hydroSlider.value);

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

    const totalSupply = batteryMW + ccgtMW + ctMW + hydroMW;

    // Update battery state of charge
    // Negative battery value = charging (increasing SOC)
    // Positive battery value = discharging (decreasing SOC)
    const energyChangeMWh = -batteryMW * (1/12); // 5-minute intervals = 1/12 hour, MW to MWh
    const socChange = energyChangeMWh / BATTERY_CAPACITY_MWH;
    batterySOC = Math.max(0, Math.min(1, batterySOC + socChange));

    // Constrain battery power based on SOC
    if (batterySOC >= 1 && batteryMW < 0) {
        // Battery full, can't charge more
        batterySlider.value = 0;
        updateSupplyValues();
    } else if (batterySOC <= 0 && batteryMW > 0) {
        // Battery empty, can't discharge more
        batterySlider.value = 0;
        updateSupplyValues();
    }

    updateBatterySOCDisplay();

    // Calculate cost for this 5-minute interval
    // Cost = (Power in MW) * (Operating Cost in $/MWh) * (Duration in hours)
    // For 5-minute intervals, duration = 1/12 hour
    // For battery, we use absolute value since both charging and discharging have efficiency losses
    const batteryCost = Math.abs(batteryMW) * BATTERY_OPCOST * (1/12);
    const ccgtCost = calculateCCGTCost(ccgtMW) * (1/12);  // Linear cost function * time
    const ctCost = calculateCTCost(ctMW) * (1/12);        // Linear cost function * time
    const hydroCost = hydroMW * HYDRO_OPCOST * (1/12);
    const currentIntervalCost = batteryCost + ccgtCost + ctCost + hydroCost;

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
    // Note: After switchToActualData(), datasets 7-8 are actual demand lines, 9-12 are supply
    myChart.data.datasets[9].data.push(batteryMW);  // Battery
    myChart.data.datasets[10].data.push(ccgtMW);     // CCGT
    myChart.data.datasets[11].data.push(ctMW);       // CT
    myChart.data.datasets[12].data.push(hydroMW);   // Hydro

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

        if (Math.abs(demandChange) < 10) {
            // Minimal change
            nextDemandChange.textContent = '(~0 MW)';
            nextDemandChange.className = 'font-semibold text-gray-600';
        } else if (demandChange > 0) {
            // Increase (harder to meet)
            nextDemandChange.textContent = `(↑${Math.round(demandChange)} MW)`;
            if (demandChange > 500) {
                nextDemandChange.className = 'font-semibold text-red-600';
            } else {
                nextDemandChange.className = 'font-semibold text-orange-600';
            }
        } else {
            // Decrease (easier to meet)
            nextDemandChange.textContent = `(↓${Math.round(Math.abs(demandChange))} MW)`;
            nextDemandChange.className = 'font-semibold text-green-600';
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

    // Change button to "Pause"
    startButton.textContent = 'Pause';
    startButton.disabled = false;

    editProfileButton.disabled = true;
    gameTick = 0;
    batterySOC = 0.2; // Reset to 20%

    // Set initial ramp tracking for hydro
    prevHydro = parseFloat(hydroSlider.value);

    totalCost = 0; // Reset cost tracking
    updateBatterySOCDisplay();
    currentCostValueSpan.textContent = '0';
    totalCostValueSpan.textContent = '0';

    // Enable event buttons during gameplay
    cloudCoverBtn.disabled = false;
    demandSpikeBtn.disabled = false;

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
}

function resumeGame() {
    gamePaused = false;

    // Hide "Resume" and "Restart" buttons, show "Pause" button
    pauseButtons.classList.add('hidden');
    startButton.classList.remove('hidden');

    // Resume the game loop
    gameInterval = setInterval(gameLoop, gameSpeed * 1000);
}

function resetGame() {
    gameStarted = false; // Mark game as not started
    gamePaused = false; // Mark game as not paused
    clearInterval(gameInterval);

    // Reset button states
    startButton.textContent = 'Start Game';
    startButton.disabled = false;
    startButton.classList.remove('hidden');
    pauseButtons.classList.add('hidden');

    batterySlider.disabled = true;
    batteryInput.disabled = true;
    hydroSlider.disabled = true;
    hydroInput.disabled = true;
    editProfileButton.disabled = false;
    gameTick = 0;
    batterySOC = 0.2; // Reset to 20%
    prevHydro = 0; // Reset ramp tracking
    totalCost = 0; // Reset cost tracking

    // Reset game speed to default
    gameSpeed = 1.0;
    gameSpeedSlider.value = 1.0;
    gameSpeedTime.textContent = '1.0';

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

    // Reset sliders and inputs
    batterySlider.value = 0;
    hydroSlider.value = 0;
    batteryInput.value = 0;
    hydroInput.value = 0;
    updateSupplyValues();
    updateBatterySOCDisplay();
    updateCCGTDisplay();
    updateCCGTPowerSlider();
    updateCTDisplay();
    updateCTPowerSlider();

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

    // Reset status banner to stable
    statusBanner.className = 'mb-4 px-4 py-3 rounded-lg text-center font-semibold text-lg transition-all duration-300 bg-green-100 text-green-800';
    statusBanner.textContent = '✓ Grid Stable';

    // Disable event buttons when game is not running
    cloudCoverBtn.disabled = true;
    demandSpikeBtn.disabled = true;

    // Re-enable controls for pre-game setup
    batterySlider.disabled = false;
    batteryInput.disabled = false;
    hydroSlider.disabled = false;
    hydroInput.disabled = false;
    ccgtCommitBtn.disabled = false;
    ctCommitBtn.disabled = false;

    // Clear chart data
    myChart.data.datasets[7].data = []; // Battery
    myChart.data.datasets[8].data = []; // CCGT
    myChart.data.datasets[9].data = []; // CT
    myChart.data.datasets[10].data = []; // Hydro

    // Switch back to hourly forecast dots
    switchToForecastData();

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
                    intersect: false
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
    const profile = seasonalProfilesData.california.profiles[currentSeason];

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
                    onDragEnd: function(e, datasetIndex, index, value) {
                        let updatedValue = value;
                        if (value < 0) updatedValue = 0;
                        if (value > 100) updatedValue = 100;
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

    currentCFProfileText.textContent = currentSeason.charAt(0).toUpperCase() + currentSeason.slice(1);
}

function updateCFChart() {
    const profile = seasonalProfilesData.california.profiles[currentSeason];

    cfChart.data.datasets[0].data = profile.solarCF.map(cf => cf * 100);
    cfChart.data.datasets[1].data = profile.windCF.map(cf => cf * 100);
    cfChart.update();

    // Update CF profile text
    if (isCFProfileModified) {
        currentCFProfileText.textContent = 'User Defined';
    } else {
        currentCFProfileText.textContent = currentSeason.charAt(0).toUpperCase() + currentSeason.slice(1);
    }
    currentCFProfileName = currentSeason.charAt(0).toUpperCase() + currentSeason.slice(1);
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
    const profile = seasonalProfilesData.california.profiles[currentSeason];
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
    seasonalProfilesData.california.profiles[presetSeason] =
        JSON.parse(JSON.stringify(originalSeasonalProfilesData.california.profiles[presetSeason]));

    // Update current season
    currentSeason = presetSeason;
    isCFProfileModified = false; // Reset modified flag when applying preset

    // Load the new season's data
    const profile = seasonalProfilesData.california.profiles[presetSeason];
    cfChart.data.datasets[0].data = profile.solarCF.map(cf => cf * 100);
    cfChart.data.datasets[1].data = profile.windCF.map(cf => cf * 100);
    cfChart.update('none');

    // Update the CF profile display text
    currentCFProfileText.textContent = presetSeason.charAt(0).toUpperCase() + presetSeason.slice(1);
}

// --- TUTORIAL LOGIC ---
const tutorialSteps = [
    {
        title: 'Welcome to the Grid Operator Game!',
        text: 'Your mission: Balance California\'s electricity grid for 24 hours by matching supply to net demand exactly. Let\'s take a quick tour!',
        position: 'center'
    },
    {
        element: '#tutorial-step-2',
        title: 'The Generation & Demand Chart',
        text: 'This shows the hourly demand and renewable generation (solar, wind, nuclear, etc.). The red line is Net Demand - your target to match with flexible resources.',
        position: 'right',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-3',
        title: 'Game Controls',
        text: 'Control game speed, start/pause the game, and trigger random events like cloud cover (reduces solar) or demand spikes (sudden load increase).',
        position: 'left',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-4',
        title: 'Flexible Generation Resources',
        text: 'Use Battery (instant), Hydro (fast ramp), CCGT (60-90 min startup), and CT Peakers (10-20 min startup) to fill the gap between demand and renewables.',
        position: 'left',
        highlightClass: 'rounded-lg'
    },
    {
        element: '#tutorial-step-5',
        title: 'Game Metrics & Monitoring',
        text: 'Track your performance: Keep Delta (Supply - Demand) near zero to avoid Emergency Alerts (±500 MW) and Blackouts (±1500 MW). Minimize total cost!',
        position: 'bottom',
        highlightClass: 'rounded-lg'
    },
    {
        title: 'Ready to Play!',
        text: 'Set up your resources, click Start Game, and balance the grid! Aim for zero alerts and blackouts to win the confetti celebration. Good luck!',
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
        highlightedTutorialElement.classList.remove('tutorial-highlight-active', 'rounded-full', 'rounded-lg');
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
        highlightedTutorialElement.classList.remove('tutorial-highlight-active', 'rounded-full', 'rounded-lg');
        highlightedTutorialElement = null;
    }

    tutorialTitleEl.textContent = step.title;
    tutorialTextEl.textContent = step.text;

    if (step.element) {
        const targetElement = document.querySelector(step.element);
        if (targetElement) {
            tutorialOverlay.style.display = 'none';
            highlightedTutorialElement = targetElement;
            highlightedTutorialElement.classList.add('tutorial-highlight-active');
            if (step.highlightClass) {
                highlightedTutorialElement.classList.add(step.highlightClass);
            }

            highlightedTutorialElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
            setTimeout(() => {
                positionTutorialPopover(targetElement, tutorialPopover, step.position);
            }, 300);
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

// --- 11. KICK EVERYTHING OFF ---
initialize().then(() => {
    // Start tutorial after a short delay to let the page fully load
    setTimeout(startTutorial, 500);
});


