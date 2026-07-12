const COMPARE_COLORS = ['#8957e5', '#f0883e', '#58a6ff', '#3fb950'];
const MAX_COMPARE = 4;
const MIN_COMPARE = 2;

let ALL_CITIES = [];

function pickerItem(city) {
    const latest = city.latest || {};
    const temp = latest.temperature !== undefined ? `${latest.temperature} C` : t('no_data_yet');
    return `
        <label class="picker-item">
            <input type="checkbox" value="${city.id}">
            <span class="picker-name">${city.name}</span>
            <span class="picker-detail">${city.country} | ${temp}</span>
        </label>
    `;
}

function selectedCityIds() {
    return [...document.querySelectorAll('#city-picker input:checked')].map(el => el.value);
}

function enforceLimit() {
    const checked = selectedCityIds().length;
    document.querySelectorAll('#city-picker input').forEach(el => {
        el.disabled = !el.checked && checked >= MAX_COMPARE;
    });
}

async function loadPicker() {
    loadSiteContent();
    hideError();
    const picker = document.getElementById('city-picker');
    picker.innerHTML = `<p>${t('loading')}</p>`;
    try {
        const result = await apiRequest('/cities');
        ALL_CITIES = result.cities;
        if (ALL_CITIES.length < MIN_COMPARE) {
            picker.innerHTML = `<p>${t('compare_need_more')}</p>`;
            document.getElementById('compare-btn').disabled = true;
            return;
        }
        document.getElementById('compare-btn').disabled = false;
        picker.innerHTML = ALL_CITIES.map(pickerItem).join('');
        // preselect the first two so the page works with a single click
        const boxes = picker.querySelectorAll('input');
        boxes[0].checked = true;
        boxes[1].checked = true;
        picker.addEventListener('change', enforceLimit);
        enforceLimit();
    } catch (error) {
        // leave a retry button instead of a dead "Loading..." forever
        showError(t('error_cities'));
        picker.innerHTML = '';
        const retry = document.createElement('button');
        retry.className = 'btn btn-secondary';
        retry.textContent = t('retry');
        retry.addEventListener('click', loadPicker);
        picker.appendChild(retry);
    }
}

function compareRow(label, values) {
    return `<tr><td>${label}</td>${values.map(v => `<td>${fmt(v)}</td>`).join('')}</tr>`;
}

function renderCompareTable(cities, summaries) {
    const head = `<thead><tr><th>${t('metric')}</th>` +
        cities.map(c => `<th>${c.name}</th>`).join('') + '</tr></thead>';

    const rows = [
        compareRow(t('average') + ' (' + t('temperature') + ')', summaries.map(s => s?.avg_temperature)),
        compareRow(t('min_label'), summaries.map(s => s?.temp_range?.min)),
        compareRow(t('max_label'), summaries.map(s => s?.temp_range?.max)),
        compareRow(t('avg_speed') + ' (' + t('wind') + ')', summaries.map(s => s?.avg_windspeed)),
        compareRow(t('peak_speed'), summaries.map(s => s?.peak_windspeed)),
        compareRow(t('dominant_direction'), summaries.map(s =>
            s?.dominant_wind_direction !== undefined && s?.dominant_wind_direction !== null
                ? `${s.dominant_wind_direction} (${getWindDirection(s.dominant_wind_direction)})` : null)),
        compareRow(t('calm_pct_label'), summaries.map(s => s?.calm_periods?.calm_percentage)),
        compareRow(t('data_points'), summaries.map(s => s?.data_points)),
    ];

    // optional metrics only when at least one city has them
    if (summaries.some(s => s?.avg_humidity !== undefined)) {
        rows.push(compareRow(t('humidity'), summaries.map(s => s?.avg_humidity)));
    }
    if (summaries.some(s => s?.avg_apparent_temperature !== undefined)) {
        rows.push(compareRow(t('feels_like'), summaries.map(s => s?.avg_apparent_temperature)));
    }
    if (summaries.some(s => s?.total_precipitation !== undefined)) {
        rows.push(compareRow(t('precipitation'), summaries.map(s => s?.total_precipitation)));
    }
    if (summaries.some(s => s?.avg_aqi !== undefined)) {
        rows.push(compareRow(t('avg_aqi'), summaries.map(s => s?.avg_aqi)));
    }
    if (summaries.some(s => s?.avg_pm2_5 !== undefined)) {
        rows.push(compareRow('PM2.5', summaries.map(s => s?.avg_pm2_5)));
    }

    document.getElementById('compare-table').innerHTML = head + '<tbody>' + rows.join('') + '</tbody>';
}

async function runCompare() {
    hideError();
    const ids = selectedCityIds();
    if (ids.length < MIN_COMPARE || ids.length > MAX_COMPARE) {
        showError(t('compare_pick'));
        return;
    }

    const btn = document.getElementById('compare-btn');
    btn.disabled = true;
    const period = Math.max(parseInt(document.getElementById('period').value, 10) || 24, 2);

    try {
        const cities = ids.map(id => ALL_CITIES.find(c => c.id === id));

        const summaries = await Promise.all(ids.map(id =>
            apiRequest(`/cities/${encodeURIComponent(id)}/summary?period=${period}`)
                .then(r => r.summary).catch(() => null)));

        const histories = await Promise.all(ids.map(id =>
            apiRequest(`/cities/${encodeURIComponent(id)}/data?limit=${period}`)
                .then(r => [...r.data].reverse()).catch(() => [])));

        // Every request failed or returned nothing: say so instead of
        // rendering an empty table (a city with no data yet is fine, but
        // all-empty means the API was unreachable).
        if (summaries.every(s => s === null) && histories.every(h => h.length === 0)) {
            showError(t('compare_no_data'));
            return;
        }

        renderCompareTable(cities, summaries);

        const series = field => cities.map((c, i) => ({
            name: c.name,
            color: COMPARE_COLORS[i % COMPARE_COLORS.length],
            points: histories[i].map(rec => ({
                label: formatDateTime(rec.time),
                y: typeof rec[field] === 'number' ? rec[field] : null
            }))
        }));

        renderMultiLineChart(document.getElementById('compare-temp-chart'),
            series('temperature'), { unit: 'C', emptyText: t('chart_empty') });
        renderMultiLineChart(document.getElementById('compare-wind-chart'),
            series('windspeed'), { unit: 'km/h', emptyText: t('chart_empty') });

        document.getElementById('compare-results').style.display = 'block';
    } catch (error) {
        showError(t('error_cities'));
    } finally {
        btn.disabled = false;
    }
}

window.onload = () => {
    loadPicker();
    document.getElementById('compare-btn').addEventListener('click', runCompare);
};
