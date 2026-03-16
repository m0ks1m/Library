from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_cors import CORS
from functools import wraps
import sqlite3
import os
import csv
from datetime import datetime
import re
from instance.fill_db import fill
from config import DB_PATH


app = Flask(__name__)
app.secret_key = 'SECRET'
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

def ensure_database_ready():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    has_employee_table = False
    has_users = False
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employee'")
        has_employee_table = cursor.fetchone() is not None
        if has_employee_table:
            cursor.execute("SELECT COUNT(*) FROM employee")
            has_users = (cursor.fetchone()[0] or 0) > 0
    finally:
        conn.close()

    if not has_employee_table:
        fill()
    elif not has_users:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO employee (first_name, last_name, patronymic, position, login, password)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("Иван", "Иванов", "Иванович", "Библиотекарь", "user1", "pass"),
                ("Пётр", "Петров", "Петрович", "Администратор", "user2", "pass"),
                ("Дмитрий", "Смирнов", "Олегович", "Бухгалтер", "user3", "pass"),
            ]
        )
        conn.commit()
        conn.close()

    # Для авторизации не блокируем вход ошибками миграций раздела поставок.
    ensure_reader_schema()



# Wrapper for role management
def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)  # доступ запрещен
            return f(*args, **kwargs)
        return decorated_view
    return wrapper




def ensure_reader_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reader'")
    if not cursor.fetchone():
        conn.close()
        return

    cursor.execute("PRAGMA table_info(reader)")
    columns = {row[1] for row in cursor.fetchall()}

    if 'ticket_number' not in columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN ticket_number VARCHAR(30)")
    if 'registered_at' not in columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN registered_at TIMESTAMP")
        cursor.execute("UPDATE reader SET registered_at = COALESCE(registered_at, CURRENT_TIMESTAMP)")
    if 'status' not in columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'")
        cursor.execute("UPDATE reader SET status = COALESCE(status, 'ACTIVE')")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reader_penalty_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reader_id INTEGER NOT NULL,
            delta_points INTEGER NOT NULL,
            reason VARCHAR(30) NOT NULL,
            commentary VARCHAR(250),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            employee_id INTEGER,
            FOREIGN KEY (reader_id) REFERENCES reader (id),
            FOREIGN KEY (employee_id) REFERENCES employee (id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reader_action_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reader_id INTEGER NOT NULL,
            action_type VARCHAR(50) NOT NULL,
            details VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            employee_id INTEGER,
            FOREIGN KEY (reader_id) REFERENCES reader (id),
            FOREIGN KEY (employee_id) REFERENCES employee (id)
        )
    """)

    cursor.execute("SELECT id FROM reader WHERE ticket_number IS NULL OR ticket_number = ''")
    for (reader_id,) in cursor.fetchall():
        cursor.execute("UPDATE reader SET ticket_number = ? WHERE id = ?", (f"RB-{reader_id:04d}", reader_id))

    conn.commit()
    conn.close()


def ensure_supply_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(250) NOT NULL,
            contact_person VARCHAR(250),
            phone VARCHAR(50),
            email VARCHAR(250),
            city VARCHAR(100),
            street VARCHAR(150),
            house VARCHAR(30),
            apartment VARCHAR(30),
            comment VARCHAR(250),
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(supplier)")
    supplier_columns = {row[1] for row in cursor.fetchall()}
    migration_columns = {
        'phone': "ALTER TABLE supplier ADD COLUMN phone VARCHAR(50)",
        'email': "ALTER TABLE supplier ADD COLUMN email VARCHAR(250)",
        'city': "ALTER TABLE supplier ADD COLUMN city VARCHAR(100)",
        'street': "ALTER TABLE supplier ADD COLUMN street VARCHAR(150)",
        'house': "ALTER TABLE supplier ADD COLUMN house VARCHAR(30)",
        'apartment': "ALTER TABLE supplier ADD COLUMN apartment VARCHAR(30)",
        'comment': "ALTER TABLE supplier ADD COLUMN comment VARCHAR(250)",
        'is_active': "ALTER TABLE supplier ADD COLUMN is_active INTEGER DEFAULT 1",
        'created_at': "ALTER TABLE supplier ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }
    for column_name, sql in migration_columns.items():
        if column_name not in supplier_columns:
            cursor.execute(sql)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_contract (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number VARCHAR(50) NOT NULL,
            signed_at DATE NOT NULL,
            supplier_id INTEGER NOT NULL,
            start_date DATE,
            end_date DATE,
            amount_or_terms VARCHAR(250),
            comment VARCHAR(250),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES supplier(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supply_invoice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number VARCHAR(50) NOT NULL,
            invoice_date DATE NOT NULL,
            supplier_id INTEGER NOT NULL,
            contract_id INTEGER,
            responsible_person VARCHAR(120),
            comment VARCHAR(250),
            status VARCHAR(20) DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES supplier(id),
            FOREIGN KEY (contract_id) REFERENCES supplier_contract(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supply_invoice_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL DEFAULT 0,
            FOREIGN KEY (invoice_id) REFERENCES supply_invoice(id),
            FOREIGN KEY (book_id) REFERENCES book(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acceptance_act (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_number VARCHAR(50) NOT NULL,
            act_date DATE NOT NULL,
            supplier_id INTEGER NOT NULL,
            contract_id INTEGER,
            responsible_person VARCHAR(120),
            comment VARCHAR(250),
            status VARCHAR(20) DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES supplier(id),
            FOREIGN KEY (contract_id) REFERENCES supplier_contract(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acceptance_act_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL DEFAULT 0,
            FOREIGN KEY (act_id) REFERENCES acceptance_act(id),
            FOREIGN KEY (book_id) REFERENCES book(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_copy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            copy_uid VARCHAR(30) UNIQUE,
            book_id INTEGER NOT NULL,
            acceptance_act_id INTEGER,
            status VARCHAR(20) DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES book(id),
            FOREIGN KEY (acceptance_act_id) REFERENCES acceptance_act(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS writeoff_act (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_number VARCHAR(50) NOT NULL,
            act_date DATE NOT NULL,
            basis VARCHAR(250),
            responsible_person VARCHAR(120),
            comment VARCHAR(250),
            status VARCHAR(20) DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS writeoff_act_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id INTEGER NOT NULL,
            book_copy_id INTEGER NOT NULL,
            reason VARCHAR(40) NOT NULL,
            FOREIGN KEY (act_id) REFERENCES writeoff_act(id),
            FOREIGN KEY (book_copy_id) REFERENCES book_copy(id)
        )
    """)

    cursor.execute("PRAGMA table_info(reader)")
    reader_columns = {row[1] for row in cursor.fetchall()}
    if 'city' not in reader_columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN city VARCHAR(100)")
    if 'street' not in reader_columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN street VARCHAR(150)")
    if 'house' not in reader_columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN house VARCHAR(30)")
    if 'apartment' not in reader_columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN apartment VARCHAR(30)")
    if 'pdn_consent' not in reader_columns:
        cursor.execute("ALTER TABLE reader ADD COLUMN pdn_consent INTEGER DEFAULT 1")

    cursor.execute("PRAGMA table_info(book)")
    book_columns = {row[1] for row in cursor.fetchall()}
    if 'description' not in book_columns:
        cursor.execute("ALTER TABLE book ADD COLUMN description TEXT")

    cursor.execute("PRAGMA table_info(given_book)")
    given_columns = {row[1] for row in cursor.fetchall()}
    if 'book_copy_id' not in given_columns:
        cursor.execute("ALTER TABLE given_book ADD COLUMN book_copy_id INTEGER")
    if 'return_status' not in given_columns:
        cursor.execute("ALTER TABLE given_book ADD COLUMN return_status VARCHAR(20)")
    if 'return_comment' not in given_columns:
        cursor.execute("ALTER TABLE given_book ADD COLUMN return_comment VARCHAR(250)")
    if 'overdue_days' not in given_columns:
        cursor.execute("ALTER TABLE given_book ADD COLUMN overdue_days INTEGER DEFAULT 0")

    cursor.execute("PRAGMA table_info(book_copy)")
    copy_columns = {row[1] for row in cursor.fetchall()}
    copy_migrations = {
        'source_type': "ALTER TABLE book_copy ADD COLUMN source_type VARCHAR(30)",
        'source_id': "ALTER TABLE book_copy ADD COLUMN source_id INTEGER",
        'received_at': "ALTER TABLE book_copy ADD COLUMN received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        'note': "ALTER TABLE book_copy ADD COLUMN note VARCHAR(250)",
    }
    for col, sql in copy_migrations.items():
        if col not in copy_columns:
            cursor.execute(sql)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_copy_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_copy_id INTEGER NOT NULL,
            old_status VARCHAR(20),
            new_status VARCHAR(20) NOT NULL,
            reason VARCHAR(50),
            comment VARCHAR(250),
            reader_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_copy_id) REFERENCES book_copy(id),
            FOREIGN KEY (reader_id) REFERENCES reader(id)
        )
    """)

    conn.commit()
    conn.close()


def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits[0] in ('7', '8'):
        return '7' + digits[1:]
    return digits


COPY_STATUSES = {
    'available',
    'issued',
    'reserved',
    'overdue',
    'damaged',
    'lost',
    'written_off',
    'processing'
}


def log_copy_status(cursor, copy_id, old_status, new_status, reason='', comment='', reader_id=None):
    cursor.execute(
        """
        INSERT INTO book_copy_history (book_copy_id, old_status, new_status, reason, comment, reader_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (copy_id, old_status, new_status, reason, comment, reader_id)
    )




