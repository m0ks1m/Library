import sqlite3
from datetime import date, timedelta

from config import DB_PATH


def fill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON")

        with open('instance/script.sql', encoding='utf-8') as sql_script:
            cursor.executescript(sql_script.read())

        tables_in_delete_order = [
            'write_off_act_item', 'write_off_act', 'book_copy', 'acceptance_act_item', 'acceptance_act',
            'supplier_invoice_item', 'supplier_invoice', 'supplier_contract',
            'reader_action_history', 'reader_penalty_history', 'lading_bill', 'order_request',
            'debiting_act', 'given_book', 'book', 'genre', 'author', 'supplier',
            'reader', 'employee', 'system_settings'
        # Создание таблиц
        with open("instance/script.sql", encoding="utf-8") as sql_script:
            cursor.executescript(sql_script.read())

        # Очищаем таблицы, чтобы повторный запуск fill() не плодил дубли
        tables_in_delete_order = [
            "reader_action_history",
            "reader_penalty_history",
            "lading_bill",
            "order_request",
            "debiting_act",
            "given_book",
            "book",
            "genre",
            "author",
            "supplier",
            "reader",
            "employee",
            "system_settings",
        ]

        for table_name in tables_in_delete_order:
            cursor.execute(f"DELETE FROM {table_name}")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))

        today = date.today()

        employees = [
            ("Иван", "Иванов", "Иванович", "Библиотекарь", "user1", "pass"),
            ("Пётр", "Петров", "Петрович", "Администратор", "user2", "pass"),
            ("Дмитрий", "Смирнов", "Олегович", "Бухгалтер", "user3", "pass"),
        ]
        cursor.executemany("INSERT INTO employee (first_name, last_name, patronymic, position, login, password) VALUES (?, ?, ?, ?, ?, ?)", employees)
        cursor.executemany(
            """
            INSERT INTO employee (first_name, last_name, patronymic, position, login, password)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            employees,
        )

        authors = [
            ("Лев", "Толстой", "Николаевич", "1828", "Россия"),
            ("Фёдор", "Достоевский", "Михайлович", "1821", "Россия"),
            ("Антон", "Чехов", "Павлович", "1860", "Россия"),
            ("Айзек", "Азимов", "", "1920", "США"),
        ]
        cursor.executemany("INSERT INTO author (first_name, last_name, patronymic, birth_year, country) VALUES (?, ?, ?, ?, ?)", authors)
        cursor.executemany(
            """
            INSERT INTO author (first_name, last_name, patronymic, birth_year, country)
            VALUES (?, ?, ?, ?, ?)
            """,
            authors,
        )

        genres = [
            ("Художественная", "Роман"),
            ("Художественная", "Повесть"),
            ("Художественная", "Рассказ"),
            ("Научная", "Фантастика"),
        ]
        cursor.executemany("INSERT INTO genre (genre_type, name) VALUES (?, ?)", genres)
        cursor.executemany(
            """
            INSERT INTO genre (genre_type, name)
            VALUES (?, ?)
            """,
            genres,
        )

        books = [
            ("isbn1", "Война и мир", "1869", 10, 1, 1, "Эксмо"),
            ("isbn2", "Преступление и наказание", "1866", 5, 2, 1, "АСТ"),
            ("isbn3", "Вишнёвый сад", "1904", 8, 3, 3, "Речь"),
            ("isbn4", "Основание", "1951", 7, 4, 4, "Азбука"),
        ]
        cursor.executemany("INSERT INTO book (isbn, name, year, quantity, author_id, genre_id, publishing_house) VALUES (?, ?, ?, ?, ?, ?, ?)", books)

        readers = [
            ("RB-0001", "Алексей", "Сидоров", "Алексеевич", "1990-05-15", "г. Москва, ул. Ленина, д. 1, кв. 10", "Москва", "Ленина", "1", "10", "alex@example.com", "71234567890", str(today - timedelta(days=120)), "ACTIVE", 0),
            ("RB-0002", "Мария", "Кузнецова", "Сергеевна", "1985-08-20", "г. Казань, ул. Гоголя, д. 5, кв. 12", "Казань", "Гоголя", "5", "12", "maria@example.com", "79876543210", str(today - timedelta(days=80)), "ACTIVE", 5),
            ("RB-0003", "Илья", "Орлов", "Петрович", "1994-11-02", "г. Самара, ул. Победы, д. 7, кв. 2", "Самара", "Победы", "7", "2", "ilya@example.com", "79997774411", str(today - timedelta(days=35)), "BLOCKED", 1),
        ]
        cursor.executemany("""
            INSERT INTO reader (ticket_number, first_name, last_name, patronymic, date_birth, address, city, street, house, apartment, email, phone, registered_at, status, penalty_points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, readers)
        cursor.executemany(
            """
            INSERT INTO book (isbn, name, year, quantity, author_id, genre_id, publishing_house)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            books,
        )

        # Даты для тестовых сценариев
        today = date.today()

        # Читатели
        # ВАЖНО: оставляем только новую структуру на 11 полей,
        # потому что INSERT ниже ожидает 11 значений
        readers = [
            (
                "RB-0001",
                "Алексей",
                "Сидоров",
                "Алексеевич",
                "1990-05-15",
                "г. Москва",
                "alex@example.com",
                "71234567890",
                str(today - timedelta(days=120)),
                "ACTIVE",
                0,
            ),
            (
                "RB-0002",
                "Мария",
                "Кузнецова",
                "Сергеевна",
                "1985-08-20",
                "г. Казань",
                "maria@example.com",
                "79876543210",
                str(today - timedelta(days=80)),
                "ACTIVE",
                5,
            ),
            (
                "RB-0003",
                "Илья",
                "Орлов",
                "Петрович",
                "1994-11-02",
                "г. Самара",
                "ilya@example.com",
                "79997774411",
                str(today - timedelta(days=35)),
                "BLOCKED",
                1,
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO reader (
                ticket_number,
                first_name,
                last_name,
                patronymic,
                date_birth,
                address,
                email,
                phone,
                registered_at,
                status,
                penalty_points
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            readers,
        )

        suppliers = [
            ("Книжный мир", "info@knigi.ru", "Сергей Васильев", "+7 (900) 111-22-33", "info@knigi.ru", "Москва, ул. Пушкина, 10", "Надежный поставщик", 1),
            ("Литература", "sales@literatura.ru", "Ольга Петрова", "+7 (901) 222-33-44", "sales@literatura.ru", "Казань, ул. Баумана, 5", "Поставки под заказ", 1),
        ]
        cursor.executemany("INSERT INTO supplier (name, contact, contact_person, phone, email, address, commentary, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", suppliers)

        cursor.execute("INSERT INTO system_settings (standart_rental_period, max_books_per_reader, late_return_penalty) VALUES (?, ?, ?)", (14, 5, 10))

        given_books = [
            (1, str(today - timedelta(days=24)), str(today - timedelta(days=10)), None, 1, 1, 1),
            (1, str(today - timedelta(days=14)), str(today - timedelta(days=7)), str(today - timedelta(days=8)), 2, 1, 2),
            (1, str(today - timedelta(days=3)), str(today + timedelta(days=7)), None, 1, 1, 3),
            (1, str(today - timedelta(days=18)), str(today - timedelta(days=5)), None, 2, 2, 4),
        ]
        cursor.executemany("INSERT INTO given_book (quantity, given_date, return_date, return_date_fact, reader_id, employee_id, book_id) VALUES (?, ?, ?, ?, ?, ?, ?)", given_books)
        cursor.executemany(
            """
            INSERT INTO supplier (name, contact, contact_person)
            VALUES (?, ?, ?)
            """,
            suppliers,
        )

        # Системные настройки
        cursor.execute(
            """
            INSERT INTO system_settings (
                standart_rental_period,
                max_books_per_reader,
                late_return_penalty
            ) VALUES (?, ?, ?)
            """,
            (14, 5, 10),
        )

        # Выданные книги: активные, просроченные и возвращённые
        given_books = [
            # просрочена
            (1, str(today - timedelta(days=24)), str(today - timedelta(days=10)), None, 1, 1, 1),
            # возвращена вовремя
            (1, str(today - timedelta(days=14)), str(today - timedelta(days=7)), str(today - timedelta(days=8)), 2, 1, 2),
            # активная, не просрочена
            (1, str(today - timedelta(days=3)), str(today + timedelta(days=7)), None, 1, 1, 3),
            # просрочена у второго читателя
            (1, str(today - timedelta(days=18)), str(today - timedelta(days=5)), None, 2, 2, 4),
        ]
        cursor.executemany(
            """
            INSERT INTO given_book (
                quantity,
                given_date,
                return_date,
                return_date_fact,
                reader_id,
                employee_id,
                book_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            given_books,
        )

        order_requests = [
            (str(today - timedelta(days=20)), 15, 4, 1),
            (str(today - timedelta(days=12)), 10, 2, 1),
            (str(today - timedelta(days=2)), 6, 1, 2),
        ]
        cursor.executemany("INSERT INTO order_request (date, quantity, book_id, employee_id) VALUES (?, ?, ?, ?)", order_requests)
        cursor.executemany(
            """
            INSERT INTO order_request (date, quantity, book_id, employee_id)
            VALUES (?, ?, ?, ?)
            """,
            order_requests,
        )

        lading_bills = [
            (str(today - timedelta(days=19)), 4, 1, 1),
            (str(today - timedelta(days=11)), 2, 2, 2),
            (str(today - timedelta(days=1)), 1, 3, 1),
        ]
        cursor.executemany("INSERT INTO lading_bill (date, book_id, order_request_id, supplier_id) VALUES (?, ?, ?, ?)", lading_bills)
        cursor.executemany(
            """
            INSERT INTO lading_bill (date, book_id, order_request_id, supplier_id)
            VALUES (?, ?, ?, ?)
            """,
            lading_bills,
        )

        debiting_acts = [
            (str(today - timedelta(days=30)), 1, "Порча обложки и страниц", 3),
            (str(today - timedelta(days=9)), 2, "Утеря экземпляров", 2),
            (str(today - timedelta(days=4)), 1, "Дефект печати", 1),
        ]
        cursor.executemany("INSERT INTO debiting_act (date, quantity, commentary, book_id) VALUES (?, ?, ?, ?)", debiting_acts)

        penalty_history = [
            (2, 3, "overdue", "Просрочка возврата книги", str(today - timedelta(days=9)), 1),
            (2, 2, "rule_violation", "Нарушение правил пользования", str(today - timedelta(days=3)), 2),
            (3, 1, "other", "Ручная корректировка", str(today - timedelta(days=2)), 2),
        ]
        cursor.executemany("INSERT INTO reader_penalty_history (reader_id, delta_points, reason, commentary, created_at, employee_id) VALUES (?, ?, ?, ?, ?, ?)", penalty_history)

        reader_actions = [
            (1, "CREATE", "Создана карточка читателя", str(today - timedelta(days=120)), 1),
            (2, "CREATE", "Создана карточка читателя", str(today - timedelta(days=80)), 1),
            (2, "PENALTY_ADD", "Начислено 3 балла (просрочка)", str(today - timedelta(days=9)), 1),
            (3, "STATUS_CHANGE", "Статус изменен на BLOCKED", str(today - timedelta(days=1)), 2),
        ]
        cursor.executemany("INSERT INTO reader_action_history (reader_id, action_type, details, created_at, employee_id) VALUES (?, ?, ?, ?, ?)", reader_actions)

        contracts = [
            ("CTR-001", str(today - timedelta(days=60)), 1, str(today - timedelta(days=60)), str(today + timedelta(days=305)), "Лимит 500000", "Основной договор"),
            ("CTR-002", str(today - timedelta(days=40)), 2, str(today - timedelta(days=40)), str(today + timedelta(days=200)), "Поставка по заявкам", "Резервный договор"),
        ]
        cursor.executemany("INSERT INTO supplier_contract (contract_number, contract_date, supplier_id, start_date, end_date, terms_note, commentary) VALUES (?, ?, ?, ?, ?, ?, ?)", contracts)

        cursor.execute("INSERT INTO supplier_invoice (invoice_number, invoice_date, supplier_id, contract_id, employee_id, commentary, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?)", ("INV-001", str(today - timedelta(days=10)), 1, 1, 2, "Поставка художественной литературы", 15000))
        cursor.executemany("INSERT INTO supplier_invoice_item (invoice_id, book_id, quantity, unit_price) VALUES (?, ?, ?, ?)", [(1, 1, 5, 1000), (1, 2, 5, 2000)])

        cursor.execute("INSERT INTO acceptance_act (act_number, act_date, supplier_id, contract_id, employee_id, commentary, total_amount, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("ACPT-001", str(today - timedelta(days=8)), 1, 1, 2, "Принято без замечаний", 15000, "CONFIRMED"))
        cursor.executemany("INSERT INTO acceptance_act_item (act_id, book_id, quantity, unit_price) VALUES (?, ?, ?, ?)", [(1, 1, 3, 1000), (1, 2, 2, 2000)])

        copies = [
            ("BC-1-1-1", 1, 1, "AVAILABLE"),
            ("BC-1-1-2", 1, 1, "AVAILABLE"),
            ("BC-1-1-3", 1, 1, "AVAILABLE"),
            ("BC-2-1-1", 2, 1, "AVAILABLE"),
            ("BC-2-1-2", 2, 1, "WRITTEN_OFF"),
        ]
        cursor.executemany("INSERT INTO book_copy (inventory_code, book_id, acceptance_act_id, status) VALUES (?, ?, ?, ?)", copies)

        cursor.execute("INSERT INTO write_off_act (act_number, act_date, basis, employee_id, commentary, status) VALUES (?, ?, ?, ?, ?, ?)", ("WO-001", str(today - timedelta(days=2)), "Износ", 2, "Списан поврежденный экземпляр", "CONFIRMED"))
        cursor.execute("INSERT INTO write_off_act_item (act_id, copy_id, reason) VALUES (?, ?, ?)", (1, 5, 'damage'))
        ]
        cursor.executemany(
            """
            INSERT INTO debiting_act (date, quantity, commentary, book_id)
            VALUES (?, ?, ?, ?)
            """,
            debiting_acts,
        )

        # История штрафных баллов
        penalty_history = [
            (2, 3, "overdue", "Просрочка возврата книги", str(today - timedelta(days=9)), 1),
            (2, 2, "rule_violation", "Нарушение правил пользования", str(today - timedelta(days=3)), 2),
            (3, 1, "other", "Ручная корректировка", str(today - timedelta(days=2)), 2),
        ]
        cursor.executemany(
            """
            INSERT INTO reader_penalty_history (
                reader_id,
                delta_points,
                reason,
                commentary,
                created_at,
                employee_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            penalty_history,
        )

        # История действий по читателям
        reader_actions = [
            (1, "CREATE", "Создана карточка читателя", str(today - timedelta(days=120)), 1),
            (2, "CREATE", "Создана карточка читателя", str(today - timedelta(days=80)), 1),
            (2, "PENALTY_ADD", "Начислено 3 балла (просрочка)", str(today - timedelta(days=9)), 1),
            (3, "STATUS_CHANGE", "Статус изменён на BLOCKED", str(today - timedelta(days=1)), 2),
        ]
        cursor.executemany(
            """
            INSERT INTO reader_action_history (
                reader_id,
                action_type,
                details,
                created_at,
                employee_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            reader_actions,
        )

        conn.commit()
        print("База данных успешно заполнена тестовыми данными!")

    finally:
        conn.close()
