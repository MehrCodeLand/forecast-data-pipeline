function cityCard(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : t('no_data_yet');
    const wind = latest.windspeed !== undefined ? `${latest.windspeed} km/h` : '--';

    return `
        <a class="card city-card" href="city.html?city=${encodeURIComponent(city.id)}">
            <h3>${city.name}</h3>
            <p class="city-country">${city.country}</p>
            <div class="metric-value">${temp}</div>
            <p class="metric-unit">${t('latest_temperature')}</p>
            <p>${t('wind_label')} <span>${wind}</span></p>
            <p>${t('records_label')} <span>${city.records}</span></p>
        </a>
    `;
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
        if (!result.cities.length) {
            grid.innerHTML = `<div class="card"><p>${t('no_cities')}</p></div>`;
            return;
        }
        grid.innerHTML = result.cities.slice(0, 6).map(cityCard).join('');
    } catch (error) {
        grid.innerHTML = '';
        showError(t('error_cities'));
    }
}

window.onload = loadHome;
