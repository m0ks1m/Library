let selectedReaderId = null;

document.addEventListener('DOMContentLoaded', async function () {
    await searchReaders();
});

function getReaderPayload() {
    return {
        firstName: document.getElementById('first-name').value.trim(),
        lastName: document.getElementById('last-name').value.trim(),
        patronymic: document.getElementById('patronymic').value.trim(),
        birthdate: document.getElementById('birthdate').value,
        phone: normalizePhone(document.getElementById('phone').value),
        email: document.getElementById('email').value.trim(),
        city: document.getElementById('city').value.trim(),
        street: document.getElementById('street').value.trim(),
        house: document.getElementById('house').value.trim(),
        apartment: document.getElementById('apartment').value.trim(),
        status: document.getElementById('reader-status').value
    };
}

async function saveReader() {
    const readerId = document.getElementById('reader-id').value;
    const payload = getReaderPayload();

    if (!payload.firstName || !payload.lastName || !payload.birthdate || !payload.phone || !payload.email || !payload.city || !payload.street || !payload.house) {
        alert('Заполните обязательные поля');
        return;
    }

    const url = readerId ? `/api/readers/${readerId}` : '/api/readers';
    const method = readerId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        alert(result.error || 'Ошибка сохранения');
        return;
    }

    alert(readerId ? 'Карточка обновлена' : 'Читатель добавлен');
    resetReaderForm();
    await searchReaders();
}

