async function loadRawData() {
    showLoading(true);
    hideError();
    
    const limit = document.getElementById('data-limit').value;
    
    try {
        const data = await apiRequest(`/data?limit=${limit}`);
        
        document.getElementById('total-records').textContent = data.count;
        document.getElementById('showing-records').textContent = data.data.length;
        
        displayDataTable(data.data);
        showLoading(false);
    } catch (error) {
        showError('Failed to load data. Please check if the API is running.');
    }
}

function displayDataTable(data) {
    const tbody = document.getElementById('data-tbody');
    tbody.innerHTML = '';
    
    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.id}</td>
            <td>${formatDateTime(row.time)}</td>
            <td>${row.temperature}</td>
            <td>${row.windspeed}</td>
            <td>${row.winddirection}° (${getWindDirection(row.winddirection)})</td>
            <td>${row.weathercode}</td>
            <td>${row.is_day ? '☀️ Day' : '🌙 Night'}</td>
        `;
        tbody.appendChild(tr);
    });
}

window.onload = loadRawData;