// News page: renders the posts published from the admin panel. Until the
// first post exists the page shows a friendly empty state rather than a
// blank screen.

// Posts are bilingual; show the current language and fall back to the other
// one so a post written in only one language is still readable.
function postText(post, field) {
    const primary = (post[CURRENT_LANG] || {})[field];
    const fallback = (post[CURRENT_LANG === 'fa' ? 'en' : 'fa'] || {})[field];
    return (primary && primary.trim()) ? primary : (fallback || '');
}

function postDate(value) {
    if (!value) return '';
    const date = new Date(value);
    if (isNaN(date)) return '';
    const locale = CURRENT_LANG === 'fa' ? 'fa-IR' : 'en-US';
    return date.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
}

// Posts come from our own admin panel, but they are still rendered as text
// nodes rather than HTML so a stray angle bracket can never inject markup.
function textNode(tag, className, value) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = value;
    return el;
}

function renderPost(post) {
    const article = document.createElement('article');
    article.className = 'card news-item';

    const meta = document.createElement('div');
    meta.className = 'news-meta';
    const date = postDate(post.published_at);
    if (date) meta.appendChild(textNode('span', 'news-date', date));
    if (post.tag) meta.appendChild(textNode('span', 'news-tag', post.tag));
    if (meta.childNodes.length) article.appendChild(meta);

    article.appendChild(textNode('h3', 'news-heading', postText(post, 'title')));

    const summary = postText(post, 'summary');
    if (summary) article.appendChild(textNode('p', 'news-summary', summary));

    // The body keeps the author's line breaks (white-space: pre-line in CSS)
    // and is collapsed behind a toggle so the list stays scannable.
    const body = postText(post, 'body');
    if (body) {
        const bodyEl = textNode('p', 'news-body', body);
        bodyEl.hidden = true;
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'btn btn-secondary news-toggle';
        toggle.textContent = t('news_read_more');
        toggle.addEventListener('click', () => {
            bodyEl.hidden = !bodyEl.hidden;
            toggle.textContent = bodyEl.hidden ? t('news_read_more') : t('news_read_less');
        });
        article.appendChild(bodyEl);
        article.appendChild(toggle);
    }

    return article;
}

function renderEmptyState(container) {
    const card = document.createElement('div');
    card.className = 'card news-empty';
    card.appendChild(textNode('div', 'news-empty-icon', '📰'));
    card.appendChild(textNode('h3', '', t('news_empty_title')));
    card.appendChild(textNode('p', 'page-lead', t('news_empty_body')));
    container.appendChild(card);
}

async function loadNews() {
    showLoading(true);
    hideError();
    loadSiteContent();

    const container = document.getElementById('news-list');
    container.innerHTML = '';

    try {
        const data = await apiRequest('/news');
        showLoading(false);
        const items = data.items || [];
        if (!items.length) {
            renderEmptyState(container);
            return;
        }
        items.forEach(post => container.appendChild(renderPost(post)));
    } catch (error) {
        showLoading(false);
        // An older backend without /news answers 404: that is not an error
        // for the visitor, it just means there is nothing to show yet.
        if (error.status === 404) {
            renderEmptyState(container);
            return;
        }
        showError(t('news_error'));
    }
}

window.onload = loadNews;
