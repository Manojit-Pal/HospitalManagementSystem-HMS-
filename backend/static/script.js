// static/script.js - Corrected version with debug logs for Now Serving section

// --- Fetch Functions ---

// Function to fetch and display system stats
function fetchSystemStats() {
    // Use the global variable defined in index.html
    fetch(systemStatsUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching stats:', data.details);
                document.getElementById('totalPatients').textContent = 'N/A';
                document.getElementById('availableBeds').textContent = 'N/A';
                document.getElementById('appointmentsToday').textContent = 'N/A';
                return;
            }
            document.getElementById('totalPatients').textContent = data.total_patients;
            document.getElementById('availableBeds').textContent = data.available_beds;
            document.getElementById('appointmentsToday').textContent = data.appointments_today;
        })
        .catch(error => {
            console.error('Error fetching system stats:', error);
            document.getElementById('totalPatients').textContent = 'Error';
            document.getElementById('availableBeds').textContent = 'Error';
            document.getElementById('appointmentsToday').textContent = 'Error';
        });
}

// Function to fetch and display recent activities
function fetchRecentActivities() {
    // Use the global variable defined in index.html
    fetch(recentActivitiesUrl)
        .then(response => { if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); } return response.json(); })
        .then(data => {
            if (data.error) { console.error('Backend error fetching recent activities:', data.details); document.getElementById('recentPatientsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading patients</li>'; document.getElementById('recentAdmissionsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading admissions</li>'; return; }

            // Update Recent Patients list
            const patientsList = document.getElementById('recentPatientsList'); patientsList.innerHTML = '';
            if (data.patients && data.patients.length > 0) { data.patients.forEach(patient => { const listItem = document.createElement('li'); listItem.classList.add('list-group-item'); listItem.innerHTML = `<span class="activity-details">${patient.name}</span><span class="activity-time">ID: ${patient.patient_id ? patient.patient_id.substring(0, 6) + '...' : 'N/A'}</span>`; patientsList.appendChild(listItem); }); } else { patientsList.innerHTML = '<li class="list-group-item text-center text-muted">No recent patients.</li>'; }

            // Update Recent Admissions list
            const admissionsList = document.getElementById('recentAdmissionsList'); admissionsList.innerHTML = '';
            if (data.admissions && data.admissions.length > 0) { data.admissions.forEach(admission => { const listItem = document.createElement('li'); listItem.classList.add('list-group-item'); const formattedAdmissionTime = admission.admission_time; listItem.innerHTML = `<span class="activity-details">${admission.patient_name} admitted</span><span class="activity-time">${formattedAdmissionTime}</span>`; admissionsList.appendChild(listItem); }); } else { admissionsList.innerHTML = '<li class="list-group-item text-center text-muted">No recent admissions.</li>'; }
        })
        .catch(error => { console.error('Error fetching recent activities:', error); document.getElementById('recentPatientsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading patients</li>'; document.getElementById('recentAdmissionsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading admissions</li>'; });
}

// Function to fetch and display now serving data
function fetchNowServing() {
    fetch('/get_now_serving') // Make a GET request to your Flask endpoint
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // This line clears the container before adding new cards
            console.log("Fetching Now Serving data. Clearing previous cards."); // Debug log BEFORE clearing
            const nowServingList = document.getElementById('nowServingList');
            // Clear existing content
            nowServingList.innerHTML = '';

            // This log shows the exact data received from the backend
            console.log("Received Now Serving data:", data);

            if (data.error) {
                console.error('Backend error fetching now serving data:', data.details);
                nowServingList.innerHTML = `
                            <div class="col-md-12 text-center">
                                <p class="card-text text-danger">Error loading now serving data</p>
                            </div>
                        `;
                return;
            }

            if (data && data.length > 0) {
                data.forEach(item => {
                    const cardCol = document.createElement('div');
                    cardCol.classList.add('col-md-4', 'text-center'); // Use col-md-4 for layout

                    const card = document.createElement('div');
                    card.classList.add('card', 'p-3', 'shadow-sm', 'h-100'); // Add card styling

                    card.innerHTML = `
                                <div class="card-body">
                                    <h5 class="card-title">${item.department}</h5>
                                    <p class="card-text serving-token">${item.token_number}</p>
                                 </div>
                            `;
                    cardCol.appendChild(card);
                    nowServingList.appendChild(cardCol);
                });
            } else {
                // Display a message if no departments are currently serving
                nowServingList.innerHTML = `
                            <div class="col-md-12 text-center">
                                <p class="card-text text-muted">No departments currently serving.</p>
                            </div>
                            `;
            }
        })
        .catch(error => {
            console.error('Error fetching now serving data:', error);
            const nowServingList = document.getElementById('nowServingList');
            nowServingList.innerHTML = `
                            <div class="col-md-12 text-center">
                                <p class="card-text text-danger">Error loading now serving data</p>
                            </div>
                            `;
        });
}

// Function to fetch admissions data and update the chart
function fetchAdmissionsDataForChart() {
    // Use the global variable defined in index.html
    fetch(admissionsDataUrl) // Make sure this URL now points to your *new* backend endpoint/logic
        .then(response => { if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); } return response.json(); })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching admissions data:', data.details);
                // Existing error handling...
                if (window.admissionsChart) {
                    window.admissionsChart.data.labels = ['Error'];
                    window.admissionsChart.data.datasets[0].data = [0];
                    // Update title on error
                    if (window.admissionsChart.options.plugins && window.admissionsChart.options.plugins.title) {
                        window.admissionsChart.options.plugins.title.text = 'Error loading data';
                    } else if (window.admissionsChart.options.title) {
                        window.admissionsChart.options.title.text = 'Error loading data';
                    }
                    window.admissionsChart.update();
                }
                return;
            }

            // Check if chart object and data exist and have expected properties
            if (window.admissionsChart && data.labels && data.data) {
                // Update the chart's data and labels
                window.admissionsChart.data.labels = data.labels; // Should now be the last 5 dates
                window.admissionsChart.data.datasets[0].data = data.data; // Should now be the daily counts

                // *** Update chart title for clarity ***
                const newTitle = 'Patient Admissions - Last 5 Days';
                if (window.admissionsChart.options.plugins && window.admissionsChart.options.plugins.title) {
                    window.admissionsChart.options.plugins.title.text = newTitle;
                } else if (window.admissionsChart.options.title) { // Fallback for older Chart.js
                    window.admissionsChart.options.title.text = newTitle;
                }


                // Update the chart to display the new data
                window.admissionsChart.update();
            } else {
                console.warn("Chart object not found or data format unexpected.");
                // Existing handling for missing chart/data...
                if (window.admissionsChart) {
                    window.admissionsChart.data.labels = ['No Data'];
                    window.admissionsChart.data.datasets[0].data = [0];
                    if (window.admissionsChart.options.plugins && window.admissionsChart.options.plugins.title) {
                        window.admissionsChart.options.plugins.title.text = 'No data available';
                    } else if (window.admissionsChart.options.title) {
                        window.admissionsChart.options.title.text = 'No data available';
                    }
                    window.admissionsChart.update();
                }
            }
        })
        .catch(error => {
            console.error('Error fetching admissions data:', error);

            if (window.admissionsChart) {
                window.admissionsChart.data.labels = ['Error'];
                window.admissionsChart.data.datasets[0].data = [0];
                if (window.admissionsChart.options.plugins && window.admissionsChart.options.plugins.title) {
                    window.admissionsChart.options.plugins.title.text = 'Error loading data';
                } else if (window.admissionsChart.options.title) {
                    window.admissionsChart.options.title.text = 'Error loading data';
                }
                window.admissionsChart.update();
            }
        });
}

