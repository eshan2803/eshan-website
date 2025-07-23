// Backend URL and global variables
const BACKEND_URL = "https://transport-model.onrender.com";
let map;
let completeResultsForCsv = [];

// UI Element References
const commoditySelector = document.getElementById('commodity-type');
const capacityInputGroup = document.getElementById('capacity-input-group');
const fuelOptionsDiv = document.getElementById('fuel-options');
const foodOptionsDiv = document.getElementById('food-options');
const capacityLabel = document.getElementById('capacity-label');
const bogRecirculationDetailsPanel = document.getElementById('bogRecirculationDetails');
const bogRecirculationRadio = document.getElementById('bogRecirculation');
const shipDetailsWrapper = document.getElementById('ship-details-wrapper');
const customShipDetailsPanel = document.getElementById('customShipDetails');
const shipArchetypeSelect = document.getElementById('shipArchetypeSelect');

// --- Main Function to Control UI Visibility ---
function updateFormVisibility() {
    const selectedCommodity = commoditySelector.value;
    const shipOptions = shipArchetypeSelect.options;

    if (selectedCommodity === 'fuel') {
        // --- SHOW FUEL SECTIONS ---
        fuelOptionsDiv.classList.remove('hidden');
        foodOptionsDiv.classList.add('hidden');
        shipDetailsWrapper.classList.remove('hidden');
        capacityInputGroup.classList.remove('hidden');

        capacityLabel.textContent = 'LH2 Plant Capacity (TPD):';
        shipOptions[1].textContent = 'Small-Scale Carrier (20,000 m³)';
        shipOptions[2].textContent = 'Midsized Carrier (90,000 m³)';
        shipOptions[3].textContent = 'Standard Modern Carrier (174,000 m³)';
        shipOptions[4].textContent = 'Q-Flex Carrier (210,000 m³)';
        shipOptions[5].textContent = 'Q-Max Carrier (266,000 m³)';
        
        // Handle BOG panel visibility
        if (bogRecirculationRadio.checked) {
            bogRecirculationDetailsPanel.classList.remove('hidden');
        } else {
            bogRecirculationDetailsPanel.classList.add('hidden');
        }

    } else if (selectedCommodity === 'food') {
        // --- SHOW FOOD SECTIONS ---
        fuelOptionsDiv.classList.add('hidden');
        foodOptionsDiv.classList.remove('hidden');
        shipDetailsWrapper.classList.remove('hidden');

        capacityLabel.textContent = 'Processing & Freezing Facility Capacity (Tons/Day):';
        shipOptions[1].textContent = 'Feeder Vessel (~2,000 Containers)';
        shipOptions[2].textContent = 'Midsized Vessel (~6,000 Containers)';
        shipOptions[3].textContent = 'Post-Panamax Vessel (~10,000 Containers)';
        shipOptions[4].textContent = 'New-Panamax Vessel (~14,000 Containers)';
        shipOptions[5].textContent = 'Ultra-Large Vessel (20,000+ Containers)';
    }

    // Handle custom ship panel visibility (this works for both fuel and food)
    if (shipArchetypeSelect.value === 'custom') {
        customShipDetailsPanel.classList.remove('hidden');
    } else {
        customShipDetailsPanel.classList.add('hidden');
    }
}

