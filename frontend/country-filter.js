// Country filter: a row of chips built from the countries we actually track,
// used on the home page and the cities page to narrow the city list (and the
// map) down to one country.
//
// The English country name is the key, so a selection stays valid when the
// visitor switches language and can be carried in a URL (?country=iran).

function countryKey(city) {
    return (city.country || '').trim().toLowerCase();
}

// Whether this city carries a country name in the language being shown.
// Farsi is the only translation the site has; English is the source text.
function hasCountryTranslation(city) {
    return CURRENT_LANG !== 'fa' || !!(city.country_fa || '').trim();
}

// Countries present in the city list, each with a label in the current
// language and how many cities it holds. Sorted by name.
function collectCountries(cities) {
    const byKey = new Map();
    cities.forEach(city => {
        const key = countryKey(city);
        if (!key) return;

        const existing = byKey.get(key);
        if (!existing) {
            byKey.set(key, {
                key, label: cityCountry(city), count: 1,
                translated: hasCountryTranslation(city),
            });
            return;
        }

        existing.count += 1;
        // Cities of one country can be translated unevenly (an old city with
        // no Farsi name next to a new one that has it). Take the label from
        // a translated city so the chip is not the odd English one out.
        if (!existing.translated && hasCountryTranslation(city)) {
            existing.label = cityCountry(city);
            existing.translated = true;
        }
    });
    return [...byKey.values()].sort((a, b) => a.label.localeCompare(b.label));
}

function filterByCountry(cities, selected) {
    if (!selected || selected === 'all') return cities;
    return cities.filter(city => countryKey(city) === selected);
}

// Renders the chips into `container` and calls onSelect(key) on every change.
// Nothing is rendered for a single country - there would be nothing to filter.
function renderCountryFilter(container, cities, selected, onSelect) {
    if (!container) return;

    const countries = collectCountries(cities);
    if (countries.length < 2) {
        container.innerHTML = '';
        container.hidden = true;
        return;
    }
    container.hidden = false;

    const chips = [{ key: 'all', label: t('country_all'), count: cities.length }, ...countries];

    container.innerHTML = '';
    container.setAttribute('role', 'group');
    container.setAttribute('aria-label', t('country_filter'));

    chips.forEach(entry => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'country-chip' + (entry.key === selected ? ' selected' : '');
        chip.dataset.country = entry.key;
        chip.setAttribute('aria-pressed', entry.key === selected ? 'true' : 'false');

        const label = document.createElement('span');
        label.className = 'country-chip-label';
        label.textContent = entry.label;
        chip.appendChild(label);

        const count = document.createElement('span');
        count.className = 'country-chip-count';
        count.textContent = entry.count;
        chip.appendChild(count);

        chip.addEventListener('click', () => {
            selected = entry.key;
            container.querySelectorAll('.country-chip').forEach(other => {
                const active = other.dataset.country === selected;
                other.classList.toggle('selected', active);
                other.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
            onSelect(selected);
        });

        container.appendChild(chip);
    });
}

// Reads ?country= so a selection can be linked to (the home page's "See all"
// link uses this to open the cities page already filtered).
function countryFromUrl() {
    const value = new URLSearchParams(window.location.search).get('country');
    return value ? value.trim().toLowerCase() : 'all';
}
