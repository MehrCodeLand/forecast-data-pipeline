const HOME_PREVIEW_LIMIT = 6;

let HOME_CITIES = [];
let HOME_COUNTRY = 'all';

function cityCard(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : t('no_data_yet');
    const wind = latest.windspeed !== undefined ? `${latest.windspeed} km/h` : '--';

    return `
        <a class="card city-card" href="city.html?city=${encodeURIComponent(city.id)}">
            <h3>${cityName(city)}</h3>
            <p class="city-country">${cityCountry(city)}</p>
            <div class="metric-value">${temp}</div>
            <p class="metric-unit">${t('latest_temperature')}</p>
            <p>${t('wind_label')} <span>${wind}</span></p>
            <p>${t('records_label')} <span>${city.records}</span></p>
        </a>
    `;
}

// Draws the preview grid for the selected country and keeps the "See all"
// link pointing at the same selection on the cities page.
function renderHomeCities() {
    const grid = document.getElementById('cities-preview');
    const matches = filterByCountry(HOME_CITIES, HOME_COUNTRY);

    if (!matches.length) {
        grid.innerHTML = `<div class="card"><p>${t('no_cities_country')}</p></div>`;
    } else {
        grid.innerHTML = matches.slice(0, HOME_PREVIEW_LIMIT).map(cityCard).join('');
    }

    const seeAll = document.getElementById('see-all-cities');
    if (seeAll) {
        seeAll.href = HOME_COUNTRY === 'all'
            ? 'cities.html'
            : `cities.html?country=${encodeURIComponent(HOME_COUNTRY)}`;
    }

    const more = document.getElementById('cities-more');
    if (more) {
        const hidden = matches.length - HOME_PREVIEW_LIMIT;
        more.textContent = hidden > 0 ? t('cities_more').replace('{n}', hidden) : '';
    }
}

async function loadHome() {
    const content = await loadSiteContent();
    if (content) {
        if (content.tagline) {
            document.getElementById('hero-tagline').textContent = content.tagline;
        }
        if (content.home_intro) {
            document.getElementById('hero-intro').textContent = content.home_intro;
        }
        if (content.home_examples) {
            document.getElementById('home-examples').textContent = content.home_examples;
        }
    }

    const grid = document.getElementById('cities-preview');
    try {
        const result = await apiRequest('/cities');
        HOME_CITIES = result.cities;
        if (!HOME_CITIES.length) {
            grid.innerHTML = `<div class="card"><p>${t('no_cities')}</p></div>`;
            return;
        }

        renderCountryFilter(
            document.getElementById('country-filter'), HOME_CITIES, HOME_COUNTRY,
            country => { HOME_COUNTRY = country; renderHomeCities(); });
        renderHomeCities();
    } catch (error) {
        grid.innerHTML = '';
        showError(t('error_cities'));
    }
}

window.onload = loadHome;