// CSV Download Function
function downloadCSV() {
    if (completeResultsForCsv.length === 0) {
        showModal("No data to download. Please run a calculation first.");
        return;
    }

    let csvContent = "";
    completeResultsForCsv.forEach(row => {
        csvContent += row.map(item => {
            // Ensure commas within data are handled by enclosing in quotes
            if (typeof item === 'string' && item.includes(',')) {
                return `"${item}"`;
            }
            return item;
        }).join(",") + "\n";
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) { // Feature detection for HTML5 download attribute
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', 'lca_results.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } else {
        // Fallback for older browsers
        window.open('data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent));
    }
}

// LinkedIn Share Function
function shareOnLinkedIn() {
    const pageUrl = window.location.href;
    const shareText = encodeURIComponent("Check out my commodity transport LCA results! Generated using Eshan Singh's awesome tool: " + pageUrl);
    const linkedInShareUrl = `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(pageUrl)}&title=${encodeURIComponent("Commodity Transport LCA Results")}&summary=${shareText}&source=${encodeURIComponent("Eshan Singh's Transport Model")}`;
    window.open(linkedInShareUrl, '_blank', 'width=600,height=400');
    showModal("Your results page link has been prepared for sharing on LinkedIn. Please add a screenshot of your results manually!");
}

// Form Submission Handler
async function handleCalculation(e) {
    e.preventDefault();

    const lcaForm = document.getElementById('lcaForm');
    const calculateButton = lcaForm.querySelector('button[type="submit"]');
    const statusMessagesDiv = document.getElementById('statusMessages');
    const outputsDiv = document.getElementById('outputs');

    // Helper functions for UI updates
    function logStatus(message) { 
        statusMessagesDiv.innerHTML += `<p>> ${message}</p>`; 
        statusMessagesDiv.scrollTop = statusMessagesDiv.scrollHeight; 
        statusMessagesDiv.classList.remove('hidden');
    }
    function clearStatus() { statusMessagesDiv.innerHTML = ''; }
    function showModal(message) {
        document.getElementById('modalMessageText').textContent = message;
        document.getElementById('messageModal').style.display = "block";
    }
    document.getElementById('modalCloseButton').onclick = () => { 
        document.getElementById('messageModal').style.display = "none"; 
    };

    // Reset UI for new calculation
    clearStatus();
    logStatus("Collecting user inputs...");
    calculateButton.disabled = true;
    calculateButton.textContent = 'Calculating...';
    outputsDiv.classList.add('hidden');

    // Conditionally build the userInputs object
    const commodity = document.getElementById('commodity-type').value;
    const shipArchetype = document.getElementById('shipArchetypeSelect').value;
    
    let userInputs = {
        commodity_type: commodity,
        start: document.getElementById('startLocation').value,
        end: document.getElementById('endLocation').value,
        storage_time_A: parseFloat(document.getElementById('storageTimeA').value),
        storage_time_B: parseFloat(document.getElementById('storageTimeB').value),
        storage_time_C: parseFloat(document.getElementById('storageTimeC').value),
        LH2_plant_capacity: parseFloat(document.getElementById('lh2PlantCapacity').value),
        ship_archetype: shipArchetype,
    };

    if (commodity === 'fuel') {
        // Add fuel-specific keys
        Object.assign(userInputs, {
            fuel_type: parseInt(document.getElementById('fuel_type').value),
            marine_fuel_choice: document.getElementById('marineFuelChoice').value,
            recirculation_BOG: document.querySelector('input[name="bogTreatment"]:checked').value,
            BOG_recirculation_truck: parseFloat(document.getElementById('bogRecirculationTruck').value),
            BOG_recirculation_truck_apply: document.getElementById('bogRecirculationTruckApply').value,
            BOG_recirculation_storage: parseFloat(document.getElementById('bogRecirculationStorage').value),
            BOG_recirculation_storage_apply: document.getElementById('bogRecirculationStorageApply').value,
            BOG_recirculation_mati_trans: parseFloat(document.getElementById('bogRecirculationMaritime').value),
            BOG_recirculation_mati_trans_apply: document.getElementById('bogRecirculationMaritimeApply').value,
        });
    } else if (commodity === 'food') {
        // Add food-specific keys
        Object.assign(userInputs, {
            food_type: document.getElementById('food_type').value,
            marine_fuel_choice: document.getElementById('marineFuelChoice').value,
            shipment_size_containers: parseInt(document.getElementById('shipmentSizeContainers').value)
        });
    }

    if (shipArchetype === 'custom') {
        Object.assign(userInputs, {
            total_ship_volume: parseFloat(document.getElementById('totalShipVolume').value),
            ship_number_of_tanks: parseInt(document.getElementById('shipNumberOfTanks').value),
            ship_tank_shape: parseInt(document.getElementById('shipTankShape').value),
        });
    }

    try {
        logStatus("Sending data to the Python server... (This may take a minute)");
        const response = await fetch(`${BACKEND_URL}/calculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userInputs)
        });
        logStatus("Waiting for response...");
        const results = await response.json();
        if (results.status === 'error') throw new Error(results.message);
        logStatus("Calculation complete. Rendering results...");

        const routeBounds = displayMap(results.map_data, results.food_type);
        displayTables(results.table_data, commodity);
        completeResultsForCsv = results.csv_data;
        
        if (results.charts) {
            document.getElementById('costChartImg').src = "data:image/png;base64," + results.charts.cost_chart_base64;
            document.getElementById('emissionChartImg').src = "data:image/png;base64," + results.charts.emission_chart_base64;
        }
        
        const comparisonSection = document.getElementById('comparisonSection');
        const comparisonContainer = document.getElementById('comparisonTableContainer');
        if (results.local_sourcing_comparison) {
            const localData = results.local_sourcing_comparison;
            const shipmentCostPerKg = results.table_data.summary1_data[0][1];
            const shipmentEmissionsPerKg = results.table_data.summary1_data[2][1];

            const comparisonHeaders = ['', 'International Shipment', `Local Sourcing (from ${localData.source_name})`];
            const comparisonData = [
                ['Transport Cost ($/kg)', parseFloat(shipmentCostPerKg).toFixed(2), localData.cost_per_kg.toFixed(2)],
                ['Transport Emissions (kg CO2e/kg)', parseFloat(shipmentEmissionsPerKg).toFixed(2), localData.emissions_per_kg.toFixed(2)]
            ];

            comparisonContainer.innerHTML = createTableHtml(comparisonHeaders, comparisonData);
            comparisonSection.classList.remove('hidden');
        } else {
            comparisonSection.classList.add('hidden');
        }

        const greenPremiumSection = document.getElementById('greenPremiumSection');
        const greenPremiumContainer = document.getElementById('greenPremiumTableContainer');
        if (results.table_data.green_premium_data) {
            greenPremiumContainer.innerHTML = createTableHtml(
                results.table_data.green_premium_headers,
                results.table_data.green_premium_data
            );
            greenPremiumSection.classList.remove('hidden');
        } else {
            greenPremiumSection.classList.add('hidden');
        }

        outputsDiv.classList.remove('hidden');
        setTimeout(() => {
            map.invalidateSize();
            if (routeBounds && routeBounds.isValid()) {
                map.fitBounds(routeBounds.pad(0.1));
            }
        }, 1);
    } catch (error) {
        logStatus(`Error: ${error.message}`);
        showModal(`An error occurred: ${error.message}.`);
    } finally {
        calculateButton.disabled = false;
        calculateButton.textContent = 'Calculate';
    }
}

// Map Display Function
function displayMap(mapData, foodType) {
    console.log("displayMap called with data:", mapData);
    if (map) {
        map.remove();
        console.log("Previous map instance removed.");
    }

    if (!mapData || !mapData.coor_start || typeof mapData.coor_start.lat !== 'number' || typeof mapData.coor_start.lng !== 'number') {
        console.error("Map data or coor_start is invalid or missing. Cannot render map.", mapData);
        document.getElementById('map').innerHTML = '<p style="padding:20px; text-align:center;">Map data is unavailable or start coordinates are missing.</p>';
        return;
    }

    try {
        let initialLat = mapData.coor_start.lat;
        let initialLng = mapData.coor_start.lng;
        let initialZoom = 6;

        if (mapData.coor_end && typeof mapData.coor_end.lat === 'number' && typeof mapData.coor_end.lng === 'number') {
            initialLat = (mapData.coor_start.lat + mapData.coor_end.lat) / 2;
            initialLng = (mapData.coor_start.lng + mapData.coor_end.lng) / 2;
            initialZoom = 3;
        }

        map = L.map('map').setView([initialLat, initialLng], initialZoom);
        console.log("Leaflet map instance created and size invalidated.");

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        console.log("Tile layer added.");

        const bounds = L.latLngBounds();

        function addMarkerToMap(coords, name, iconUrl) {
            if (coords && typeof coords.lat === 'number' && typeof coords.lng === 'number') {
                let markerOptions = {};
                if (iconUrl) {
                    markerOptions.icon = L.icon({
                        iconUrl: iconUrl,
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
                    });
                }
                L.marker([coords.lat, coords.lng], markerOptions).addTo(map).bindPopup(name);
                bounds.extend([coords.lat, coords.lng]);
            } else {
                console.warn("Invalid or missing coordinates for marker:", name, coords);
            }
        }

        addMarkerToMap(mapData.coor_start, 'Start Location');
        addMarkerToMap(mapData.coor_end, 'End Location');
        addMarkerToMap(mapData.start_port, `Origin Port: ${mapData.start_port ? mapData.start_port.name : 'N/A'}`, 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png');
        addMarkerToMap(mapData.end_port, `Destination Port: ${mapData.end_port ? mapData.end_port.name : 'N/A'}`, 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png');

        function addPolylineToMap(coordsArray, color, options = {}) {
            if (coordsArray && Array.isArray(coordsArray) && coordsArray.length > 0) {
                const validCoords = coordsArray.filter(p => Array.isArray(p) && p.length === 2 && typeof p[0] === 'number' && typeof p[1] === 'number');
                if (validCoords.length > 0) {
                    L.polyline(validCoords, { color: color, weight: 3, ...options }).addTo(map);
                    validCoords.forEach(p => bounds.extend(p));
                } else {
                    console.warn(`Polyline with color ${color} had no valid coordinates.`);
                }
            } else {
                console.warn(`No data or empty array for polyline with color ${color}.`);
            }
        }

        // Food emoji routes
        const foodEmojis = {
            'strawberry': '🍓',
            'hass_avocado': '🥑',
            'banana': '🍌'
        };

        if (foodEmojis[foodType] && mapData.sea_route_coords && Array.isArray(mapData.sea_route_coords)) {
            const emoji = foodEmojis[foodType];
            const foodIcon = L.divIcon({
                html: emoji,
                className: 'emoji-icon',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });

            const markerInterval = Math.max(1, Math.floor(mapData.sea_route_coords.length / 25));
            mapData.sea_route_coords.forEach((point, index) => {
                if (index > 0 && index % markerInterval === 0) {
                    L.marker(point, { icon: foodIcon }).addTo(map);
                }
            });

            addPolylineToMap(mapData.road_route_start_coords, 'blue');
            addPolylineToMap(mapData.road_route_end_coords, 'blue');
            addPolylineToMap(mapData.sea_route_coords, 'rgba(0, 128, 0, 0.6)', { dashArray: '8, 8' });
        } else {
            addPolylineToMap(mapData.road_route_start_coords, 'blue');
            addPolylineToMap(mapData.road_route_end_coords, 'blue');
            addPolylineToMap(mapData.sea_route_coords, 'green');
        }

        if (bounds.isValid()) {
            console.log("Fitting map to valid bounds.");
        } else if (mapData.coor_start && typeof mapData.coor_start.lat === 'number') {
            map.setView([mapData.coor_start.lat, mapData.coor_start.lng], 6);
            console.log("Map view set to start coordinate as bounds were invalid.");
        } else {
            console.warn("No valid bounds to fit map.");
        }

        return bounds;
    } catch (e) {
        console.error("Error occurred within displayMap function:", e);
        document.getElementById('map').innerHTML = `<p style="padding:20px; text-align:center;">An error occurred while rendering the map.</p>`;
    }
}

// Table Creation Helper
function createTableHtml(headers, dataArray, isDetailed = false) {
      // Start with the table header
      let html = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead>';

      // Start the table body
      html += '<tbody>';

      // Loop through each ROW in the data array
      dataArray.forEach(row => {
        html += '<tr>'; // Start a new table row for each data row

        // Loop through each CELL in the current row
        row.forEach((cell, index) => {
          let cellContent = cell;

          // Apply special number formatting only for the detailed table
          if (isDetailed) {
            if (index === 0) { // First column (Process Step) is always text
              cellContent = cell;
            } else if (index >= 7) { // "Per unit" columns (Opex/kg, Capex/kg, Cost/kg, etc.) get 4 decimal places
              cellContent = isNaN(Number(cell)) ? cell : Number(cell).toFixed(4);
            } else { // Raw data columns (Opex, Capex, Energy, CO2eq, Chem, BOG/Spoilage) get scientific notation (indices 1-6)
              cellContent = isNaN(Number(cell)) ? cell : Number(cell).toExponential(2);
            }
          }
          // Add the individual table cell
          html += `<td>${cellContent}</td>`;
        });

        html += '</tr>'; // End the table row
      });

      html += '</tbody>'; // End the table body
      return '<table>' + html + '</table>'; // Wrap everything in a <table> tag
    }

// Table Display Function
function displayTables(tableData, commodity) {
    // --- 1. DETAILED TABLE LOGIC ---
    // Get the detailed table elements
    const detailedTableTitle = document.getElementById('detailedTableTitle');
    const detailedTableContainer = document.getElementById('detailedTableContainer');

    // Hide the detailed table and its title (it is not used in transport-model-new.html, but keeping the logic here)
    if (detailedTableTitle) detailedTableTitle.classList.add('hidden');
    if (detailedTableContainer) detailedTableContainer.classList.add('hidden');

    // The data is still processed and ready for CSV download, just not displayed.
    let detailedHeaders = tableData.detailed_headers || [];
    let detailedData = tableData.detailed_data || [];

    // This filtering logic is still important for the CSV data,
    // even if the table isn't displayed on the UI.
    if (commodity === 'food') {
        // If the commodity is food, filter out the GJ columns
        // These indices need to be carefully checked against your backend's new_detailed_headers
        // Assuming your backend sends the full headers and data,
        // these indices are based on `new_detailed_headers` in app_food.py
        const costPerGJIndex = detailedHeaders.indexOf('Cost/GJ ($/GJ)');
        const eco2PerGJIndex = detailedHeaders.indexOf('eCO2/GJ (kg/GJ)');

        const columnsToRemove = [];
        if (costPerGJIndex !== -1) columnsToRemove.push(costPerGJIndex);
        if (eco2PerGJIndex !== -1) columnsToRemove.push(eco2PerGJIndex);

        // Sort in descending order so that removing elements doesn't affect subsequent indices
        columnsToRemove.sort((a, b) => b - a);

        detailedHeaders = detailedHeaders.filter((_, index) => !columnsToRemove.includes(index));
        detailedData = detailedData.map(row => {
            let newRow = [...row]; // Create a copy to avoid modifying original
            columnsToRemove.forEach(index => {
                if (index < newRow.length) {
                    newRow.splice(index, 1);
                }
            });
            return newRow;
        });
    }
    // No longer rendering the detailed table HTML here

    // --- 2. SUMMARY TABLE 1 LOGIC (No changes here) ---
    const summary1Headers = tableData.summary1_headers || [];
    const summary1Data = tableData.summary1_data || [];
    document.getElementById('summaryTableContainer').innerHTML = createTableHtml(summary1Headers, summary1Data);


    // --- 3. SUMMARY TABLE 2 (PER GJ) LOGIC ---
    const summary2Container = document.getElementById('summaryTableContainer2');
    // In transport-model-new.html, the H4 for "Per GJ Results" is the previous sibling
    const summary2Title = summary2Container.previousElementSibling; 

    if (commodity === 'fuel' && tableData.summary2_data && tableData.summary2_data.length > 0) {
        // ONLY show this table if the commodity is 'fuel'
        summary2Container.innerHTML = createTableHtml(tableData.summary2_headers, tableData.summary2_data);
        summary2Container.classList.remove('hidden');
        if (summary2Title) summary2Title.classList.remove('hidden'); // Ensure the title is also shown
    } else {
        // Hide this table for 'food' or if there's no data
        summary2Container.innerHTML = '';
        summary2Container.classList.add('hidden');
        if (summary2Title) summary2Title.classList.add('hidden'); // Ensure the title is also hidden
    }

    // --- 4. ASSUMPTION TABLE LOGIC (No changes here) ---
    const assumptionHeaders = tableData.assumed_prices_headers || [];
    const assumptionData = tableData.assumed_prices_data || [];
    const assumptionContainer = document.getElementById('assumptionTableContainer');
    if(assumptionContainer) {
        assumptionContainer.innerHTML = createTableHtml(assumptionHeaders, assumptionData);
    }
}

// Modal show function
function showModal(message) {
    document.getElementById('modalMessageText').textContent = message;
    document.getElementById('messageModal').style.display = "block";
}

// transport-model.js

document.addEventListener('DOMContentLoaded', () => {
    // CHANGE: Declare a variable in an accessible scope to store the CSV data
    let csvData = [];

    // --- Toggle Visibility for Form Options ---

    // Commodity Type (Fuel vs. Food)
    const commodityType = document.getElementById('commodity-type');
    const fuelOptions = document.getElementById('fuel-options');
    const foodOptions = document.getElementById('food-options');
    const capacityLabel = document.getElementById('capacity-label');
    const capacityInput = document.getElementById('lh2PlantCapacity');
    const shipDetailsWrapper = document.getElementById('ship-details-wrapper');

    commodityType.addEventListener('change', () => {
        if (commodityType.value === 'fuel') {
            fuelOptions.classList.remove('hidden');
            foodOptions.classList.add('hidden');
            shipDetailsWrapper.classList.remove('hidden');
            capacityInput.value = "24";
            capacityLabel.textContent = "LH2 Plant Capacity (TPD):";
        } else {
            fuelOptions.classList.add('hidden');
            foodOptions.classList.remove('hidden');
            shipDetailsWrapper.classList.add('hidden');
            capacityInput.value = "50";
            capacityLabel.textContent = "Facility Capacity (Tons/Day):";
        }
    });

    // Boil-off Gas (BOG) Recirculation Details
    const bogRecirculationRadio = document.querySelector('input[name="bogTreatment"][value="2"]');
    const bogExpelRadio = document.querySelector('input[name="bogTreatment"][value="1"]');
    const bogRecirculationDetails = document.getElementById('bogRecirculationDetails');

    bogRecirculationRadio.addEventListener('change', () => {
        if (bogRecirculationRadio.checked) {
            bogRecirculationDetails.classList.remove('hidden');
        }
    });
    bogExpelRadio.addEventListener('change', () => {
        if (bogExpelRadio.checked) {
            bogRecirculationDetails.classList.add('hidden');
        }
    });

    // Custom Ship Details
    const shipArchetypeSelect = document.getElementById('shipArchetypeSelect');
    const customShipDetails = document.getElementById('customShipDetails');

    shipArchetypeSelect.addEventListener('change', () => {
        if (shipArchetypeSelect.value === 'custom') {
            customShipDetails.classList.remove('hidden');
        } else {
            customShipDetails.classList.add('hidden');
        }
    });

    // --- Main Form Submission ---
    const lcaForm = document.getElementById('lcaForm');
    lcaForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const button = this.querySelector('button[type="submit"]');
        const statusDiv = document.getElementById('statusMessages');

        button.disabled = true;
        statusDiv.innerHTML = 'Initializing... Preparing to send request.';
        statusDiv.classList.remove('hidden');
        document.getElementById('outputs').classList.add('hidden');

        const inputs = {
            start: document.getElementById('startLocation').value,
            end: document.getElementById('endLocation').value,
            commodity_type: document.getElementById('commodity-type').value,
            fuel_type: parseInt(document.getElementById('fuel_type').value, 10),
            food_type: document.getElementById('food_type').value,
            recirculation_BOG: document.querySelector('input[name="bogTreatment"]:checked').value,
            BOG_recirculation_truck: parseFloat(document.getElementById('bogRecirculationTruck').value),
            BOG_recirculation_truck_apply: document.getElementById('bogRecirculationTruckApply').value,
            BOG_recirculation_storage: parseFloat(document.getElementById('bogRecirculationStorage').value),
            BOG_recirculation_storage_apply: document.getElementById('bogRecirculationStorageApply').value,
            BOG_recirculation_mati_trans: parseFloat(document.getElementById('bogRecirculationMaritime').value),
            BOG_recirculation_mati_trans_apply: document.getElementById('bogRecirculationMaritimeApply').value,
            marine_fuel_choice: document.getElementById('marineFuelChoice').value,
            LH2_plant_capacity: parseFloat(document.getElementById('lh2PlantCapacity').value),
            storage_time_A: parseFloat(document.getElementById('storageTimeA').value),
            storage_time_B: parseFloat(document.getElementById('storageTimeB').value),
            storage_time_C: parseFloat(document.getElementById('storageTimeC').value),
            shipment_size_containers: parseInt(document.getElementById('shipmentSizeContainers').value),
            ship_archetype: document.getElementById('shipArchetypeSelect').value,
            total_ship_volume: parseFloat(document.getElementById('totalShipVolume').value),
            ship_number_of_tanks: parseInt(document.getElementById('shipNumberOfTanks').value, 10),
            ship_tank_shape: parseInt(document.getElementById('shipTankShape').value, 10),
        };

        statusDiv.innerHTML = 'Request sent. Waiting for server to process...';

        fetch('https://lca-food-fuel-2e4559590eca.herokuapp.com/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(inputs)
            })
            .then(response => {
                statusDiv.innerHTML = 'Response received. Processing data...';
                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status !== "success") {
                    throw new Error(data.message || "The server returned an error.");
                }

                // CHANGE: Store the CSV data from the response into our variable.
                csvData = data.csv_data;

                // --- Populate results on the page ---
                document.getElementById('costChartImg').src = `data:image/png;base64,${data.charts.cost_chart_base64}`;
                document.getElementById('emissionChartImg').src = `data:image/png;base64,${data.charts.emission_chart_base64}`;

                // Populate summary tables, detailed tables, map, etc.
                // ... (your existing or future UI update logic would go here) ...

                statusDiv.classList.add('hidden');
                document.getElementById('outputs').classList.remove('hidden');
                window.scrollTo({
                    top: document.getElementById('outputs').offsetTop,
                    behavior: 'smooth'
                });

            })
            .catch(error => {
                statusDiv.innerHTML = `An error occurred: ${error.message}`;
                console.error("Error during calculation:", error);
            })
            .finally(() => {
                button.disabled = false;
            });
    });

    // CHANGE: Implement the CSV download functionality.
    const downloadButton = document.getElementById('downloadCsvButton');
    downloadButton.addEventListener('click', function() {
        if (!csvData || csvData.length === 0) {
            alert("No data available to download. Please run a calculation first.");
            return;
        }

        // Convert the array of arrays into a CSV string
        // This handles cells with commas by enclosing them in double quotes
        const csvContent = csvData.map(rowArray => {
            return rowArray.map(cell => {
                let cellStr = String(cell).replace(/"/g, '""'); // Escape double quotes
                if (cellStr.includes(',') || cellStr.includes('"') || cellStr.includes('\n')) {
                    cellStr = `"${cellStr}"`; // Enclose in double quotes
                }
                return cellStr;
            }).join(',');
        }).join('\n');

        // Create a Blob and trigger the download
        const blob = new Blob([csvContent], {
            type: 'text/csv;charset=utf-8;'
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", "lca_results.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
});
