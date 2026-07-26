// Payment result page. The backend redirects here after verifying the
// payment with Zibal, passing the outcome in the query string. This page
// only *displays* that outcome - the authoritative record lives server-side.

(function () {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status') || 'failed';
    const amount = params.get('amount');
    const ref = params.get('ref');
    const track = params.get('track');

    const icons = { success: '✓', pending: '…', failed: '×' };
    const titleKeys = {
        success: 'pay_success_title',
        pending: 'pay_pending_title',
        failed: 'pay_failed_title'
    };
    const messageKeys = {
        success: 'pay_success_msg',
        pending: 'pay_pending_msg',
        failed: 'pay_failed_msg'
    };

    loadSiteContent();

    const iconEl = document.getElementById('payment-icon');
    iconEl.textContent = icons[status] || icons.failed;
    iconEl.className = 'payment-icon payment-' + (icons[status] ? status : 'failed');

    document.getElementById('payment-title').textContent = t(titleKeys[status] || titleKeys.failed);
    document.getElementById('payment-message').textContent = t(messageKeys[status] || messageKeys.failed);

    const details = document.getElementById('payment-details');
    let html = '';
    if (amount) {
        const locale = CURRENT_LANG === 'fa' ? 'fa-IR' : 'en-US';
        html += `<p>${t('pay_amount')} <span>${Number(amount).toLocaleString(locale)} ${t('toman')}</span></p>`;
    }
    if (ref) html += `<p>${t('pay_ref')} <span>${ref}</span></p>`;
    if (track) html += `<p>${t('pay_track')} <span>${track}</span></p>`;
    details.innerHTML = html;
})();
