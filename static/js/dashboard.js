document.addEventListener('DOMContentLoaded', function() {
    // Загрузка данных для dashboard
    loadMetrics();
    loadNotifications();
});

// Загрузка показателей с реальными данными
function loadMetrics() {
    const metricsContainer = document.querySelector('.metrics');
    
    // Показываем заглушку загрузки
    metricsContainer.innerHTML = `
        <div class="metric-loading">
            <div class="loading-spinner"></div>
            <span>Загрузка данных...</span>
        </div>
    `;
    
    // Делаем AJAX-запрос к API
    const xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/metrics', true);
    
    xhr.onload = function() {
        if (xhr.status === 200) {
            try {
                const metrics = JSON.parse(xhr.responseText);
                renderMetrics(metrics);
            } catch (e) {
                showMetricsError('Ошибка обработки данных');
            }
        } else {
            showMetricsError('Ошибка сервера: ' + xhr.status);
        }
    };
    
    xhr.onerror = function() {
        showMetricsError('Ошибка соединения');
    };
    
    xhr.send();
    
    // Функция отрисовки метрик
    function renderMetrics(metrics) {
        metricsContainer.innerHTML = '';
        
        metrics.forEach(metric => {
            const metricCard = document.createElement('div');
            metricCard.className = `metric-card ${metric.class}`;
            metricCard.innerHTML = `
                <div class="metric-title">${metric.title}</div>
                <div class="metric-value">${metric.value}</div>
            `;
            metricsContainer.appendChild(metricCard);
        });
    }
    
    // Функция показа ошибки
    function showMetricsError(message) {
        metricsContainer.innerHTML = `
            <div class="metric-error">
                ${message}
                <button onclick="loadMetrics()">⟳ Обновить</button>
            </div>
        `;
    }
}

// // Загрузка уведомлений
// function loadNotifications() {
//     // В реальном приложении здесь будет AJAX запрос
//     const notifications = [
//         {
//             type: 'danger',
//             icon: 'exclamation',
//             title: '15 книг требуют срочного списания',
//             time: 'Сегодня, 10:45'
//         },
//         {
//             type: 'warning',
//             icon: 'clock',
//             title: '42 книги с истекающим сроком возврата',
//             time: 'Вчера, 16:30'
//         },
//         {
//             type: 'info',
//             icon: 'bookmark',
//             title: '7 новых запросов на бронирование',
//             time: 'Вчера, 14:15'
//         }
//     ];

//     const notificationsContainer = document.querySelector('.notifications');
//     const notificationsList = notificationsContainer.querySelector('.notifications-list') ||
//         document.createElement('div');

//     notificationsList.className = 'notifications-list';
//     notificationsList.innerHTML = '';

//     notifications.forEach(notification => {
//         const notificationItem = document.createElement('div');
//         notificationItem.className = 'notification-item';
//         notificationItem.innerHTML = `
//             <div class="notification-icon ${notification.type}">
//                 <i class="fas fa-${notification.icon}"></i>
//             </div>
//             <div class="notification-content">
//                 <div class="notification-title">${notification.title}</div>
//                 <div class="notification-time">${notification.time}</div>
//             </div>
//         `;
//         notificationsList.appendChild(notificationItem);
//     });

//     if (!notificationsContainer.querySelector('.notifications-list')) {
//         notificationsContainer.appendChild(notificationsList);
//     }
// }
