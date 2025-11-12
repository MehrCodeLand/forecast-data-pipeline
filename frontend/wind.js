async function loadWindData() {
    showLoading(true);
    hideError();
    
    const period = document.getElementById('wind-period').value;
    
    try {
        const [avgSpeed, peakSpeed, direction, variability] = await Promise.all([
            apiRequest(`/wind/average-speed?period=${period}`),
            apiRequest(`/wind/peak-speed?period=${period}`),
            apiRequest(`/wind/dominant-direction?period=${period}`),
            apiRequest(`/wind/direction-variability?period=${period}`)
        ]);

        document.getElementById('avg-wind').textContent = avgSpeed.average_windspeed;
        document.getElementById('peak-wind').textContent = peakSpeed.peak_windspeed;
        document.getElementById('wind-direction').textContent = direction.dominant_direction;
        document.getElementById('direction-text').textContent = getWindDirection(direction.dominant_direction);
        document.getElementById('wind-variability').textContent = variability.direction_variability;

        showLoading(false);
        await loadCalmPeriods();
    } catch (error) {
        showError('Failed to load wind data. Please check if the API is running.');
    }
}

async function loadCalmPeriods() {
    const period = document.getElementById('wind-period').value;
    const threshold = document.getElementById('calm-threshold').value;
    
    try {
        const data = await apiRequest(`/wind/calm-periods?period=${period}&threshold=${threshold}`);
        
        document.getElementById('calm-count').textContent = data.result.calm_periods;
        document.getElementById('total-periods').textContent = data.result.total_periods;
        document.getElementById('calm-percentage').textContent = data.result.calm_percentage;
    } catch (error) {
        console.error('Failed to load calm periods:', error);
    }
}

window.onload = loadWindData;