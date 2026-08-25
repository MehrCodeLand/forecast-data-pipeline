// Shareable snapshot cards.
//
// Every section of a city dashboard gets a small share button. Clicking it
// renders the values currently on screen into a branded portrait image
// (drawn on a canvas - no external library), previews it, and lets the
// visitor download it or hand it to the phone's native share sheet.

const SHARE_CARD_W = 1080;
const SHARE_CARD_H = 1350;
const SHARE_PAD = 80;

// Accent pairs (highlight, deep) used for the card background gradient, so
// each kind of section is recognisable at a glance.
const SHARE_THEMES = {
    default: ['#8957e5', '#2b1055'],
    air: ['#2ea043', '#07321a'],
    temp: ['#f0883e', '#5a1e05'],
    wind: ['#58a6ff', '#062a4d'],
    records: ['#a371f7', '#2a0a52']
};

// ASCII slug for filenames. Farsi text leaves nothing behind, so callers
// pass an explicit `fileBase` and these results are only used as a fallback.
function shareSlug(value) {
    return String(value || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
}

// Units like "°C" and "µg/m³" are neutral characters: inside a Farsi (RTL)
// canvas they get reordered into "C°". Isolating them keeps them readable.
function ltrIsolate(text) {
    return '⁦' + text + '⁩';
}

// The card is always drawn with the bundled Persian font so Farsi text is
// shaped correctly; waiting for it avoids a first render in a fallback font.
async function ensureShareFonts() {
    if (!document.fonts || !document.fonts.load) return;
    try {
        await Promise.all([
            document.fonts.load('700 88px Vazirmatn'),
            document.fonts.load('600 32px Vazirmatn'),
            document.fonts.load('400 32px Vazirmatn')
        ]);
    } catch (e) {
        // Rendering still works with a fallback font.
    }
}

function shareFont(weight, size) {
    return `${weight} ${size}px Vazirmatn, -apple-system, 'Segoe UI', Arial, sans-serif`;
}

function roundedRect(ctx, x, y, w, h, r) {
    if (ctx.roundRect) {
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, r);
        return;
    }
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
}

// Shrinks the font until the text fits, then ellipsises what still overflows.
function fitText(ctx, text, maxWidth, weight, size, minSize) {
    let current = size;
    ctx.font = shareFont(weight, current);
    while (ctx.measureText(text).width > maxWidth && current > minSize) {
        current -= 2;
        ctx.font = shareFont(weight, current);
    }
    if (ctx.measureText(text).width <= maxWidth) return text;

    let clipped = text;
    while (clipped.length > 1 && ctx.measureText(clipped + '…').width > maxWidth) {
        clipped = clipped.slice(0, -1);
    }
    return clipped + '…';
}

function wrapText(ctx, text, maxWidth, maxLines) {
    const words = String(text).split(/\s+/).filter(Boolean);
    const lines = [];
    let line = '';

    words.forEach(word => {
        const candidate = line ? `${line} ${word}` : word;
        if (ctx.measureText(candidate).width <= maxWidth || !line) {
            line = candidate;
        } else {
            lines.push(line);
            line = word;
        }
    });
    if (line) lines.push(line);

    if (lines.length > maxLines) {
        lines.length = maxLines;
        let last = lines[maxLines - 1];
        while (last.length > 1 && ctx.measureText(last + '…').width > maxWidth) {
            last = last.slice(0, -1);
        }
        lines[maxLines - 1] = last + '…';
    }
    return lines;
}

