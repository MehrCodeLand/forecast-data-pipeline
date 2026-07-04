async function loadSummary() {
    showLoading(true);
    hideError();
    
    const period = document.getElementById('period').value;
    
    try {
        const data = await apiRequest(`/summary?period=${period}`);
        displaySummary(data.summary);
        showLoading(false);
    } catch (error) {
        showError('Failed to load weather summary. Please check if the API is running.');
    }
}

function displaySummary(summary) {
    const grid = document.getElementById('summary-grid');
    
    grid.innerHTML = `
        <div class="card">
            <h3>Temperature</h3>
            <div class="metric-value">${fmt(summary.avg_temperature)}</div>
            <p class="metric-unit">°C average</p>
            <div class="metric-detail">
                <p>Min: <span>${fmt(summary.temp_range?.min)}°C</span></p>
                <p>Max: <span>${fmt(summary.temp_range?.max)}°C</span></p>
            </div>
        </div>

        <div class="card">
            <h3>Wind Speed</h3>
            <div class="metric-value">${fmt(summary.avg_windspeed)}</div>
            <p class="metric-unit">km/h average</p>
            <div class="metric-detail">
                <p>Peak: <span>${fmt(summary.peak_windspeed)} km/h</span></p>
            </div>
        </div>

        <div class="card">
            <h3>Wind Direction</h3>
            <div class="metric-value">${fmt(summary.dominant_wind_direction)}</div>
            <p class="metric-unit">degrees</p>
            <p class="direction-text">${getWindDirection(summary.dominant_wind_direction)}</p>
        </div>

        <div class="card">
            <h3>Calm Periods</h3>
            <div class="metric-value">${fmt(summary.calm_periods?.calm_percentage)}</div>
            <p class="metric-unit">% calm time</p>
            <div class="metric-detail">
                <p>Calm: <span>${fmt(summary.calm_periods?.calm_periods)}</span></p>
                <p>Total: <span>${fmt(summary.calm_periods?.total_periods)}</span></p>
            </div>
        </div>

        <div class="card">
            <h3>Wind Variability</h3>
            <div class="metric-value">${fmt(summary.wind_variability)}</div>
            <p class="metric-unit">std deviation</p>
        </div>

        <div class="card">
            <h3>Data Points</h3>
            <div class="metric-value">${fmt(summary.data_points)}</div>
            <p class="metric-unit">analyzed</p>
        </div>
    `;
}

window.onload = loadSummary;