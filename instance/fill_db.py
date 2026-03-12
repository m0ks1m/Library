import sqlite3
from config import DB_PATH


def fill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON")

        # Создание таблиц
        with open('instance/script.sql', encoding='utf-8') as sql_script:
            cursor.executescript(sql_script.read())

        # Очищаем таблицы, чтобы повторный запуск fill() не плодил дубли.
        tables_in_delete_order = [
            'lading_bill',
            'order_request',
            'debiting_act',
            'given_book',
            'book',
            'genre',
            'author',
            'supplier',
            'reader',
            'employee',
            'system_settings',
        ]
        for table_name in tables_in_delete_order:
            cursor.execute(f"DELETE FROM {table_name}")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))

        # Сотрудники
        employees = [
            ("Иван", "Иванов", "Иванович", "Библиотекарь", "user1", "pass"),
            ("Пётр", "Петров", "Петрович", "Администратор", "user2", "pass"),
            ("Дмитрий", "Смирнов", "Олегович", "Бухгалтер", "user3", "pass"),
        ]
        cursor.executemany(
            "INSERT INTO employee (first_name, last_name, patronymic, position, login, password) VALUES (?, ?, ?, ?, ?, ?)",
            employees,
        )

        # Авторы
        authors = [
            ("Лев", "Толстой", "Николаевич", "1828", "Россия"),
            ("Фёдор", "Достоевский", "Михайлович", "1821", "Россия"),
            ("Антон", "Чехов", "Павлович", "1860", "Россия"),
            ("Айзек", "Азимов", "", "1920", "США"),
        ]
        cursor.executemany(
            "INSERT INTO author (first_name, last_name, patronymic, birth_year, country) VALUES (?, ?, ?, ?, ?)",
            authors,
        )

        # Жанры
        genres = [
            ("Художественная", "Роман"),
            ("Художественная", "Повесть"),
            ("Художественная", "Рассказ"),
            ("Научная", "Фантастика"),
        ]
        cursor.executemany(
            "INSERT INTO genre (genre_type, name) VALUES (?, ?)",
            genres,
        )

        # Книги
        books = [
            ("isbn1", "Война и мир", "1869", 10, 1, 1, "Эксмо"),
            ("isbn2", "Преступление и наказание", "1866", 5, 2, 1, "АСТ"),
            ("isbn3", "Вишнёвый сад", "1904", 8, 3, 3, "Речь"),
            ("isbn4", "Основание", "1951", 7, 4, 4, "Азбука"),
        ]
        cursor.executemany(
            "INSERT INTO book (isbn, name, year, quantity, author_id, genre_id, publishing_house) VALUES (?, ?, ?, ?, ?, ?, ?)",
            books,
        )

        # Читатели
        readers = [
            ("Алексей", "Сидоров", "Алексеевич", "1990-05-15", "г. Москва", "alex@example.com", "71234567890", 0),
            ("Мария", "Кузнецова", "Сергеевна", "1985-08-20", "г. Казань", "maria@example.com", "79876543210", 2),
        ]
        cursor.executemany(
            "INSERT INTO reader (first_name, last_name, patronymic, date_birth, address, email, phone, penalty_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            readers,
        )

        # Поставщики
        suppliers = [
            ("Книжный мир", "info@knigi.ru", "Сергей Васильев"),
            ("Литература", "sales@literatura.ru", "Ольга Петрова"),
        ]
        cursor.executemany(
            "INSERT INTO supplier (name, contact, contact_person) VALUES (?, ?, ?)",
            suppliers,
        )

        # Системные настройки
        cursor.execute(
            "INSERT INTO system_settings (standart_rental_period, max_books_per_reader, late_return_penalty) VALUES (?, ?, ?)",
            (14, 5, 10),
        )

        # Выданные книги (1 активная, 1 возвращённая)
        given_books = [
            (1, "2024-01-10", "2024-01-24", None, 1, 1, 1),
            (1, "2024-01-01", "2024-01-14", "2024-01-13", 2, 1, 2),
        ]
        cursor.executemany(
            "INSERT INTO given_book (quantity, given_date, return_date, return_date_fact, reader_id, employee_id, book_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            given_books,
        )

        # Заявки на заказ
        order_requests = [
            ("2024-02-01", 15, 4, 1),
            ("2024-02-03", 10, 2, 1),
        ]
        cursor.executemany(
            "INSERT INTO order_request (date, quantity, book_id, employee_id) VALUES (?, ?, ?, ?)",
            order_requests,
        )

        # Накладные
        lading_bills = [
            ("2024-02-10", 4, 1, 1),
            ("2024-02-12", 2, 2, 2),
        ]
        cursor.executemany(
            "INSERT INTO lading_bill (date, book_id, order_request_id, supplier_id) VALUES (?, ?, ?, ?)",
            lading_bills,
        )

        # Акты списания
        debiting_acts = [
            ("2024-01-20", 1, "Порча обложки и страниц", 3),
            ("2024-01-28", 2, "Утеря экземпляров", 2),
        ]
        cursor.executemany(
            "INSERT INTO debiting_act (date, quantity, commentary, book_id) VALUES (?, ?, ?, ?)",
            debiting_acts,
        )

        conn.commit()
        print("База данных успешно заполнена тестовыми данными!")
    finally:
        conn.close()
