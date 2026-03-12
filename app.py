from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_cors import CORS
from functools import wraps
import sqlite3
import os
import csv
from datetime import datetime
from instance.fill_db import fill
from config import DB_PATH

app = Flask(__name__)
app.secret_key = 'SECRET'
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

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
    if request.method == 'POST':
        login_ = request.form['login']
        password_ = request.form['password']
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
    data = request.get_json()
    login_ = data.get('login')
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Книг в наличии (сумма quantity из таблицы book)
        cursor.execute('SELECT SUM(quantity) FROM book')
        available_books = cursor.fetchone()[0] or 0
        
        # 2. Книг на руках у читателей (сумма quantity из given_book где не возвращено)
        cursor.execute('''
            SELECT SUM(quantity) 
            FROM given_book 
            WHERE return_date_fact IS NULL
        ''')
        borrowed_books = cursor.fetchone()[0] or 0
        
        # 3. Всего книг в фонде (книги в наличии + выданные)
        total_books = available_books + borrowed_books
        
        # # 4. Требуют списания (книги с quantity <= 0)
        # cursor.execute('SELECT COUNT(*) FROM book WHERE quantity <= 0')
        # to_write_off = cursor.fetchone()[0] or 0
        
        # # 5. Новые поступления (за последние 30 дней)
        # cursor.execute('''
        #     SELECT COUNT(*) 
        #     FROM lading_bill 
        #     WHERE date >= date('now', '-30 days')
        # ''')
        # new_arrivals = cursor.fetchone()[0] or 0
        
        metrics = [
            {"title": "Всего книг в фонде", "value": f"{total_books:,}", "class": "primary"},
            {"title": "Книг в наличии", "value": f"{available_books:,}", "class": "success"},
            {"title": "На руках у читателей", "value": f"{borrowed_books:,}", "class": "info"},
            # {"title": "Требуют списания", "value": f"{to_write_off:,}", "class": "warning"},
            # {"title": "Новые поступления", "value": f"{new_arrivals:,}", "class": "danger"}
        ]
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    finally:
        conn.close()
        
