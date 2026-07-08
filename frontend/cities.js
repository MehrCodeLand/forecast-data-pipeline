function cityListCard(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : 'No data yet';
    const wind = latest.windspeed !== undefined
        ? `${latest.windspeed} km/h ${getWindDirection(latest.winddirection)}` : '--';
    const updated = latest.timestamp ? formatDateTime(latest.timestamp) : '--';

    return `
        <a class="card city-card" href="city.html?city=${encodeURIComponent(city.id)}">
            <h3>${city.name}</h3>
            <p class="city-country">${city.country}</p>
            <div class="metric-value">${temp}</div>
            <p class="metric-unit">latest temperature</p>
            <p>Wind: <span>${wind}</span></p>
            <p>Records collected: <span>${city.records}</span></p>
            <p>Last update: <span>${updated}</span></p>
        </a>
    `;
}

async function loadCities() {
    showLoading(true);
    hideError();
    loadSiteContent();

    const grid = document.getElementById('cities-grid');
    try {
        const result = await apiRequest('/cities');
        showLoading(false);
        if (!result.cities.length) {
            grid.innerHTML = '<div class="card"><p>No cities are being tracked yet.</p></div>';
            return;
        }
        grid.innerHTML = result.cities.map(cityListCard).join('');
    } catch (error) {
        showError('Could not load cities. Please check if the API is running.');
    }
}

window.onload = loadCities;
