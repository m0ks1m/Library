
// Поиск читателя по телефону
async function findReader() {
    const phone = document.getElementById('reader-ticket').value.trim();
    if (!phone) {
        alert('Введите номер телефона читателя');
        return;
    }

    try {
        const response = await fetch(`/api/reader/by-phone?phone=${encodeURIComponent(phone)}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        const readerInfo = document.getElementById('reader-info');
        const createReaderBtn = document.getElementById('create-reader-btn');

        if (!data.exists) {
            readerInfo.style.display = 'none';
            
            if (!createReaderBtn) {
                const btn = document.createElement('button');
                btn.id = 'create-reader-btn';
                btn.className = 'btn btn-primary';
                btn.style.marginTop = '10px';
                btn.style.width = 'auto';
                btn.textContent = 'Создать нового читателя';
                btn.onclick = () => {
                    window.location.href = '/readers';
                };
                
                const formGroup = document.querySelector('#reader-ticket').closest('.form-group');
                formGroup.appendChild(btn);
            }
            
            alert('Читатель с таким телефоном не найден');
            return;
        }

        currentReader = data.reader;
        document.getElementById('reader-name').textContent = 
            `${data.reader.last_name} ${data.reader.first_name} ${data.reader.patronymic || ''}`.trim();
        document.getElementById('reader-phone').textContent = data.reader.phone;
        document.getElementById('reader-penalty-points').textContent = data.reader.penalty_points;
        
        readerInfo.style.display = 'block';
        
        if (createReaderBtn) {
            createReaderBtn.remove();
        }
    } catch (error) {
        console.error('Ошибка при поиске читателя:', error);
        alert('Произошла ошибка при поиске читателя: ' + error.message);
    }
}

// Поиск книги по ISBN или ID
async function findBook() {
    const identifier = document.getElementById('book-isbn').value.trim();
    if (!identifier) {
        alert('Введите ISBN или код книги');
        return;
    }

    try {
        const response = await fetch(`/api/book/by-identifier?identifier=${encodeURIComponent(identifier)}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentBook = data.book;
        document.getElementById('book-title').textContent = data.book.title;
        document.getElementById('book-author').textContent = data.book.author;
        document.getElementById('book-year').textContent = data.book.year;
        document.getElementById('book-publishing_house').textContent = data.book.publishing_house;

        
        document.getElementById('book-info').style.display = 'block';
        
        
    } catch (error) {
        console.error('Ошибка при поиске книги:', error);
        alert('Произошла ошибка при поиске книги: ' + error.message);
    }
}

// Выдача книги
async function issueBook() {
    if (!currentReader || !currentBook) {
        alert('Необходимо найти читателя и книгу');
        return;
    }

    const issueDate = document.getElementById('issue-date').value;
    const returnDate = document.getElementById('return-date').value;

    if (!issueDate || !returnDate) {
        alert('Заполните даты выдачи и возврата');
        return;
    }

    try {
        const response = await fetch('/api/book/issue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                reader_id: currentReader.id,
                book_id: currentBook.id,
                issue_date: issueDate,
                return_date: returnDate
            })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        alert('Книга успешно выдана!');
        resetIssueForm();
    } catch (error) {
        console.error('Ошибка при выдаче книги:', error);
        alert('Произошла ошибка при выдаче книги: ' + error.message);
    }
}

// Сброс формы выдачи
function resetIssueForm() {
    document.getElementById('reader-ticket').value = '';
    document.getElementById('reader-info').style.display = 'none';
    document.getElementById('book-isbn').value = '';
    document.getElementById('book-info').style.display = 'none';
    document.getElementById('issue-notes').value = '';
    
    const createReaderBtn = document.getElementById('create-reader-btn');
    if (createReaderBtn) {
        createReaderBtn.remove();
    }
    
    currentReader = null;
    currentBook = null;
    
    // Сброс дат
    document.getElementById('issue-date').value = '';
    document.getElementById('return-date').value = '';
    document.getElementById('return-date').readOnly = false;
}


// Глобальная переменная для хранения стандартного периода выдачи
let standartRentalPeriod = 10; // Значение по умолчанию

// Загрузка системных настроек при загрузке страницы
async function loadSystemSettings() {
    try {
        const response = await fetch('/api/system/get');
        const data = await response.json();
        
        if (data.system_settings.standart_rental_period) {
            standartRentalPeriod = data.system_settings.standart_rental_period;
        }
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
    }
}

// Обновление даты возврата при изменении даты выдачи
function updateReturnDate() {
    const issueDateInput = document.getElementById('issue-date');
    const returnDateInput = document.getElementById('return-date');
    
    if (!issueDateInput.value) return;
    
    const issueDate = new Date(issueDateInput.value);
    const returnDate = new Date(issueDate);
    returnDate.setDate(issueDate.getDate() + standartRentalPeriod);
    
    returnDateInput.valueAsDate = returnDate;
}