def sync_overdue_copy_statuses(cursor):
    cursor.execute(
        """
        SELECT gb.book_copy_id
        FROM given_book gb
        JOIN book_copy bc ON bc.id = gb.book_copy_id
        WHERE gb.return_date_fact IS NULL
          AND date(gb.return_date) < date('now')
          AND bc.status = 'issued'
        """
    )
    for (copy_id,) in cursor.fetchall():
        cursor.execute("UPDATE book_copy SET status = 'overdue' WHERE id = ?", (copy_id,))
        log_copy_status(cursor, copy_id, 'issued', 'overdue', 'auto_overdue')

def log_reader_action(cursor, reader_id, action_type, details='', employee_id=None):
    cursor.execute(
        "INSERT INTO reader_action_history (reader_id, action_type, details, employee_id) VALUES (?, ?, ?, ?)",
        (reader_id, action_type, details, employee_id)
    )


def log_penalty_change(cursor, reader_id, delta_points, reason, commentary='', employee_id=None):
    cursor.execute(
        "INSERT INTO reader_penalty_history (reader_id, delta_points, reason, commentary, employee_id) VALUES (?, ?, ?, ?, ?)",
        (reader_id, delta_points, reason, commentary, employee_id)
    )

# Главная страница
@app.route('/')
@role_required('Библиотекарь', 'Бухгалтер', 'Администратор')
@login_required
def index():
    return render_template('/index.html', role=current_user.role)

# Страница книг
@app.route('/books')
@role_required('Библиотекарь', 'Администратор')
@login_required
def books_page():
    return render_template('books.html', role=current_user.role)

# Страница со списком читателей
@app.route('/readers')
@role_required('Библиотекарь', 'Администратор')
@login_required
def readers_page():
    return render_template('readers.html', role=current_user.role)

# Страница выдачи и возврата книг
@app.route('/transactions')
@role_required('Библиотекарь', 'Администратор')
@login_required
def transactions_page():
    return render_template('transactions.html', role=current_user.role)

# Страница отчётов
@app.route('/reports')
@role_required('Бухгалтер', 'Администратор')
@login_required
def reports_page():
    return render_template('reports.html', role=current_user.role)

# Страница настроек
@app.route('/settings')
@role_required('Администратор')
@login_required
def settings_page():
    return render_template('settings.html', role=current_user.role, system_settings={'system_settings': get_system_settings_data() or {}})

# Страница поставщиков и поставок
@app.route('/supplies')
@role_required('Библиотекарь', 'Бухгалтер', 'Администратор')
@login_required
def supplies_page():
    ensure_supply_schema()
    return render_template('supplies.html', role=current_user.role)

###############################################################################################

# API Routes

@login_manager.user_loader
def load_user(user_id):
    row = get_user_by_id(user_id)
    if row:
        return type('AnonUser', (UserMixin,), {
            'id': str(row[0]),
            'login': row[1],
            'role': row[3],
            'first_name': row[4],
            'last_name': row[5]
        })()
    return None


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    ensure_database_ready()
    if request.method == 'POST':
        login_ = (request.form.get('login') or request.form.get('username') or '').strip()
        password_ = request.form.get('password', '')
        if not login_ or not password_:
            flash("Неверный логин или пароль")
            return render_template('login.html')
        user = get_user_by_login(login_)
        if user and user[2] == password_:
            user_obj = type('AnonUser', (UserMixin,), {
                'id': str(user[0]),
                'login': user[1],
                'role': user[3]  
            })()
            login_user(user_obj)
            return redirect(url_for('index'))
        flash("Неверный логин или пароль")
    return render_template('login.html')


