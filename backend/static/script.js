// static/script.js 

function fetchSystemStats() {
    
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


function fetchRecentActivities() {

    fetch(recentActivitiesUrl)
        .then(response => { if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); } return response.json(); })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching recent activities:', data.details);
                document.getElementById('recentPatientsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading patients</li>';
                document.getElementById('recentAdmissionsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading admissions</li>';
                return;
            }

            const patientsList = document.getElementById('recentPatientsList');
            patientsList.innerHTML = '';
            if (data.patients && data.patients.length > 0) {
                data.patients.forEach(patient => {
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item');
                    listItem.innerHTML = `<span class="activity-details">${patient.name}</span><span class="activity-time">ID: ${patient.patient_id ? patient.patient_id.substring(0, 6) + '...' : 'N/A'}</span>`; patientsList.appendChild(listItem);
                });
            }
            else {
                patientsList.innerHTML = '<li class="list-group-item text-center text-muted">No recent patients.</li>';
            }


            const admissionsList = document.getElementById('recentAdmissionsList');
            admissionsList.innerHTML = '';
            if (data.admissions && data.admissions.length > 0) {
                data.admissions.forEach(admission => {
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item');
                    const formattedAdmissionTime = admission.admission_time;
                    listItem.innerHTML = `<span class="activity-details">${admission.patient_name} admitted</span><span class="activity-time">${formattedAdmissionTime}</span>`; admissionsList.appendChild(listItem);
                });
            } else {
                admissionsList.innerHTML = '<li class="list-group-item text-center text-muted">No recent admissions.</li>';
            }
        })
        .catch(error => {
            console.error('Error fetching recent activities:', error);
            document.getElementById('recentPatientsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading patients</li>';
            document.getElementById('recentAdmissionsList').innerHTML = '<li class="list-group-item text-center text-danger">Error loading admissions</li>';
        });
}


function fetchNowServing() {
    fetch('/get_now_serving')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Fetching Now Serving data. Clearing previous cards.");
            const nowServingList = document.getElementById('nowServingList');
            nowServingList.innerHTML = '';

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
                    cardCol.classList.add('col-md-4', 'text-center');

                    const card = document.createElement('div');
                    card.classList.add('card', 'p-3', 'shadow-sm', 'h-100');

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


function fetchAdmissionsDataForChart() {

    fetch(admissionsDataUrl)
        .then(response => { if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); } return response.json(); })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching admissions data:', data.details);

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
                return;
            }

            if (window.admissionsChart && data.labels && data.data) {

                window.admissionsChart.data.labels = data.labels;
                window.admissionsChart.data.datasets[0].data = data.data;

                const newTitle = 'Patient Admissions - Last 5 Days';
                if (window.admissionsChart.options.plugins && window.admissionsChart.options.plugins.title) {
                    window.admissionsChart.options.plugins.title.text = newTitle;
                } else if (window.admissionsChart.options.title) {
                    window.admissionsChart.options.title.text = newTitle;
                }

                window.admissionsChart.update();
            } else {
                console.warn("Chart object not found or data format unexpected.");
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

function fetchDailyOpdStats() {
    const dailyOpdCanvas = document.getElementById('dailyOpdChart');
    const chartContainer = dailyOpdCanvas ? dailyOpdCanvas.parentElement : null;

    fetch(dailyOpdStatsUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching daily OPD data:', data.details);
                displayChartErrorMessage(chartContainer, 'Error loading data');
                return;
            }

            if (!data || !data.labels || data.labels.length === 0 || !data.data || data.data.length === 0) {
                console.log("No daily OPD data available.");
                displayNoDataMessage(chartContainer, 'No patient has booked OPD today.');
                if (window.dailyOpdChart) {
                    window.dailyOpdChart.destroy();
                    window.dailyOpdChart = null;
                }
                return;
            }

            if (dailyOpdCanvas && chartContainer) {

                chartContainer.innerHTML = '';
                chartContainer.appendChild(dailyOpdCanvas);

                if (!window.dailyOpdChart) {
                    const ctx = dailyOpdCanvas.getContext('2d');
                    window.dailyOpdChart = new Chart(ctx, {
                        type: 'pie',
                        data: {
                            labels: [],
                            datasets: [{
                                data: [],
                                backgroundColor: [],
                                borderColor: document.body.classList.contains('dark-mode') ? '#343a40' : '#fff',
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
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                    }
                                },
                                title: {
                                    display: true,
                                    text: "Today's OPD Bookings by Department",
                                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                }
                            }
                        }
                    });
                }

                window.dailyOpdChart.data.labels = data.labels;
                window.dailyOpdChart.data.datasets[0].data = data.data;

                window.dailyOpdChart.data.datasets[0].backgroundColor = generateColors(data.labels.length);

                updateChartTitle(window.dailyOpdChart, "Today's OPD Bookings by Department");
                window.dailyOpdChart.update();

            } else {
                console.error("Daily OPD chart canvas element or container not found during data processing.");
                displayChartErrorMessage(null, 'Chart area not found');
            }
        })
        .catch(error => {
            console.error('Error fetching daily OPD stats:', error);
            displayChartErrorMessage(chartContainer, 'Error loading data');
            if (window.dailyOpdChart) {
                window.dailyOpdChart.destroy();
                window.dailyOpdChart = null;
            }
        });
}


