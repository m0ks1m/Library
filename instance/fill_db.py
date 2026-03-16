import sqlite3
from pathlib import Path
from datetime import date, timedelta

from config import DB_PATH


def fill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON")

        # Создание таблиц
        sql_path = Path(__file__).resolve().parent / "script.sql"
        with open(sql_path, encoding="utf-8") as sql_script:
            cursor.executescript(sql_script.read())

        # Очищаем таблицы, чтобы повторный запуск fill() не плодил дубли
        tables_in_delete_order = [
            "book_copy_history",
            "reader_action_history",
            "reader_penalty_history",
            "writeoff_act_item",
            "writeoff_act",
            "given_book",
            "book_copy",
            "acceptance_act_item",
            "acceptance_act",
            "supply_invoice_item",
            "supply_invoice",
            "supplier_contract",
            "lading_bill",
            "order_request",
            "debiting_act",
            "book",
            "genre",
            "author",
            "supplier",
            "reader",
            "employee",
            "system_settings",
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        for table_name in tables_in_delete_order:
            if table_name not in existing_tables:
                continue
            cursor.execute(f"DELETE FROM {table_name}")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))

        # Сотрудники
        employees = [
            ("Иван", "Иванов", "Иванович", "Библиотекарь", "user1", "pass"),
            ("Пётр", "Петров", "Петрович", "Администратор", "user2", "pass"),
            ("Дмитрий", "Смирнов", "Олегович", "Бухгалтер", "user3", "pass"),
        ]
        cursor.executemany(
            """
            INSERT INTO employee (first_name, last_name, patronymic, position, login, password)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
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
            """
            INSERT INTO author (first_name, last_name, patronymic, birth_year, country)
            VALUES (?, ?, ?, ?, ?)
            """,
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
            """
            INSERT INTO genre (genre_type, name)
            VALUES (?, ?)
            """,
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
                "г. Москва, ул. Арбат, д. 7, кв. 15",
                "Москва",
                "Арбат",
                "7",
                "15",
                "alex@example.com",
                "71234567890",
                str(today - timedelta(days=120)),
                "ACTIVE",
                1,
                0,
            ),
            (
                "RB-0002",
                "Мария",
                "Кузнецова",
                "Сергеевна",
                "1985-08-20",
                "г. Казань, ул. Кремлевская, д. 2, кв. 8",
                "Казань",
                "Кремлевская",
                "2",
                "8",
                "maria@example.com",
                "79876543210",
                str(today - timedelta(days=80)),
                "ACTIVE",
                0,
                5,
            ),
            (
                "RB-0003",
                "Илья",
                "Орлов",
                "Петрович",
                "1994-11-02",
                "г. Самара, ул. Молодогвардейская, д. 14",
                "Самара",
                "Молодогвардейская",
                "14",
                "",
                "ilya@example.com",
                "79997774411",
                str(today - timedelta(days=35)),
                "BLOCKED",
                1,
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
                city,
                street,
                house,
                apartment,
                email,
                phone,
                registered_at,
                status,
                pdn_consent,
                penalty_points
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            readers,
        )

        # Поставщики
        suppliers = [
            ("Книжный мир", "Сергей Васильев", "74951234567", "info@knigi.ru", "Москва", "Тверская", "10", "12", "Надежный партнер", 1),
            ("Литература", "Ольга Петрова", "78431234567", "sales@literatura.ru", "Казань", "Баумана", "5", "", "Региональный поставщик", 1),
        ]
        cursor.executemany(
            """
            INSERT INTO supplier (name, contact_person, phone, email, city, street, house, apartment, comment, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            suppliers,
        )

        # Договоры с поставщиками
        supplier_contracts = [
            ("D-2026-001", str(today - timedelta(days=90)), 1, str(today - timedelta(days=90)), str(today + timedelta(days=275)), "500000", "Основной договор"),
            ("D-2026-002", str(today - timedelta(days=45)), 2, str(today - timedelta(days=45)), str(today + timedelta(days=320)), "Поставка по заявкам", "Гибкие условия"),
        ]
        cursor.executemany(
            """
            INSERT INTO supplier_contract (contract_number, signed_at, supplier_id, start_date, end_date, amount_or_terms, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            supplier_contracts,
        )

        # Накладные и позиции
        invoices = [
            ("INV-001", str(today - timedelta(days=30)), 1, 1, "Иванов И.И.", "Поставка классики", "CONFIRMED"),
            ("INV-002", str(today - timedelta(days=10)), 2, 2, "Петров П.П.", "Новые издания", "CONFIRMED"),
        ]
        cursor.executemany(
            """
            INSERT INTO supply_invoice (invoice_number, invoice_date, supplier_id, contract_id, responsible_person, comment, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            invoices,
        )
        cursor.executemany(
            """
            INSERT INTO supply_invoice_item (invoice_id, book_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
            """,
            [
                (1, 1, 3, 450.0),
                (1, 2, 2, 500.0),
                (2, 3, 4, 350.0),
                (2, 4, 3, 620.0),
            ],
        )

        # Акты приема и позиции
        acceptance_acts = [
            ("ACC-001", str(today - timedelta(days=28)), 1, 1, "Иванов И.И.", "Принято без замечаний", "CONFIRMED"),
            ("ACC-002", str(today - timedelta(days=9)), 2, 2, "Петров П.П.", "Частичная поставка", "CONFIRMED"),
        ]
        cursor.executemany(
            """
            INSERT INTO acceptance_act (act_number, act_date, supplier_id, contract_id, responsible_person, comment, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            acceptance_acts,
        )
        cursor.executemany(
            """
            INSERT INTO acceptance_act_item (act_id, book_id, quantity, unit_price)
            VALUES (?, ?, ?, ?)
            """,
            [
                (1, 1, 3, 450.0),
                (1, 2, 2, 500.0),
                (2, 3, 2, 350.0),
                (2, 4, 2, 620.0),
            ],
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


        # Экземпляры книг
        book_copies = [
            ("CP-0001", 1, 1, "issued", "acceptance_act", 1, str(today - timedelta(days=28)), "На руках у читателя"),
            ("CP-0002", 1, 1, "available", "acceptance_act", 1, str(today - timedelta(days=28)), ""),
            ("CP-0003", 1, 1, "damaged", "acceptance_act", 1, str(today - timedelta(days=28)), "Нужен ремонт"),
            ("CP-0004", 2, 1, "overdue", "acceptance_act", 1, str(today - timedelta(days=28)), "Просроченный возврат"),
            ("CP-0005", 2, 1, "available", "acceptance_act", 1, str(today - timedelta(days=28)), ""),
            ("CP-0006", 3, 2, "lost", "acceptance_act", 2, str(today - timedelta(days=9)), "Утеряно читателем"),
            ("CP-0007", 3, 2, "available", "acceptance_act", 2, str(today - timedelta(days=9)), ""),
            ("CP-0008", 4, 2, "written_off", "acceptance_act", 2, str(today - timedelta(days=9)), "Списано"),
            ("CP-0009", 4, 2, "processing", "acceptance_act", 2, str(today - timedelta(days=9)), "На реставрации"),
            ("CP-0010", 4, 2, "reserved", "acceptance_act", 2, str(today - timedelta(days=9)), "Забронировано"),
        ]
        cursor.executemany(
            """
            INSERT INTO book_copy (copy_uid, book_id, acceptance_act_id, status, source_type, source_id, received_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            book_copies,
        )

        # Привязка активных выдач к экземплярам
        cursor.execute("UPDATE given_book SET book_copy_id = 1 WHERE id = 1")
        cursor.execute("UPDATE given_book SET book_copy_id = 5 WHERE id = 2")
        cursor.execute("UPDATE given_book SET book_copy_id = 7 WHERE id = 3")
        cursor.execute("UPDATE given_book SET book_copy_id = 4 WHERE id = 4")

        # Заявки на заказ
        order_requests = [
            (str(today - timedelta(days=20)), 15, 4, 1),
            (str(today - timedelta(days=12)), 10, 2, 1),
            (str(today - timedelta(days=2)), 6, 1, 2),
        ]
        cursor.executemany(
            """
            INSERT INTO order_request (date, quantity, book_id, employee_id)
            VALUES (?, ?, ?, ?)
            """,
            order_requests,
        )

        # Накладные
        lading_bills = [
            (str(today - timedelta(days=19)), 4, 1, 1),
            (str(today - timedelta(days=11)), 2, 2, 2),
            (str(today - timedelta(days=1)), 1, 3, 1),
        ]
        cursor.executemany(
            """
            INSERT INTO lading_bill (date, book_id, order_request_id, supplier_id)
            VALUES (?, ?, ?, ?)
            """,
            lading_bills,
        )

        # Акты списания
        debiting_acts = [
            (str(today - timedelta(days=30)), 1, "Порча обложки и страниц", 3),
            (str(today - timedelta(days=9)), 2, "Утеря экземпляров", 2),
            (str(today - timedelta(days=4)), 1, "Дефект печати", 1),
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


        # Акты списания (по экземплярам)
        cursor.execute(
            """
            INSERT INTO writeoff_act (act_number, act_date, basis, responsible_person, comment, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("WO-001", str(today - timedelta(days=5)), "Износ фонда", "Смирнов Д.О.", "Списание поврежденного экземпляра", "CONFIRMED"),
        )
        cursor.execute(
            """
            INSERT INTO writeoff_act_item (act_id, book_copy_id, reason)
            VALUES (?, ?, ?)
            """,
            (1, 8, "износ"),
        )

        conn.commit()
        print("База данных успешно заполнена тестовыми данными!")

    finally:
        conn.close()
