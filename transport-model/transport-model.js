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

        capacityLabel.textContent = 'Liquefaction Plant Capacity (TPD):';
        shipOptions[1].textContent = 'Small-Scale Carrier (20,000 m³)';
        shipOptions[2].textContent = 'Aframax Product Tanker - SAF/MeOH (80,000 m³)';
        shipOptions[3].textContent = 'Midsized Carrier (90,000 m³)';
        shipOptions[4].textContent = 'Standard Modern Carrier - LNG (174,000 m³)';
        shipOptions[5].textContent = 'Q-Flex Carrier (210,000 m³)';
        shipOptions[6].textContent = 'Q-Max Carrier (266,000 m³)';
        
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
        shipOptions[6].textContent = 'Ultra-Large Vessel (20,000+ Containers)'; // Duplicate to maintain array length
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

// Plotly Chart Rendering Functions
function renderCostChart(chartData) {
    if (!chartData || !chartData.labels) {
        console.error("Invalid chart data for cost chart");
        return;
    }

    // Create stacked horizontal bar chart
    const traces = [];

    // Insurance (purple)
    if (chartData.insurance && chartData.insurance.some(v => v > 0)) {
        traces.push({
            y: chartData.labels,
            x: chartData.insurance,
            name: 'Overheads & Fees',
            type: 'bar',
            orientation: 'h',
            marker: { color: '#800080' },
            hovertemplate: '%{y}<br>Overheads: $%{x:.4f}/kg<extra></extra>'
        });
    }

    // OPEX (light green)
    traces.push({
        y: chartData.labels,
        x: chartData.opex,
        name: 'OPEX',
        type: 'bar',
        orientation: 'h',
        marker: { color: '#8BC34A' },
        hovertemplate: '%{y}<br>OPEX: $%{x:.4f}/kg<extra></extra>'
    });

    // CAPEX (darker green)
    traces.push({
        y: chartData.labels,
        x: chartData.capex,
        name: 'CAPEX',
        type: 'bar',
        orientation: 'h',
        marker: { color: '#4CAF50' },
        hovertemplate: '%{y}<br>CAPEX: $%{x:.4f}/kg<extra></extra>'
    });

    // Carbon Tax (yellow)
    if (chartData.carbon_tax && chartData.carbon_tax.some(v => v > 0)) {
        traces.push({
            y: chartData.labels,
            x: chartData.carbon_tax,
            name: 'Carbon Tax',
            type: 'bar',
            orientation: 'h',
            marker: { color: '#FFC107' },
            hovertemplate: '%{y}<br>Carbon Tax: $%{x:.4f}/kg<extra></extra>'
        });
    }

    // Calculate dynamic height
    const numRows = chartData.labels.length;
    const baseHeight = 350;
    const rowHeight = 30;
    const totalHeight = baseHeight + (numRows * rowHeight);

    const layout = {
        title: {
            text: chartData.title,
            font: { size: 18, family: 'Inter, sans-serif', color: '#1f2937', weight: 600 },
            x: 0,
            xanchor: 'left',
            y: 0.98,
            yanchor: 'top'
        },
        xaxis: {
            title: {
                text: chartData.x_label,
                font: { size: 13, family: 'Inter, sans-serif', color: '#4b5563' }
            },
            gridcolor: '#e5e7eb',
            showline: true,
            linecolor: '#d1d5db',
            linewidth: 1,
            zeroline: false,
            automargin: true
        },
        yaxis: {
            autorange: 'reversed',
            gridcolor: 'rgba(0,0,0,0)',
            showline: false,
            tickfont: { size: 11, family: 'Inter, sans-serif', color: '#374151' },
            automargin: true
        },
        barmode: 'stack',
        hovermode: 'closest',
        showlegend: true,
        legend: {
            orientation: 'v',
            yanchor: 'bottom',
            y: 0.02,
            xanchor: 'right',
            x: 0.98,
            font: { size: 10, family: 'Inter, sans-serif' },
            bgcolor: 'rgba(255, 255, 255, 0.95)',
            bordercolor: '#d1d5db',
            borderwidth: 1
        },
        margin: { t: 70, b: 80 },
        height: totalHeight,
        plot_bgcolor: '#fafafa',
        paper_bgcolor: '#ffffff',
        autosize: true
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
    };

    Plotly.newPlot('costChart', traces, layout, config);

    // Display context text in HTML div below chart
    const contextDiv = document.getElementById('costChartContext');
    if (chartData.overlay_text && contextDiv) {
        contextDiv.innerHTML = chartData.overlay_text.split('\n').map(line => `<p>${line}</p>`).join('');
        contextDiv.style.display = 'block';
    }
}

