const CITY_ID = new URLSearchParams(window.location.search).get('city');

function setText(id, value) {
    document.getElementById(id).textContent = value;
}

async function loadCityInfo() {
    const city = await apiRequest(`/cities/${encodeURIComponent(CITY_ID)}`);
    document.title = `${city.name} - Weather Watch`;
    setText('city-name', `${city.name}, ${city.country}`);
    setText('city-meta',
        `${city.latitude}, ${city.longitude} | ${city.records} ${t('records_collected')} | ${t('last_update')} ${formatDateTime(city.last_record)}`);
    return city;
}

function summaryCards(summary) {
    return `
        <div class="card">
            <h3>${t('temperature')}</h3>
            <div class="metric-value">${fmt(summary.avg_temperature)}</div>
            <p class="metric-unit">${t('deg_c_avg')}</p>
            <div class="metric-detail">
                <p>${t('min_label')} <span>${fmt(summary.temp_range?.min)}</span></p>
                <p>${t('max_label')} <span>${fmt(summary.temp_range?.max)}</span></p>
            </div>
        </div>
        <div class="card">
            <h3>${t('wind_speed')}</h3>
            <div class="metric-value">${fmt(summary.avg_windspeed)}</div>
            <p class="metric-unit">${t('kmh_avg')}</p>
            <div class="metric-detail">
                <p>${t('peak_label')} <span>${fmt(summary.peak_windspeed)} km/h</span></p>
            </div>
        </div>
        <div class="card">
            <h3>${t('wind_direction')}</h3>
            <div class="metric-value">${fmt(summary.dominant_wind_direction)}</div>
            <p class="metric-unit">${t('degrees')}</p>
            <p class="direction-text">${getWindDirection(summary.dominant_wind_direction)}</p>
        </div>
        <div class="card">
            <h3>${t('calm_periods')}</h3>
            <div class="metric-value">${fmt(summary.calm_periods?.calm_percentage)}</div>
            <p class="metric-unit">${t('pct_calm')}</p>
        </div>
        <div class="card">
            <h3>${t('data_points')}</h3>
            <div class="metric-value">${fmt(summary.data_points)}</div>
            <p class="metric-unit">${t('analyzed')}</p>
        </div>
    `;
}

async function loadSummary(period) {
    const result = await apiRequest(`/cities/${encodeURIComponent(CITY_ID)}/summary?period=${period}`);
    document.getElementById('summary-grid').innerHTML = summaryCards(result.summary);
}

async function loadTemperature(period) {
    const base = `/cities/${encodeURIComponent(CITY_ID)}/temperature`;
    const results = await Promise.allSettled([
        apiRequest(`${base}/average?period=${period}`),
        apiRequest(`${base}/range?period=${period}`),
        apiRequest(`${base}/rate-of-change?hours=${Math.max(period, 2)}`),
        apiRequest(`${base}/delta?hours=${period}`)
    ]);
    const [avg, range, rate, delta] = results.map(r => r.status === 'fulfilled' ? r.value : {});

    setText('avg-temp', fmt(avg.average_temperature));
    setText('temp-min', fmt(range.temperature_range?.min));
    setText('temp-max', fmt(range.temperature_range?.max));
    setText('temp-range-val', fmt(range.temperature_range?.range));
    setText('rate-change', fmt(rate.avg_rate_of_change));
    setText('delta', fmt(delta.delta_per_hour));
}

async function loadWind(period) {
    const base = `/cities/${encodeURIComponent(CITY_ID)}/wind`;
    const results = await Promise.allSettled([
        apiRequest(`${base}/average-speed?period=${period}`),
        apiRequest(`${base}/peak-speed?period=${period}`),
        apiRequest(`${base}/dominant-direction?period=${period}`),
        apiRequest(`${base}/direction-variability?period=${Math.max(period, 2)}`)
    ]);
    const [avg, peak, direction, variability] = results.map(r => r.status === 'fulfilled' ? r.value : {});

    setText('avg-wind', fmt(avg.average_windspeed));
    setText('peak-wind', fmt(peak.peak_windspeed));
    setText('wind-direction', fmt(direction.dominant_direction));
    setText('direction-text', getWindDirection(direction.dominant_direction));
    setText('wind-variability', fmt(variability.direction_variability));
}

async function loadCalmPeriods() {
    const period = document.getElementById('period').value;
    const threshold = document.getElementById('calm-threshold').value;
    try {
        const data = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/wind/calm-periods?period=${period}&threshold=${threshold}`);
        setText('calm-count', fmt(data.result?.calm_periods));
        setText('total-periods', fmt(data.result?.total_periods));
        setText('calm-percentage', fmt(data.result?.calm_percentage));
    } catch (error) {
        console.error('Failed to load calm periods:', error);
    }
}

async function loadCityData() {
    const limit = document.getElementById('data-limit').value;
    try {
        const data = await apiRequest(`/cities/${encodeURIComponent(CITY_ID)}/data?limit=${limit}`);
        setText('total-records', fmt(data.total));
        setText('showing-records', data.data.length);

        const tbody = document.getElementById('data-tbody');
        tbody.innerHTML = '';
        data.data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${fmt(row.id)}</td>
                <td>${formatDateTime(row.time)}</td>
                <td>${fmt(row.temperature)}</td>
                <td>${fmt(row.windspeed)}</td>
                <td>${fmt(row.winddirection)} (${getWindDirection(row.winddirection)})</td>
                <td>${fmt(row.weathercode)}</td>
                <td>${row.is_day ? t('day') : t('night')}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Failed to load raw data:', error);
    }
}

async function loadCityDashboard() {
    if (!CITY_ID) {
        window.location.href = 'cities.html';
        return;
    }

    showLoading(true);
    hideError();
    loadSiteContent();

    const period = document.getElementById('period').value;

    try {
        await loadCityInfo();
        await Promise.allSettled([
            loadSummary(period),
            loadTemperature(period),
            loadWind(period),
            loadCalmPeriods(),
            loadCityData()
        ]);
        showLoading(false);
    } catch (error) {
        showError(t('error_city'));
    }
}

window.onload = loadCityDashboard;
