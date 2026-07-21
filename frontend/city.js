const CITY_ID = new URLSearchParams(window.location.search).get('city');

function setText(id, value) {
    document.getElementById(id).textContent = value;
}

async function loadCityInfo() {
    const city = await apiRequest(`/cities/${encodeURIComponent(CITY_ID)}`);
    document.title = `${city.name} - Weather Watch`;
    setText('city-name', `${city.name}, ${city.country}`);

    const latest = city.latest || {};
    const condition = latest.condition_desc ? ` | ${latest.condition_desc}` : '';
    setText('city-meta',
        `${city.latitude}, ${city.longitude} | ${city.records} ${t('records_collected')} | ${t('last_update')} ${formatDateTime(city.last_record)}${condition}`);
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
    if (summary.avg_aqi !== undefined) {
        cards += metricCard(t('avg_aqi'), summary.avg_aqi, t('aqi_scale'));
    }
    if (summary.avg_pm2_5 !== undefined) {
        cards += metricCard('PM2.5', summary.avg_pm2_5, t('avg_ugm3'));
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
    renderAirQualityCards(result.summary);
}

// OpenWeather AQI is a 1-5 index. Map each level to a label and a color.
const AQI_LEVELS = {
    1: { key: 'aqi_good', color: '#3fb950' },
    2: { key: 'aqi_fair', color: '#b8c832' },
    3: { key: 'aqi_moderate', color: '#d29922' },
    4: { key: 'aqi_poor', color: '#f0883e' },
    5: { key: 'aqi_very_poor', color: '#f85149' }
};

// Pollutant components (OpenWeather, in µg/m³) with a reference "high" value
// used to scale the horizontal bars so they are comparable at a glance.
const POLLUTANTS = [
    { key: 'pm2_5', label: 'PM2.5', max: 75 },
    { key: 'pm10', label: 'PM10', max: 200 },
    { key: 'o3', label: 'O₃', max: 240 },
    { key: 'no2', label: 'NO₂', max: 200 },
    { key: 'so2', label: 'SO₂', max: 350 },
    { key: 'co', label: 'CO', max: 15000 }
];

function renderAirQualityCards(summary) {
    const section = document.getElementById('air-quality-section');
    const current = (summary && summary.current) || {};
    const hasAir = current.aqi != null || summary.avg_aqi != null;
    if (!hasAir) {
        section.style.display = 'none';
        return;
    }
    section.style.display = '';

    const aqi = current.aqi;
    const level = AQI_LEVELS[aqi];
    const rating = level ? t(level.key) : '--';

    document.getElementById('air-quality-grid').innerHTML = `
        <div class="card aqi-card">
            <h3>${t('aqi')}</h3>
            <div id="aqi-gauge" class="aqi-gauge"></div>
            <p class="metric-unit">${t('aqi_scale')}</p>
        </div>
        <div class="card">
            <h3>${t('pollutants')}</h3>
            <div id="pollutant-bars"></div>
        </div>
    `;

    renderAqiGauge(document.getElementById('aqi-gauge'),
        typeof aqi === 'number' ? aqi : null, rating);

    const items = POLLUTANTS
        .filter(p => current[p.key] != null)
        .map(p => ({ label: p.label, value: current[p.key], max: p.max, unit: 'µg/m³' }));
    renderHBars(document.getElementById('pollutant-bars'), items);

    renderAirAdvice(aqi, items);
}

// Plain-language health guidance from the current AQI level, plus the main
// pollutant (the one highest relative to its reference level).
function renderAirAdvice(aqi, pollutantItems) {
    const card = document.getElementById('aqi-advice-card');
    const el = document.getElementById('aqi-advice');
    if (!card || !el || typeof aqi !== 'number') {
        if (card) card.style.display = 'none';
        return;
    }
    const level = Math.max(1, Math.min(5, Math.round(aqi)));
    let text = t('aqi_advice_' + level);

    if (pollutantItems && pollutantItems.length) {
        const dominant = pollutantItems.reduce((a, b) =>
            (b.value / b.max) > (a.value / a.max) ? b : a);
        text += ' ' + t('main_pollutant').replace('{p}', dominant.label);
    }
    el.textContent = text;
    card.style.display = '';
}

async function loadCharts(period) {
    try {
        const data = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/data?limit=${Math.max(period, 2)}`);
        // API returns newest-first; charts read oldest -> newest.
        const chrono = [...data.data].reverse();

        const series = field => chrono.map(r => ({
            label: shortTime(r.time),
            y: typeof r[field] === 'number' ? r[field] : null
        }));

        renderLineChart(document.getElementById('temp-chart'), series('temperature'),
            { color: '#f0883e', unit: 'C', emptyText: t('chart_empty') });
        renderLineChart(document.getElementById('wind-chart'), series('windspeed'),
            { color: '#58a6ff', unit: 'km/h', emptyText: t('chart_empty') });

        // Air-quality trend charts (only meaningful when such data exists)
        if (chrono.some(r => typeof r.aqi === 'number')) {
            renderLineChart(document.getElementById('aqi-chart'), series('aqi'),
                { color: '#a371f7', unit: 'AQI', emptyText: t('chart_empty') });
        }
        if (chrono.some(r => typeof r.pm2_5 === 'number')) {
            renderLineChart(document.getElementById('pm25-chart'), series('pm2_5'),
                { color: '#3fb950', unit: 'µg/m³', emptyText: t('chart_empty') });
        }

        // Precipitation & sky: precipitation as bars, humidity + cloud cover
        // as overlaid lines. Shown when any of these fields are present.
        const hasPrecip = chrono.some(r => typeof r.precipitation === 'number');
        const hasHumidity = chrono.some(r => typeof r.humidity === 'number');
        const hasClouds = chrono.some(r => typeof r.clouds === 'number');
        const precipSection = document.getElementById('precip-section');
        if (hasPrecip || hasHumidity || hasClouds) {
            precipSection.style.display = '';
            if (hasPrecip) {
                renderBarChart(document.getElementById('precip-chart'), series('precipitation'),
                    { color: '#58a6ff', unit: 'mm', emptyText: t('chart_empty') });
            } else {
                document.getElementById('precip-chart').innerHTML =
                    `<p class="chart-empty">${t('no_precip')}</p>`;
            }
            const humiditySeries = [];
            if (hasHumidity) humiditySeries.push({ name: t('humidity'), color: '#3fb950', points: series('humidity') });
            if (hasClouds) humiditySeries.push({ name: t('clouds'), color: '#8b949e', points: series('clouds') });
            renderMultiLineChart(document.getElementById('humidity-chart'), humiditySeries,
                { unit: '%', emptyText: t('chart_empty') });
        } else {
            precipSection.style.display = 'none';
        }
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

function localTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const locale = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'fa') ? 'fa-IR' : 'en-US';
    return d.toLocaleString(locale, { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' });
}

// Naive short-term projection: draws the forecast points as a dashed-looking
// line (rendered as a normal line here) with a clear "estimate" note.
async function loadForecast() {
    const section = document.getElementById('forecast-section');
    try {
        const temp = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/forecast?field=temperature&hours=6`).catch(() => null);
        if (temp && temp.forecast) {
            section.style.display = '';
            renderLineChart(document.getElementById('temp-forecast-chart'),
                temp.forecast.map(p => ({ label: localTime(p.time), y: p.value })),
                { color: '#f0883e', unit: 'C', emptyText: t('chart_empty') });
        } else {
            section.style.display = 'none';
            return;
        }

        const aqi = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/forecast?field=aqi&hours=6`).catch(() => null);
        const aqiCard = document.getElementById('aqi-forecast-card');
        if (aqi && aqi.forecast) {
            aqiCard.style.display = '';
            renderLineChart(document.getElementById('aqi-forecast-chart'),
                aqi.forecast.map(p => ({ label: localTime(p.time), y: p.value })),
                { color: '#a371f7', unit: 'AQI', emptyText: t('chart_empty') });
        } else {
            aqiCard.style.display = 'none';
        }
    } catch (error) {
        section.style.display = 'none';
    }
}

async function loadPatterns() {
    const section = document.getElementById('patterns-section');
    const weekdays = (typeof I18N !== 'undefined' && I18N[CURRENT_LANG] && I18N[CURRENT_LANG].weekdays)
        || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    try {
        const temp = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/patterns?field=temperature`).catch(() => null);
        if (!temp || !temp.grid) {
            section.style.display = 'none';
            return;
        }
        section.style.display = '';
        renderHeatmap(document.getElementById('temp-heatmap'), {
            grid: temp.grid, min: temp.min, max: temp.max,
            colors: ['#58a6ff', '#3fb950', '#f0883e', '#f85149'],
            rowLabels: weekdays, unit: 'C', emptyText: t('chart_empty')
        });

        const aqi = await apiRequest(
            `/cities/${encodeURIComponent(CITY_ID)}/patterns?field=aqi`).catch(() => null);
        const aqiCard = document.getElementById('aqi-pattern-card');
        if (aqi && aqi.grid) {
            aqiCard.style.display = '';
            renderHeatmap(document.getElementById('aqi-heatmap'), {
                grid: aqi.grid, min: aqi.min, max: aqi.max,
                colors: ['#3fb950', '#d29922', '#f85149'],
                rowLabels: weekdays, unit: 'AQI', emptyText: t('chart_empty')
            });
        } else {
            aqiCard.style.display = 'none';
        }
    } catch (error) {
        section.style.display = 'none';
    }
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
            loadForecast(),
            loadPatterns(),
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
