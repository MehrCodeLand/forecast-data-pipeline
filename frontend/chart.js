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