function resetReaderForm() {
    document.getElementById('reader-id').value = '';
    document.getElementById('reader-form-title').textContent = 'Регистрация нового читателя';
    ['first-name', 'last-name', 'patronymic', 'birthdate', 'phone', 'email', 'city', 'street', 'house', 'apartment'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('reader-status').value = 'ACTIVE';
}

async function searchReaders() {
    const query = document.getElementById('search-query')?.value.trim() || '';
    const response = await fetch(`/api/readers?query=${encodeURIComponent(query)}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
        alert(data.error || 'Ошибка поиска читателей');
        return;
    }

    displayReaderResults(data.readers || []);
}

function displayReaderResults(results) {
    const tbody = document.getElementById('readers-table-body');
    tbody.innerHTML = '';

    results.forEach(reader => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${reader.id}</td>
            <td>${reader.ticket_number || '-'}</td>
            <td>${reader.last_name} ${reader.first_name} ${reader.patronymic || ''}</td>
            <td>${reader.phone || '-'}</td>
            <td>${reader.email || '-'}</td>
            <td>${reader.status || '-'}</td>
            <td>${reader.active_issues}</td>
            <td>${reader.overdue_issues}</td>
            <td>${reader.penalty_points}</td>
            <td>
                <button class="btn btn-primary" onclick="openReaderCard(${reader.id})">Карточка</button>
                <button class="btn btn-secondary" onclick="loadReaderToEdit(${reader.id})">Ред.</button>
                <button class="btn btn-danger" onclick="removeReader(${reader.id})">Удалить</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function openReaderCard(readerId) {
    const response = await fetch(`/api/readers/${readerId}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
        alert(data.error || 'Не удалось загрузить карточку читателя');
        return;
    }

    selectedReaderId = readerId;
    const reader = data.reader;
    document.getElementById('reader-card-empty').style.display = 'none';
    document.getElementById('reader-card-content').style.display = 'block';
    document.getElementById('reader-card-ticket').textContent = `№ билета: ${reader.ticket_number || '-'}`;

    document.getElementById('reader-info-grid').innerHTML = `
        <div class="reader-info-item"><div class="reader-info-label">ФИО</div><div class="reader-info-value">${reader.last_name} ${reader.first_name} ${reader.patronymic || ''}</div></div>
        <div class="reader-info-item"><div class="reader-info-label">Контакты</div><div class="reader-info-value">${reader.phone || '-'} / ${reader.email || '-'}</div></div>
        <div class="reader-info-item"><div class="reader-info-label">Дата регистрации</div><div class="reader-info-value">${reader.registered_at || '-'}</div></div>
        <div class="reader-info-item"><div class="reader-info-label">Статус</div><div class="reader-info-value">${reader.status || '-'}</div></div>
        <div class="reader-info-item"><div class="reader-info-label">Активные выдачи</div><div class="reader-info-value">${reader.active_issues}</div></div>
        <div class="reader-info-item"><div class="reader-info-label">Просрочки</div><div class="reader-info-value">${reader.overdue_issues}</div></div>
        <div class="reader-info-item"><div class="reader-info-label">Штрафные баллы</div><div class="reader-info-value">${reader.penalty_points}</div></div>
    `;

    document.getElementById('reader-actions-body').innerHTML = (data.action_history || []).map(item =>
        `<tr><td>${item.created_at}</td><td>${item.action_type}</td><td>${item.details || '-'}</td></tr>`
    ).join('') || '<tr><td colspan="3">Нет записей</td></tr>';

    document.getElementById('reader-penalties-body').innerHTML = (data.penalty_history || []).map(item =>
        `<tr><td>${item.created_at}</td><td>${item.delta_points}</td><td>${item.reason}</td><td>${item.commentary || '-'}</td></tr>`
    ).join('') || '<tr><td colspan="4">Нет записей</td></tr>';

    showTab('reader-card');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.tab[onclick*="reader-card"]').classList.add('active');
}

async function loadReaderToEdit(readerId) {
    const response = await fetch(`/api/readers/${readerId}`);
    const data = await response.json();
    if (!response.ok || !data.success) {
        alert(data.error || 'Не удалось загрузить данные читателя');
        return;
    }

    const r = data.reader;
    document.getElementById('reader-id').value = r.id;
    document.getElementById('reader-form-title').textContent = `Редактирование читателя #${r.id}`;
    document.getElementById('first-name').value = r.first_name || '';
    document.getElementById('last-name').value = r.last_name || '';
    document.getElementById('patronymic').value = r.patronymic || '';
    document.getElementById('birthdate').value = r.date_birth || '';
    document.getElementById('phone').value = formatPhone(r.phone || '');
    document.getElementById('email').value = r.email || '';
    document.getElementById('city').value = r.city || '';
    document.getElementById('street').value = r.street || '';
    document.getElementById('house').value = r.house || '';
    document.getElementById('apartment').value = r.apartment || '';
    document.getElementById('reader-status').value = r.status || 'ACTIVE';

    showTab('add-reader');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.tab[onclick*="add-reader"]').classList.add('active');
}

async function removeReader(readerId) {
    if (!confirm('Удалить карточку читателя?')) return;

    const response = await fetch(`/api/readers/${readerId}`, { method: 'DELETE' });
    const result = await response.json();
    if (!response.ok || !result.success) {
        alert(result.error || 'Ошибка удаления');
        return;
    }

    if (selectedReaderId === readerId) {
        selectedReaderId = null;
        document.getElementById('reader-card-content').style.display = 'none';
        document.getElementById('reader-card-empty').style.display = 'block';
    }

    await searchReaders();
}

async function applyPenaltyChange() {
    if (!selectedReaderId) {
        alert('Сначала выберите читателя');
        return;
    }

    const payload = {
        delta_points: Number(document.getElementById('penalty-delta').value),
        reason: document.getElementById('penalty-reason').value,
        commentary: document.getElementById('penalty-comment').value.trim()
    };

    const response = await fetch(`/api/readers/${selectedReaderId}/penalty`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
        alert(result.error || 'Ошибка изменения штрафных баллов');
        return;
    }

    document.getElementById('penalty-comment').value = '';
    await openReaderCard(selectedReaderId);
    await searchReaders();
}

function resetReaderSearch() {
    document.getElementById('search-query').value = '';
    searchReaders();
}


function normalizePhone(value) {
    const digits = (value || '').replace(/\D/g, '');
    if (digits.length === 11 && (digits[0] === '7' || digits[0] === '8')) {
        return '7' + digits.slice(1);
    }
    return digits;
}

function formatPhone(value) {
    const digits = normalizePhone(value);
    if (digits.length !== 11) return value;
    return `+7 (${digits.slice(1,4)}) ${digits.slice(4,7)}-${digits.slice(7,9)}-${digits.slice(9,11)}`;
}

function attachMasks() {
    const phoneInput = document.getElementById('phone');
    const emailInput = document.getElementById('email');

    phoneInput?.addEventListener('input', () => {
        const digits = normalizePhone(phoneInput.value).slice(0, 11);
        if (digits.length === 0) {
            phoneInput.value = '';
            return;
        }
        const body = digits.slice(1);
        let out = '+7';
        if (body.length > 0) out += ' (' + body.slice(0,3);
        if (body.length >= 3) out += ') ' + body.slice(3,6);
        if (body.length >= 6) out += '-' + body.slice(6,8);
        if (body.length >= 8) out += '-' + body.slice(8,10);
        phoneInput.value = out;
    });

    emailInput?.addEventListener('blur', () => {
        emailInput.value = emailInput.value.trim().toLowerCase();
    });
}

attachMasks();