@app.route('/api/readers', methods=['POST'])
def add_reader():
    try:
        data = request.get_json()
        print(data)
        
        # Валидация данных
        required_fields = ['firstName', 'lastName', 'phone', 'address', 'email', 'birthdate']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Не заполнены обязательные поля"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Вставка данных в БД
        cursor.execute('''
            INSERT INTO reader 
            (first_name, last_name, patronymic, date_birth, phone, address, email) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['firstName'],
            data['lastName'],
            data.get('patronymic', ''),
            data.get('birthdate', ''),
            data['phone'],
            data['address'],
            data['email']
        ))
        
        conn.commit()
        reader_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Читатель успешно зарегистрирован",
            "readerId": reader_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/readers/search', methods=['GET'])
def search_readers():
    try:
        search_query = request.args.get('query')
        
        if not search_query:
            return jsonify({"error": "Не указана строка для поиска"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ищем в любом из полей: first_name, last_name, patronymic, contact
        cursor.execute('''
            SELECT * FROM reader 
            WHERE first_name LIKE ? 
               OR last_name LIKE ? 
               OR patronymic LIKE ? 
               OR phone LIKE ?
        ''', [f"%{search_query}%"] * 4)
        
        readers = cursor.fetchall()
        conn.close()
        
        readers_list = []
        for reader in readers:
            readers_list.append({
                "id": reader[0],
                "firstName": reader[1],
                "lastName": reader[2],
                "patronymic": reader[3],
                "birthdate": reader[4],
                "adress": reader[5],
                "email": reader[6],
                "phone": reader[7],
                "penalty_points": reader[8],
            })
        
        return jsonify({
            "success": True,
            "readers": readers_list,
            "count": len(readers_list)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

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
        phone = request.args.get('phone')
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
    try:
        identifier = request.args.get('identifier')
        if not identifier:
            return jsonify({"error": "Не указан идентификатор"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.name, b.year, b.isbn, b.quantity, 
                   a.first_name, a.last_name, a.patronymic,
                   g.name as genre, b.publishing_house
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
            WHERE b.isbn = ? OR b.id = ?
        ''', (identifier, identifier))
        
        book = cursor.fetchone()
        conn.close()
        
        if not book:
            return jsonify({"error": "Книга не найдена"}), 404
        
        return jsonify({
            "book": {
                "id": book[0],
                "title": book[1],
                "year": book[2],
                "isbn": book[3],
                "quantity": book[4],
                "author": ' '.join(filter(None, [book[5], book[6], book[7]])),
                "genre": book[8],
                "publishing_house": book[9],
            }
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
    try:
        data = request.get_json()
        required_fields = ['reader_id', 'book_id', 'issue_date', 'return_date']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Не все обязательные поля заполнены"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем доступность книги (количество в общем каталоге)
        cursor.execute('SELECT quantity FROM book WHERE id = ?', (data['book_id'],))
        book = cursor.fetchone()
        
        if not book or book[0] <= 0:
            conn.close()
            return jsonify({"error": "Книга недоступна для выдачи"}), 400
        
        # Проверяем, есть ли уже выданные экземпляры этого reader_id и book_id
        cursor.execute('''
            SELECT id, quantity FROM given_book 
            WHERE reader_id = ? AND book_id = ? AND return_date >= ?
        ''', (data['reader_id'], data['book_id'], data['issue_date']))
        
        given_book = cursor.fetchone()
        
        # Создаем новую запись о выдаче
        cursor.execute('''
            INSERT INTO given_book
            (reader_id, book_id, given_date, return_date, employee_id, quantity) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['reader_id'], 
            data['book_id'], 
            data['issue_date'], 
            data['return_date'], 
            current_user.id,
            1
        ))

        
        # Уменьшаем количество доступных книг в общем каталоге
        cursor.execute('''
            UPDATE book SET quantity = quantity - 1 
            WHERE id = ?
        ''', (data['book_id'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": str(e)}), 500
    
    
# Поиск книги для возврата
@app.route('/api/book/find-for-return', methods=['GET'])
def find_book_for_return():
    try:
        reader_id = request.args.get('reader_id')
        isbn = request.args.get('isbn')
        
        if not reader_id or not isbn:
            return jsonify({"error": "Необходимо указать ID читателя и ISBN"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ищем активную выдачу по читателю и ISBN
        cursor.execute('''
            SELECT gb.id as record_id, 
                b.name as book_title, 
                a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as book_author,
                gb.given_date as issue_date,
                gb.return_date as planned_return_date
            FROM given_book gb
            JOIN book b ON gb.book_id = b.id
            JOIN author a ON b.author_id = a.id
            WHERE gb.reader_id = ? 
            AND b.isbn = ?
            AND gb.return_date_fact IS NULL
            LIMIT 1
        ''', (reader_id, isbn))
        
        issue_record = cursor.fetchone()
        conn.close()
        
        if not issue_record:
            return jsonify({"error": "Активная выдача не найдена"}), 404
        
        # Преобразуем результат в словарь
        result = {
            "record_id": issue_record[0],
            "book_title": issue_record[1],
            "book_author": issue_record[2],
            "issue_date": issue_record[3],
            "planned_return_date": issue_record[4]
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Обработка возврата книги
@app.route('/api/book/return', methods=['POST'])
def return_book():
    try:
        data = request.get_json()
        required_fields = ['record_id', 'actual_return_date']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Не все обязательные поля заполнены"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем полную информацию о выдаче
        cursor.execute('''
            SELECT gb.book_id, gb.quantity, gb.reader_id, gb.return_date,
                   (SELECT late_return_penalty FROM system_settings WHERE id = 1) as penalty
            FROM given_book gb
            WHERE gb.id = ? AND gb.return_date_fact IS NULL
        ''', (data['record_id'],))
        
        issue_record = cursor.fetchone()
        
        if not issue_record:
            conn.close()
            return jsonify({"error": "Выдача не найдена или книга уже возвращена"}), 400
        
        book_id, quantity, reader_id, planned_return_date, penalty_points = issue_record
        actual_return_date = data['actual_return_date']
        
        # Проверяем просрочку
        if actual_return_date > planned_return_date:
            # Начисляем штрафные баллы
            cursor.execute('''
                UPDATE reader
                SET penalty_points = penalty_points + ?
                WHERE id = ?
            ''', (penalty_points, reader_id))
        
        # Обновляем запись о выдаче
        cursor.execute('''
            UPDATE given_book 
            SET return_date_fact = ?
            WHERE id = ?
        ''', (actual_return_date, data['record_id']))
        
        # Увеличиваем количество доступных книг
        cursor.execute('''
            UPDATE book 
            SET quantity = quantity + ? 
            WHERE id = ?
        ''', (quantity, book_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
        
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, login, password, position, first_name, last_name FROM employee WHERE login = ?", (login,))
    row = cursor.fetchone()
    conn.close()
    return row  # (id, login, password, position)

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, login, password, position, first_name, last_name FROM employee WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row




if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        fill()
    app.run(debug=True)
