function cityListCard(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : t('no_data_yet');
    const wind = latest.windspeed !== undefined
        ? `${latest.windspeed} km/h ${getWindDirection(latest.winddirection)}` : '--';
    const updated = latest.timestamp ? formatDateTime(latest.timestamp) : '--';

    return `
        <a class="card city-card" href="city.html?city=${encodeURIComponent(city.id)}">
            <h3>${city.name}</h3>
            <p class="city-country">${city.country}</p>
            <div class="metric-value">${temp}</div>
            <p class="metric-unit">${t('latest_temperature')}</p>
            <p>${t('wind_label')} <span>${wind}</span></p>
            <p>${t('records_label')} <span>${city.records}</span></p>
            <p>${t('last_update')} <span>${updated}</span></p>
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
            grid.innerHTML = `<div class="card"><p>${t('no_cities')}</p></div>`;
            return;
        }
        grid.innerHTML = result.cities.map(cityListCard).join('');
    } catch (error) {
        showError(t('error_cities'));
    }
}

window.onload = loadCities;
