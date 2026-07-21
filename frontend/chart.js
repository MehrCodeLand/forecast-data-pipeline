// Minimal dependency-free SVG line chart. Colors come from CSS (theme-aware);
// the series color is passed in. Charts always read left-to-right (oldest to
// newest) even on RTL pages, which is the natural reading order for a timeline.

// Multi-series variant used by the compare page: series is an array of
// { name, color, points: [{label, y}] }. X positions are index-based so
// cities with slightly different timestamps still overlay cleanly.
function renderMultiLineChart(container, series, opts) {
    opts = opts || {};
    const unit = opts.unit || '';
    const emptyText = opts.emptyText || 'Not enough data to chart yet.';

    const drawable = series
        .map(s => ({ ...s, points: s.points.filter(p => typeof p.y === 'number' && !isNaN(p.y)) }))
        .filter(s => s.points.length >= 2);
    if (!drawable.length) {
        container.innerHTML = `<p class="chart-empty">${emptyText}</p>`;
        return;
    }

    const W = 640, H = 280;
    const padL = 48, padR = 16, padT = 16, padB = 56;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const allY = drawable.flatMap(s => s.points.map(p => p.y));
    let minY = Math.min(...allY), maxY = Math.max(...allY);
    if (minY === maxY) { minY -= 1; maxY += 1; }
    const margin = (maxY - minY) * 0.12;
    minY -= margin; maxY += margin;

    const maxN = Math.max(...drawable.map(s => s.points.length));
    const xAt = (i, n) => padL + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
    const yAt = v => padT + plotH - ((v - minY) / (maxY - minY)) * plotH;
    const round = x => Math.round(x * 10) / 10;

    const STEPS = 4;
    let grid = '', yLabels = '';
    for (let s = 0; s <= STEPS; s++) {
        const value = minY + (s / STEPS) * (maxY - minY);
        const y = round(yAt(value));
        grid += `<line class="chart-grid" x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}"></line>`;
        yLabels += `<text class="chart-axis" x="${padL - 8}" y="${y + 4}" text-anchor="end">${round(value)}</text>`;
    }

    let paths = '', dots = '';
    drawable.forEach(s => {
        const n = s.points.length;
        const line = s.points
            .map((p, i) => `${i === 0 ? 'M' : 'L'} ${round(xAt(i, n))} ${round(yAt(p.y))}`)
            .join(' ');
        paths += `<path d="${line}" fill="none" stroke="${s.color}" stroke-width="2"
                        stroke-linejoin="round" stroke-linecap="round"></path>`;
        s.points.forEach((p, i) => {
            const title = `${s.name}${p.label ? ' - ' + p.label : ''}: ${p.y}${unit ? ' ' + unit : ''}`;
            dots += `<circle class="chart-dot" cx="${round(xAt(i, n))}" cy="${round(yAt(p.y))}" r="2.5"
                             style="fill:${s.color}"><title>${title}</title></circle>`;
        });
    });

    // Legend row under the plot
    let legend = '';
    let lx = padL;
    drawable.forEach(s => {
        legend += `<circle cx="${lx}" cy="${H - 14}" r="5" style="fill:${s.color}"></circle>` +
                  `<text class="chart-axis chart-legend" x="${lx + 10}" y="${H - 10}">${s.name}</text>`;
        lx += 14 + s.name.length * 7 + 24;
    });

    container.innerHTML = `
        <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img">
            ${grid}
            ${paths}
            ${dots}
            ${yLabels}
            ${legend}
        </svg>
    `;
}