// Draws the whole card and returns the canvas.
function drawShareCard(payload) {
    const rtl = document.documentElement.dir === 'rtl';
    const canvas = document.createElement('canvas');
    canvas.width = SHARE_CARD_W;
    canvas.height = SHARE_CARD_H;
    const ctx = canvas.getContext('2d');

    const [accent, deep] = SHARE_THEMES[payload.theme] || SHARE_THEMES.default;

    // Background: diagonal gradient plus a soft highlight in the top corner.
    const gradient = ctx.createLinearGradient(0, 0, SHARE_CARD_W, SHARE_CARD_H);
    gradient.addColorStop(0, accent);
    gradient.addColorStop(0.55, deep);
    gradient.addColorStop(1, '#08090d');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, SHARE_CARD_W, SHARE_CARD_H);

    const glowX = rtl ? SHARE_CARD_W * 0.2 : SHARE_CARD_W * 0.8;
    const glow = ctx.createRadialGradient(glowX, 120, 0, glowX, 120, 620);
    glow.addColorStop(0, 'rgba(255,255,255,0.20)');
    glow.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, SHARE_CARD_W, SHARE_CARD_H);

    // All text is anchored to the "start" edge, which canvas flips for RTL.
    ctx.direction = rtl ? 'rtl' : 'ltr';
    ctx.textAlign = 'start';
    ctx.textBaseline = 'alphabetic';
    const startX = rtl ? SHARE_CARD_W - SHARE_PAD : SHARE_PAD;
    const maxWidth = SHARE_CARD_W - SHARE_PAD * 2;

    // ----- header: site name -----
    ctx.fillStyle = 'rgba(255,255,255,0.92)';
    ctx.font = shareFont(700, 40);
    ctx.fillText(fitText(ctx, payload.siteName, maxWidth - 90, 700, 40, 24), startX, 120);

    ctx.strokeStyle = 'rgba(255,255,255,0.22)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(SHARE_PAD, 152);
    ctx.lineTo(SHARE_CARD_W - SHARE_PAD, 152);
    ctx.stroke();

    // ----- section chip -----
    let y = 232;
    if (payload.section) {
        ctx.font = shareFont(600, 30);
        const label = fitText(ctx, payload.section, maxWidth - 60, 600, 30, 20);
        const chipW = ctx.measureText(label).width + 44;
        const chipX = rtl ? startX - chipW : startX;
        ctx.fillStyle = 'rgba(255,255,255,0.16)';
        roundedRect(ctx, chipX, y - 38, chipW, 54, 27);
        ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,0.95)';
        ctx.fillText(label, rtl ? startX - 22 : startX + 22, y);
        y += 96;
    }

    // ----- city / headline -----
    ctx.fillStyle = '#ffffff';
    const headline = fitText(ctx, payload.title, maxWidth, 700, 86, 44);
    ctx.font = shareFont(700, 86);
    ctx.fillText(headline, startX, y + 30);
    y += 74;

    if (payload.subtitle) {
        ctx.fillStyle = 'rgba(255,255,255,0.72)';
        ctx.font = shareFont(400, 34);
        ctx.fillText(fitText(ctx, payload.subtitle, maxWidth, 400, 34, 22), startX, y + 40);
        y += 46;
    }

    // ----- stat tiles: two per row, a lone last one spans the full width -----
    const stats = (payload.stats || []).filter(s => s && s.value !== undefined && s.value !== null);
    const gap = 28;
    const tileH = 196;
    const halfW = (maxWidth - gap) / 2;
    let tileY = y + 70;

    stats.forEach((stat, index) => {
        const isLastAlone = index === stats.length - 1 && stats.length % 2 === 1;
        const wide = isLastAlone;
        const column = index % 2;
        const tileW = wide ? maxWidth : halfW;
        // In RTL the first column starts from the right edge.
        const offset = wide ? 0 : column * (halfW + gap);
        const tileX = rtl ? SHARE_CARD_W - SHARE_PAD - tileW - offset
                          : SHARE_PAD + offset;

        ctx.fillStyle = 'rgba(255,255,255,0.10)';
        roundedRect(ctx, tileX, tileY, tileW, tileH, 26);
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.18)';
        ctx.lineWidth = 2;
        roundedRect(ctx, tileX, tileY, tileW, tileH, 26);
        ctx.stroke();

        const textX = rtl ? tileX + tileW - 32 : tileX + 32;
        const innerW = tileW - 64;

        ctx.fillStyle = 'rgba(255,255,255,0.66)';
        ctx.font = shareFont(400, 28);
        ctx.fillText(fitText(ctx, stat.label, innerW, 400, 28, 18), textX, tileY + 60);

        const value = ltrIsolate(String(stat.value));
        ctx.fillStyle = '#ffffff';
        const valueSize = wide ? 76 : 68;
        const valueText = fitText(ctx, value, innerW, 700, valueSize, 34);
        ctx.font = shareFont(700, valueSize);
        ctx.fillText(valueText, textX, tileY + 140);

        if (stat.unit) {
            const valueWidth = ctx.measureText(valueText).width;
            ctx.fillStyle = 'rgba(255,255,255,0.66)';
            ctx.font = shareFont(400, 28);
            const unitX = rtl ? textX - valueWidth - 12 : textX + valueWidth + 12;
            ctx.fillText(fitText(ctx, ltrIsolate(stat.unit), innerW - valueWidth - 12, 400, 28, 16),
                         unitX, tileY + 140);
        }

        // Move to the next row after the right-hand tile (or a full-width one).
        if (column === 1 || wide) tileY += tileH + gap;
    });

    // ----- optional note (e.g. health advice) -----
    if (payload.note) {
        ctx.fillStyle = 'rgba(255,255,255,0.78)';
        ctx.font = shareFont(400, 30);
        const lines = wrapText(ctx, payload.note, maxWidth, 3);
        lines.forEach((line, i) => ctx.fillText(line, startX, tileY + 44 + i * 44));
    }

    // ----- footer: when it was measured, and where it came from -----
    ctx.fillStyle = 'rgba(255,255,255,0.60)';
    ctx.font = shareFont(400, 28);
    ctx.fillText(fitText(ctx, payload.timestamp || '', maxWidth * 0.6, 400, 28, 18),
                 startX, SHARE_CARD_H - 88);

    ctx.textAlign = 'end';
    const endX = rtl ? SHARE_PAD : SHARE_CARD_W - SHARE_PAD;
    ctx.fillStyle = 'rgba(255,255,255,0.75)';
    ctx.font = shareFont(600, 28);
    ctx.fillText(payload.domain || window.location.host, endX, SHARE_CARD_H - 88);

    return canvas;
}

