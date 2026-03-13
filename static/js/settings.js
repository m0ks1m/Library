// settings.js - Логика страницы настроек

// Показать выбранную вкладку настроек
function showSettingsTab(tabId) {
    document.querySelectorAll('.settings-tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    document.getElementById(tabId).style.display = 'block';
    event.currentTarget.classList.add('active');
}

// Сохранение системных настроек
function saveSystemSettings() {
    const settings = {
        language: document.getElementById('system-language').value,
        backupFrequency: document.getElementById('backup-frequency').value,
        sessionTimeout: document.getElementById('session-timeout').value
    };

    // В реальном приложении здесь будет AJAX запрос
    console.log('Сохранение системных настроек:', settings);
    alert('Системные настройки сохранены');
}

// Сохранение библиотечных настроек
function saveLibrarySettings() {
    const settings = {
        standart_rental_period: document.getElementById('standart_rental_period').value,
        max_books_per_reader: document.getElementById('max_books_per_reader').value,
        late_return_penalty: document.getElementById('late_return_penalty').value,
    };

    fetch('/api/system/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw err; });
        }
        return response.json();
    })
    .then(data => {
        console.log('Успешно сохранено:', data);
        alert('Настройки успешно сохранены!');
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка при сохранении: ' + (error.error || 'Неизвестная ошибка'));
    });
}

// Сохранение пользовательских настроек
function saveUserSettings() {
    const password = document.getElementById('user-password').value;
    const passwordConfirm = document.getElementById('user-password-confirm').value;

    if (password && password !== passwordConfirm) {
        alert('Пароли не совпадают');
        return;
    }

    const settings = {
        name: document.getElementById('user-name').value,
        email: document.getElementById('user-email').value,
        password: password || undefined,
        receiveNotifications: document.getElementById('receive-notifications').checked
    };

    // В реальном приложении здесь будет AJAX запрос
    console.log('Сохранение пользовательских настроек:', settings);
    alert('Пользовательские настройки сохранены');

    if (password) {
        document.getElementById('user-password').value = '';
        document.getElementById('user-password-confirm').value = '';
    }
}

// Отправка формы добавления нового пользователя
function sendNewUserData() {
    const form = document.getElementById('new-user-form');
    if (!form) return;

    const formData = new FormData(form);
    const userData = {
        firstName: formData.get('first_name'),
        lastName: formData.get('last_name'),
        patronymic: formData.get('patronymic'),
        position: formData.get('position'),
        login: formData.get('login'),
        password: formData.get('password')
    };

    fetch('/api/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            alert('Пользователь успешно добавлен');
            form.reset();
        } else {
            alert('Ошибка: ' + (result.message || result.error));
        }
    })
    .catch(error => {
        console.error('Ошибка при отправке:', error);
        alert('Ошибка при отправке данных');
    });
}



// Загрузка настроек при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    // В реальном приложении здесь будет загрузка текущих настроек с сервера
    // loadCurrentSettings();

    // Обработка параметров URL для открытия конкретной вкладки
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');

    if (tab && ['system-settings', 'library-settings', 'user-settings'].includes(tab)) {
        showSettingsTab(tab);
    }

    const addUserBtn = document.getElementById('add-user-btn');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', sendNewUserData);
    }
});
