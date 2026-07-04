async function loadTemperatureData() {
    showLoading(true);
    hideError();
    
    const period = document.getElementById('temp-period').value;
    document.getElementById('analysis-period').textContent = period;
    
    try {
        const [avgData, rangeData, rateData, deltaData] = await Promise.all([
            apiRequest(`/temperature/average?period=${period}`),
            apiRequest(`/temperature/range?period=${period}`),
            apiRequest(`/temperature/rate-of-change?hours=${period}`),
            apiRequest(`/temperature/delta?hours=${period}`)
        ]);

        document.getElementById('avg-temp').textContent = fmt(avgData.average_temperature);
        document.getElementById('temp-min').textContent = fmt(rangeData.temperature_range?.min);
        document.getElementById('temp-max').textContent = fmt(rangeData.temperature_range?.max);
        document.getElementById('temp-range-val').textContent = fmt(rangeData.temperature_range?.range);
        document.getElementById('rate-change').textContent = fmt(rateData.avg_rate_of_change);
        document.getElementById('delta').textContent = fmt(deltaData.delta_per_hour);
        document.getElementById('last-updated').textContent = new Date().toLocaleString();

        showLoading(false);
    } catch (error) {
        showError('Failed to load temperature data. Please check if the API is running.');
    }
}

window.onload = loadTemperatureData;