// Live world map: plots every tracked city as a dot on the static
// equirectangular land path from world-map.js. Hover shows name and the
// latest temperature; clicking a dot opens the city dashboard.

function _mapX(lon) { return (lon + 180) / 360 * 1000; }
function _mapY(lat) { return (90 - lat) / 180 * 500; }

function renderCityMap(container, cities) {
    if (!cities.length) {
        container.innerHTML = `<p class="chart-empty">${t('no_cities')}</p>`;
        return;
    }

    const dots = cities.map((city, i) => {
        const x = _mapX(city.longitude).toFixed(1);
        const y = _mapY(city.latitude).toFixed(1);
        return `
            <g class="map-dot" data-index="${i}" transform="translate(${x}, ${y})">
                <circle r="12" class="map-dot-halo"></circle>
                <circle r="5" class="map-dot-core"></circle>
            </g>
        `;
    }).join('');

    container.innerHTML = `
        <div class="map-wrapper">
            <svg class="world-map" viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid meet" role="img">
                <path class="map-land" d="${WORLD_MAP_PATH}"></path>
                ${dots}
            </svg>
            <div class="map-tooltip" id="map-tooltip"></div>
        </div>
    `;

    const wrapper = container.querySelector('.map-wrapper');
    const tooltip = container.querySelector('#map-tooltip');

    container.querySelectorAll('.map-dot').forEach(dot => {
        const city = cities[parseInt(dot.dataset.index, 10)];
        const latest = city.latest || {};
        const temp = latest.temperature !== undefined
            ? `${latest.temperature} C` : t('no_data_yet');
        const wind = latest.windspeed !== undefined ? ` | ${latest.windspeed} km/h` : '';

        dot.addEventListener('mousemove', event => {
            const rect = wrapper.getBoundingClientRect();
            tooltip.innerHTML = `<strong>${city.name}</strong>, ${city.country}<br>${temp}${wind}`;
            tooltip.style.display = 'block';
            let x = event.clientX - rect.left + 14;
            let y = event.clientY - rect.top - 10;
            // keep the tooltip inside the map area
            x = Math.min(x, rect.width - tooltip.offsetWidth - 6);
            y = Math.max(y, 4);
            tooltip.style.left = x + 'px';
            tooltip.style.top = y + 'px';
        });
        dot.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
        });
        dot.addEventListener('click', () => {
            window.location.href = `city.html?city=${encodeURIComponent(city.id)}`;
        });
    });
}
