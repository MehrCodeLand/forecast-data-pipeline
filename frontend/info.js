async function loadInfo() {
    const content = await loadSiteContent();
    if (!content) {
        showError('Could not load site content. Please check if the API is running.');
        return;
    }

    if (content.about_title) {
        document.getElementById('about-title').textContent = content.about_title;
    }
    if (content.about_text) {
        document.getElementById('about-text').textContent = content.about_text;
    }
    if (content.mission_text) {
        document.getElementById('mission-text').textContent = content.mission_text;
    }
    if (content.data_description) {
        document.getElementById('data-description').textContent = content.data_description;
    }
    if (content.contact_email) {
        const link = document.getElementById('contact-email');
        link.textContent = content.contact_email;
        link.href = `mailto:${content.contact_email}`;
    }
}

window.onload = loadInfo;