// Function to fetch and display daily OPD chart data
function fetchDailyOpdStats() {
    const dailyOpdCanvas = document.getElementById('dailyOpdChart');
    const chartContainer = dailyOpdCanvas ? dailyOpdCanvas.parentElement : null; // Get the parent container

    fetch(dailyOpdStatsUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching daily OPD data:', data.details);
                displayChartErrorMessage(chartContainer, 'Error loading data'); // Use helper for error message
                return;
            }

            // --- NEW: Check if data is empty ---
            if (!data || !data.labels || data.labels.length === 0 || !data.data || data.data.length === 0) {
                console.log("No daily OPD data available.");
                displayNoDataMessage(chartContainer, 'No patient has booked OPD today.'); // Display specific message
                // Destroy existing chart if it was previously rendered
                if (window.dailyOpdChart) {
                    window.dailyOpdChart.destroy();
                    window.dailyOpdChart = null; // Clear the reference
                }
                return; // Stop processing if no data
            }
            // --- END NEW ---


            // If data is available, ensure the canvas is visible and initialize/update the chart
            if (dailyOpdCanvas && chartContainer) {
                // Clear any previous messages
                chartContainer.innerHTML = '';
                chartContainer.appendChild(dailyOpdCanvas); // Ensure canvas is back in container

                if (!window.dailyOpdChart) {
                    // Initialize chart if it doesn't exist (e.g., first load after no data)
                    const ctx = dailyOpdCanvas.getContext('2d');
                    window.dailyOpdChart = new Chart(ctx, {
                        type: 'pie', // Set type to 'pie'
                        data: {
                            labels: [], // Will be populated by fetch function
                            datasets: [{
                                data: [], // Will be populated by fetch function
                                backgroundColor: [], // Will be populated by fetch function
                                borderColor: document.body.classList.contains('dark-mode') ? '#343a40' : '#fff', // Border color
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'top',
                                    labels: {
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Initial legend color
                                    }
                                },
                                title: {
                                    display: true,
                                    text: "Today's OPD Bookings by Department", // Initial title
                                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Initial title color
                                }
                            }
                        }
                    });
                }


                // Update the chart's data and labels
                window.dailyOpdChart.data.labels = data.labels;
                window.dailyOpdChart.data.datasets[0].data = data.data;

                // Generate dynamic colors based on the number of departments
                window.dailyOpdChart.data.datasets[0].backgroundColor = generateColors(data.labels.length);

                updateChartTitle(window.dailyOpdChart, "Today's OPD Bookings by Department"); // Update title on success
                window.dailyOpdChart.update();

            } else {
                console.error("Daily OPD chart canvas element or container not found during data processing.");
                // Fallback if container/canvas is somehow missing
                displayChartErrorMessage(null, 'Chart area not found');
            }
        })
        .catch(error => {
            console.error('Error fetching daily OPD stats:', error);
            displayChartErrorMessage(chartContainer, 'Error loading data'); // Use helper for error message
            // Destroy existing chart on error
            if (window.dailyOpdChart) {
                window.dailyOpdChart.destroy();
                window.dailyOpdChart = null;
            }
        });
}