// Инициализация при загрузке страницы
window.addEventListener('DOMContentLoaded', async () => {
    await loadSystemSettings();
    
    // Установка начальных дат
    const today = new Date();
    document.getElementById('issue-date').valueAsDate = today;
    updateReturnDate();
    
    // Назначение обработчика изменения даты выдачи
    document.getElementById('issue-date').addEventListener('change', updateReturnDate);
});

// Глобальные переменные для возврата
let returnReader = null;
let returnBookRecord = null;

// Поиск читателя для возврата
async function findReaderForReturn() {
    const phone = document.getElementById('return-reader-phone').value.trim();
    if (!phone) {
        alert('Введите номер телефона читателя');
        return;
    }

    try {
        const response = await fetch(`/api/reader/by-phone?phone=${encodeURIComponent(phone)}`);
        const data = await response.json();

        if (data.error || !data.exists) {
            throw new Error(data.error || 'Читатель не найден');
        }

        returnReader = data.reader;
        document.getElementById('return-reader-name').textContent = 
            `${data.reader.last_name} ${data.reader.first_name} ${data.reader.patronymic || ''}`.trim();
        document.getElementById('return-reader-phone-display').textContent = data.reader.phone;
        document.getElementById('return-reader-info').style.display = 'block';
        
    } catch (error) {
        console.error('Ошибка при поиске читателя:', error);
        alert('Произошла ошибка: ' + error.message);
    }
}

// Поиск книги для возврата
async function findBookForReturn() {
    if (!returnReader) {
        alert('Сначала найдите читателя');
        return;
    }

    const isbn = document.getElementById('return-book-isbn').value.trim();
    if (!isbn) {
        alert('Введите ISBN книги');
        return;
    }

    try {
        const response = await fetch(`/api/book/find-for-return?reader_id=${returnReader.id}&isbn=${encodeURIComponent(isbn)}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        returnBookRecord = data;
        document.getElementById('return-book-title').textContent = data.book_title;
        document.getElementById('return-book-author').textContent = data.book_author;
        document.getElementById('return-issue-date').textContent = formatDate(data.issue_date);
        document.getElementById('return-planned-date').textContent = formatDate(data.planned_return_date);
        document.getElementById('return-record-id').value = data.record_id;
        
        // Проверка просрочки
        const today = new Date();
        const plannedDate = new Date(data.planned_return_date);
        
        if (today > plannedDate) {
            const diffDays = Math.floor((today - plannedDate) / (1000 * 60 * 60 * 24));
            document.getElementById('debt-message').textContent = 
                `Просрочка: ${diffDays} дней (планировалось вернуть ${formatDate(data.planned_return_date)})`;
            document.getElementById('debt-notice').style.display = 'block';
        }
        
        document.getElementById('actual-return-date').valueAsDate = today;
        document.getElementById('return-book-info').style.display = 'block';
        document.getElementById('return-btn').disabled = false;
        
    } catch (error) {
        console.error('Ошибка при поиске книги:', error);
        alert('Произошла ошибка: ' + error.message);
    }
}

// Обработка возврата книги
async function processReturn() {
    if (!returnReader || !returnBookRecord) {
        alert('Необходимо найти читателя и книгу');
        return;
    }

    const actualReturnDate = document.getElementById('actual-return-date').value;

    if (!actualReturnDate) {
        alert('Укажите фактическую дату возврата');
        return;
    }

    if (!confirm('Подтвердить возврат книги?')) {
        return;
    }

    try {
        const response = await fetch('/api/book/return', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                record_id: returnBookRecord.record_id,
                actual_return_date: actualReturnDate
            })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        alert('Книга успешно возвращена!');
        clearReturnForm();
    } catch (error) {
        console.error('Ошибка при возврате книги:', error);
        alert('Произошла ошибка: ' + error.message);
    }
}

// Очистка формы возврата
function clearReturnForm() {
    document.getElementById('return-reader-phone').value = '';
    document.getElementById('return-reader-info').style.display = 'none';
    document.getElementById('return-book-isbn').value = '';
    document.getElementById('return-book-info').style.display = 'none';
    document.getElementById('actual-return-date').value = '';
    document.getElementById('return-notes').value = '';
    document.getElementById('return-btn').disabled = true;
    document.getElementById('debt-notice').style.display = 'none';
    
    returnReader = null;
    returnBookRecord = null;
}

// Форматирование даты (используется и в выдаче и в возврате)
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU');
}
