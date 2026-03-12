const reportTitles = {
    'issued-books': 'Выданные книги',
    'overdue': 'Просрочки',
    'readers': 'Читатели',
    'book-popularity': 'Популярность книг',
    'penalties': 'Штрафные баллы',
    'write-off': 'Списанные книги',
    'arrivals': 'Поступления книг'
};

document.addEventListener('DOMContentLoaded', () => {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    document.getElementById('start-date').valueAsDate = firstDay;
    document.getElementById('end-date').valueAsDate = now;
});

async function generateReport() {
    const reportType = document.getElementById('report-type').value;
    if (!reportType) return alert('Выберите тип отчета');

    const payload = {
        report_type: reportType,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value
    };

    try {
        const response = await fetch('/api/reports/preview', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.error || 'Ошибка построения отчета');

        renderReport(reportType, result.headers, result.rows, result.summary || {});
    } catch (e) {
        alert(e.message);
    }
}

function renderReport(type, headers, rows, summary) {
    document.getElementById('report-results').style.display = 'block';
    document.getElementById('report-title').textContent = `Предпросмотр: ${reportTitles[type] || type}`;

    const kpiBlock = document.getElementById('kpi-block');
    const kpiHtml = Object.keys(summary).map(k => `<div class="metric-card primary"><div class="metric-title">${k}</div><div class="metric-value">${summary[k]}</div></div>`).join('');
    kpiBlock.innerHTML = `<div class="metrics">${kpiHtml}</div>`;

    let tableHtml = '<table class="search-results"><thead><tr>';
    headers.forEach(h => tableHtml += `<th>${h}</th>`);
    tableHtml += '</tr></thead><tbody>';

    rows.forEach(r => {
        tableHtml += '<tr>';
        r.forEach(c => tableHtml += `<td>${c ?? ''}</td>`);
        tableHtml += '</tr>';
    });

    tableHtml += '</tbody></table>';
    document.getElementById('report-content').innerHTML = tableHtml;
}

async function exportReport() {
    const reportType = document.getElementById('report-type').value;
    if (!reportType) return alert('Выберите тип отчета');

    const payload = {
        report_type: reportType,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value
    };

    try {
        const response = await fetch('/api/reports/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.error || 'Ошибка выгрузки');
        window.open(result.report_url, '_blank');
    } catch (e) {
        alert(e.message);
    }
}

function resetReportForm() {
    document.getElementById('report-type').value = '';
    document.getElementById('report-results').style.display = 'none';
}