function renderLineChart(container, points, opts) {
    opts = opts || {};
    const color = opts.color || '#8957e5';
    const unit = opts.unit || '';
    const emptyText = opts.emptyText || 'Not enough data to chart yet.';

    const valid = points.filter(p => typeof p.y === 'number' && !isNaN(p.y));
    if (valid.length < 2) {
        container.innerHTML = `<p class="chart-empty">${emptyText}</p>`;
        return;
    }

    const W = 640, H = 260;
    const padL = 48, padR = 16, padT = 16, padB = 40;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const ys = valid.map(p => p.y);
    let minY = Math.min(...ys);
    let maxY = Math.max(...ys);
    if (minY === maxY) { minY -= 1; maxY += 1; }
    const margin = (maxY - minY) * 0.12;
    minY -= margin;
    maxY += margin;

    const n = valid.length;
    const xAt = i => padL + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
    const yAt = v => padT + plotH - ((v - minY) / (maxY - minY)) * plotH;

    const round = x => Math.round(x * 10) / 10;

    // Horizontal gridlines + y-axis labels (5 steps)
    const STEPS = 4;
    let grid = '';
    let yLabels = '';
    for (let s = 0; s <= STEPS; s++) {
        const value = minY + (s / STEPS) * (maxY - minY);
        const y = round(yAt(value));
        grid += `<line class="chart-grid" x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}"></line>`;
        yLabels += `<text class="chart-axis" x="${padL - 8}" y="${y + 4}" text-anchor="end">${round(value)}</text>`;
    }

    // X-axis time labels (first, middle, last)
    let xLabels = '';
    const labelIdx = n <= 3 ? valid.map((_, i) => i) : [0, Math.floor((n - 1) / 2), n - 1];
    labelIdx.forEach((i, k) => {
        const anchor = k === 0 ? 'start' : (k === labelIdx.length - 1 ? 'end' : 'middle');
        const label = (valid[i].label || '').toString();
        xLabels += `<text class="chart-axis" x="${round(xAt(i))}" y="${H - 12}" text-anchor="${anchor}">${label}</text>`;
    });

    const linePath = valid
        .map((p, i) => `${i === 0 ? 'M' : 'L'} ${round(xAt(i))} ${round(yAt(p.y))}`)
        .join(' ');

    const areaPath =
        `M ${round(xAt(0))} ${round(padT + plotH)} ` +
        valid.map((p, i) => `L ${round(xAt(i))} ${round(yAt(p.y))}`).join(' ') +
        ` L ${round(xAt(n - 1))} ${round(padT + plotH)} Z`;

    // Data points with hover titles (native SVG tooltip)
    let dots = '';
    valid.forEach((p, i) => {
        const title = `${p.label ? p.label + ': ' : ''}${p.y}${unit ? ' ' + unit : ''}`;
        dots += `<circle class="chart-dot" cx="${round(xAt(i))}" cy="${round(yAt(p.y))}" r="2.5" style="fill:${color}"><title>${title}</title></circle>`;
    });

    const gradId = 'grad-' + Math.random().toString(36).slice(2, 8);

    container.innerHTML = `
        <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img">
            <defs>
                <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="${color}" stop-opacity="0.28"></stop>
                    <stop offset="100%" stop-color="${color}" stop-opacity="0"></stop>
                </linearGradient>
            </defs>
            ${grid}
            <path d="${areaPath}" fill="url(#${gradId})"></path>
            <path d="${linePath}" fill="none" stroke="${color}" stroke-width="2"
                  stroke-linejoin="round" stroke-linecap="round"></path>
            ${dots}
            ${yLabels}
            ${xLabels}
        </svg>
    `;
}

