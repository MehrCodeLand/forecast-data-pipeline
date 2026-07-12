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

function metricCard(title, value, unit) {
    return `
        <div class="card">
            <h3>${title}</h3>
            <div class="metric-value">${fmt(value)}</div>
            <p class="metric-unit">${unit}</p>
        </div>
    `;
}

function summaryCards(summary) {
    let cards = `
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

    // Optional metrics appear only once records carrying them have been
    // collected, so summaries over legacy-only data are unchanged.
    if (summary.avg_apparent_temperature !== undefined) {
        cards += metricCard(t('feels_like'), summary.avg_apparent_temperature, t('deg_c_avg'));
    }
    if (summary.avg_humidity !== undefined) {
        cards += metricCard(t('humidity'), summary.avg_humidity, t('pct'));
    }
    if (summary.total_precipitation !== undefined) {
        cards += metricCard(t('precipitation'), summary.total_precipitation, t('mm_total'));
    }
    if (summary.avg_pressure !== undefined) {
        cards += metricCard(t('pressure'), summary.avg_pressure, t('hpa'));
    }
    return cards;
}

function shortTime(value) {
    if (!value) return '';
    const date = new Date(value);
    const locale = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'fa') ? 'fa-IR' : 'en-US';
    return date.toLocaleString(locale, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
}

async function loadSummary(period) {
    const result = await apiRequest(`/cities/${encodeURIComponent(CITY_ID)}/summary?period=${period}`);
    document.getElementById('summary-grid').innerHTML = summaryCards(result.summary);
}

async function loadCharts(period) {
    try {
        const data = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/data?limit=${Math.max(period, 2)}`);
        // API returns newest-first; charts read oldest -> newest.
        const chrono = [...data.data].reverse();

        const tempPoints = chrono.map(r => ({
            label: shortTime(r.time),
            y: typeof r.temperature === 'number' ? r.temperature : null
        }));
        const windPoints = chrono.map(r => ({
            label: shortTime(r.time),
            y: typeof r.windspeed === 'number' ? r.windspeed : null
        }));

        renderLineChart(document.getElementById('temp-chart'), tempPoints,
            { color: '#f0883e', unit: 'C', emptyText: t('chart_empty') });
        renderLineChart(document.getElementById('wind-chart'), windPoints,
            { color: '#58a6ff', unit: 'km/h', emptyText: t('chart_empty') });
    } catch (error) {
        console.error('Failed to load charts:', error);
    }
}

function recordCard(title, rec, unit) {
    if (!rec) return '';
    return `
        <div class="card">
            <h3>${title}</h3>
            <div class="metric-value">${fmt(rec.value)}${unit ? ' ' + unit : ''}</div>
            <p class="metric-unit">${formatDateTime(rec.timestamp || rec.time)}</p>
        </div>
    `;
}

async function loadRecords() {
    try {
        const thresholdEl = document.getElementById('calm-threshold');
        const threshold = thresholdEl ? thresholdEl.value : 5;
        const res = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/records?threshold=${threshold}`);
        const r = res.records;

        let html = '';
        html += recordCard(t('hottest'), r.hottest, 'C');
        html += recordCard(t('coldest'), r.coldest, 'C');
        html += recordCard(t('windiest'), r.windiest, 'km/h');
        if (r.longest_calm_streak) {
            html += `
                <div class="card">
                    <h3>${t('longest_calm')}</h3>
                    <div class="metric-value">${fmt(r.longest_calm_streak.records)}</div>
                    <p class="metric-unit">${t('consecutive_records')}</p>
                </div>
            `;
        }
        if (r.wettest) html += recordCard(t('wettest'), r.wettest, 'mm');
        if (r.most_humid) html += recordCard(t('most_humid'), r.most_humid, '%');

        document.getElementById('records-grid').innerHTML = html;
    } catch (error) {
        console.error('Failed to load records:', error);
    }
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
        const city = await loadCityInfo();
        showLoading(false);

        // If the city has no records yet, don't paint a wall of "--";
        // explain why (and show the collector's last error if there is one).
        if (!city.records) {
            await showNoDataNotice();
            return;
        }

        await Promise.allSettled([
            loadSummary(period),
            loadCharts(period),
            loadRecords(),
            loadTemperature(period),
            loadWind(period),
            loadCalmPeriods(),
            loadCityData()
        ]);
    } catch (error) {
        showLoading(false);
        showError(t('error_city'));
    }
}

// Shows a clear message when a city has collected nothing yet, including the
// scheduler's last error for this city (e.g. cannot reach the weather API),
// so the cause is visible instead of a page full of "--".
async function showNoDataNotice() {
    let reason = '';
    try {
        const status = await apiRequest('/scheduler/status');
        const cityStatus = (status.cities && status.cities[CITY_ID]) || {};
        if (!status.running) {
            reason = t('collector_stopped');
        } else if (cityStatus.last_error) {
            reason = `${t('last_error')} ${cityStatus.last_error}`;
        } else {
            reason = t('collector_soon').replace('{min}', status.interval_minutes);
        }
    } catch (e) {
        reason = '';
    }
    const banner = document.getElementById('error');
    banner.innerHTML = `<strong>${t('no_data_title')}</strong><br>${t('no_data_body')} ${reason}`;
    banner.className = 'error notice';
    banner.style.display = 'block';
}

window.onload = loadCityDashboard;
