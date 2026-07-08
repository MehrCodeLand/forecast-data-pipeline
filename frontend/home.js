function cityCard(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : 'No data yet';
    const wind = latest.windspeed !== undefined ? `${latest.windspeed} km/h` : '--';

    return `
        <a class="card city-card" href="city.html?city=${encodeURIComponent(city.id)}">
            <h3>${city.name}</h3>
            <p class="city-country">${city.country}</p>
            <div class="metric-value">${temp}</div>
            <p class="metric-unit">latest temperature</p>
            <p>Wind: <span>${wind}</span></p>
            <p>Records: <span>${city.records}</span></p>
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
            grid.innerHTML = '<div class="card"><p>No cities are being tracked yet.</p></div>';
            return;
        }
        grid.innerHTML = result.cities.slice(0, 6).map(cityCard).join('');
    } catch (error) {
        grid.innerHTML = '';
        showError('Could not load cities. Please check if the API is running.');
    }
}

window.onload = loadHome;