// Semicircular AQI gauge: five colored segments (Good -> Very Poor) with a
// needle pointing at the current 1-5 value, and the value + rating in the
// centre. Theme-aware via CSS for the text.
function renderAqiGauge(container, aqi, ratingText) {
    const COLORS = ['#3fb950', '#b8c832', '#d29922', '#f0883e', '#f85149'];
    const cx = 100, cy = 105, r = 82, sw = 20;
    const rad = deg => (deg * Math.PI) / 180;
    const pt = (deg, radius) => [
        +(cx + radius * Math.cos(rad(deg))).toFixed(2),
        +(cy - radius * Math.sin(rad(deg))).toFixed(2)
    ];

    // Five 36-degree segments spanning the 180..0 half circle (over the top).
    let segs = '';
    for (let i = 0; i < 5; i++) {
        const a1 = 180 - i * 36;
        const a2 = 180 - (i + 1) * 36;
        const [x1, y1] = pt(a1, r);
        const [x2, y2] = pt(a2, r);
        const active = (aqi && Math.ceil(aqi) === i + 1);
        segs += `<path d="M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}"
                    fill="none" stroke="${COLORS[i]}" stroke-width="${sw}"
                    stroke-linecap="butt" opacity="${active ? 1 : 0.4}"></path>`;
    }

    // Needle at the value angle (value 1..5 -> 162..18 degrees).
    let needle = '';
    if (typeof aqi === 'number') {
        const clamped = Math.max(1, Math.min(5, aqi));
        const ang = 180 - (clamped - 0.5) * 36;
        const [nx, ny] = pt(ang, r - sw / 2 - 4);
        needle = `<line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}"
                     class="gauge-needle" stroke-width="3" stroke-linecap="round"></line>
                  <circle cx="${cx}" cy="${cy}" r="5" class="gauge-hub"></circle>`;
    }

    const bigVal = (typeof aqi === 'number') ? aqi : '--';

    container.innerHTML = `
        <svg class="chart gauge" viewBox="0 0 200 135" preserveAspectRatio="xMidYMid meet" role="img">
            ${segs}
            ${needle}
            <text x="100" y="95" text-anchor="middle" class="gauge-value">${bigVal}</text>
            <text x="100" y="122" text-anchor="middle" class="gauge-rating">${ratingText || ''}</text>
        </svg>
    `;
}

// Vertical bar chart over time (used for precipitation). points: [{label, y}].
function renderBarChart(container, points, opts) {
    opts = opts || {};
    const color = opts.color || '#58a6ff';
    const unit = opts.unit || '';
    const emptyText = opts.emptyText || 'Not enough data to chart yet.';

    const valid = points.filter(p => typeof p.y === 'number' && !isNaN(p.y));
    if (!valid.length) {
        container.innerHTML = `<p class="chart-empty">${emptyText}</p>`;
        return;
    }

    const W = 640, H = 240;
    const padL = 44, padR = 16, padT = 16, padB = 40;
    const plotW = W - padL - padR, plotH = H - padT - padB;

    let maxY = Math.max(...valid.map(p => p.y), 0.1);
    maxY = maxY * 1.15;
    const n = valid.length;
    const gap = 3;
    const bw = Math.max(2, plotW / n - gap);
    const round = x => Math.round(x * 10) / 10;
    const yAt = v => padT + plotH - (v / maxY) * plotH;

    const STEPS = 4;
    let grid = '', yLabels = '';
    for (let s = 0; s <= STEPS; s++) {
        const value = (s / STEPS) * maxY;
        const y = round(yAt(value));
        grid += `<line class="chart-grid" x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}"></line>`;
        yLabels += `<text class="chart-axis" x="${padL - 8}" y="${y + 4}" text-anchor="end">${round(value)}</text>`;
    }

    let bars = '';
    valid.forEach((p, i) => {
        const x = padL + i * (plotW / n) + gap / 2;
        const y = round(yAt(p.y));
        const h = round(padT + plotH - y);
        const title = `${p.label ? p.label + ': ' : ''}${p.y}${unit ? ' ' + unit : ''}`;
        bars += `<rect x="${round(x)}" y="${y}" width="${round(bw)}" height="${Math.max(h, 0)}"
                    rx="2" fill="${color}"><title>${title}</title></rect>`;
    });

    const labelIdx = n <= 3 ? valid.map((_, i) => i) : [0, Math.floor((n - 1) / 2), n - 1];
    let xLabels = '';
    labelIdx.forEach((i, k) => {
        const anchor = k === 0 ? 'start' : (k === labelIdx.length - 1 ? 'end' : 'middle');
        const cx = padL + i * (plotW / n) + (plotW / n) / 2;
        xLabels += `<text class="chart-axis" x="${round(cx)}" y="${H - 12}" text-anchor="${anchor}">${valid[i].label || ''}</text>`;
    });

    container.innerHTML = `
        <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img">
            ${grid}${bars}${yLabels}${xLabels}
        </svg>
    `;
}

