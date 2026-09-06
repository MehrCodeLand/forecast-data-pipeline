let ALL_CITIES = [];
let SELECTED_COUNTRY = 'all';

function cityListCard(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : t('no_data_yet');
    const wind = latest.windspeed !== undefined
        ? `${latest.windspeed} km/h ${getWindDirection(latest.winddirection)}` : '--';
    const updated = latest.timestamp ? formatDateTime(latest.timestamp) : '--';

    return `
        <a class="card city-card" href="city.html?city=${encodeURIComponent(city.id)}">
            <h3>${cityName(city)}</h3>
            <p class="city-country">${cityCountry(city)}</p>
            <div class="metric-value">${temp}</div>
            <p class="metric-unit">${t('latest_temperature')}</p>
            <p>${t('wind_label')} <span>${wind}</span></p>
            <p>${t('records_label')} <span>${city.records}</span></p>
            <p>${t('last_update')} <span>${updated}</span></p>
        </a>
    `;
}

// The filter drives the map as well as the grid, so both always show the
// same set of cities.
function renderFilteredCities() {
    const grid = document.getElementById('cities-grid');
    const matches = filterByCountry(ALL_CITIES, SELECTED_COUNTRY);

    renderCityMap(document.getElementById('city-map'), matches);

    if (!matches.length) {
        grid.innerHTML = `<div class="card"><p>${t('no_cities_country')}</p></div>`;
        return;
    }
    grid.innerHTML = matches.map(cityListCard).join('');
}

async function loadCities() {
    showLoading(true);
    hideError();
    loadSiteContent();

    const grid = document.getElementById('cities-grid');
    try {
        const result = await apiRequest('/cities');
        showLoading(false);
        ALL_CITIES = result.cities;

        if (!ALL_CITIES.length) {
            renderCityMap(document.getElementById('city-map'), []);
            grid.innerHTML = `<div class="card"><p>${t('no_cities')}</p></div>`;
            return;
        }

        // A country can be preselected by link (the home page's "See all"),
        // but only if we actually track it.
        const requested = countryFromUrl();
        const known = ALL_CITIES.some(city => countryKey(city) === requested);
        SELECTED_COUNTRY = known ? requested : 'all';

        renderCountryFilter(
            document.getElementById('country-filter'), ALL_CITIES, SELECTED_COUNTRY,
            country => { SELECTED_COUNTRY = country; renderFilteredCities(); });
        renderFilteredCities();
    } catch (error) {
        showError(t('error_cities'));
    }
}

window.onload = loadCities;
