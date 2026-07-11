async function apiRequest(endpoint) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
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
        return content;
    } catch (error) {
        return null;
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

document.addEventListener('DOMContentLoaded', () => {
    const donate = document.getElementById('donate-link');
    if (donate) {
        donate.addEventListener('click', () => showToast(t('coming_soon')));
    }
});

// PWA: register the service worker so the site can be installed on phones
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js').catch(error => {
            console.error('Service worker registration failed:', error);
        });
    });
}