// Function to fetch and display monthly OPD chart data
function fetchMonthlyOpdStats() {
    const monthlyOpdCanvas = document.getElementById('monthlyOpdChart');
    const chartContainer = monthlyOpdCanvas ? monthlyOpdCanvas.parentElement : null; // Get the parent container

    fetch(monthlyOpdStatsUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching monthly OPD data:', data.details);
                displayChartErrorMessage(chartContainer, 'Error loading data'); // Use helper for error message
                return;
            }

            // --- NEW: Check if data is empty ---
            if (!data || !data.labels || data.labels.length === 0 || !data.data || data.data.length === 0) {
                console.log("No monthly OPD data available.");
                displayNoDataMessage(chartContainer, 'No patient has booked OPD in the last month.'); // Display specific message
                // Destroy existing chart if it was previously rendered
                if (window.monthlyOpdChart) {
                    window.monthlyOpdChart.destroy();
                    window.monthlyOpdChart = null; // Clear the reference
                }
                return; // Stop processing if no data
            }
            // --- END NEW ---

            // If data is available, ensure the canvas is visible and initialize/update the chart
            if (monthlyOpdCanvas && chartContainer) {
                // Clear any previous messages
                chartContainer.innerHTML = '';
                chartContainer.appendChild(monthlyOpdCanvas); // Ensure canvas is back in container

                if (!window.monthlyOpdChart) {
                    // Initialize chart if it doesn't exist
                    const ctx = monthlyOpdCanvas.getContext('2d');
                    window.monthlyOpdChart = new Chart(ctx, {
                        type: 'pie', // Set type to 'pie'
                        data: {
                            labels: [], // Will be populated by fetch function
                            datasets: [{
                                data: [], // Will be populated by fetch function
                                backgroundColor: [], // Will be populated by fetch function
                                borderColor: document.body.classList.contains('dark-mode') ? '#343a40' : '#fff', // Border color
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'top',
                                    labels: {
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Initial legend color
                                    }
                                },
                                title: {
                                    display: true,
                                    text: "Last Month's OPD Bookings by Department", // Initial title
                                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Initial title color
                                }
                            }
                        }
                    });
                }

                // Update the chart's data and labels
                window.monthlyOpdChart.data.labels = data.labels;
                window.monthlyOpdChart.data.datasets[0].data = data.data;

                // Generate dynamic colors
                window.monthlyOpdChart.data.datasets[0].backgroundColor = generateColors(data.labels.length);

                updateChartTitle(window.monthlyOpdChart, "Last Month's OPD Bookings by Department"); // Update title on success
                window.monthlyOpdChart.update();

            } else {
                console.error("Monthly OPD chart canvas element or container not found during data processing.");
                displayChartErrorMessage(null, 'Chart area not found');
            }
        })
        .catch(error => {
            console.error('Error fetching monthly OPD stats:', error);
            displayChartErrorMessage(chartContainer, 'Error loading data'); // Use helper for error message
            // Destroy existing chart on error
            if (window.monthlyOpdChart) {
                window.monthlyOpdChart.destroy();
                window.monthlyOpdChart = null;
            }
        });
}


