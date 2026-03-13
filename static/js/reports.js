const reportTitles = {
    'issued-books': 'Отчет по выданным книгам',
    'overdue-books': 'Отчет по просрочкам',
    'readers': 'Отчет по читателям',
    'book-popularity': 'Отчет по популярности книг',
    'penalty-points': 'Отчет по штрафным баллам',
    'write-off': 'Отчет по списанным книгам',
    'new-arrivals': 'Отчет по поступлениям книг'
};

let currentReportRequest = null;

document.addEventListener('DOMContentLoaded', function () {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    document.getElementById('start-date').valueAsDate = firstDay;
    document.getElementById('end-date').valueAsDate = lastDay;
    document.getElementById('period-fields').style.display = 'flex';

    document.getElementById('report-type').addEventListener('change', clearPreview);
});

function buildRequestPayload() {
    return {
        report_type: document.getElementById('report-type').value,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value
    };
}

async function generateReport() {
    const payload = buildRequestPayload();

    if (!payload.report_type) {
        alert('Выберите тип отчета');
        return;
    }

    if (payload.start_date && payload.end_date && new Date(payload.start_date) > new Date(payload.end_date)) {
        alert('Дата начала не может быть позже даты окончания');
        return;
    }

    try {
        const response = await fetch('/api/reports/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (!response.ok || !result.success) {
            alert('Ошибка при формировании предпросмотра: ' + (result.error || response.statusText));
            return;
        }

        currentReportRequest = payload;
        renderReportPreview(result.report);
        setupExportButton();
    } catch (error) {
        console.error(error);
        alert('Произошла ошибка при запросе предпросмотра отчета');
    }
}

function renderReportPreview(report) {
    const reportContainer = document.getElementById('report-results');
    const reportTitle = document.getElementById('report-title');
    const reportContent = document.getElementById('report-content');

    reportTitle.textContent = report.title || reportTitles[report.report_type] || 'Предпросмотр отчета';

    const kpiHtml = (report.kpi || []).map(item => `
        <div class="kpi-card">
            <div class="kpi-value">${item.value}</div>
            <div class="kpi-label">${item.label}</div>
        </div>
    `).join('');

    const headers = (report.columns || []).map(col => `<th>${col}</th>`).join('');
    const rows = (report.rows || []).map(row => `<tr>${row.map(cell => `<td>${cell ?? ''}</td>`).join('')}</tr>`).join('');

    reportContent.innerHTML = `
        <div class="report-meta">
            <span><strong>Тип:</strong> ${reportTitle.textContent}</span>
            ${report.period?.start && report.period?.end ? `<span><strong>Период:</strong> ${report.period.start} — ${report.period.end}</span>` : ''}
            <span><strong>Найдено записей:</strong> ${report.totals?.records || 0}</span>
        </div>
        <div class="kpi-grid">${kpiHtml}</div>
        <div class="table-wrap">
            <table class="report-table">
                <thead><tr>${headers}</tr></thead>
                <tbody>${rows || `<tr><td colspan="${report.columns.length}">Нет данных по выбранным фильтрам</td></tr>`}</tbody>
            </table>
        </div>
    `;

    reportContainer.style.display = 'block';
}

function setupExportButton() {
    const exportOptions = document.getElementById('export-options');
    const downloadButton = document.getElementById('download-report-btn');

    downloadButton.style.display = 'inline-flex';
    exportOptions.style.display = 'flex';

    downloadButton.onclick = async function (event) {
        event.preventDefault();
        if (!currentReportRequest) return;

        const response = await fetch('/api/reports/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentReportRequest)
        });
        const result = await response.json();

        if (!response.ok || !result.success) {
            alert('Ошибка выгрузки отчета: ' + (result.error || response.statusText));
            return;
        }

        window.location.href = result.report_url;
    };
}

function clearPreview() {
    document.getElementById('report-results').style.display = 'none';
    document.getElementById('export-options').style.display = 'none';
}

function resetReportForm() {
    document.getElementById('report-type').value = '';
    document.getElementById('report-results').style.display = 'none';
    document.getElementById('export-options').style.display = 'none';
    currentReportRequest = null;
}