function renderEmissionChart(chartData) {
    if (!chartData || !chartData.labels) {
        console.error("Invalid chart data for emission chart");
        return;
    }

    const trace = {
        y: chartData.labels,
        x: chartData.emissions,
        name: 'Emissions',
        type: 'bar',
        orientation: 'h',
        marker: { color: '#4CAF50' },
        hovertemplate: '%{y}<br>Emissions: %{x:.4f} kg CO₂eq/kg<extra></extra>'
    };

    // Calculate dynamic height
    const numRows = chartData.labels.length;
    const baseHeight = 350;
    const rowHeight = 30;
    const totalHeight = baseHeight + (numRows * rowHeight);

    const layout = {
        title: {
            text: chartData.title,
            font: { size: 18, family: 'Inter, sans-serif', color: '#1f2937', weight: 600 },
            x: 0,
            xanchor: 'left',
            y: 0.98,
            yanchor: 'top'
        },
        xaxis: {
            title: {
                text: chartData.x_label,
                font: { size: 13, family: 'Inter, sans-serif', color: '#4b5563' }
            },
            gridcolor: '#e5e7eb',
            showline: true,
            linecolor: '#d1d5db',
            linewidth: 1,
            zeroline: false,
            automargin: true
        },
        yaxis: {
            autorange: 'reversed',
            gridcolor: 'rgba(0,0,0,0)',
            showline: false,
            tickfont: { size: 11, family: 'Inter, sans-serif', color: '#374151' },
            automargin: true
        },
        hovermode: 'closest',
        showlegend: false,
        margin: { t: 70, b: 80 },
        height: totalHeight,
        plot_bgcolor: '#fafafa',
        paper_bgcolor: '#ffffff',
        autosize: true
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
    };

    Plotly.newPlot('emissionChart', [trace], layout, config);

    // Display context text in HTML div below chart
    const contextDiv = document.getElementById('emissionChartContext');
    if (chartData.overlay_text && contextDiv) {
        contextDiv.innerHTML = chartData.overlay_text.split('\n').map(line => `<p>${line}</p>`).join('');
        contextDiv.style.display = 'block';
    }
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

    // --- Cleanup: Remove old arrow AND the spacer ---
    const existingClonedArrow = document.getElementById('cloned-arrow-for-results');
    if (existingClonedArrow) {
        existingClonedArrow.remove();
    }
    const existingSpacer = document.getElementById('cloned-arrow-spacer');
    if (existingSpacer) {
        existingSpacer.remove();
    }
    // --------------------------------------------------

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

        // --- Arrow & Spacer Creation (MODIFIED) ---
        const originalArrow = document.querySelector('.scroll-down-arrow');
        const formCard = statusMessagesDiv.closest('.glass-card');

        if (originalArrow && formCard) {
            // 1. Create an invisible spacer div
            const spacer = document.createElement('div');
            spacer.id = 'cloned-arrow-spacer';
            spacer.style.height = '8rem'; // <-- ADJUST THIS VALUE FOR MORE/LESS SPACE

            // 2. Clone the arrow
            const clonedArrow = originalArrow.cloneNode(true);
            clonedArrow.id = 'cloned-arrow-for-results';
            clonedArrow.style.cursor = 'pointer';
            clonedArrow.style.margin = 'auto';

            clonedArrow.addEventListener('click', () => {
                outputsDiv.scrollIntoView({ behavior: 'smooth' });
            });
            
            // 3. Place the spacer and then the arrow after the form card
            formCard.insertAdjacentElement('afterend', clonedArrow);
            formCard.insertAdjacentElement('afterend', spacer);
        }
        // -------------------------------------------

        const routeBounds = displayMap(results.map_data, results.food_type);
        displayTables(results.table_data, commodity);
        completeResultsForCsv = results.csv_data;
        
        console.log("Full results object:", results);
        if (results.charts) {
            console.log("Charts data received:", results.charts);

            // Check if we have new Plotly data format
            if (results.charts.cost_chart_data && results.charts.cost_chart_data.labels) {
                console.log("✅ Using new Plotly data format");
                renderCostChart(results.charts.cost_chart_data);
                renderEmissionChart(results.charts.emission_chart_data);

                // Force Plotly to resize charts after a short delay to ensure proper rendering
                setTimeout(() => {
                    Plotly.Plots.resize('costChart');
                    Plotly.Plots.resize('emissionChart');
                }, 100);
            }
            // Fallback to old base64 format if backend not yet deployed
            else if (results.charts.cost_chart_base64) {
                console.warn("⚠️ Backend not deployed yet - using old matplotlib format");
                document.getElementById('costChart').innerHTML = `<img src="data:image/png;base64,${results.charts.cost_chart_base64}" class="w-full" alt="Cost Chart">`;
                document.getElementById('emissionChart').innerHTML = `<img src="data:image/png;base64,${results.charts.emission_chart_base64}" class="w-full" alt="Emission Chart">`;
            } else {
                console.error("❌ No valid chart data found (neither Plotly nor base64)");
                console.log("Charts object:", results.charts);
            }
        } else {
            console.error("❌ No charts object in results");
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

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Attach event listeners
    commoditySelector.addEventListener('change', updateFormVisibility);
    document.querySelectorAll('input[name="bogTreatment"]').forEach(radio => {
        radio.addEventListener('change', updateFormVisibility);
    });
    shipArchetypeSelect.addEventListener('change', updateFormVisibility);
    
    // Set the initial state of the form when the page loads
    updateFormVisibility();

    // Attach event listeners for buttons
    document.getElementById('downloadCsvButton').addEventListener('click', downloadCSV);
    document.getElementById('shareLinkedInButton').addEventListener('click', shareOnLinkedIn);
    document.getElementById('lcaForm').addEventListener('submit', handleCalculation);
    
    // Modal close button
    document.getElementById('modalCloseButton').onclick = () => { 
        document.getElementById('messageModal').style.display = "none"; 
    };
});
