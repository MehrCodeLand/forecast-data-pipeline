// Fetch JSON from the API with a timeout and one automatic retry on
// transient failures (network drop, timeout, 5xx). Client errors like 404
// are NOT retried - they are real answers ("no data for this city yet").
async function apiRequest(endpoint, attempt = 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, { signal: controller.signal });
        if (!response.ok) {
            const error = new Error(`HTTP error! status: ${response.status}`);
            error.status = response.status;
            throw error;
        }
        return await response.json();
    } catch (error) {
        const transient = error.status === undefined || error.status >= 500;
        if (transient && attempt < 2) {
            await new Promise(resolve => setTimeout(resolve, 600));
            return apiRequest(endpoint, attempt + 1);
        }
        console.error('API Error:', endpoint, error);
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

function showLoading(show = true) {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.style.display = show ? 'block' : 'none';
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
    showLoading(false);
}

function hideError() {
    const errorDiv = document.getElementById('error');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

// Null-safe display: keeps real zero values visible instead of showing '--'
function fmt(value) {
    return (value === null || value === undefined) ? '--' : value;
}

function getWindDirection(degrees) {
    if (degrees === null || degrees === undefined) {
        return '--';
    }
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
    const index = Math.round(((degrees % 360) + 360) % 360 / 22.5) % 16;
    return directions[index];
}

function formatDateTime(dateString) {
    if (!dateString) {
        return '--';
    }
    const date = new Date(dateString);
    const locale = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'fa') ? 'fa-IR' : 'en-US';
    return date.toLocaleString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Loads admin-managed site content in the current language and applies the
// shared parts (site name, footer). Returns the language block so pages can
// render their own sections. Any field left empty in the current language
// falls back to the other language so a page section is never blank.
async function loadSiteContent() {
    try {
        const full = await apiRequest('/content');
        const primary = full[CURRENT_LANG] || {};
        const fallback = full[CURRENT_LANG === 'fa' ? 'en' : 'fa'] || {};

        const content = {};
        Object.keys({ ...fallback, ...primary }).forEach(key => {
            content[key] = (primary[key] !== undefined && primary[key] !== '')
                ? primary[key] : fallback[key];
        });

        const siteName = document.getElementById('site-name');
        if (siteName && content.site_name) {
            siteName.textContent = content.site_name;
            document.title = content.site_name;
        }
        const footerText = document.getElementById('footer-text');
        if (footerText && content.footer_text) {
            footerText.textContent = content.footer_text;
        }

        // Custom site icon (admin-uploaded data: URL): use it for the browser
        // tab favicon and as a small logo next to the site name in the navbar.
        if (full.icon_data_url) {
            applySiteIcon(full.icon_data_url);
        }
        // Optional payment/checkout URL the coffee modal continues to.
        SITE_DONATE_URL = (typeof full.donate_url === 'string') ? full.donate_url.trim() : '';
        return content;
    } catch (error) {
        return null;
    }
}

// Apply an admin-uploaded icon to the favicon and the navbar brand.
function applySiteIcon(dataUrl) {
    document.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"]')
        .forEach(link => { link.href = dataUrl; });

    const brand = document.querySelector('.nav-brand');
    const siteName = document.getElementById('site-name');
    if (brand && siteName && !document.getElementById('site-logo')) {
        const img = document.createElement('img');
        img.id = 'site-logo';
        img.className = 'site-logo';
        img.alt = '';
        img.src = dataUrl;
        brand.insertBefore(img, siteName);
    }
}

// "Buy me a coffee" is not wired to a payment provider yet; clicking it
// shows a small coming-soon toast. Runs on every page.
function showToast(message) {
    let toast = document.getElementById('app-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast';
        toast.className = 'app-toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

// ----- "Buy me a coffee" modal -----

// Optional checkout URL the modal's Continue button opens (set by the admin
// via Site Content -> donate link). Empty means "coming soon".
let SITE_DONATE_URL = '';

// Coffee tiers. Amounts in Toman; names come from i18n so they localize.
const COFFEE_TIERS = [
    { id: 'espresso', nameKey: 'coffee_espresso', toman: 50000 },
    { id: 'americano', nameKey: 'coffee_americano', toman: 75000 },
    { id: 'coldbrew', nameKey: 'coffee_coldbrew', toman: 100000 }
];

function formatToman(amount) {
    const locale = (typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'fa') ? 'fa-IR' : 'en-US';
    return `${amount.toLocaleString(locale)} ${t('toman')}`;
}

function openDonateModal() {
    let overlay = document.getElementById('donate-overlay');
    if (overlay) { overlay.classList.add('show'); return; }

    overlay = document.createElement('div');
    overlay.id = 'donate-overlay';
    overlay.className = 'modal-overlay';

    const tiers = COFFEE_TIERS.map((tier, i) => `
        <button type="button" class="coffee-tier${i === 0 ? ' selected' : ''}" data-id="${tier.id}">
            <span class="coffee-cup">☕</span>
            <span class="coffee-name">${t(tier.nameKey)}</span>
            <span class="coffee-price">${formatToman(tier.toman)}</span>
        </button>
    `).join('');

    overlay.innerHTML = `
        <div class="modal-card" role="dialog" aria-modal="true" aria-label="${t('donate_title')}">
            <button type="button" class="modal-close" aria-label="${t('donate_close')}">&times;</button>
            <h3 class="modal-title">${t('donate_title')}</h3>
            <p class="modal-text">${t('donate_intro')}</p>
            <p class="modal-text">${t('donate_where')}</p>
            <p class="modal-pick">${t('donate_pick')}</p>
            <div class="coffee-tiers">${tiers}</div>
            <div class="donate-fields">
                <div class="form-field">
                    <label for="donate-first">${t('first_name')}</label>
                    <input type="text" id="donate-first" maxlength="60" autocomplete="given-name">
                </div>
                <div class="form-field">
                    <label for="donate-last">${t('last_name')}</label>
                    <input type="text" id="donate-last" maxlength="60" autocomplete="family-name">
                </div>
            </div>
            <p class="donate-error" id="donate-error"></p>
            <button type="button" class="btn donate-continue" id="donate-continue">${t('donate_continue')}</button>
        </div>
    `;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('show'));

    let selected = COFFEE_TIERS[0].id;
    overlay.querySelectorAll('.coffee-tier').forEach(btn => {
        btn.addEventListener('click', () => {
            selected = btn.dataset.id;
            overlay.querySelectorAll('.coffee-tier').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });

    const close = () => overlay.classList.remove('show');
    overlay.querySelector('.modal-close').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

    const errorEl = overlay.querySelector('#donate-error');
    const continueBtn = overlay.querySelector('#donate-continue');

    continueBtn.addEventListener('click', async () => {
        const first = overlay.querySelector('#donate-first').value.trim();
        const last = overlay.querySelector('#donate-last').value.trim();
        errorEl.textContent = '';

        if (!first || !last) {
            errorEl.textContent = t('donate_name_required');
            return;
        }

        continueBtn.disabled = true;
        continueBtn.textContent = t('donate_redirecting');
        try {
            const res = await fetch(`${API_BASE_URL}/payment/request`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ first_name: first, last_name: last, tier_id: selected })
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                throw new Error(body.detail || `HTTP ${res.status}`);
            }
            const data = await res.json();
            // Hand the visitor over to the Zibal payment page.
            window.location.href = data.payment_url;
        } catch (err) {
            console.error('Payment request failed:', err);
            errorEl.textContent = t('donate_error');
            continueBtn.disabled = false;
            continueBtn.textContent = t('donate_continue');
        }
    });
}

// Attach immediately: scripts sit at the end of the body so the button
// already exists, and this keeps the handler independent of load-event
// timing (the button must always respond to clicks).
(() => {
    const donate = document.getElementById('donate-link');
    if (donate) {
        donate.addEventListener('click', openDonateModal);
    }
})();

// PWA: register the service worker so the site can be installed on phones.
// updateViaCache: 'none' makes the browser re-check sw.js on every visit
// instead of trusting its HTTP cache, so new versions roll out immediately.
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js', { updateViaCache: 'none' })
            .then(registration => registration.update().catch(() => {}))
            .catch(error => {
                console.error('Service worker registration failed:', error);
            });
    });
}
