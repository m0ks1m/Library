// Массив для хранения книг (временное решение)
let books = [];

document.addEventListener('DOMContentLoaded', function() {

    // Проверка параметров URL
    const urlParams = new URLSearchParams(window.location.search);
    const action = urlParams.get('action');

    if (action === 'search') {
        document.querySelector('.tab[onclick*="search-book"]').click();
    }
});

// Сохранение книги
function saveBook() {
    if (!validateForm('add-book-form')) return;

    const book = {
        id: Date.now(),
        title: document.getElementById('title').value,
        author: document.getElementById('author').value,
        isbn: document.getElementById('isbn').value,
        year: document.getElementById('year').value,
        genre: document.getElementById('genre').value,
        quantity: document.getElementById('quantity').value,
        available: document.getElementById('quantity').value,
        location: document.getElementById('location').value,
        description: document.getElementById('description').value,
        cover: document.getElementById('cover-preview').src || ''
    };

    // В реальном приложении здесь будет AJAX запрос
    books.push(book);
    alert('Книга успешно добавлена!');
    resetBookForm();
}

// Сброс формы добавления книги
function resetBookForm() {
    document.getElementById('title').value = '';
    document.getElementById('author').value = '';
    document.getElementById('isbn').value = '';
    document.getElementById('year').value = '';
    document.getElementById('genre').value = '';
    document.getElementById('quantity').value = '1';
    document.getElementById('location').value = '';
    document.getElementById('description').value = '';
    document.getElementById('cover-preview').style.display = 'none';
    document.getElementById('cover-preview').src = '#';
    document.querySelector('.cover-upload i').style.display = 'block';
    document.querySelector('.cover-upload span').textContent = 'Загрузите обложку книги';
}

let allBooks = []; // Глобальная переменная для хранения всех книг

// Загружаем все книги при загрузке страницы
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/books/all');
        const data = await response.json();
        if (data.success) {
            allBooks = data.books;
        }
    } catch (error) {
        console.error('Ошибка при загрузке книг:', error);
    }
});

// Функция поиска книг с фильтрацией
function searchBooks() {
    const title = document.getElementById('search-title').value.toLowerCase();
    const author = document.getElementById('search-author').value.toLowerCase();
    const genre = document.getElementById('search-genre').value;
    const isbn = document.getElementById('search-isbn').value.toLowerCase();

    // Фильтрация книг
    const filteredBooks = allBooks.filter(book => {
        const matchesTitle = title === '' || book.title.toLowerCase().includes(title);
        const matchesAuthor = author === '' || book.author.toLowerCase().includes(author);
        const matchesGenre = genre === '' || book.genre.toLowerCase() === genre.toLowerCase();
        const matchesIsbn = isbn === '' || (book.isbn && book.isbn.toLowerCase().includes(isbn));
        
        return matchesTitle && matchesAuthor && matchesGenre && matchesIsbn;
    });

    displaySearchResults(filteredBooks);
}

// Функция сброса поиска
function resetSearch() {
    document.getElementById('search-title').value = '';
    document.getElementById('search-author').value = '';
    document.getElementById('search-genre').value = '';
    document.getElementById('search-isbn').value = '';
    displaySearchResults(allBooks);
}

// Отображение результатов
function displaySearchResults(results) {
    const tbody = document.getElementById('books-table-body');
    tbody.innerHTML = '';

    if (results.length === 0) {
        document.getElementById('search-results').style.display = 'none';
        alert('Книги не найдены');
        return;
    }

    results.forEach(book => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${book.title}</td>
            <td>${book.author}</td>
            <td>${book.genre}</td>
            <td>${book.quantity}</td>
            <td>${book.available}</td>
            <td>${book.publishing_house || 'Не указано'}</td>
            <td class="actions">
                <button class="btn btn-danger" onclick="showWriteOffModal(${book.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('search-results').style.display = 'block';
}


// Списание книги
function showWriteOffModal(bookId) {
    currentBookId = bookId;
    showModal('write-off-modal');
}

function confirmWriteOff() {
    const reason = document.getElementById('write-off-reason').value;
    const comment = document.getElementById('write-off-comment').value;

    if (!reason) {
        alert('Укажите причину списания');
        return;
    }

    // В реальном приложении здесь будет AJAX запрос
    books = books.filter(book => book.id !== currentBookId);
    alert('Книга списана');
    hideModal('write-off-modal');
    searchBooks(); // Обновляем результаты поиска
}


// Проверка книги по ISBN
async function checkBookByISBN() {
    const isbn = document.getElementById('isbn').value.trim();
    if (!isbn) return;

    try {
        const response = await fetch(`/api/book/check-isbn?isbn=${encodeURIComponent(isbn)}`);
        const data = await response.json();

        if (data.exists) {
            // Автозаполнение полей если книга найдена
            document.getElementById('title').value = data.book.name || '';
            document.getElementById('author').value = data.author_name || '';
            document.getElementById('year').value = data.book.year || '';
            document.getElementById('publishing_house').value = data.book.publishing_house || '';
            document.getElementById('genre').value = data.genre_id || '';
            document.getElementById('description').value = data.book.description || '';
        }
    } catch (error) {
        console.error('Ошибка при проверке ISBN:', error);
    }
}

// Сохранение книги
async function saveBook() {
    const title = document.getElementById('title').value.trim();
    const author = document.getElementById('author').value.trim();
    const isbn = document.getElementById('isbn').value.trim();
    const year = document.getElementById('year').value.trim();
    const genre = document.getElementById('genre').value;
    const quantity = document.getElementById('quantity').value;
    const publishingHouse = document.getElementById('publishing_house').value.trim();

    if (!title || !author || !genre || !quantity || !publishingHouse) {
        alert('Заполните все обязательные поля');
        return;
    }

    try {
        const response = await fetch('/api/book/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title,
                author,
                isbn,
                year,
                genre,
                quantity,
                publishing_house: publishingHouse
            })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        alert('Книга успешно добавлена!');
        resetBookForm();
    } catch (error) {
        console.error('Ошибка при добавлении книги:', error);
        alert('Произошла ошибка: ' + error.message);
    }
}

// Сброс формы
function resetBookForm() {
    document.getElementById('title').value = '';
    document.getElementById('author').value = '';
    document.getElementById('isbn').value = '';
    document.getElementById('year').value = '';
    document.getElementById('genre').value = '';
    document.getElementById('quantity').value = '1';
    document.getElementById('publishing_house').value = '';
    document.getElementById('description').value = '';
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Проверка ISBN при изменении
    document.getElementById('isbn').addEventListener('change', checkBookByISBN);
});