import sqlite3
from config import DB_PATH


def _seed_book_copies(cursor):
    cursor.execute("SELECT id, isbn, quantity FROM book ORDER BY id")
    books = cursor.fetchall()
    for book_id, isbn, quantity in books:
        for i in range(1, quantity + 1):
            cursor.execute(
                """
                INSERT INTO book_copy (copy_uid, book_id, status, arrival_date, source_type, source_id, note)
                VALUES (?, ?, 'доступна', date('now', '-120 day'), 'seed', NULL, 'Тестовый экземпляр')
                """,
                (f"{isbn.upper()}-{i:04d}", book_id),
            )


def _recount_book_quantity(cursor):
    cursor.execute(
        """
        UPDATE book
        SET quantity = (
            SELECT COUNT(*) FROM book_copy bc
            WHERE bc.book_id = book.id AND bc.status != 'списана'
        )
        """
    )


def fill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON")

        with open('instance/script.sql', encoding='utf-8') as sql_script:
            cursor.executescript(sql_script.read())

        tables = [
            'writeoff_item', 'writeoff_act', 'acceptance_item', 'acceptance_act',
            'invoice_item', 'invoice', 'supplier_contract', 'lading_bill', 'order_request',
            'debiting_act', 'given_book', 'penalty_operation', 'reader_action_log', 'book_copy',
            'book', 'genre', 'author', 'supplier', 'reader', 'employee', 'system_settings'
        ]
        for t in tables:
            cursor.execute(f"DELETE FROM {t}")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (t,))

        employees = [
            ("Иван", "Иванов", "Иванович", "Библиотекарь", "user1", "pass"),
            ("Пётр", "Петров", "Петрович", "Администратор", "user2", "pass"),
            ("Ольга", "Смирнова", "Алексеевна", "Бухгалтер", "user3", "pass"),
        ]
        cursor.executemany("INSERT INTO employee (first_name, last_name, patronymic, position, login, password) VALUES (?, ?, ?, ?, ?, ?)", employees)

        authors = [
            ("Лев", "Толстой", "Николаевич", "1828", "Россия"),
            ("Фёдор", "Достоевский", "Михайлович", "1821", "Россия"),
            ("Антон", "Чехов", "Павлович", "1860", "Россия"),
            ("Айзек", "Азимов", "", "1920", "США"),
            ("Аркадий", "Стругацкий", "Натанович", "1925", "СССР"),
        ]
        cursor.executemany("INSERT INTO author (first_name, last_name, patronymic, birth_year, country) VALUES (?, ?, ?, ?, ?)", authors)

        genres = [
            ("Художественная", "Роман"),
            ("Художественная", "Повесть"),
            ("Художественная", "Рассказ"),
            ("Научная", "Фантастика"),
        ]
        cursor.executemany("INSERT INTO genre (genre_type, name) VALUES (?, ?)", genres)

        books = [
            ("isbn1", "Война и мир", "1869", 6, 1, 1, "Эксмо", "Классический роман"),
            ("isbn2", "Преступление и наказание", "1866", 5, 2, 1, "АСТ", "Классика"),
            ("isbn3", "Вишнёвый сад", "1904", 4, 3, 3, "Речь", "Пьеса"),
            ("isbn4", "Основание", "1951", 7, 4, 4, "Азбука", "Фантастика"),
            ("isbn5", "Пикник на обочине", "1972", 6, 5, 4, "АСТ", "Фантастическая повесть"),
        ]
        cursor.executemany("INSERT INTO book (isbn, name, year, quantity, author_id, genre_id, publishing_house, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", books)

        _seed_book_copies(cursor)

        readers = [
            ("R-0001", "Алексей", "Сидоров", "Алексеевич", "1990-05-15", "Москва", "alex@example.com", "71234567890", "2024-01-10", "active", 1, "2024-01-10 10:05:00", 2),
            ("R-0002", "Мария", "Кузнецова", "Сергеевна", "1985-08-20", "Казань", "maria@example.com", "79876543210", "2024-02-03", "active", 1, "2024-02-03 12:15:00", 7),
            ("R-0003", "Николай", "Орлов", "Павлович", "2001-04-01", "Самара", "orlov@example.com", "79998887766", "2024-03-01", "blocked", 1, "2024-03-01 09:00:00", 0),
        ]
        cursor.executemany(
            """INSERT INTO reader (ticket_number, first_name, last_name, patronymic, date_birth, address, email, phone, registered_at, status, pd_consent, pd_consent_at, penalty_points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            readers,
        )

        suppliers = [
            ("Книжный мир", "Сергей Васильев", "+7 900 111-11-11", "info@knigi.ru", "Москва, ул. Ленина, 1", "Основной поставщик", 1),
            ("Литература", "Ольга Петрова", "+7 900 222-22-22", "sales@literatura.ru", "Санкт-Петербург, Невский 10", "Региональный", 1),
        ]
        cursor.executemany("INSERT INTO supplier (name, contact_person, phone, email, address, comment, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", suppliers)

        contracts = [
            ("DOG-2024-001", "2024-01-05", 1, "2024-01-05", "2025-01-05", "Поставка художественной литературы", "Ежемесячные поставки"),
            ("DOG-2024-002", "2024-02-10", 2, "2024-02-10", "2025-02-10", "Поставка научной литературы", "По заявкам"),
        ]
        cursor.executemany("INSERT INTO supplier_contract (contract_number, signed_date, supplier_id, start_date, end_date, terms, comment) VALUES (?, ?, ?, ?, ?, ?, ?)", contracts)

        cursor.execute("INSERT INTO system_settings (standart_rental_period, max_books_per_reader, late_return_penalty) VALUES (14, 5, 10)")

        invoices = [
            ("INV-001", "2024-03-01", 1, 1, 1, "Весенняя поставка"),
            ("INV-002", "2024-03-10", 2, 2, 1, "Фантастика"),
        ]
        cursor.executemany("INSERT INTO invoice (invoice_number, date, supplier_id, contract_id, employee_id, comment) VALUES (?, ?, ?, ?, ?, ?)", invoices)
        invoice_items = [
            (1, 1, 3, 500.0), (1, 2, 2, 450.0), (2, 4, 4, 700.0), (2, 5, 2, 680.0)
        ]
        cursor.executemany("INSERT INTO invoice_item (invoice_id, book_id, quantity, price) VALUES (?, ?, ?, ?)", invoice_items)

        acceptance = [
            ("ACT-IN-001", "2024-03-02", 1, 1, 1, "Принято без замечаний", 1),
            ("ACT-IN-002", "2024-03-12", 2, 2, 1, "Частичная поставка", 1),
        ]
        cursor.executemany("INSERT INTO acceptance_act (act_number, date, supplier_id, contract_id, employee_id, comment, confirmed) VALUES (?, ?, ?, ?, ?, ?, ?)", acceptance)
        acceptance_items = [
            (1, 1, 2, 500.0), (1, 3, 1, 300.0), (2, 4, 2, 700.0)
        ]
        cursor.executemany("INSERT INTO acceptance_item (act_id, book_id, quantity, price) VALUES (?, ?, ?, ?)", acceptance_items)

        # добавить экземпляры из актов приёма
        for act_id, book_id, quantity, _ in acceptance_items:
            for i in range(quantity):
                cursor.execute(
                    "INSERT INTO book_copy (copy_uid, book_id, status, arrival_date, source_type, source_id, note) VALUES (?, ?, 'доступна', date('now', '-30 day'), 'acceptance_act', ?, 'Поступление по акту')",
                    (f"ACT{act_id}-B{book_id}-{i+1:03d}", book_id, act_id),
                )

        # выдачи
        cursor.execute("SELECT id FROM book_copy WHERE book_id = 1 AND status='доступна' ORDER BY id LIMIT 1")
        copy_1 = cursor.fetchone()[0]
        cursor.execute("UPDATE book_copy SET status='выдана' WHERE id=?", (copy_1,))

        cursor.execute("SELECT id FROM book_copy WHERE book_id = 4 AND status='доступна' ORDER BY id LIMIT 1")
        copy_2 = cursor.fetchone()[0]
        cursor.execute("UPDATE book_copy SET status='просрочена' WHERE id=?", (copy_2,))

        issues = [
            (1, "2024-03-15", "2024-03-29", None, "", 1, 1, 1, copy_1),
            (1, "2024-02-10", "2024-02-24", "2024-03-01", "С опозданием", 2, 1, 4, copy_2),
        ]
        cursor.executemany(
            "INSERT INTO given_book (quantity, given_date, return_date, return_date_fact, return_comment, reader_id, employee_id, book_id, book_copy_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            issues,
        )

        penalties = [
            (2, 10, 'просрочка', 'Задержка возврата на 6 дней', '2024-03-01 11:00:00', 1),
            (2, -3, 'списание', 'Частичное списание по решению администратора', '2024-03-05 15:00:00', 2),
            (1, 2, 'нарушение правил', 'Повреждение обложки', '2024-03-18 14:20:00', 1),
        ]
        cursor.executemany("INSERT INTO penalty_operation (reader_id, delta_points, reason, comment, created_at, employee_id) VALUES (?, ?, ?, ?, ?, ?)", penalties)

        reader_actions = [
            (1, 'registration', 'Регистрация читателя'),
            (2, 'registration', 'Регистрация читателя'),
            (1, 'issue', 'Выдача книги Война и мир'),
            (2, 'return', 'Возврат книги Основание с просрочкой'),
        ]
        cursor.executemany("INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)", reader_actions)

        # акты списания
        cursor.execute("SELECT id FROM book_copy WHERE status='доступна' ORDER BY id LIMIT 2")
        to_write_off = [x[0] for x in cursor.fetchall()]
        cursor.execute(
            "INSERT INTO writeoff_act (act_number, date, basis, employee_id, comment, confirmed) VALUES ('ACT-OUT-001', '2024-03-20', 'Плановое списание', 2, 'Изношенные экземпляры', 1)"
        )
        writeoff_act_id = cursor.lastrowid
        reasons = ['износ', 'повреждение']
        for idx, copy_id in enumerate(to_write_off):
            cursor.execute("INSERT INTO writeoff_item (act_id, book_copy_id, reason) VALUES (?, ?, ?)", (writeoff_act_id, copy_id, reasons[idx % len(reasons)]))
            cursor.execute("UPDATE book_copy SET status='списана', note='Списана актом ACT-OUT-001' WHERE id=?", (copy_id,))

        # legacy tables for compatibility
        cursor.execute("INSERT INTO order_request (date, quantity, book_id, employee_id) VALUES ('2024-03-01', 4, 4, 1)")
        cursor.execute("INSERT INTO lading_bill (date, book_id, order_request_id, supplier_id) VALUES ('2024-03-03', 4, 1, 2)")
        cursor.execute("INSERT INTO debiting_act (date, quantity, commentary, book_id) VALUES ('2024-03-20', 2, 'Списание по акту ACT-OUT-001', 1)")

        _recount_book_quantity(cursor)

        conn.commit()
        print("База данных успешно заполнена тестовыми данными!")
    finally:
        conn.close()