function fetchInventoryChartData() {

    const inventoryCanvas = document.getElementById('inventoryStockChart');
    const chartContainer = inventoryCanvas ? inventoryCanvas.closest('.chart-container') : null;

    if (typeof inventoryChartDataUrl === 'undefined') {
        console.error("inventoryChartDataUrl is not defined!");
        displayChartErrorMessage(chartContainer, 'Chart data URL is missing. Check configuration.');
        return; // Stop execution if URL is not defined
    }

    fetch(inventoryChartDataUrl)
        .then(response => {
            if (!response.ok) {
                // Handle HTTP errors (e.g., 404 Not Found, 500 Internal Server Error)
                console.error(`HTTP error fetching inventory chart data: ${response.status}`);
                displayChartErrorMessage(chartContainer, 'Error loading chart data.');
                throw new Error(`HTTP error! status: ${response.status}`); // Propagate error
            }
            return response.json();
        })
        .then(data => {
            // Check for backend-specific errors returned in the JSON payload
            if (data.error) {
                console.error('Backend error fetching inventory data:', data.details || data.error);
                displayChartErrorMessage(chartContainer, `Backend error: ${data.message || data.error}`);
                // Optionally update the chart to show an error state if it exists
                if (window.inventoryStockChart) {
                    window.inventoryStockChart.data.labels = ['Error'];
                    window.inventoryStockChart.data.datasets[0].data = [0]; // Reset data
                    updateChartTitle(window.inventoryStockChart, 'Error loading data');
                    window.inventoryStockChart.update();
                }
                return; // Stop processing on error
            }

            // Check if data is empty
            if (!data || !data.labels || data.labels.length === 0 || !data.data || data.data.length === 0) {
                console.log("No inventory data available for charting.");
                displayNoDataMessage(chartContainer, 'No inventory items available for charting.'); // Display specific message
                // Destroy existing chart if it was previously rendered
                if (window.inventoryStockChart) {
                    window.inventoryStockChart.destroy();
                    window.inventoryStockChart = null; // Clear the reference
                }
                return; // Stop processing if no data
            }


            // Check if chart object exists and data has expected properties
            if (inventoryCanvas && chartContainer) {
                // Clear any previous messages and ensure canvas is in container
                chartContainer.innerHTML = '';
                chartContainer.appendChild(inventoryCanvas);

                if (!window.inventoryStockChart) {
                    // Initialize chart if it doesn't exist
                    const ctx = inventoryCanvas.getContext('2d');
                    window.inventoryStockChart = new Chart(ctx, {
                        type: 'bar', // Bar chart type
                        data: {
                            labels: [], // Will be populated by fetch function
                            datasets: [{
                                label: 'Quantity in Stock',
                                data: [], // Will be populated by fetch function
                                backgroundColor: [
                                    'rgba(75, 192, 192, 0.6)', // Example colors
                                    'rgba(153, 102, 255, 0.6)',
                                    'rgba(255, 159, 64, 0.6)',
                                    'rgba(255, 99, 132, 0.6)',
                                    'rgba(54, 162, 235, 0.6)',
                                    'rgba(201, 203, 207, 0.6)'
                                    // Add more colors or use generateColors function
                                ],
                                borderColor: [
                                    'rgba(75, 192, 192, 1)',
                                    'rgba(153, 102, 255, 1)',
                                    'rgba(255, 159, 64, 1)',
                                    'rgba(255, 99, 132, 1)',
                                    'rgba(54, 162, 235, 1)',
                                    'rgba(201, 203, 207, 1)'
                                ],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false, // Allow height adjustment via CSS
                            plugins: {
                                legend: {
                                    display: false // Hide legend if it's just one dataset
                                },
                                title: {
                                    display: true, // Ensure title is displayed
                                    text: 'Inventory Stock Levels', // Initial Title
                                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Initial title color
                                },
                                tooltip: { // Add tooltips for better info on hover
                                    callbacks: {
                                        label: function (context) {
                                            let label = context.dataset.label || '';
                                            if (label) {
                                                label += ': ';
                                            }
                                            // Assuming units are not returned in this data, just show quantity
                                            label += context.raw; // + (data.units && data.units[context.dataIndex] ? ' ' + data.units[context.dataIndex] : '');
                                            return label;
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true, // Start y-axis at 0
                                    title: {
                                        display: true,
                                        text: 'Quantity',
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Axis title color
                                    },
                                    ticks: {
                                        stepSize: 1, // Ensure whole numbers if quantities are integers
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Axis tick color
                                    },
                                    grid: {
                                        color: document.body.classList.contains('dark-mode') ? 'rgba(241, 241, 241, 0.1)' : 'rgba(0, 0, 0, 0.1)' // Grid line color
                                    }
                                },
                                x: {
                                    title: {
                                        display: true,
                                        text: 'Item Name',
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Axis title color
                                    },
                                    ticks: {
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057' // Axis tick color
                                    },
                                    grid: {
                                        color: document.body.classList.contains('dark-mode') ? 'rgba(241, 241, 241, 0.1)' : 'rgba(0, 0, 0, 0.1)' // Grid line color
                                    }
                                }
                            }
                        }
                    });
                }

                // Update the chart's data and labels
                window.inventoryStockChart.data.labels = data.labels; // Item names
                window.inventoryStockChart.data.datasets[0].data = data.data; // Quantities

                // Generate dynamic colors based on the number of items
                window.inventoryStockChart.data.datasets[0].backgroundColor = generateColors(data.labels.length);


                updateChartTitle(window.inventoryStockChart, 'Inventory Stock Levels'); // Update title on success
                window.inventoryStockChart.update();


            } else {
                console.error("Inventory chart canvas element or container not found during data processing.");
                displayChartErrorMessage(null, 'Chart area not found');
            }
        })
        .catch(error => {
            console.error('Error fetching inventory data:', error);
            displayChartErrorMessage(chartContainer, 'Could not load inventory chart.');
            // Optionally update the chart to show an error state if it exists
            if (window.inventoryStockChart) {
                window.inventoryStockChart.data.labels = ['Error'];
                window.inventoryStockChart.data.datasets[0].data = [0];
                updateChartTitle(window.inventoryStockChart, 'Error loading data');
                window.inventoryStockChart.update();
            }
        });
}

/**
 * Fetches low stock inventory items from the backend and updates the UI.
 */
function fetchLowStockItems() {
    const lowStockListElement = document.getElementById('lowStockItemsList');
    const lowStockCountElement = document.getElementById('lowStockCount');

    // Check if elements exist. If the HTML section is wrapped in Jinja2 {% if %},
    // these elements might not exist for non-hospital users, which is expected.
    if (!lowStockListElement || !lowStockCountElement) {
        // console.warn("Low stock alert elements not found on this page. This is expected for non-hospital users if using Jinja2 wrapper.");
        return; // Exit if elements are missing (likely due to Jinja2 check)
    }

    // --- NEW: Frontend Authorization Check ---
    // Check if the current user type is 'hospital'.
    // currentUserType should be set in a script tag in your HTML using Jinja2.
    if (typeof currentUserType === 'undefined' || currentUserType !== 'hospital') {
        console.log("User is not authorized to view low stock items (Frontend check).");
        // Display a message indicating lack of permission
        lowStockListElement.innerHTML = '<li class="list-group-item text-center text-info">You do not have permission to view low stock alerts.</li>';
        lowStockCountElement.textContent = 'N/A'; // Or hide the badge entirely
        // Optionally hide the entire section if it was rendered despite the check (less common with Jinja2)
        // const lowStockSection = lowStockListElement.closest('.low-stock-alert-section');
        // if (lowStockSection) {
        //     lowStockSection.style.display = 'none';
        // }
        return; // Exit the function if not authorized
    }
    // --- END NEW ---

    // Check if URL is defined (still necessary for authorized users)
    if (typeof lowStockItemsUrl === 'undefined') {
        console.error("lowStockItemsUrl is not defined!");
         lowStockListElement.innerHTML = '<li class="list-group-item text-center text-danger">Configuration Error: Low stock URL missing.</li>';
         lowStockCountElement.textContent = 'Error';
        return; // Exit if URL is missing
    }


    // Set loading state
    lowStockListElement.innerHTML = '<li class="list-group-item text-center text-muted">Loading low stock items...</li>';
    lowStockCountElement.textContent = '...';


    fetch(lowStockItemsUrl)
        .then(response => {
            // --- Handle 403 Forbidden response from backend ---
            // This is the backend authorization check response
            if (response.status === 403) {
                 console.warn("Backend returned 403 Forbidden for low stock data.");
                 // Read the backend's message and display it
                 return response.json().then(data => {
                     lowStockListElement.innerHTML = `<li class="list-group-item text-center text-info">${data.message || 'You do not have permission to view low stock items.'}</li>`;
                     lowStockCountElement.textContent = 'N/A';
                     // Throw an error to stop further processing in this chain
                     throw new Error('Unauthorized access to low stock data.');
                 });
            }
            // --- END NEW ---

            if (!response.ok) {
                console.error(`HTTP error fetching low stock data: ${response.status}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // This block only runs if the fetch was successful (status 200-299)
            if (data.error) {
                console.error('Backend error fetching low stock items:', data.details || data.error);
                lowStockListElement.innerHTML = `<li class="list-group-item text-center text-danger">Error: ${data.message || data.error}</li>`;
                lowStockCountElement.textContent = 'Error';
                return;
            }

            // Update the count badge
            lowStockCountElement.textContent = data.count;

            // Populate the list
            lowStockListElement.innerHTML = ''; // Clear loading message

            if (data.low_stock_items && data.low_stock_items.length > 0) {
                data.low_stock_items.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center'); // Bootstrap list item styling
                    listItem.innerHTML = `
                        <span>
                            <strong>${item.item_name}</strong> (ID: ${item.item_id ? item.item_id.substring(0, 6) + '...' : 'N/A'})
                        </span>
                        <span class="badge bg-danger rounded-pill">
                            ${item.quantity} ${item.unit || ''}
                        </span>
                    `;
                    lowStockListElement.appendChild(listItem);
                });
            } else {
                // Display message if no items are low stock
                lowStockListElement.innerHTML = '<li class="list-group-item text-center text-muted">No items are currently low in stock.</li>';
            }
        })
        .catch(error => {
            // This catch block handles network errors and errors thrown in the .then() blocks (like the 403 error)
            console.error('Error fetching low stock items:', error);
             // Only display a generic error if it wasn't the 403 handled specifically above
             if (!error.message || !error.message.includes('Unauthorized access')) {
                 lowStockListElement.innerHTML = `<li class="list-group-item text-center text-danger">Could not load low stock items.</li>`;
                 lowStockCountElement.textContent = 'Error';
             }
        });
}


// Helper function to generate a set of distinct colors (Keep this)
function generateColors(numColors) {
    const colors = [];
    const baseColors = [
        '#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#20c997', '#fd7e14', '#e83e8c', '#6610f2', '#00bcd4',
        '#343a40', '#17a2b8', '#ffc107', '#f8f9fa', '#e9ecef', '#dee2e6', '#ced4da', '#adb5bd', '#6c757d', '#495057'
    ]; // Added more colors
    for (let i = 0; i < numColors; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

// Helper function to update chart title (Keep this)
function updateChartTitle(chart, newTitle) {
    if (chart && chart.options.plugins && chart.options.plugins.title) {
        chart.options.plugins.title.text = newTitle;
    } else if (chart && chart.options.title) { // Fallback for older Chart.js
        chart.options.title.text = newTitle;
    }
}

// --- NEW Helper Functions for Messages ---

// Displays a "No Data" message in the specified container
function displayNoDataMessage(container, message) {
    if (container) {
        container.innerHTML = `
            <div class="text-center text-muted p-4">
                <p class="lead">${message}</p>
            </div>
        `;
    }
}

// Displays an "Error" message in the specified container
function displayChartErrorMessage(container, message) {
    if (container) {
        container.innerHTML = `
             <div class="text-center text-danger p-4">
                 <p class="lead">${message}</p>
             </div>
         `;
    }
}

// MODIFY this function to call updateChartColors only if the chart object exists
function updateChartColors(isDarkMode) {
    const tickColor = isDarkMode ? '#f1f1f1' : '#495057';
    const gridColor = isDarkMode ? '#333' : '#e9ecef';
    const legendTitleColor = isDarkMode ? '#f1f1f1' : '#495057'; // Color for legend labels and title
    const borderColor = isDarkMode ? '#343a40' : '#fff'; // Border color for pie slices

    // Update Admissions Chart (Line Chart)
    if (window.admissionsChart) { // Check if chart object exists
        if (window.admissionsChart.options.scales) {
            if (window.admissionsChart.options.scales.y && window.admissionsChart.options.scales.y.ticks)
                window.admissionsChart.options.scales.y.ticks.color = tickColor;
            if (window.admissionsChart.options.scales.x && window.admissionsChart.options.scales.x.ticks)
                window.admissionsChart.options.scales.x.ticks.color = tickColor;
            if (window.admissionsChart.options.scales.y && window.admissionsChart.options.scales.y.grid)
                window.admissionsChart.options.scales.y.grid.color = gridColor;
            if (window.admissionsChart.options.scales.x && window.admissionsChart.options.scales.x.grid)
                window.admissionsChart.options.scales.x.grid.color = gridColor;
        }
        if (window.admissionsChart.options.plugins) {
            if (window.admissionsChart.options.plugins.legend && window.admissionsChart.options.plugins.legend.labels)
                window.admissionsChart.options.plugins.legend.labels.color = legendTitleColor;
            if (window.admissionsChart.options.plugins.title)
                window.admissionsChart.options.plugins.title.color = legendTitleColor;
        }
        window.admissionsChart.update(); // Update the chart
    }

    // Update Daily OPD Pie Chart
    if (window.dailyOpdChart) { // Check if chart object exists
        if (window.dailyOpdChart.options.plugins) {
            if (window.dailyOpdChart.options.plugins.legend && window.dailyOpdChart.options.plugins.legend.labels)
                window.dailyOpdChart.options.plugins.legend.labels.color = legendTitleColor;
            if (window.dailyOpdChart.options.plugins.title)
                window.dailyOpdChart.options.plugins.title.color = legendTitleColor;
        }
        if (window.dailyOpdChart.data.datasets && window.dailyOpdChart.data.datasets[0]) {
            window.dailyOpdChart.data.datasets[0].borderColor = borderColor;
        }
        window.dailyOpdChart.update(); // Update the chart
    }

    // Update Monthly OPD Pie Chart
    if (window.monthlyOpdChart) { // Check if chart object exists
        if (window.monthlyOpdChart.options.plugins) {
            if (window.monthlyOpdChart.options.plugins.legend && window.monthlyOpdChart.options.plugins.legend.labels)
                window.monthlyOpdChart.options.plugins.legend.labels.color = legendTitleColor;
            if (window.monthlyOpdChart.options.plugins.title)
                window.monthlyOpdChart.options.plugins.title.color = legendTitleColor;
        }
        if (window.monthlyOpdChart.data.datasets && window.monthlyOpdChart.data.datasets[0]) {
            window.monthlyOpdChart.data.datasets[0].borderColor = borderColor;
        }
        window.monthlyOpdChart.update(); // Update the chart
    }
}

// --- Chart Initialization ---

// Moved Chart.js initialization here from the HTML
// This code runs when script.js is loaded (and deferred means after DOM is ready)
const chartCanvas = document.getElementById('admissionsChart');

// Check if the canvas element exists before trying to initialize the chart
if (chartCanvas) {
    const ctx = chartCanvas.getContext('2d');
    // Initialize the global admissionsChart variable
    admissionsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [], // Start with empty labels; data will be fetched
            datasets: [{
                label: 'Admissions',
                data: [], // Start with empty data; data will be fetched
                borderColor: 'rgba(0, 123, 255, 0.8)',
                tension: 0.3,
                borderWidth: 1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        // Set initial tick color, will be updated by updateChartColors
                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                    },
                    grid: {
                        // Set initial grid color, will be updated by updateChartColors
                        color: document.body.classList.contains('dark-mode') ? '#333' : '#e9ecef'
                    }
                },
                x: {
                    ticks: {
                        // Set initial tick color, will be updated by updateChartColors
                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                    },
                    grid: {
                        // Set initial grid color, will be updated by updateChartColors
                        color: document.body.classList.contains('dark-mode') ? '#333' : '#e9ecef'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        // Set initial legend label color, will be updated by updateChartColors
                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                    }
                },
                title: {
                    display: true,
                    text: 'Loading Admissions Data...', // Initial title
                    // Set initial title color, will be updated by updateChartColors
                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                }
            }
        }
    });
} else {
    console.error("Chart canvas element not found!");
}


// --- Load Handler and Other Global JS ---

// Main Load Handler
window.addEventListener("load", function () {
    // Ensure the page loader is hidden
    const loaderWrapper = document.getElementById("loader-wrapper");
    if (loaderWrapper) {
        loaderWrapper.style.display = "none";
    }
    document.body.classList.add("loaded"); // Assuming 'loaded' class is used for styling transitions

    // Initialize AOS
    AOS.init({ duration: 1000, once: true });

    // Apply saved theme
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        // Manually update chart colors if dark mode is applied on load before toggle listener is active
        updateChartColors(true);
    }

    // Call functions to fetch dynamic data on load
    // These functions now use the global URL variables defined in index.html
    fetchSystemStats();
    fetchRecentActivities();
    fetchNowServing();
    fetchAdmissionsDataForChart(); // Call the function after chart is initialized
    fetchDailyOpdStats(); // New call
    fetchMonthlyOpdStats(); // New call
    fetchInventoryChartData();
    fetchLowStockItems();

    const lowStockThresholdElement = document.querySelector('.low-stock-alert-section .card-text');
    if (lowStockThresholdElement && typeof LOW_STOCK_THRESHOLD_JS !== 'undefined') {
        lowStockThresholdElement.textContent = `Items with quantity at or below ${LOW_STOCK_THRESHOLD_JS} are listed below.`;
    }

});

// Helper function to update chart colors based on dark mode status
// This function needs to be defined in a scope accessible by the dark mode toggle listener and the load handler
function updateChartColors(isDarkMode) {
    const tickColor = isDarkMode ? '#f1f1f1' : '#495057';
    const gridColor = isDarkMode ? '#333' : '#e9ecef';
    const legendTitleColor = isDarkMode ? '#f1f1f1' : '#495057'; // Color for legend labels and title

    if (window.admissionsChart) {
        // Update scale colors
        if (window.admissionsChart.options.scales) {
            if (window.admissionsChart.options.scales.y && window.admissionsChart.options.scales.y.ticks)
                window.admissionsChart.options.scales.y.ticks.color = tickColor;
            if (window.admissionsChart.options.scales.x && window.admissionsChart.options.scales.x.ticks)
                window.admissionsChart.options.scales.x.ticks.color = tickColor;
            if (window.admissionsChart.options.scales.y && window.admissionsChart.options.scales.y.grid)
                window.admissionsChart.options.scales.y.grid.color = gridColor;
            if (window.admissionsChart.options.scales.x && window.admissionsChart.options.scales.x.grid)
                window.admissionsChart.options.scales.x.grid.color = gridColor;
        }

        // Update plugin colors
        if (window.admissionsChart.options.plugins) {
            if (window.admissionsChart.options.plugins.legend && window.admissionsChart.options.plugins.legend.labels)
                window.admissionsChart.options.plugins.legend.labels.color = legendTitleColor;
            if (window.admissionsChart.options.plugins.title)
                window.admissionsChart.options.plugins.title.color = legendTitleColor;
        }

        // IMPORTANT: Call update() to apply the changes
        window.admissionsChart.update();
    }
}

// ... existing code in this script block (AOS, Loader, Scroll Top, Dark Mode) ...

document.addEventListener('DOMContentLoaded', function () {

    // --- Dark Mode Toggle Logic ---
    const toggle = document.getElementById('darkModeToggle');
    const body = document.body; // Get body element once

    if (toggle) {
        // Apply theme from localStorage on page load immediately
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            if (savedTheme === 'dark') {
                body.classList.add('dark-mode'); // Apply custom class
                body.setAttribute('data-bs-theme', 'dark'); // Apply Bootstrap attribute
                // Update icon immediately on load
                const moonIcon = toggle.querySelector('.moon-icon');
                const sunIcon = toggle.querySelector('.sun-icon');
                if (moonIcon) moonIcon.style.display = 'none';
                if (sunIcon) sunIcon.style.display = 'inline-block';
            } else {
                // Ensure light theme is explicitly set if saved as 'light'
                body.classList.remove('dark-mode');
                body.setAttribute('data-bs-theme', 'light');
                // Update icon immediately on load
                const moonIcon = toggle.querySelector('.moon-icon');
                const sunIcon = toggle.querySelector('.sun-icon');
                if (moonIcon) moonIcon.style.display = 'inline-block';
                if (sunIcon) sunIcon.style.display = 'none';
            }
            // Also update chart colors immediately on load based on saved theme
            // This assumes updateChartColors exists and handles null charts gracefully
            if (typeof updateChartColors === 'function') {
                updateChartColors(savedTheme === 'dark');
            } else {
                console.warn("updateChartColors function not found.");
            }


        } else {
            // If no saved theme, default to light and ensure attribute is set
            body.setAttribute('data-bs-theme', 'light');
            // Ensure custom class is removed if no theme saved (defaults to light)
            body.classList.remove('dark-mode');
        }

        

        // Add event listener for the toggle button click
        toggle.addEventListener('click', () => {
            // Toggle the custom dark-mode class (for your custom CSS)
            body.classList.toggle('dark-mode');

            // --- NEW: Toggle Bootstrap's data-bs-theme attribute ---
            const isDarkMode = body.classList.contains('dark-mode');
            if (isDarkMode) {
                body.setAttribute('data-bs-theme', 'dark');
            } else {
                body.setAttribute('data-bs-theme', 'light');
            }
            // --- END NEW ---

            // Save preference to localStorage
            const theme = isDarkMode ? 'dark' : 'light';
            localStorage.setItem('theme', theme);

            // Update chart colors (if charts are on this page and initialized)
            if (typeof updateChartColors === 'function') {
                updateChartColors(isDarkMode);
            } else {
                console.warn("updateChartColors function not found.");
            }


            // Update icon based on theme
            const moonIcon = toggle.querySelector('.moon-icon');
            const sunIcon = toggle.querySelector('.sun-icon');
            if (isDarkMode) {
                if (moonIcon) moonIcon.style.display = 'none';
                if (sunIcon) sunIcon.style.display = 'inline-block';
            } else {
                if (moonIcon) moonIcon.style.display = 'inline-block';
                if (sunIcon) sunIcon.style.display = 'none';
            }
        });

    } else {
        console.warn("Dark mode toggle button not found!");
    }

    // Add the scroll to top button setup inside load handler if you want to ensure element exists
    const scrollBtn = document.getElementById('scrollTopBtn');
    if (scrollBtn) {
        window.onscroll = () => {
            scrollBtn.style.display = window.scrollY > 200 ? 'block' : 'none';
        };
        scrollBtn.onclick = () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };
    } else {
        console.warn("Scroll top button not found!");
    }

    // --- Chatbot Toggle Logic ---
    const chatbotToggleBtn = document.getElementById('chatbot-toggle-btn');
    const chatWindow = document.getElementById('chat-window');
    const chatCloseBtn = document.getElementById('chat-close-btn');
    const chatBody = document.getElementById('chat-body'); // Get chat body here too

    // Check if the toggle elements exist before adding listeners
    if (chatbotToggleBtn && chatWindow && chatCloseBtn && chatBody) {
        chatbotToggleBtn.addEventListener('click', function () {
            const isHidden = chatWindow.style.display === 'none' || chatWindow.style.display === ''; // Check for initial state too
            chatWindow.style.display = isHidden ? 'flex' : 'none'; // Use 'flex'
            chatbotToggleBtn.style.display = isHidden ? 'none' : 'flex'; // Toggle button visibility

            if (isHidden) { // If opening
                // Scroll to the bottom of the chat window
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        });

        chatCloseBtn.addEventListener('click', function () {
            chatWindow.style.display = 'none'; // Hide window
            chatbotToggleBtn.style.display = 'flex'; // Show toggle button
        });
    } else {
        console.error("Chatbot toggle UI elements not found!");
    }
    // --- End Chatbot Toggle Logic ---


    // --- Chatbot Message Sending and Display Logic ---
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    // chatBody is already defined above

    // Check if chat interaction elements exist
    if (chatBody && chatInput && chatSendBtn) {

        // Function to display a message
        function displayMessage(message, sender) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('chat-message', sender + '-message');
            messageElement.textContent = message; // Use textContent for security
            chatBody.appendChild(messageElement);
            chatBody.scrollTop = chatBody.scrollHeight; // Scroll down
        }

        // Function to send a message to the backend
        async function sendMessage(message) {
            displayMessage(message, 'user'); // Display user message
            chatInput.value = ''; // Clear input

            const chatbotEndpoint = '/chatbot/send_message'; // Your backend endpoint

            try {
                const response = await fetch(chatbotEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // Add CSRF token header if needed for Flask-WTF or similar
                        // 'X-CSRFToken': '{{ csrf_token() }}' // Example if using Flask templates directly
                    },
                    body: JSON.stringify({ message: message })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                const botResponse = data.response; // Adjust if your backend sends a different structure

                if (botResponse) {
                    displayMessage(botResponse, 'bot'); // Display bot response
                } else {
                    displayMessage('Received empty response from bot.', 'bot');
                }

            } catch (error) {
                console.error('Error sending/receiving chatbot message:', error);
                displayMessage('Sorry, something went wrong. Please try again later.', 'bot'); // User-friendly error
            }
        }

        // Event listener for send button
        chatSendBtn.addEventListener('click', function () {
            const message = chatInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        });

        // Event listener for Enter key
        chatInput.addEventListener('keypress', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent default newline/submit
                const message = chatInput.value.trim();
                if (message) {
                    sendMessage(message);
                }
            }
        });

        // Optional: Display initial welcome message via JS if needed,
        // although it's already in your HTML. Remove from HTML if adding here.
        // displayMessage('Welcome! How can I help you today?', 'bot');

    } else {
        console.error("Chatbot message UI elements not found!");
    }
    // --- End Chatbot Message Sending and Display Logic ---


    // --- Scroll-to-Top Button Logic ---
    const scrollTopBtn = document.getElementById('scrollTopBtn');

    if (scrollTopBtn) {
        // Show button when scrolling down
        window.addEventListener('scroll', () => {
            if (window.scrollY > 200) { // Show after scrolling down 200px
                scrollTopBtn.style.display = 'block'; // Or 'inline-block' or 'flex' depending on styling
            } else {
                scrollTopBtn.style.display = 'none';
            }
        });

        // Scroll to top when clicked
        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
    // --- End Scroll-to-Top Button Logic ---

});

// End of DOMContentLoaded listener

// Optional: Periodical refreshes (remove if not desired)
setInterval(fetchSystemStats, 60000); // Refresh stats every 60 seconds
setInterval(fetchRecentActivities, 30000); // Refresh recent activities every 30 seconds
setInterval(fetchNowServing, 5000); // Refresh now serving every 5 seconds
setInterval(fetchDailyOpdStats, 60000); // Refresh daily OPD stats every 60 seconds
setInterval(fetchMonthlyOpdStats, 300000);// Refresh monthly OPD stats every 5minutes (less frequent)
setInterval(fetchInventoryChartData, 60000); 
setInterval(fetchLowStockItems, 60000);