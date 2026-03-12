let currentReaderId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadReaders();
});

function saveReader() {
    if (!document.getElementById('pd-consent').checked) {
        alert('Без согласия на обработку ПД регистрация невозможна.');
        return;
    }

    const formData = {
        firstName: document.getElementById('first-name').value.trim(),
        lastName: document.getElementById('last-name').value.trim(),
        patronymic: document.getElementById('patronymic').value.trim(),
        birthdate: document.getElementById('birthdate').value,
        phone: document.getElementById('phone').value,
        email: document.getElementById('email').value.trim(),
        address: document.getElementById('address').value.trim(),
        pdConsent: true
    };

    fetch('/api/readers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    })
        .then(r => r.json().then(j => ({ok: r.ok, body: j})))
        .then(({ok, body}) => {
            if (!ok) throw new Error(body.error || 'Ошибка регистрации');
            alert(`Читатель добавлен. Билет: ${body.ticketNumber}`);
            resetReaderForm();
            showTab('search-reader');
            loadReaders();
        })
        .catch(e => alert(e.message));
}

function resetReaderForm() {
    ['first-name', 'last-name', 'patronymic', 'birthdate', 'phone', 'email', 'address'].forEach(id => {
        document.getElementById(id).value = '';
    });
    document.getElementById('pd-consent').checked = false;
}

function searchReaders() {
    const q = document.getElementById('search-query').value.trim();
    loadReaders(q);
}

function loadReaders(query = '') {
    const url = query ? `/api/readers?query=${encodeURIComponent(query)}` : '/api/readers';
    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Ошибка загрузки');
            renderReaders(data.readers || []);
        })
        .catch(e => alert(e.message));
}

function renderReaders(readers) {
    const tbody = document.getElementById('readers-table-body');
    tbody.innerHTML = '';

    readers.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${r.id}</td>
            <td>${r.ticket_number || '-'}</td>
            <td>${r.last_name} ${r.first_name} ${r.patronymic || ''}</td>
            <td>${r.phone || '-'}</td>
            <td>${r.email || '-'}</td>
            <td>${r.status || '-'}</td>
            <td>${r.active_issues || 0}</td>
            <td>${r.overdue_count || 0}</td>
            <td>${r.penalty_points || 0}</td>
            <td>${r.pd_consent ? 'Да' : 'Нет'}</td>
            <td>
                <button class="btn btn-primary" onclick="openReaderCard(${r.id})">Карточка</button>
                <button class="btn btn-danger" onclick="removeReader(${r.id})">Удалить</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function openReaderCard(readerId) {
    currentReaderId = readerId;
    fetch(`/api/readers/${readerId}/card`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Не удалось загрузить карточку');
            const reader = data.reader;
            const historyRows = (data.history || []).map(h => `<li>${h.created_at}: <b>${h.action_type}</b> — ${h.comment || ''}</li>`).join('');
            const penaltyRows = (data.penalties || []).map(p => `<li>${p.created_at}: ${p.delta_points > 0 ? '+' : ''}${p.delta_points} (${p.reason}) ${p.comment || ''}</li>`).join('');
            document.getElementById('reader-card-content').innerHTML = `
                <p><b>ФИО:</b> ${reader.last_name} ${reader.first_name} ${reader.patronymic || ''}</p>
                <p><b>Билет:</b> ${reader.ticket_number || '-'}</p>
                <p><b>Контакты:</b> ${reader.phone || '-'}, ${reader.email || '-'}</p>
                <p><b>Дата регистрации:</b> ${reader.registered_at || '-'}</p>
                <p><b>Статус:</b> ${reader.status || '-'}</p>
                <p><b>Активные выдачи:</b> ${reader.active_issues || 0}</p>
                <p><b>Просрочки:</b> ${reader.overdue_count || 0}</p>
                <p><b>Штрафные баллы:</b> ${reader.penalty_points || 0}</p>
                <p><b>Согласие на ПД:</b> ${reader.pd_consent ? 'Да' : 'Нет'} (${reader.pd_consent_at || '-'})</p>
                <h4>История действий</h4>
                <ul>${historyRows || '<li>Нет записей</li>'}</ul>
                <h4>История штрафов</h4>
                <ul>${penaltyRows || '<li>Нет записей</li>'}</ul>
            `;
            showModal('reader-card-modal');
        })
        .catch(e => alert(e.message));
}

function applyPenalty() {
    if (!currentReaderId) return;
    const delta = Number(document.getElementById('penalty-delta').value || 0);
    const reason = document.getElementById('penalty-reason').value;
    const comment = document.getElementById('penalty-comment').value;

    fetch(`/api/readers/${currentReaderId}/penalties`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({delta_points: delta, reason, comment})
    })
        .then(r => r.json())
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Ошибка');
            openReaderCard(currentReaderId);
            loadReaders();
        })
        .catch(e => alert(e.message));
}

function removeReader(readerId) {
    if (!confirm('Деактивировать карточку читателя?')) return;
    fetch(`/api/readers/${readerId}`, {method: 'DELETE'})
        .then(r => r.json())
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Ошибка удаления');
            loadReaders();
        })
        .catch(e => alert(e.message));
}