function fetchMonthlyOpdStats() {
    const monthlyOpdCanvas = document.getElementById('monthlyOpdChart');
    const chartContainer = monthlyOpdCanvas ? monthlyOpdCanvas.parentElement : null;

    fetch(monthlyOpdStatsUrl)
        .then(response => {
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching monthly OPD data:', data.details);
                displayChartErrorMessage(chartContainer, 'Error loading data');
                return;
            }

            if (!data || !data.labels || data.labels.length === 0 || !data.data || data.data.length === 0) {
                console.log("No monthly OPD data available.");
                displayNoDataMessage(chartContainer, 'No patient has booked OPD in the last month.');
                if (window.monthlyOpdChart) {
                    window.monthlyOpdChart.destroy();
                    window.monthlyOpdChart = null;
                }
                return;
            }


            if (monthlyOpdCanvas && chartContainer) {

                chartContainer.innerHTML = '';
                chartContainer.appendChild(monthlyOpdCanvas);

                if (!window.monthlyOpdChart) {

                    const ctx = monthlyOpdCanvas.getContext('2d');
                    window.monthlyOpdChart = new Chart(ctx, {
                        type: 'pie',
                        data: {
                            labels: [],
                            datasets: [{
                                data: [],
                                backgroundColor: [],
                                borderColor: document.body.classList.contains('dark-mode') ? '#343a40' : '#fff',
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
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                    }
                                },
                                title: {
                                    display: true,
                                    text: "Last Month's OPD Bookings by Department",
                                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                }
                            }
                        }
                    });
                }

                window.monthlyOpdChart.data.labels = data.labels;
                window.monthlyOpdChart.data.datasets[0].data = data.data;

                window.monthlyOpdChart.data.datasets[0].backgroundColor = generateColors(data.labels.length);

                updateChartTitle(window.monthlyOpdChart, "Last Month's OPD Bookings by Department");
                window.monthlyOpdChart.update();

            } else {
                console.error("Monthly OPD chart canvas element or container not found during data processing.");
                displayChartErrorMessage(null, 'Chart area not found');
            }
        })
        .catch(error => {
            console.error('Error fetching monthly OPD stats:', error);
            displayChartErrorMessage(chartContainer, 'Error loading data');

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
        return;
    }

    fetch(inventoryChartDataUrl)
        .then(response => {
            if (!response.ok) {

                console.error(`HTTP error fetching inventory chart data: ${response.status}`);
                displayChartErrorMessage(chartContainer, 'Error loading chart data.');
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {

            if (data.error) {
                console.error('Backend error fetching inventory data:', data.details || data.error);
                displayChartErrorMessage(chartContainer, `Backend error: ${data.message || data.error}`);

                if (window.inventoryStockChart) {
                    window.inventoryStockChart.data.labels = ['Error'];
                    window.inventoryStockChart.data.datasets[0].data = [0];
                    updateChartTitle(window.inventoryStockChart, 'Error loading data');
                    window.inventoryStockChart.update();
                }
                return;
            }

            if (!data || !data.labels || data.labels.length === 0 || !data.data || data.data.length === 0) {
                console.log("No inventory data available for charting.");
                displayNoDataMessage(chartContainer, 'No inventory items available for charting.');

                if (window.inventoryStockChart) {
                    window.inventoryStockChart.destroy();
                    window.inventoryStockChart = null;
                }
                return;
            }

            if (inventoryCanvas && chartContainer) {

                chartContainer.innerHTML = '';
                chartContainer.appendChild(inventoryCanvas);

                if (!window.inventoryStockChart) {

                    const ctx = inventoryCanvas.getContext('2d');
                    window.inventoryStockChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Quantity in Stock',
                                data: [],
                                backgroundColor: [
                                    'rgba(75, 192, 192, 0.6)',
                                    'rgba(153, 102, 255, 0.6)',
                                    'rgba(255, 159, 64, 0.6)',
                                    'rgba(255, 99, 132, 0.6)',
                                    'rgba(54, 162, 235, 0.6)',
                                    'rgba(201, 203, 207, 0.6)'

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
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: false
                                },
                                title: {
                                    display: true,
                                    text: 'Inventory Stock Levels',
                                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function (context) {
                                            let label = context.dataset.label || '';
                                            if (label) {
                                                label += ': ';
                                            }

                                            label += context.raw;
                                            return label;
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Quantity',
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                    },
                                    ticks: {
                                        stepSize: 1,
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                    },
                                    grid: {
                                        color: document.body.classList.contains('dark-mode') ? 'rgba(241, 241, 241, 0.1)' : 'rgba(0, 0, 0, 0.1)'
                                    }
                                },
                                x: {
                                    title: {
                                        display: true,
                                        text: 'Item Name',
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                    },
                                    ticks: {
                                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                                    },
                                    grid: {
                                        color: document.body.classList.contains('dark-mode') ? 'rgba(241, 241, 241, 0.1)' : 'rgba(0, 0, 0, 0.1)'
                                    }
                                }
                            }
                        }
                    });
                }

                window.inventoryStockChart.data.labels = data.labels;
                window.inventoryStockChart.data.datasets[0].data = data.data;


                window.inventoryStockChart.data.datasets[0].backgroundColor = generateColors(data.labels.length);


                updateChartTitle(window.inventoryStockChart, 'Inventory Stock Levels');
                window.inventoryStockChart.update();


            } else {
                console.error("Inventory chart canvas element or container not found during data processing.");
                displayChartErrorMessage(null, 'Chart area not found');
            }
        })
        .catch(error => {
            console.error('Error fetching inventory data:', error);
            displayChartErrorMessage(chartContainer, 'Could not load inventory chart.');

            if (window.inventoryStockChart) {
                window.inventoryStockChart.data.labels = ['Error'];
                window.inventoryStockChart.data.datasets[0].data = [0];
                updateChartTitle(window.inventoryStockChart, 'Error loading data');
                window.inventoryStockChart.update();
            }
        });
}