// Horizontal labelled bars (used for the pollutant profile). items:
// [{label, value, max, unit}]. Bar length is value/max (clamped) and its
// color reflects how high the fraction is. Pure HTML so it is theme-aware.
function renderHBars(container, items) {
    container.innerHTML = items.map(it => {
        const frac = Math.max(0, Math.min(1, it.value / it.max));
        const color = frac < 0.34 ? '#3fb950' : (frac < 0.67 ? '#d29922' : '#f85149');
        const pct = (frac * 100).toFixed(0);
        return `
            <div class="hbar-row">
                <span class="hbar-label">${it.label}</span>
                <span class="hbar-track"><span class="hbar-fill" style="width:${pct}%;background:${color}"></span></span>
                <span class="hbar-value">${it.value} <small>${it.unit || ''}</small></span>
            </div>
        `;
    }).join('');
}

// Hour-of-day (x, 24 cols) by weekday (y, 7 rows) heatmap. grid is a 7x24
// array of numbers or null. Cells are colored between the given stop colors
// by value; empty cells are muted. rowLabels/colLabels label the axes.
function renderHeatmap(container, opts) {
    const grid = opts.grid || [];
    const min = opts.min, max = opts.max;
    const stops = opts.colors || ['#58a6ff', '#f0883e'];
    const rowLabels = opts.rowLabels || [];
    const colLabels = opts.colLabels || [];
    const unit = opts.unit || '';

    if (!grid.length || min === undefined || max === undefined) {
        container.innerHTML = `<p class="chart-empty">${opts.emptyText || ''}</p>`;
        return;
    }

    const hex = c => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
    const lerp = (a, b, t) => Math.round(a + (b - a) * t);
    function colorFor(v) {
        if (v === null || v === undefined) return 'var(--bg-tertiary)';
        const t = max === min ? 0.5 : (v - min) / (max - min);
        // interpolate across the stop list
        const seg = t * (stops.length - 1);
        const i = Math.min(Math.floor(seg), stops.length - 2);
        const local = seg - i;
        const c1 = hex(stops[i]), c2 = hex(stops[i + 1]);
        return `rgb(${lerp(c1[0], c2[0], local)},${lerp(c1[1], c2[1], local)},${lerp(c1[2], c2[2], local)})`;
    }

    let header = '<div class="hm-cell hm-corner"></div>';
    for (let h = 0; h < 24; h++) {
        header += `<div class="hm-hlabel">${h % 3 === 0 ? h : ''}</div>`;
    }

    let rows = '';
    for (let d = 0; d < grid.length; d++) {
        rows += `<div class="hm-rlabel">${rowLabels[d] || d}</div>`;
        for (let h = 0; h < 24; h++) {
            const v = grid[d][h];
            const title = v === null || v === undefined
                ? `${rowLabels[d] || ''} ${h}:00`
                : `${rowLabels[d] || ''} ${h}:00 — ${v}${unit ? ' ' + unit : ''}`;
            rows += `<div class="hm-cell" style="background:${colorFor(v)}" title="${title}"></div>`;
        }
    }

    container.innerHTML = `
        <div class="heatmap" style="direction:ltr">
            <div class="hm-grid">${header}${rows}</div>
            <div class="hm-legend">
                <span>${min}${unit ? ' ' + unit : ''}</span>
                <span class="hm-scale" style="background:linear-gradient(to right, ${stops.join(',')})"></span>
                <span>${max}${unit ? ' ' + unit : ''}</span>
            </div>
        </div>
    `;
}