@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        print(data)

        # Обязательные поля
        required_fields = ['firstName', 'lastName', 'patronymic', 'position', 'login', 'password']
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({"error": "Не заполнены обязательные поля"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Проверка уникальности логина
        cursor.execute("SELECT id FROM employee WHERE login = ?", (data['login'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Пользователь с таким логином уже существует"}), 409

        # Вставка нового пользователя
        cursor.execute('''
            INSERT INTO employee 
            (first_name, last_name, patronymic, position, login, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['firstName'],
            data['lastName'],
            data['patronymic'],
            data['position'],
            data['login'],
            data['password']  
        ))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "message": "Пользователь успешно добавлен",
            "userId": user_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

@app.route('/api/login', methods=['POST'])
def api_login():
    ensure_database_ready()
    data = request.get_json() or {}
    login_ = (data.get('login') or data.get('username') or '').strip()
    password_ = data.get('password')

    user = get_user_by_login(login_)
    if user and user[2] == password_:
        user_obj = type('AnonUser', (UserMixin,), {
            'id': str(user[0]),
            'login': user[1],
            'role': user[3]
        })()
        login_user(user_obj)
        return jsonify({'message': 'Успешный вход'}), 200
    else:
        return jsonify({'message': 'Неверный логин или пароль'}), 401

@app.route('/api/metrics')
def get_metrics():
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        sync_overdue_copy_statuses(cursor)
        conn.commit()

        cursor.execute('SELECT COUNT(*) FROM book')
        book_cards_total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM book_copy')
        copies_total = cursor.fetchone()[0] or 0

        def count_by_status(status):
            cursor.execute('SELECT COUNT(*) FROM book_copy WHERE status = ?', (status,))
            return cursor.fetchone()[0] or 0

        available_copies = count_by_status('available')
        issued_copies = count_by_status('issued')
        overdue_copies = count_by_status('overdue')
        damaged_copies = count_by_status('damaged')
        lost_copies = count_by_status('lost')
        written_off_copies = count_by_status('written_off')

        cursor.execute('SELECT COUNT(*) FROM reader')
        readers_total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM reader WHERE date(registered_at) >= date('now', '-30 days')")
        new_readers_30d = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(DISTINCT reader_id) FROM given_book WHERE return_date_fact IS NULL")
        readers_with_active = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(DISTINCT reader_id) FROM given_book WHERE return_date_fact IS NULL AND date(return_date) < date('now')")
        readers_with_overdue = cursor.fetchone()[0] or 0

        metrics = [
            {"title": "Карточек книг", "value": f"{book_cards_total:,}", "class": "primary"},
            {"title": "Экземпляров всего", "value": f"{copies_total:,}", "class": "primary"},
            {"title": "Доступных", "value": f"{available_copies:,}", "class": "success"},
            {"title": "Выданных", "value": f"{issued_copies:,}", "class": "info"},
            {"title": "Просроченных", "value": f"{overdue_copies:,}", "class": "warning"},
            {"title": "Поврежденных", "value": f"{damaged_copies:,}", "class": "warning"},
            {"title": "Утерянных", "value": f"{lost_copies:,}", "class": "danger"},
            {"title": "Списанных", "value": f"{written_off_copies:,}", "class": "danger"},
            {"title": "Читателей всего", "value": f"{readers_total:,}", "class": "primary"},
            {"title": "Новых за 30 дней", "value": f"{new_readers_30d:,}", "class": "success"},
            {"title": "Читатели с активными выдачами", "value": f"{readers_with_active:,}", "class": "info"},
            {"title": "Читатели с просрочками", "value": f"{readers_with_overdue:,}", "class": "warning"},
        ]

        return jsonify(metrics)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


@app.route('/api/readers', methods=['GET'])
@login_required
def list_readers():
    ensure_reader_schema()
    try:
        query = (request.args.get('query') or '').strip()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = """
            SELECT
                r.id,
                r.ticket_number,
                r.first_name,
                r.last_name,
                r.patronymic,
                r.date_birth,
                r.address,
                r.city,
                r.street,
                r.house,
                r.apartment,
                r.email,
                r.phone,
                r.registered_at,
                r.status,
                r.penalty_points,
                COALESCE(SUM(CASE WHEN gb.return_date_fact IS NULL THEN gb.quantity ELSE 0 END), 0) AS active_issues,
                COALESCE(SUM(CASE WHEN gb.return_date_fact IS NULL AND date(gb.return_date) < date('now') THEN gb.quantity ELSE 0 END), 0) AS overdue_issues
            FROM reader r
            LEFT JOIN given_book gb ON gb.reader_id = r.id
            WHERE 1=1
        """
        params = []
        if query:
            sql += """
                AND (
                    r.id = ?
                    OR r.ticket_number LIKE ?
                    OR (r.last_name || ' ' || r.first_name || ' ' || COALESCE(r.patronymic, '')) LIKE ?
                    OR r.phone LIKE ?
                    OR r.email LIKE ?
                )
            """
            params.extend([query if query.isdigit() else -1, f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])

        sql += """
            GROUP BY r.id, r.ticket_number, r.first_name, r.last_name, r.patronymic, r.date_birth, r.address, r.city, r.street, r.house, r.apartment, r.email, r.phone, r.registered_at, r.status, r.penalty_points
            ORDER BY r.last_name, r.first_name
        """

        cursor.execute(sql, params)
        readers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'readers': readers, 'count': len(readers)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers', methods=['POST'])
@login_required
def add_reader():
    ensure_reader_schema()
    try:
        data = request.get_json() or {}
        required_fields = ['firstName', 'lastName', 'phone', 'city', 'street', 'house', 'email', 'birthdate']
        if not all(data.get(field) for field in required_fields):
            return jsonify({'error': 'Не заполнены обязательные поля'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO reader (first_name, last_name, patronymic, date_birth, phone, address, city, street, house, apartment, email, registered_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (
            data['firstName'].strip(),
            data['lastName'].strip(),
            data.get('patronymic', '').strip(),
            data['birthdate'],
            normalize_phone(data['phone']),
            f"г. {data['city'].strip()}, ул. {data['street'].strip()}, д. {data['house'].strip()}" + (f", кв. {data.get('apartment', '').strip()}" if data.get('apartment') else ''),
            data['city'].strip(),
            data['street'].strip(),
            data['house'].strip(),
            data.get('apartment', '').strip(),
            data['email'].strip().lower(),
            data.get('status', 'ACTIVE')
        ))

        reader_id = cursor.lastrowid
        ticket_number = f"RB-{reader_id:04d}"
        cursor.execute("UPDATE reader SET ticket_number = ? WHERE id = ?", (ticket_number, reader_id))
        log_reader_action(cursor, reader_id, 'CREATE', 'Создана карточка читателя', current_user.id)

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Читатель успешно зарегистрирован', 'readerId': reader_id, 'ticketNumber': ticket_number}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/search', methods=['GET'])
@login_required
def search_readers():
    ensure_reader_schema()
    return list_readers()


@app.route('/api/readers/<int:reader_id>', methods=['GET'])
@login_required
def get_reader_details(reader_id):
    ensure_reader_schema()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        sync_overdue_copy_statuses(cursor)
        conn.commit()

        cursor.execute("""
            SELECT
                r.id,
                r.ticket_number,
                r.first_name,
                r.last_name,
                r.patronymic,
                r.date_birth,
                r.address,
                r.city,
                r.street,
                r.house,
                r.apartment,
                r.email,
                r.phone,
                r.registered_at,
                r.status,
                r.penalty_points,
                COALESCE(SUM(CASE WHEN gb.return_date_fact IS NULL THEN gb.quantity ELSE 0 END), 0) AS active_issues,
                COALESCE(SUM(CASE WHEN gb.return_date_fact IS NULL AND date(gb.return_date) < date('now') THEN gb.quantity ELSE 0 END), 0) AS overdue_issues
            FROM reader r
            LEFT JOIN given_book gb ON gb.reader_id = r.id
            WHERE r.id = ?
            GROUP BY r.id
        """, (reader_id,))
        reader = cursor.fetchone()
        if not reader:
            conn.close()
            return jsonify({'error': 'Читатель не найден'}), 404

        cursor.execute("""
            SELECT date(created_at) AS created_at, action_type, details
            FROM reader_action_history
            WHERE reader_id = ?
            ORDER BY created_at DESC, id DESC
        """, (reader_id,))
        action_history = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT date(created_at) AS created_at, delta_points, reason, commentary
            FROM reader_penalty_history
            WHERE reader_id = ?
            ORDER BY created_at DESC, id DESC
        """, (reader_id,))
        penalty_history = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify({'success': True, 'reader': dict(reader), 'action_history': action_history, 'penalty_history': penalty_history}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/<int:reader_id>', methods=['PUT'])
@login_required
def update_reader(reader_id):
    ensure_reader_schema()
    try:
        data = request.get_json() or {}
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT id, status FROM reader WHERE id = ?', (reader_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            return jsonify({'error': 'Читатель не найден'}), 404

        cursor.execute("""
            UPDATE reader
            SET first_name = ?, last_name = ?, patronymic = ?, date_birth = ?, phone = ?, address = ?, city = ?, street = ?, house = ?, apartment = ?, email = ?, status = ?
            WHERE id = ?
        """, (
            data.get('firstName', '').strip(),
            data.get('lastName', '').strip(),
            data.get('patronymic', '').strip(),
            data.get('birthdate'),
            normalize_phone(data.get('phone')),
            f"г. {data.get('city', '').strip()}, ул. {data.get('street', '').strip()}, д. {data.get('house', '').strip()}" + (f", кв. {data.get('apartment', '').strip()}" if data.get('apartment') else ''),
            data.get('city', '').strip(),
            data.get('street', '').strip(),
            data.get('house', '').strip(),
            data.get('apartment', '').strip(),
            data.get('email', '').strip().lower(),
            data.get('status', 'ACTIVE'),
            reader_id
        ))

        log_reader_action(cursor, reader_id, 'UPDATE', 'Обновлены данные карточки читателя', current_user.id)
        if existing[1] != data.get('status', 'ACTIVE'):
            log_reader_action(cursor, reader_id, 'STATUS_CHANGE', f"Статус изменен на {data.get('status', 'ACTIVE')}", current_user.id)

        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/<int:reader_id>', methods=['DELETE'])
@login_required
def delete_reader(reader_id):
    ensure_reader_schema()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM given_book WHERE reader_id = ? AND return_date_fact IS NULL', (reader_id,))
        active_issues = cursor.fetchone()[0]
        if active_issues > 0:
            conn.close()
            return jsonify({'error': 'Нельзя удалить читателя с активными выдачами'}), 400

        cursor.execute('DELETE FROM reader_penalty_history WHERE reader_id = ?', (reader_id,))
        cursor.execute('DELETE FROM reader_action_history WHERE reader_id = ?', (reader_id,))
        cursor.execute('DELETE FROM reader WHERE id = ?', (reader_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/<int:reader_id>/penalty', methods=['POST'])
@login_required
def change_reader_penalty(reader_id):
    ensure_reader_schema()
    try:
        data = request.get_json() or {}
        delta_points = int(data.get('delta_points', 0))
        reason = data.get('reason', 'other')
        commentary = data.get('commentary', '')

        if delta_points == 0:
            return jsonify({'error': 'Значение изменения штрафных баллов не может быть 0'}), 400

        allowed_reasons = {'overdue', 'book_damage', 'book_loss', 'rule_violation', 'other'}
        if reason not in allowed_reasons:
            return jsonify({'error': 'Некорректная причина начисления/списания'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT penalty_points FROM reader WHERE id = ?', (reader_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Читатель не найден'}), 404

        new_value = max(0, row[0] + delta_points)
        applied_delta = new_value - row[0]

        cursor.execute('UPDATE reader SET penalty_points = ? WHERE id = ?', (new_value, reader_id))
        log_penalty_change(cursor, reader_id, applied_delta, reason, commentary, current_user.id)
        action_type = 'PENALTY_ADD' if applied_delta >= 0 else 'PENALTY_DEDUCT'
        log_reader_action(cursor, reader_id, action_type, f"Изменение баллов: {applied_delta}. Причина: {reason}", current_user.id)

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'penalty_points': new_value, 'delta_points': applied_delta}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/suppliers', methods=['GET'])
@login_required
def list_suppliers():
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM supplier ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'suppliers': rows})


@app.route('/api/suppliers', methods=['POST'])
@login_required
def create_supplier():
    ensure_supply_schema()
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'Название обязательно'}), 400
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO supplier (name, contact_person, phone, email, city, street, house, apartment, comment, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get('name', '').strip(),
            data.get('contact_person', '').strip(),
            normalize_phone(data.get('phone', '')),
            data.get('email', '').strip().lower(),
            data.get('city', '').strip(),
            data.get('street', '').strip(),
            data.get('house', '').strip(),
            data.get('apartment', '').strip(),
            data.get('comment', '').strip(),
            1 if data.get('is_active', True) else 0,
        ),
    )
    supplier_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'supplier_id': supplier_id}), 201


@app.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
@login_required
def update_supplier(supplier_id):
    ensure_supply_schema()
    data = request.get_json() or {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE supplier
        SET name=?, contact_person=?, phone=?, email=?, city=?, street=?, house=?, apartment=?, comment=?, is_active=?
        WHERE id=?
        """,
        (
            data.get('name', '').strip(),
            data.get('contact_person', '').strip(),
            normalize_phone(data.get('phone', '')),
            data.get('email', '').strip().lower(),
            data.get('city', '').strip(),
            data.get('street', '').strip(),
            data.get('house', '').strip(),
            data.get('apartment', '').strip(),
            data.get('comment', '').strip(),
            1 if data.get('is_active', True) else 0,
            supplier_id,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
@login_required
def delete_supplier(supplier_id):
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE supplier SET is_active = 0 WHERE id = ?", (supplier_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/contracts', methods=['GET', 'POST'])
@login_required
def contracts_handler():
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if request.method == 'GET':
        cursor.execute(
            """
            SELECT c.*, s.name AS supplier_name
            FROM supplier_contract c
            JOIN supplier s ON s.id = c.supplier_id
            ORDER BY c.id DESC
            """
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'contracts': rows})

    data = request.get_json() or {}
    cursor.execute(
        """
        INSERT INTO supplier_contract (contract_number, signed_at, supplier_id, start_date, end_date, amount_or_terms, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get('contract_number'),
            data.get('signed_at'),
            data.get('supplier_id'),
            data.get('start_date'),
            data.get('end_date'),
            data.get('amount_or_terms', ''),
            data.get('comment', ''),
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'contract_id': new_id}), 201


def _calc_total(items):
    return round(sum((int(i.get('quantity', 0)) * float(i.get('unit_price', 0) or 0)) for i in items), 2)


@app.route('/api/invoices', methods=['GET', 'POST'])
@login_required
def invoices_handler():
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute(
            """
            SELECT i.*, s.name AS supplier_name, c.contract_number,
                   COALESCE(SUM(ii.quantity * ii.unit_price), 0) AS total
            FROM supply_invoice i
            JOIN supplier s ON s.id = i.supplier_id
            LEFT JOIN supplier_contract c ON c.id = i.contract_id
            LEFT JOIN supply_invoice_item ii ON ii.invoice_id = i.id
            GROUP BY i.id
            ORDER BY i.id DESC
            """
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'invoices': rows})

    data = request.get_json() or {}
    items = data.get('items', [])
    cursor.execute(
        """
        INSERT INTO supply_invoice (invoice_number, invoice_date, supplier_id, contract_id, responsible_person, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data.get('invoice_number'),
            data.get('invoice_date'),
            data.get('supplier_id'),
            data.get('contract_id'),
            data.get('responsible_person', ''),
            data.get('comment', ''),
        ),
    )
    invoice_id = cursor.lastrowid
    for item in items:
        cursor.execute(
            "INSERT INTO supply_invoice_item (invoice_id, book_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (invoice_id, item.get('book_id'), item.get('quantity'), item.get('unit_price', 0)),
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'invoice_id': invoice_id, 'total': _calc_total(items)}), 201


@app.route('/api/acceptance-acts', methods=['GET', 'POST'])
@login_required
def acceptance_acts_handler():
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute(
            """
            SELECT a.*, s.name AS supplier_name, c.contract_number,
                   COALESCE(SUM(ai.quantity * ai.unit_price), 0) AS total
            FROM acceptance_act a
            JOIN supplier s ON s.id = a.supplier_id
            LEFT JOIN supplier_contract c ON c.id = a.contract_id
            LEFT JOIN acceptance_act_item ai ON ai.act_id = a.id
            GROUP BY a.id
            ORDER BY a.id DESC
            """
        )
        acts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'acts': acts})

    data = request.get_json() or {}
    items = data.get('items', [])
    cursor.execute(
        """
        INSERT INTO acceptance_act (act_number, act_date, supplier_id, contract_id, responsible_person, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data.get('act_number'),
            data.get('act_date'),
            data.get('supplier_id'),
            data.get('contract_id'),
            data.get('responsible_person', ''),
            data.get('comment', ''),
        ),
    )
    act_id = cursor.lastrowid

    for item in items:
        q = int(item.get('quantity', 0))
        p = float(item.get('unit_price', 0) or 0)
        book_id = item.get('book_id')
        cursor.execute(
            "INSERT INTO acceptance_act_item (act_id, book_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (act_id, book_id, q, p),
        )
        cursor.execute("UPDATE book SET quantity = quantity + ? WHERE id = ?", (q, book_id))
        for _ in range(q):
            uid = f"CP-{act_id}-{book_id}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            cursor.execute(
                "INSERT INTO book_copy (copy_uid, book_id, acceptance_act_id, status, source_type, source_id, received_at) VALUES (?, ?, ?, 'available', 'acceptance_act', ?, CURRENT_TIMESTAMP)",
                (uid, book_id, act_id, act_id),
            )

    cursor.execute("UPDATE acceptance_act SET status = 'CONFIRMED' WHERE id = ?", (act_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'act_id': act_id, 'total': _calc_total(items)}), 201


@app.route('/api/acceptance-acts/<int:act_id>/print', methods=['GET'])
@login_required
def print_acceptance_act(act_id):
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.*, s.name AS supplier_name, c.contract_number
        FROM acceptance_act a
        JOIN supplier s ON s.id = a.supplier_id
        LEFT JOIN supplier_contract c ON c.id = a.contract_id
        WHERE a.id = ?
        """,
        (act_id,),
    )
    act = cursor.fetchone()
    if not act:
        conn.close()
        return jsonify({'error': 'Акт не найден'}), 404
    cursor.execute(
        """
        SELECT ai.quantity, ai.unit_price, b.name AS book_name
        FROM acceptance_act_item ai
        JOIN book b ON b.id = ai.book_id
        WHERE ai.act_id = ?
        """,
        (act_id,),
    )
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'act': dict(act), 'items': items, 'total': _calc_total(items)})


@app.route('/api/writeoff-acts', methods=['GET', 'POST'])
@login_required
def writeoff_acts_handler():
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute(
            """
            SELECT w.*, COUNT(wi.id) AS items_count
            FROM writeoff_act w
            LEFT JOIN writeoff_act_item wi ON wi.act_id = w.id
            GROUP BY w.id
            ORDER BY w.id DESC
            """
        )
        acts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'acts': acts})

    data = request.get_json() or {}
    items = data.get('items', [])
    allowed = {'износ', 'утеря', 'повреждение', 'устаревание', 'другое'}

    cursor.execute(
        """
        INSERT INTO writeoff_act (act_number, act_date, basis, responsible_person, comment, status)
        VALUES (?, ?, ?, ?, ?, 'CONFIRMED')
        """,
        (
            data.get('act_number'),
            data.get('act_date'),
            data.get('basis', ''),
            data.get('responsible_person', ''),
            data.get('comment', ''),
        ),
    )
    act_id = cursor.lastrowid

    for item in items:
        copy_id = item.get('book_copy_id')
        reason = (item.get('reason') or '').strip().lower()
        if reason not in allowed:
            reason = 'другое'
        cursor.execute(
            "SELECT book_id, status FROM book_copy WHERE id = ?",
            (copy_id,),
        )
        copy_row = cursor.fetchone()
        if not copy_row:
            continue
        book_id, old_status = copy_row
        cursor.execute(
            "INSERT INTO writeoff_act_item (act_id, book_copy_id, reason) VALUES (?, ?, ?)",
            (act_id, copy_id, reason),
        )
        cursor.execute("UPDATE book_copy SET status = 'written_off' WHERE id = ?", (copy_id,))
        if old_status == 'available':
            cursor.execute("UPDATE book SET quantity = MAX(0, quantity - 1) WHERE id = ?", (book_id,))
        log_copy_status(cursor, copy_id, old_status, 'written_off', 'writeoff_act', reason)

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'act_id': act_id}), 201


@app.route('/api/book-copies', methods=['GET'])
@login_required
def list_book_copies():
    ensure_supply_schema()
    status = request.args.get('status')
    uid = (request.args.get('uid') or '').strip()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    sql = """
        SELECT bc.id, bc.copy_uid, bc.status, bc.received_at, bc.source_type, bc.source_id, bc.note,
               b.name AS book_name,
               (a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '')) AS author
        FROM book_copy bc
        JOIN book b ON b.id = bc.book_id
        JOIN author a ON a.id = b.author_id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND bc.status = ?"
        params.append(status)
    if uid:
        sql += " AND bc.copy_uid LIKE ?"
        params.append(f"%{uid}%")
    sql += " ORDER BY bc.id DESC LIMIT 500"
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'copies': rows})


@app.route('/api/book-copies/<int:copy_id>/history', methods=['GET'])
@login_required
def get_book_copy_history(copy_id):
    ensure_supply_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT bch.*, (r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '')) AS reader_name
        FROM book_copy_history bch
        LEFT JOIN reader r ON r.id = bch.reader_id
        WHERE bch.book_copy_id = ?
        ORDER BY bch.id DESC
        """,
        (copy_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'history': rows})


@app.route('/api/books/all', methods=['GET'])
def get_all_books():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем все книги с информацией об авторах и жанрах
        cursor.execute('''
            SELECT 
                b.id, b.isbn, b.name as title, b.year, b.quantity, b.publishing_house,
                a.id as author_id, a.first_name, a.last_name, a.patronymic,
                g.id as genre_id, g.name as genre_name
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
        ''')
        
        books = cursor.fetchall()
        conn.close()
        
        books_list = []
        for book in books:
            # Формируем полное имя автора
            author_name = ' '.join(filter(None, [book[7], book[8], book[9]]))
            
            books_list.append({
                "id": book[0],
                "isbn": book[1],
                "title": book[2],
                "year": book[3],
                "quantity": book[4],
                "publishing_house": book[5],
                "author_id": book[6],
                "author": author_name,
                "genre_id": book[10],
                "genre": book[11],
                "available": book[4]  # Предполагаем, что все книги доступны
            })
        
        return jsonify({
            "success": True,
            "books": books_list
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Получение информации о читателе по телефону
@app.route('/api/reader/by-phone', methods=['GET'])
def get_reader_by_phone():
    try:
        phone = normalize_phone(request.args.get('phone'))
        if not phone:
            return jsonify({"error": "Не указан телефон"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, last_name, first_name, patronymic, phone, penalty_points 
            FROM reader WHERE phone = ?
        ''', (phone,))
        
        reader = cursor.fetchone()
        conn.close()
        
        if not reader:
            return jsonify({"exists": False}), 200
        
        return jsonify({
            "exists": True,
            "reader": {
                "id": reader[0],
                "last_name": reader[1],
                "first_name": reader[2],
                "patronymic": reader[3],
                "phone": reader[4]
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Проверка книги по ISBN
@app.route('/api/book/check-isbn', methods=['GET'])
def check_book_by_isbn():
    try:
        isbn = request.args.get('isbn')
        if not isbn:
            return jsonify({"error": "ISBN не указан"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Ищем книгу с автором и жанром
        cursor.execute('''
            SELECT b.id, b.name, b.year, b.publishing_house,
                   a.id as author_id, a.last_name || ' ' || a.first_name as author_name,
                   g.id as genre_id, g.name as genre_name
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
            WHERE b.isbn = ?
            LIMIT 1
        ''', (isbn,))

        book = cursor.fetchone()
        conn.close()

        if book:
            return jsonify({
                "exists": True,
                "book": {
                    "name": book[1],
                    "year": book[2],
                    "publishing_house": book[3]
                },
                "author_name": book[5],
                "genre_id": book[6],
                "genre_name": book[7]
            })

        return jsonify({"exists": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Добавление новой книги
@app.route('/api/book/add', methods=['POST'])
def add_book():
    try:
        data = request.get_json()
        required_fields = ['title', 'author', 'genre', 'quantity', 'publishing_house']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Не все обязательные поля заполнены"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Обработка автора (разбиваем ФИО)
        author_parts = data['author'].split(' ')
        last_name = author_parts[0] if len(author_parts) > 0 else ''
        first_name = author_parts[1] if len(author_parts) > 1 else ''
        patronymic = author_parts[2] if len(author_parts) > 2 else ''

        # Проверяем существование автора
        cursor.execute('''
            SELECT id FROM author 
            WHERE last_name = ? AND first_name = ? AND (patronymic = ? OR patronymic IS NULL)
        ''', (last_name, first_name, patronymic))

        author = cursor.fetchone()
        
        # Если автор не найден - создаем нового
        if not author:
            cursor.execute('''
                INSERT INTO author (last_name, first_name, patronymic)
                VALUES (?, ?, ?)
            ''', (last_name, first_name, patronymic))
            author_id = cursor.lastrowid
        else:
            author_id = author[0]

        # Получаем ID жанра
        cursor.execute('SELECT id FROM genre WHERE name = ?', (data['genre'],))
        genre = cursor.fetchone()
        
        if not genre:
            cursor.execute('''
                INSERT INTO genre (genre_type, name)
                VALUES (?, ?)
            ''', ('-', data["genre"]))
            genre = cursor.lastrowid
        else: 
            genre = genre[0]

        # Добавляем книгу
        cursor.execute('''
            INSERT INTO book (isbn, name, year, quantity, author_id, genre_id, publishing_house)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('isbn'),
            data['title'],
            data.get('year'),
            data['quantity'],
            author_id,
            genre,
            data['publishing_house']
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True})

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": str(e)}), 500

# Получение информации о книге по ISBN или ID
@app.route('/api/book/by-identifier', methods=['GET'])
def get_book_by_identifier():
    ensure_supply_schema()
    try:
        identifier = request.args.get('identifier')
        if not identifier:
            return jsonify({"error": "Не указан идентификатор"}), 400

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        sync_overdue_copy_statuses(cursor)
        conn.commit()

        cursor.execute(
            """
            SELECT b.id, b.name, b.year, b.isbn, b.quantity,
                   a.first_name, a.last_name, a.patronymic,
                   g.name as genre, b.publishing_house, b.description
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
            WHERE b.isbn = ? OR b.id = ?
            LIMIT 1
            """,
            (identifier, identifier)
        )

        book = cursor.fetchone()
        if not book:
            conn.close()
            return jsonify({"error": "Книга не найдена"}), 404

        cursor.execute(
            """
            SELECT id, copy_uid, status, received_at, source_type, source_id, note
            FROM book_copy
            WHERE book_id = ?
            ORDER BY id DESC
            """,
            (book['id'],)
        )
        copies = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({
            "book": {
                "id": book['id'],
                "title": book['name'],
                "year": book['year'],
                "isbn": book['isbn'],
                "quantity": book['quantity'],
                "author": ' '.join(filter(None, [book['first_name'], book['last_name'], book['patronymic']])),
                "genre": book['genre'],
                "publishing_house": book['publishing_house'],
                "description": book['description'],
            },
            "available_copies": [c for c in copies if c['status'] == 'available'],
            "copies": copies,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Выдача книги
def _build_report_payload(report_type, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    params = []

    report_map = {
        "issued-books": {
            "title": "Отчет по выданным книгам",
            "date_column": "gb.given_date",
            "query": """
                SELECT
                    gb.id,
                    b.name AS book_name,
                    (a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '')) AS author,
                    (r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '')) AS reader,
                    date(gb.given_date) AS issued_at,
                    date(gb.return_date) AS due_at,
                    COALESCE(date(gb.return_date_fact), 'Не возвращена') AS returned_at,
                    CASE
                        WHEN gb.return_date_fact IS NULL AND date(gb.return_date) < date('now') THEN 'Просрочена'
                        WHEN gb.return_date_fact IS NULL THEN 'На руках'
                        ELSE 'Возвращена'
                    END AS status
                FROM given_book gb
                JOIN book b ON gb.book_id = b.id
                JOIN author a ON b.author_id = a.id
                JOIN reader r ON gb.reader_id = r.id
                WHERE 1=1 {period_condition}
                ORDER BY gb.given_date DESC
            """,
            "columns": ["#", "Книга", "Автор", "Читатель", "Выдана", "Вернуть до", "Факт возврата", "Статус"],
            "row_builder": lambda r, i: [i, r["book_name"], r["author"], r["reader"], r["issued_at"], r["due_at"], r["returned_at"], r["status"]],
            "kpi_builder": lambda rows: [
                {"label": "Всего выдач", "value": len(rows)},
                {"label": "На руках", "value": sum(1 for r in rows if r["status"] == "На руках")},
                {"label": "Просрочено", "value": sum(1 for r in rows if r["status"] == "Просрочена")}
            ]
        },
        "overdue-books": {
            "title": "Отчет по просрочкам",
            "date_column": "gb.given_date",
            "query": """
                SELECT
                    gb.id,
                    b.name AS book_name,
                    (r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '')) AS reader,
                    date(gb.given_date) AS issued_at,
                    date(gb.return_date) AS due_at,
                    CAST(julianday('now') - julianday(gb.return_date) AS INTEGER) AS overdue_days
                FROM given_book gb
                JOIN book b ON gb.book_id = b.id
                JOIN reader r ON gb.reader_id = r.id
                WHERE gb.return_date_fact IS NULL
                  AND date(gb.return_date) < date('now')
                  {period_condition}
                ORDER BY overdue_days DESC
            """,
            "columns": ["#", "Книга", "Читатель", "Дата выдачи", "Плановый возврат", "Дней просрочки"],
            "row_builder": lambda r, i: [i, r["book_name"], r["reader"], r["issued_at"], r["due_at"], r["overdue_days"]],
            "kpi_builder": lambda rows: [
                {"label": "Просроченных выдач", "value": len(rows)},
                {"label": "Макс. просрочка", "value": max((r["overdue_days"] for r in rows), default=0)},
                {"label": "Средняя просрочка", "value": round(sum((r["overdue_days"] for r in rows), 0) / len(rows), 1) if rows else 0}
            ]
        },
        "readers": {
            "title": "Отчет по читателям",
            "date_column": None,
            "query": """
                SELECT
                    r.id,
                    (r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '')) AS reader,
                    r.phone,
                    r.email,
                    r.penalty_points,
                    COUNT(gb.id) AS total_issues,
                    SUM(CASE WHEN gb.return_date_fact IS NULL THEN 1 ELSE 0 END) AS active_issues
                FROM reader r
                LEFT JOIN given_book gb ON gb.reader_id = r.id
                WHERE 1=1
                GROUP BY r.id, r.last_name, r.first_name, r.patronymic, r.phone, r.email, r.penalty_points
                ORDER BY total_issues DESC, reader
            """,
            "columns": ["#", "Читатель", "Телефон", "Email", "Выдач всего", "Книг на руках", "Штрафные баллы"],
            "row_builder": lambda r, i: [i, r["reader"], r["phone"], r["email"], r["total_issues"], r["active_issues"], r["penalty_points"]],
            "kpi_builder": lambda rows: [
                {"label": "Всего читателей", "value": len(rows)},
                {"label": "Активные читатели", "value": sum(1 for r in rows if r["active_issues"] > 0)},
                {"label": "Сумма штрафных баллов", "value": sum(r["penalty_points"] for r in rows)}
            ]
        },
        "book-popularity": {
            "title": "Отчет по популярности книг",
            "date_column": None,
            "query": """
                SELECT
                    b.id,
                    b.name AS book_name,
                    (a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '')) AS author,
                    COUNT(gb.id) AS issue_count,
                    SUM(CASE WHEN gb.return_date_fact IS NULL THEN 1 ELSE 0 END) AS active_count
                FROM book b
                JOIN author a ON b.author_id = a.id
                LEFT JOIN given_book gb ON gb.book_id = b.id
                GROUP BY b.id, b.name, a.last_name, a.first_name, a.patronymic
                ORDER BY issue_count DESC, b.name
            """,
            "columns": ["#", "Книга", "Автор", "Выдано раз", "Сейчас на руках"],
            "row_builder": lambda r, i: [i, r["book_name"], r["author"], r["issue_count"], r["active_count"]],
            "kpi_builder": lambda rows: [
                {"label": "Книг в рейтинге", "value": len(rows)},
                {"label": "Всего выдач", "value": sum(r["issue_count"] for r in rows)},
                {"label": "Топ-книга", "value": rows[0]["book_name"] if rows else '-'}
            ]
        },
        "penalty-points": {
            "title": "Отчет по штрафным баллам",
            "date_column": None,
            "query": """
                SELECT
                    r.id,
                    (r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '')) AS reader,
                    r.penalty_points,
                    SUM(CASE WHEN gb.return_date_fact IS NULL AND date(gb.return_date) < date('now') THEN 1 ELSE 0 END) AS active_overdues
                FROM reader r
                LEFT JOIN given_book gb ON gb.reader_id = r.id
                GROUP BY r.id, r.last_name, r.first_name, r.patronymic, r.penalty_points
                HAVING r.penalty_points > 0 OR active_overdues > 0
                ORDER BY r.penalty_points DESC, active_overdues DESC
            """,
            "columns": ["#", "Читатель", "Штрафные баллы", "Активные просрочки"],
            "row_builder": lambda r, i: [i, r["reader"], r["penalty_points"], r["active_overdues"]],
            "kpi_builder": lambda rows: [
                {"label": "Читателей со штрафами", "value": len(rows)},
                {"label": "Сумма штрафных баллов", "value": sum(r["penalty_points"] for r in rows)},
                {"label": "Активных просрочек", "value": sum(r["active_overdues"] for r in rows)}
            ]
        },
        "write-off": {
            "title": "Отчет по списанным книгам",
            "date_column": "da.date",
            "query": """
                SELECT
                    da.id,
                    date(da.date) AS writeoff_date,
                    b.name AS book_name,
                    da.quantity,
                    da.commentary
                FROM debiting_act da
                JOIN book b ON da.book_id = b.id
                WHERE 1=1 {period_condition}
                ORDER BY da.date DESC
            """,
            "columns": ["#", "Дата", "Книга", "Кол-во", "Причина"],
            "row_builder": lambda r, i: [i, r["writeoff_date"], r["book_name"], r["quantity"], r["commentary"]],
            "kpi_builder": lambda rows: [
                {"label": "Актов списания", "value": len(rows)},
                {"label": "Списано экземпляров", "value": sum(r["quantity"] for r in rows)}
            ]
        },
        "new-arrivals": {
            "title": "Отчет по поступлениям книг",
            "date_column": "lb.date",
            "query": """
                SELECT
                    lb.id,
                    date(lb.date) AS supply_date,
                    b.name AS book_name,
                    s.name AS supplier,
                    orq.quantity
                FROM lading_bill lb
                JOIN order_request orq ON orq.id = lb.order_request_id
                JOIN book b ON b.id = lb.book_id
                JOIN supplier s ON s.id = lb.supplier_id
                WHERE 1=1 {period_condition}
                ORDER BY lb.date DESC
            """,
            "columns": ["#", "Дата", "Книга", "Поставщик", "Кол-во"],
            "row_builder": lambda r, i: [i, r["supply_date"], r["book_name"], r["supplier"], r["quantity"]],
            "kpi_builder": lambda rows: [
                {"label": "Поставок", "value": len(rows)},
                {"label": "Поступило экземпляров", "value": sum(r["quantity"] for r in rows)}
            ]
        }
    }

    if report_type not in report_map:
        raise ValueError("Неизвестный тип отчета")

    report_config = report_map[report_type]
    period_condition = ""
    if start_date and end_date and report_config.get("date_column"):
        period_condition = f" AND date({report_config['date_column']}) BETWEEN date(?) AND date(?) "
        params.extend([start_date, end_date])

    query = report_config["query"].format(period_condition=period_condition)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    table_rows = [report_config["row_builder"](row, idx + 1) for idx, row in enumerate(rows)]
    return {
        "report_type": report_type,
        "title": report_config["title"],
        "period": {"start": start_date, "end": end_date},
        "columns": report_config["columns"],
        "rows": table_rows,
        "totals": {
            "records": len(table_rows)
        },
        "kpi": report_config["kpi_builder"](rows)
    }


@app.route('/api/reports/preview', methods=['POST'])
@login_required
def preview_report_api():
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not report_type:
            return jsonify({"error": "Не указан тип отчета"}), 400

        payload = _build_report_payload(report_type, start_date, end_date)
        return jsonify({"success": True, "report": payload}), 200
    except ValueError as ex:
        return jsonify({"error": str(ex)}), 400
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route('/api/reports/export', methods=['POST'])
@login_required
def export_report_api():
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        payload = _build_report_payload(report_type, start_date, end_date)

        os.makedirs('reports', exist_ok=True)
        filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.join('reports', filename)

        with open(path, 'w', encoding='utf-8', newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            writer.writerow([payload['title']])
            if start_date and end_date:
                writer.writerow([f"Период: {start_date} - {end_date}"])
            writer.writerow([])
            writer.writerow(payload['columns'])
            writer.writerows(payload['rows'])

        return jsonify({
            "success": True,
            "report_url": f"/reports_download/{filename}",
            "filename": filename
        }), 200
    except ValueError as ex:
        return jsonify({"error": str(ex)}), 400
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report_api():
    from reports.fill_reports import (
        generate_books_by_authors_report,
        generate_issued_returned_books_report,
        generate_issued_books_report,
        generate_books_by_genres_report,
        generate_book_collection_report,
        generate_new_books_report,
        generate_debited_books_report,
        convert_docx_to_pdf
    )

    try:
        data = request.get_json()
        report_type = data.get('report_type')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        employee_id = current_user.id

        report_path = None
        if report_type == 'by-author':
            report_path = generate_books_by_authors_report(employee_id)
        elif report_type == 'issue-return':
            if not start_date or not end_date:
                return jsonify({"error": "Для отчета о выданных и возвращенных книгах необходим период."}), 400
            report_path = generate_issued_returned_books_report(employee_id, start_date, end_date)
        elif report_type == 'issued-books':
            report_path = generate_issued_books_report(employee_id)
        elif report_type == 'by-genre':
            report_path = generate_books_by_genres_report(employee_id)
        elif report_type == 'all-books':
            report_path = generate_book_collection_report(employee_id)
        elif report_type == 'new-arrivals':
            if not start_date or not end_date:
                return jsonify({"error": "Для отчета о новых поступлениях необходим период."}), 400
            report_path = generate_new_books_report(employee_id, start_date, end_date)
        elif report_type == 'write-off':
            report_path = generate_debited_books_report(employee_id)
        else:
            return jsonify({"error": "Неизвестный тип отчета"}), 400

        # Возвращаем относительный путь к файлу для скачивания
        pdf_path = convert_docx_to_pdf(report_path, 'reports')
        return jsonify({"success": True, "report_url": f"/reports_download/{os.path.basename(report_path)}", "report_pdf_url": f"/reports_download/{os.path.basename(pdf_path)}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reports_download/<filename>')
@login_required
def download_report(filename):
    try:
        return send_from_directory(os.path.join(app.root_path, 'reports'), filename, as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/api/book/issue', methods=['POST'])
def issue_book():
    ensure_supply_schema()
    try:
        data = request.get_json() or {}
        required_fields = ['reader_id', 'book_id', 'issue_date', 'return_date']

        if not all(field in data and data[field] for field in required_fields):
            return jsonify({"error": "Не все обязательные поля заполнены"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT quantity FROM book WHERE id = ?", (data['book_id'],))
        book = cursor.fetchone()
        if not book or book[0] <= 0:
            conn.close()
            return jsonify({"error": "Книга недоступна для выдачи"}), 400

        copy_id = data.get('book_copy_id')
        if copy_id:
            cursor.execute("SELECT id, status FROM book_copy WHERE id = ? AND book_id = ?", (copy_id, data['book_id']))
            copy_row = cursor.fetchone()
            if not copy_row:
                conn.close()
                return jsonify({"error": "Экземпляр книги не найден"}), 404
            if copy_row[1] != 'available':
                conn.close()
                return jsonify({"error": "Экземпляр недоступен для выдачи"}), 400
        else:
            cursor.execute(
                """
                SELECT id, status FROM book_copy
                WHERE book_id = ? AND status = 'available'
                ORDER BY id ASC LIMIT 1
                """,
                (data['book_id'],)
            )
            copy_row = cursor.fetchone()
            if not copy_row:
                conn.close()
                return jsonify({"error": "Нет доступных экземпляров книги"}), 400
            copy_id = copy_row[0]

        cursor.execute(
            """
            INSERT INTO given_book
            (reader_id, book_id, book_copy_id, given_date, return_date, employee_id, quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data['reader_id'],
                data['book_id'],
                copy_id,
                data['issue_date'],
                data['return_date'],
                current_user.id,
                1
            )
        )

        old_status = copy_row[1]
        cursor.execute("UPDATE book_copy SET status = 'issued' WHERE id = ?", (copy_id,))
        log_copy_status(cursor, copy_id, old_status, 'issued', 'issue', data.get('issue_notes', ''), data['reader_id'])

        cursor.execute('UPDATE book SET quantity = quantity - 1 WHERE id = ?', (data['book_id'],))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "book_copy_id": copy_id}), 200

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/book/find-for-return', methods=['GET'])
def find_book_for_return():
    ensure_supply_schema()
    try:
        reader_id = request.args.get('reader_id')
        isbn = request.args.get('isbn')

        if not reader_id or not isbn:
            return jsonify({"error": "Необходимо указать ID читателя и ISBN"}), 400

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        sync_overdue_copy_statuses(cursor)
        conn.commit()

        cursor.execute(
            """
            SELECT gb.id as record_id,
                   b.name as book_title,
                   a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as book_author,
                   gb.given_date as issue_date,
                   gb.return_date as planned_return_date,
                   gb.book_copy_id,
                   bc.copy_uid,
                   bc.status as copy_status
            FROM given_book gb
            JOIN book b ON gb.book_id = b.id
            JOIN author a ON b.author_id = a.id
            LEFT JOIN book_copy bc ON bc.id = gb.book_copy_id
            WHERE gb.reader_id = ?
              AND b.isbn = ?
              AND gb.return_date_fact IS NULL
            ORDER BY gb.id DESC
            LIMIT 1
            """,
            (reader_id, isbn)
        )

        issue_record = cursor.fetchone()
        conn.close()

        if not issue_record:
            return jsonify({"error": "Активная выдача не найдена"}), 404

        return jsonify(dict(issue_record))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/book/return', methods=['POST'])
def return_book():
    ensure_reader_schema()
    ensure_supply_schema()
    try:
        data = request.get_json() or {}
        required_fields = ['record_id', 'actual_return_date']

        if not all(field in data and data[field] for field in required_fields):
            return jsonify({"error": "Не все обязательные поля заполнены"}), 400

        final_status = data.get('final_status', 'available')
        if final_status not in {'available', 'damaged', 'lost', 'written_off'}:
            return jsonify({"error": "Недопустимый итоговый статус экземпляра"}), 400

        return_comment = (data.get('return_comment') or '').strip()
        penalty_delta = int(data.get('penalty_delta') or 0)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT gb.book_id, gb.quantity, gb.reader_id, gb.return_date, gb.book_copy_id,
                   (SELECT late_return_penalty FROM system_settings WHERE id = 1) as penalty
            FROM given_book gb
            WHERE gb.id = ? AND gb.return_date_fact IS NULL
            """,
            (data['record_id'],)
        )

        issue_record = cursor.fetchone()
        if not issue_record:
            conn.close()
            return jsonify({"error": "Выдача не найдена или книга уже возвращена"}), 400

        book_id, quantity, reader_id, planned_return_date, book_copy_id, overdue_penalty = issue_record
        actual_return_date = data['actual_return_date']

        overdue_days = 0
        if actual_return_date > planned_return_date:
            overdue_days = (datetime.fromisoformat(actual_return_date) - datetime.fromisoformat(planned_return_date)).days
            cursor.execute('UPDATE reader SET penalty_points = penalty_points + ? WHERE id = ?', (overdue_penalty, reader_id))
            log_penalty_change(cursor, reader_id, overdue_penalty, 'overdue', 'Автоматическое начисление за просрочку возврата', current_user.id)
            log_reader_action(cursor, reader_id, 'PENALTY_ADD', f'Автоматически начислено {overdue_penalty} баллов за просрочку', current_user.id)

        if penalty_delta:
            cursor.execute('UPDATE reader SET penalty_points = MAX(0, penalty_points + ?) WHERE id = ?', (penalty_delta, reader_id))
            reason = 'book_damage' if final_status == 'damaged' else 'book_loss' if final_status == 'lost' else 'other'
            log_penalty_change(cursor, reader_id, penalty_delta, reason, return_comment or 'Начислено при возврате', current_user.id)
            action_type = 'PENALTY_ADD' if penalty_delta > 0 else 'PENALTY_DEDUCT'
            log_reader_action(cursor, reader_id, action_type, f'Изменение баллов при возврате: {penalty_delta}', current_user.id)

        cursor.execute(
            """
            UPDATE given_book
            SET return_date_fact = ?, return_status = ?, return_comment = ?, overdue_days = ?
            WHERE id = ?
            """,
            (actual_return_date, final_status, return_comment, overdue_days, data['record_id'])
        )

        if final_status == 'available':
            cursor.execute('UPDATE book SET quantity = quantity + ? WHERE id = ?', (quantity, book_id))

        if book_copy_id:
            cursor.execute("SELECT status FROM book_copy WHERE id = ?", (book_copy_id,))
            old = cursor.fetchone()
            old_status = old[0] if old else 'issued'
            cursor.execute('UPDATE book_copy SET status = ?, note = ? WHERE id = ?', (final_status, return_comment, book_copy_id))
            log_copy_status(cursor, book_copy_id, old_status, final_status, 'return', return_comment, reader_id)

        conn.commit()
        conn.close()

        return jsonify({"success": True, "overdue_days": overdue_days})

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": str(e)}), 500


def get_system_settings_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT standart_rental_period, max_books_per_reader, late_return_penalty FROM system_settings ORDER BY id DESC LIMIT 1')
        sys_set = cursor.fetchone()
        if not sys_set:
            return None

        return {
            "standart_rental_period": sys_set[0],
            "max_books_per_reader": sys_set[1],
            "late_return_penalty": sys_set[2]
        }
    finally:
        conn.close()


# Загрузка системных настроек
@app.route('/api/system/get', methods=['GET'])
def get_system_settings():
    try:
        system_settings = get_system_settings_data()
        if not system_settings:
            return jsonify({"error": "Не заполнены системные настройки"}), 500

        return jsonify({"success": True, "system_settings": system_settings}), 200

    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

# Загрузка системных настроек
@app.route('/api/system/update', methods=['POST'])
def load_system_settings():
    try:
        data = request.get_json()
        required_fields = ["standart_rental_period", "max_books_per_reader", "late_return_penalty"]
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Не все обязательные поля заполнены"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Изменяем настройки
        cursor.execute('''
            UPDATE system_settings 
            SET standart_rental_period = ?, 
                max_books_per_reader = ?, 
                late_return_penalty = ? 
            WHERE id = 1
        ''', (data['standart_rental_period'], data['max_books_per_reader'], data['late_return_penalty']))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
def get_user_by_login(login):
    ensure_database_ready()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, login, password, position, first_name, last_name FROM employee WHERE login = ?", (login,))
    row = cursor.fetchone()
    conn.close()
    return row  # (id, login, password, position)

def get_user_by_id(user_id):
    ensure_database_ready()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, login, password, position, first_name, last_name FROM employee WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row




if __name__ == '__main__':
    ensure_database_ready()
    ensure_supply_schema()
    app.run(debug=True)