function fetchLowStockItems() {
    const lowStockListElement = document.getElementById('lowStockItemsList');
    const lowStockCountElement = document.getElementById('lowStockCount');

    if (!lowStockListElement || !lowStockCountElement) {
        return;
    }

    if (typeof currentUserType === 'undefined' || currentUserType !== 'hospital') {
        console.log("User is not authorized to view low stock items (Frontend check).");
        lowStockListElement.innerHTML = '<li class="list-group-item text-center text-info">You do not have permission to view low stock alerts.</li>';
        lowStockCountElement.textContent = 'N/A';
        return;
    }

    if (typeof lowStockItemsUrl === 'undefined') {
        console.error("lowStockItemsUrl is not defined!");
        lowStockListElement.innerHTML = '<li class="list-group-item text-center text-danger">Configuration Error: Low stock URL missing.</li>';
        lowStockCountElement.textContent = 'Error';
        return;
    }

    lowStockListElement.innerHTML = '<li class="list-group-item text-center text-muted">Loading low stock items...</li>';
    lowStockCountElement.textContent = '...';


    fetch(lowStockItemsUrl)
        .then(response => {

            if (response.status === 403) {
                console.warn("Backend returned 403 Forbidden for low stock data.");
                return response.json().then(data => {
                    lowStockListElement.innerHTML = `<li class="list-group-item text-center text-info">${data.message || 'You do not have permission to view low stock items.'}</li>`;
                    lowStockCountElement.textContent = 'N/A';
                    throw new Error('Unauthorized access to low stock data.');
                });
            }

            if (!response.ok) {
                console.error(`HTTP error fetching low stock data: ${response.status}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error('Backend error fetching low stock items:', data.details || data.error);
                lowStockListElement.innerHTML = `<li class="list-group-item text-center text-danger">Error: ${data.message || data.error}</li>`;
                lowStockCountElement.textContent = 'Error';
                return;
            }

            lowStockCountElement.textContent = data.count;
            lowStockListElement.innerHTML = '';

            if (data.low_stock_items && data.low_stock_items.length > 0) {
                data.low_stock_items.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
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
                lowStockListElement.innerHTML = '<li class="list-group-item text-center text-muted">No items are currently low in stock.</li>';
            }
        })
        .catch(error => {
            console.error('Error fetching low stock items:', error);
            if (!error.message || !error.message.includes('Unauthorized access')) {
                lowStockListElement.innerHTML = `<li class="list-group-item text-center text-danger">Could not load low stock items.</li>`;
                lowStockCountElement.textContent = 'Error';
            }
        });
}

function generateColors(numColors) {
    const colors = [];
    const baseColors = [
        '#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#20c997', '#fd7e14', '#e83e8c', '#6610f2', '#00bcd4',
        '#343a40', '#17a2b8', '#ffc107', '#f8f9fa', '#e9ecef', '#dee2e6', '#ced4da', '#adb5bd', '#6c757d', '#495057'
    ];
    for (let i = 0; i < numColors; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

function updateChartTitle(chart, newTitle) {
    if (chart && chart.options.plugins && chart.options.plugins.title) {
        chart.options.plugins.title.text = newTitle;
    } else if (chart && chart.options.title) {
        chart.options.title.text = newTitle;
    }
}

function displayNoDataMessage(container, message) {
    if (container) {
        container.innerHTML = `
            <div class="text-center text-muted p-4">
                <p class="lead">${message}</p>
            </div>
        `;
    }
}

function displayChartErrorMessage(container, message) {
    if (container) {
        container.innerHTML = `
             <div class="text-center text-danger p-4">
                 <p class="lead">${message}</p>
             </div>
         `;
    }
}

function updateChartColors(isDarkMode) {
    const tickColor = isDarkMode ? '#f1f1f1' : '#495057';
    const gridColor = isDarkMode ? '#333' : '#e9ecef';
    const legendTitleColor = isDarkMode ? '#f1f1f1' : '#495057';
    const borderColor = isDarkMode ? '#343a40' : '#fff';

    if (window.admissionsChart) {
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
        window.admissionsChart.update();
    }

    if (window.dailyOpdChart) {
        if (window.dailyOpdChart.options.plugins) {
            if (window.dailyOpdChart.options.plugins.legend && window.dailyOpdChart.options.plugins.legend.labels)
                window.dailyOpdChart.options.plugins.legend.labels.color = legendTitleColor;
            if (window.dailyOpdChart.options.plugins.title)
                window.dailyOpdChart.options.plugins.title.color = legendTitleColor;
        }
        if (window.dailyOpdChart.data.datasets && window.dailyOpdChart.data.datasets[0]) {
            window.dailyOpdChart.data.datasets[0].borderColor = borderColor;
        }
        window.dailyOpdChart.update();
    }

    if (window.monthlyOpdChart) {
        if (window.monthlyOpdChart.options.plugins) {
            if (window.monthlyOpdChart.options.plugins.legend && window.monthlyOpdChart.options.plugins.legend.labels)
                window.monthlyOpdChart.options.plugins.legend.labels.color = legendTitleColor;
            if (window.monthlyOpdChart.options.plugins.title)
                window.monthlyOpdChart.options.plugins.title.color = legendTitleColor;
        }
        if (window.monthlyOpdChart.data.datasets && window.monthlyOpdChart.data.datasets[0]) {
            window.monthlyOpdChart.data.datasets[0].borderColor = borderColor;
        }
        window.monthlyOpdChart.update();
    }
}

const chartCanvas = document.getElementById('admissionsChart');

if (chartCanvas) {
    const ctx = chartCanvas.getContext('2d');
    admissionsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Admissions',
                data: [],
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
                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                    },
                    grid: {
                        color: document.body.classList.contains('dark-mode') ? '#333' : '#e9ecef'
                    }
                },
                x: {
                    ticks: {
                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                    },
                    grid: {
                        color: document.body.classList.contains('dark-mode') ? '#333' : '#e9ecef'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                    }
                },
                title: {
                    display: true,
                    text: 'Loading Admissions Data...',
                    color: document.body.classList.contains('dark-mode') ? '#f1f1f1' : '#495057'
                }
            }
        }
    });
} else {
    console.error("Chart canvas element not found!");
}


window.addEventListener("load", function () {
    const loaderWrapper = document.getElementById("loader-wrapper");
    if (loaderWrapper) {
        loaderWrapper.style.display = "none";
    }
    document.body.classList.add("loaded");

    AOS.init({ duration: 1000, once: true });

    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        updateChartColors(true);
    }

    fetchSystemStats();
    fetchRecentActivities();
    fetchNowServing();
    fetchAdmissionsDataForChart();
    fetchDailyOpdStats();
    fetchMonthlyOpdStats();
    fetchInventoryChartData();
    fetchLowStockItems();

    const lowStockThresholdElement = document.querySelector('.low-stock-alert-section .card-text');
    if (lowStockThresholdElement && typeof LOW_STOCK_THRESHOLD_JS !== 'undefined') {
        lowStockThresholdElement.textContent = `Items with quantity at or below ${LOW_STOCK_THRESHOLD_JS} are listed below.`;
    }

});


function updateChartColors(isDarkMode) {
    const tickColor = isDarkMode ? '#f1f1f1' : '#495057';
    const gridColor = isDarkMode ? '#333' : '#e9ecef';
    const legendTitleColor = isDarkMode ? '#f1f1f1' : '#495057';

    if (window.admissionsChart) {

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
        window.admissionsChart.update();
    }
}


document.addEventListener('DOMContentLoaded', function () {
    // --- Dark Mode Toggle Logic ---
    const toggle = document.getElementById('darkModeToggle');
    const body = document.body;

    if (toggle) {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            if (savedTheme === 'dark') {
                body.classList.add('dark-mode');
                body.setAttribute('data-bs-theme', 'dark');
                const moonIcon = toggle.querySelector('.moon-icon');
                const sunIcon = toggle.querySelector('.sun-icon');
                if (moonIcon) moonIcon.style.display = 'none';
                if (sunIcon) sunIcon.style.display = 'inline-block';
            } else {
                body.classList.remove('dark-mode');
                body.setAttribute('data-bs-theme', 'light');
                const moonIcon = toggle.querySelector('.moon-icon');
                const sunIcon = toggle.querySelector('.sun-icon');
                if (moonIcon) moonIcon.style.display = 'inline-block';
                if (sunIcon) sunIcon.style.display = 'none';
            }

            if (typeof updateChartColors === 'function') {
                updateChartColors(savedTheme === 'dark');
            } else {
                console.warn("updateChartColors function not found.");
            }


        } else {
            body.setAttribute('data-bs-theme', 'light');
            body.classList.remove('dark-mode');
        }


        toggle.addEventListener('click', () => {

            body.classList.toggle('dark-mode');

            const isDarkMode = body.classList.contains('dark-mode');
            if (isDarkMode) {
                body.setAttribute('data-bs-theme', 'dark');
            } else {
                body.setAttribute('data-bs-theme', 'light');
            }

            const theme = isDarkMode ? 'dark' : 'light';
            localStorage.setItem('theme', theme);

            if (typeof updateChartColors === 'function') {
                updateChartColors(isDarkMode);
            } else {
                console.warn("updateChartColors function not found.");
            }

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
    const chatBody = document.getElementById('chat-body');


    if (chatbotToggleBtn && chatWindow && chatCloseBtn && chatBody) {
        chatbotToggleBtn.addEventListener('click', function () {
            const isHidden = chatWindow.style.display === 'none' || chatWindow.style.display === '';
            chatWindow.style.display = isHidden ? 'flex' : 'none';
            chatbotToggleBtn.style.display = isHidden ? 'none' : 'flex';
            if (isHidden) {
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        });

        chatCloseBtn.addEventListener('click', function () {
            chatWindow.style.display = 'none';
            chatbotToggleBtn.style.display = 'flex';
        });
    } else {
        console.error("Chatbot toggle UI elements not found!");
    }


    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');


    if (chatBody && chatInput && chatSendBtn) {

        function displayMessage(message, sender) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('chat-message', sender + '-message');
            messageElement.textContent = message;
            chatBody.appendChild(messageElement);
            chatBody.scrollTop = chatBody.scrollHeight;
        }

        async function sendMessage(message) {
            displayMessage(message, 'user');
            chatInput.value = '';

            const chatbotEndpoint = '/chatbot/send_message';

            try {
                const response = await fetch(chatbotEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',

                    },
                    body: JSON.stringify({ message: message })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                const botResponse = data.response;

                if (botResponse) {
                    displayMessage(botResponse, 'bot');
                } else {
                    displayMessage('Received empty response from bot.', 'bot');
                }

            } catch (error) {
                console.error('Error sending/receiving chatbot message:', error);
                displayMessage('Sorry, something went wrong. Please try again later.', 'bot');
            }
        }

        chatSendBtn.addEventListener('click', function () {
            const message = chatInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        });

        chatInput.addEventListener('keypress', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const message = chatInput.value.trim();
                if (message) {
                    sendMessage(message);
                }
            }
        });

    } else {
        console.error("Chatbot message UI elements not found!");
    }

    const scrollTopBtn = document.getElementById('scrollTopBtn');

    if (scrollTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 200) {
                scrollTopBtn.style.display = 'block';
            } else {
                scrollTopBtn.style.display = 'none';
            }
        });

        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

});


setInterval(fetchSystemStats, 60000);
setInterval(fetchRecentActivities, 30000);
setInterval(fetchNowServing, 5000);
setInterval(fetchDailyOpdStats, 60000);
setInterval(fetchMonthlyOpdStats, 300000);
setInterval(fetchInventoryChartData, 60000);
setInterval(fetchLowStockItems, 60000);