function canvasToBlob(canvas) {
    return new Promise((resolve, reject) => {
        if (!canvas.toBlob) {
            reject(new Error('toBlob is not supported'));
            return;
        }
        canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('empty blob')), 'image/png');
    });
}

// ----- the share modal -----

function closeShareModal(overlay, objectUrl) {
    overlay.classList.remove('show');
    setTimeout(() => {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        overlay.remove();
    }, 250);
}

async function openShareCard(payload) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay share-overlay';
    overlay.innerHTML = `
        <div class="modal-card share-modal" role="dialog" aria-modal="true" aria-label="${t('share_title')}">
            <button type="button" class="modal-close" aria-label="${t('donate_close')}">&times;</button>
            <h3 class="modal-title">${t('share_title')}</h3>
            <div class="share-preview"><p class="share-status">${t('share_preparing')}</p></div>
            <p class="modal-text share-hint">${t('share_hint')}</p>
            <div class="share-actions"></div>
        </div>
    `;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('show'));

    let objectUrl = null;
    const close = () => closeShareModal(overlay, objectUrl);
    overlay.querySelector('.modal-close').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    const onKey = e => {
        if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onKey); }
    };
    document.addEventListener('keydown', onKey);

    const preview = overlay.querySelector('.share-preview');
    const actions = overlay.querySelector('.share-actions');

    try {
        await ensureShareFonts();
        const canvas = drawShareCard(payload);
        const blob = await canvasToBlob(canvas);
        objectUrl = URL.createObjectURL(blob);

        // Farsi names slug to nothing, so fall back to the caller's ASCII
        // base (city id + section key) and a fixed brand.
        const base = payload.fileBase
            || [shareSlug(payload.title), shareSlug(payload.section)].filter(Boolean).join('-')
            || 'snapshot';
        const filename = `${shareSlug(payload.siteName) || 'havachetor'}-${base}.png`;

        const img = document.createElement('img');
        img.className = 'share-image';
        img.alt = t('share_card_alt');
        img.src = objectUrl;
        preview.innerHTML = '';
        preview.appendChild(img);

        const download = document.createElement('a');
        download.className = 'btn share-download';
        download.textContent = t('share_download');
        download.href = objectUrl;
        download.download = filename;
        actions.appendChild(download);

        // On phones this opens the OS share sheet with the image attached,
        // which is how people actually share these.
        const file = new File([blob], filename, { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            const shareBtn = document.createElement('button');
            shareBtn.type = 'button';
            shareBtn.className = 'btn btn-secondary';
            shareBtn.textContent = t('share_share');
            shareBtn.addEventListener('click', async () => {
                try {
                    await navigator.share({ files: [file], title: payload.title });
                } catch (e) {
                    // The visitor dismissed the sheet; nothing to report.
                }
            });
            actions.appendChild(shareBtn);
        }
    } catch (error) {
        console.error('Share card failed:', error);
        preview.innerHTML = `<p class="share-status">${t('share_failed')}</p>`;
    }
}

// ----- wiring -----

function shareIconMarkup() {
    return `
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
            <line x1="8.6" y1="10.6" x2="15.4" y2="6.4"/>
            <line x1="8.6" y1="13.4" x2="15.4" y2="17.6"/>
        </svg>
    `;
}

// Adds a share button next to a section heading. `factory` is called at click
// time so the card always shows the values currently on the page.
function attachShareButton(heading, factory) {
    if (!heading || heading.parentElement.querySelector('.share-btn')) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'share-btn';
    button.title = t('share');
    button.setAttribute('aria-label', t('share'));
    button.innerHTML = shareIconMarkup();
    button.addEventListener('click', () => {
        const payload = factory();
        if (payload) openShareCard(payload);
    });

    heading.parentElement.insertBefore(button, heading.nextSibling);
}
