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

    // Add the dark mode toggle setup inside load handler if you want to ensure elements exist
    const toggle = document.getElementById('darkModeToggle');
    if (toggle) {
        toggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const theme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
            localStorage.setItem('theme', theme);

            // Update chart colors when dark mode is toggled
            const isDarkMode = document.body.classList.contains('dark-mode');
            updateChartColors(isDarkMode); // Use the helper function
        });
        // Set initial icon based on theme
        const moonIcon = toggle.querySelector('.moon-icon');
        const sunIcon = toggle.querySelector('.sun-icon');
        if (document.body.classList.contains('dark-mode')) {
            if (moonIcon) moonIcon.style.display = 'none';
            if (sunIcon) sunIcon.style.display = 'inline-block';
        } else {
            if (moonIcon) moonIcon.style.display = 'inline-block';
            if (sunIcon) sunIcon.style.display = 'none';
        }
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
