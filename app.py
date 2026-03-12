from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_cors import CORS
from functools import wraps
import sqlite3
import os
import csv
from datetime import datetime
from uuid import uuid4

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
                abort(403)
            return f(*args, **kwargs)
        return decorated_view
    return wrapper


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def recalc_book_quantities(cursor):
    cursor.execute(
        """
        UPDATE book
        SET quantity = (
            SELECT COUNT(*)
            FROM book_copy bc
            WHERE bc.book_id = book.id
              AND bc.status != 'списана'
        )
        """
    )


# Pages
@app.route('/')
@role_required('Библиотекарь', 'Бухгалтер', 'Администратор')
@login_required
def index():
    return render_template('index.html', role=current_user.role)


@app.route('/books')
@role_required('Библиотекарь', 'Администратор')
@login_required
def books_page():
    return render_template('books.html', role=current_user.role)


@app.route('/readers')
@role_required('Библиотекарь', 'Администратор')
@login_required
def readers_page():
    return render_template('readers.html', role=current_user.role)


@app.route('/transactions')
@role_required('Библиотекарь', 'Администратор')
@login_required
def transactions_page():
    return render_template('transactions.html', role=current_user.role)


@app.route('/supplies')
@role_required('Библиотекарь', 'Администратор')
@login_required
def supplies_page():
    return render_template('supplies.html', role=current_user.role)


@app.route('/reports')
@role_required('Бухгалтер', 'Администратор')
@login_required
def reports_page():
    return render_template('reports.html', role=current_user.role)


@app.route('/settings')
@role_required('Администратор')
@login_required
def settings_page():
    return render_template('settings.html', role=current_user.role, system_settings={'system_settings': get_system_settings_data() or {}})


@login_manager.user_loader
def load_user(user_id):
    row = get_user_by_id(user_id)
    if row:
        return type('AnonUser', (UserMixin,), {
            'id': str(row['id']),
            'login': row['login'],
            'role': row['position'],
            'first_name': row['first_name'],
            'last_name': row['last_name']
        })()
    return None


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        login_ = request.form['login']
        password_ = request.form['password']
        user = get_user_by_login(login_)
        if user and user['password'] == password_:
            user_obj = type('AnonUser', (UserMixin,), {
                'id': str(user['id']),
                'login': user['login'],
                'role': user['position']
            })()
            login_user(user_obj)
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    user = get_user_by_login(data.get('login'))
    if user and user['password'] == data.get('password'):
        user_obj = type('AnonUser', (UserMixin,), {
            'id': str(user['id']),
            'login': user['login'],
            'role': user['position']
        })()
        login_user(user_obj)
        return jsonify({'message': 'Успешный вход'}), 200
    return jsonify({'message': 'Неверный логин или пароль'}), 401


@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json() or {}
        required_fields = ['firstName', 'lastName', 'patronymic', 'position', 'login', 'password']
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({'error': 'Не заполнены обязательные поля'}), 400

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM employee WHERE login = ?', (data['login'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Пользователь с таким логином уже существует'}), 409

        cursor.execute(
            '''
            INSERT INTO employee (first_name, last_name, patronymic, position, login, password)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (data['firstName'], data['lastName'], data['patronymic'], data['position'], data['login'], data['password'])
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return jsonify({'success': True, 'message': 'Пользователь успешно добавлен', 'userId': user_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics')
def get_metrics():
    conn = db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) AS c FROM book")
        total_cards = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) AS c FROM book_copy")
        total_copies = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) AS c FROM book_copy WHERE status='доступна'")
        available = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) AS c FROM book_copy WHERE status IN ('выдана', 'просрочена')")
        issued = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) AS c FROM reader")
        readers = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) AS c FROM reader WHERE penalty_points > 0")
        penalized = cursor.fetchone()['c']

        return jsonify([
            {'title': 'Карточек книг', 'value': f'{total_cards:,}', 'class': 'primary'},
            {'title': 'Экземпляров всего', 'value': f'{total_copies:,}', 'class': 'info'},
            {'title': 'Доступных экземпляров', 'value': f'{available:,}', 'class': 'success'},
            {'title': 'Выдано/просрочено', 'value': f'{issued:,}', 'class': 'warning'},
            {'title': 'Читателей', 'value': f'{readers:,}', 'class': 'primary'},
            {'title': 'Со штрафами', 'value': f'{penalized:,}', 'class': 'danger'}
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# Readers
@app.route('/api/readers', methods=['POST'])
def add_reader():
    try:
        data = request.get_json() or {}
        required_fields = ['firstName', 'lastName', 'phone', 'address', 'email', 'birthdate', 'pdConsent']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Не заполнены обязательные поля'}), 400
        if not bool(data.get('pdConsent')):
            return jsonify({'error': 'Необходимо согласие на обработку персональных данных'}), 400

        phone = ''.join(c for c in str(data['phone']) if c.isdigit())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM reader WHERE phone = ?', (phone,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Читатель с таким телефоном уже существует'}), 409

        cursor.execute('SELECT COALESCE(MAX(id),0)+1 AS next_id FROM reader')
        ticket_number = f"R-{cursor.fetchone()['next_id']:04d}"

        cursor.execute(
            '''
            INSERT INTO reader
            (ticket_number, first_name, last_name, patronymic, date_birth, phone, address, email, registered_at, status, pd_consent, pd_consent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                ticket_number, data['firstName'], data['lastName'], data.get('patronymic', ''), data['birthdate'],
                phone, data['address'], data['email'], now, data.get('status', 'active'), 1, now
            )
        )
        reader_id = cursor.lastrowid
        cursor.execute('INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)', (reader_id, 'registration', 'Регистрация с согласием на ПД'))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Читатель успешно зарегистрирован', 'readerId': reader_id, 'ticketNumber': ticket_number}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers', methods=['GET'])
def list_readers():
    try:
        query = request.args.get('query', '').strip()
        conn = db_conn()
        cursor = conn.cursor()

        sql = '''
            SELECT r.id, r.ticket_number, r.first_name, r.last_name, r.patronymic, r.date_birth,
                   r.phone, r.address, r.email, r.registered_at, r.status, r.penalty_points,
                   r.pd_consent, r.pd_consent_at,
                   (SELECT COUNT(*) FROM given_book gb WHERE gb.reader_id = r.id AND gb.return_date_fact IS NULL) AS active_issues,
                   (SELECT COUNT(*) FROM given_book gb WHERE gb.reader_id = r.id AND gb.return_date_fact IS NULL AND date(gb.return_date) < date('now')) AS overdue_count
            FROM reader r
        '''
        params = []
        if query:
            q = f'%{query}%'
            sql += '''
                WHERE r.first_name LIKE ? OR r.last_name LIKE ? OR r.patronymic LIKE ?
                   OR r.phone LIKE ? OR r.email LIKE ? OR r.ticket_number LIKE ?
                   OR CAST(r.id AS TEXT) = ?
            '''
            params = [q, q, q, q, q, q, query]
        sql += ' ORDER BY r.id DESC'

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        readers = [dict(row) for row in rows]
        for r in readers:
            r['pd_consent'] = bool(r['pd_consent'])
        return jsonify({'success': True, 'readers': readers, 'count': len(readers)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/search', methods=['GET'])
def search_readers():
    return list_readers()


@app.route('/api/readers/<int:reader_id>', methods=['PUT'])
def update_reader(reader_id):
    try:
        data = request.get_json() or {}
        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE reader
            SET first_name=?, last_name=?, patronymic=?, date_birth=?, phone=?, address=?, email=?, status=?
            WHERE id=?
            ''',
            (
                data.get('first_name'), data.get('last_name'), data.get('patronymic', ''), data.get('date_birth'),
                ''.join(c for c in str(data.get('phone', '')) if c.isdigit()), data.get('address'), data.get('email'), data.get('status', 'active'), reader_id
            )
        )
        cursor.execute('INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)', (reader_id, 'update', 'Карточка обновлена'))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/<int:reader_id>', methods=['DELETE'])
def delete_reader(reader_id):
    try:
        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE reader SET status='deleted' WHERE id=?", (reader_id,))
        cursor.execute('INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)', (reader_id, 'delete', 'Карточка деактивирована'))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/<int:reader_id>/card', methods=['GET'])
def reader_card(reader_id):
    try:
        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT r.*, 
                   (SELECT COUNT(*) FROM given_book gb WHERE gb.reader_id = r.id AND gb.return_date_fact IS NULL) AS active_issues,
                   (SELECT COUNT(*) FROM given_book gb WHERE gb.reader_id = r.id AND gb.return_date_fact IS NULL AND date(gb.return_date) < date('now')) AS overdue_count
            FROM reader r WHERE r.id=?
            ''',
            (reader_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Читатель не найден'}), 404

        cursor.execute('SELECT action_type, comment, created_at FROM reader_action_log WHERE reader_id=? ORDER BY created_at DESC', (reader_id,))
        history = [dict(h) for h in cursor.fetchall()]

        cursor.execute('SELECT delta_points, reason, comment, created_at FROM penalty_operation WHERE reader_id=? ORDER BY created_at DESC', (reader_id,))
        penalties = [dict(p) for p in cursor.fetchall()]

        reader = dict(row)
        reader['pd_consent'] = bool(reader['pd_consent'])
        conn.close()
        return jsonify({'success': True, 'reader': reader, 'history': history, 'penalties': penalties})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/readers/<int:reader_id>/penalties', methods=['GET', 'POST'])
def reader_penalties(reader_id):
    try:
        conn = db_conn()
        cursor = conn.cursor()
        if request.method == 'POST':
            data = request.get_json() or {}
            delta = int(data.get('delta_points', 0))
            if delta == 0:
                conn.close()
                return jsonify({'error': 'Баллы должны отличаться от 0'}), 400
            reason = data.get('reason', 'другое')
            comment = data.get('comment', '')
            employee_id = int(current_user.id) if getattr(current_user, 'is_authenticated', False) else None

            cursor.execute('UPDATE reader SET penalty_points = penalty_points + ? WHERE id=?', (delta, reader_id))
            cursor.execute('INSERT INTO penalty_operation (reader_id, delta_points, reason, comment, employee_id) VALUES (?, ?, ?, ?, ?)', (reader_id, delta, reason, comment, employee_id))
            cursor.execute('INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)', (reader_id, 'penalty', f'{delta} баллов: {reason}'))
            conn.commit()

        cursor.execute('SELECT penalty_points FROM reader WHERE id=?', (reader_id,))
        points_row = cursor.fetchone()
        points = points_row['penalty_points'] if points_row else 0
        cursor.execute('SELECT id, delta_points, reason, comment, created_at FROM penalty_operation WHERE reader_id=? ORDER BY created_at DESC', (reader_id,))
        history = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'penalty_points': points, 'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Books
@app.route('/api/books/all', methods=['GET'])
def get_all_books():
    try:
        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT b.id, b.isbn, b.name as title, b.year, b.quantity, b.publishing_house,
                   a.id as author_id, a.first_name, a.last_name, a.patronymic,
                   g.id as genre_id, g.name as genre_name
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
            '''
        )
        books = cursor.fetchall()
        conn.close()

        books_list = []
        for book in books:
            books_list.append({
                'id': book['id'], 'isbn': book['isbn'], 'title': book['title'], 'year': book['year'], 'quantity': book['quantity'],
                'publishing_house': book['publishing_house'], 'author_id': book['author_id'],
                'author': ' '.join(filter(None, [book['first_name'], book['last_name'], book['patronymic']])),
                'genre_id': book['genre_id'], 'genre': book['genre_name'], 'available': book['quantity']
            })
        return jsonify({'success': True, 'books': books_list}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book/check-isbn', methods=['GET'])
def check_book_by_isbn():
    try:
        isbn = request.args.get('isbn')
        if not isbn:
            return jsonify({'error': 'ISBN не указан'}), 400

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT b.id, b.name, b.year, b.publishing_house,
                   a.id as author_id, a.last_name || ' ' || a.first_name as author_name,
                   g.id as genre_id, g.name as genre_name
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
            WHERE b.isbn = ?
            LIMIT 1
            ''',
            (isbn,)
        )
        book = cursor.fetchone()
        conn.close()
        if book:
            return jsonify({
                'exists': True,
                'book': {'name': book['name'], 'year': book['year'], 'publishing_house': book['publishing_house']},
                'author_name': book['author_name'],
                'genre_id': book['genre_id'],
                'genre_name': book['genre_name']
            })
        return jsonify({'exists': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book/add', methods=['POST'])
def add_book():
    try:
        data = request.get_json() or {}
        required_fields = ['title', 'author', 'genre', 'quantity', 'publishing_house']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Не все обязательные поля заполнены'}), 400

        conn = db_conn()
        cursor = conn.cursor()

        author_parts = data['author'].split(' ')
        last_name = author_parts[0] if len(author_parts) > 0 else ''
        first_name = author_parts[1] if len(author_parts) > 1 else ''
        patronymic = author_parts[2] if len(author_parts) > 2 else ''

        cursor.execute('SELECT id FROM author WHERE last_name = ? AND first_name = ? AND (patronymic = ? OR patronymic IS NULL)', (last_name, first_name, patronymic))
        author = cursor.fetchone()
        if not author:
            cursor.execute('INSERT INTO author (last_name, first_name, patronymic) VALUES (?, ?, ?)', (last_name, first_name, patronymic))
            author_id = cursor.lastrowid
        else:
            author_id = author['id']

        cursor.execute('SELECT id FROM genre WHERE name = ?', (data['genre'],))
        genre = cursor.fetchone()
        if not genre:
            cursor.execute('INSERT INTO genre (genre_type, name) VALUES (?, ?)', ('-', data['genre']))
            genre_id = cursor.lastrowid
        else:
            genre_id = genre['id']

        cursor.execute(
            '''
            INSERT INTO book (isbn, name, year, quantity, author_id, genre_id, publishing_house)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (data.get('isbn'), data['title'], data.get('year'), 0, author_id, genre_id, data['publishing_house'])
        )
        book_id = cursor.lastrowid
        qty = int(data['quantity'])
        for i in range(qty):
            uid = f"{(data.get('isbn') or 'BOOK').upper()}-{uuid4().hex[:8]}"
            cursor.execute(
                "INSERT INTO book_copy (copy_uid, book_id, status, arrival_date, source_type, note) VALUES (?, ?, 'доступна', date('now'), 'manual', 'Добавлено вручную')",
                (uid, book_id)
            )
        recalc_book_quantities(cursor)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book/by-identifier', methods=['GET'])
def get_book_by_identifier():
    try:
        identifier = request.args.get('identifier')
        if not identifier:
            return jsonify({'error': 'Не указан идентификатор'}), 400

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT b.id, b.name, b.year, b.isbn, b.quantity,
                   a.first_name, a.last_name, a.patronymic,
                   g.name as genre, b.publishing_house
            FROM book b
            JOIN author a ON b.author_id = a.id
            JOIN genre g ON b.genre_id = g.id
            WHERE b.isbn = ? OR b.id = ?
            ''',
            (identifier, identifier)
        )
        book = cursor.fetchone()
        conn.close()

        if not book:
            return jsonify({'error': 'Книга не найдена'}), 404

        return jsonify({'book': {
            'id': book['id'],
            'title': book['name'],
            'year': book['year'],
            'isbn': book['isbn'],
            'quantity': book['quantity'],
            'author': ' '.join(filter(None, [book['first_name'], book['last_name'], book['patronymic']])),
            'genre': book['genre'],
            'publishing_house': book['publishing_house']
        }}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book-copies', methods=['GET'])
def get_book_copies():
    try:
        status = request.args.get('status')
        uid = request.args.get('uid')
        conn = db_conn()
        cursor = conn.cursor()
        sql = '''
            SELECT bc.id, bc.copy_uid, bc.status, bc.arrival_date, b.name as book
            FROM book_copy bc JOIN book b ON b.id = bc.book_id
            WHERE 1=1
        '''
        params = []
        if status:
            sql += ' AND bc.status = ?'
            params.append(status)
        if uid:
            sql += ' AND bc.copy_uid LIKE ?'
            params.append(f'%{uid}%')
        sql += ' ORDER BY bc.id DESC'

        cursor.execute(sql, params)
        copies = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'copies': copies})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reader/by-phone', methods=['GET'])
def get_reader_by_phone():
    try:
        phone = ''.join(c for c in str(request.args.get('phone', '')) if c.isdigit())
        if not phone:
            return jsonify({'error': 'Не указан телефон'}), 400

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id, last_name, first_name, patronymic, phone, penalty_points FROM reader WHERE phone = ?', (phone,))
        reader = cursor.fetchone()
        conn.close()
        if not reader:
            return jsonify({'exists': False}), 200
        return jsonify({'exists': True, 'reader': dict(reader)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# issue & return
@app.route('/api/book/issue-v2', methods=['POST'])
def issue_book_v2():
    try:
        data = request.get_json() or {}
        conn = db_conn()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as c FROM given_book WHERE reader_id = ? AND return_date_fact IS NULL', (data['reader_id'],))
        active_issues = cursor.fetchone()['c']
        settings = get_system_settings_data() or {'max_books_per_reader': 5}
        if active_issues >= settings.get('max_books_per_reader', 5):
            conn.close()
            return jsonify({'error': 'Превышен лимит книг у читателя'}), 400

        cursor.execute("SELECT id FROM book_copy WHERE book_id = ? AND status = 'доступна' ORDER BY id LIMIT 1", (data['book_id'],))
        copy = cursor.fetchone()
        if not copy:
            conn.close()
            return jsonify({'error': 'Нет доступных экземпляров'}), 400

        copy_id = copy['id']
        cursor.execute(
            '''
            INSERT INTO given_book
            (quantity, given_date, return_date, reader_id, employee_id, book_id, book_copy_id)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ''',
            (data['issue_date'], data['return_date'], data['reader_id'], current_user.id, data['book_id'], copy_id)
        )
        cursor.execute("UPDATE book_copy SET status = 'выдана' WHERE id = ?", (copy_id,))
        cursor.execute('INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)', (data['reader_id'], 'issue', f'Выдан экземпляр {copy_id}'))

        recalc_book_quantities(cursor)
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'book_copy_id': copy_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book/issue', methods=['POST'])
def issue_book():
    return issue_book_v2()


@app.route('/api/book/find-for-return', methods=['GET'])
def find_book_for_return():
    try:
        reader_id = request.args.get('reader_id')
        isbn = request.args.get('isbn')
        if not reader_id or not isbn:
            return jsonify({'error': 'Необходимо указать ID читателя и ISBN'}), 400

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT gb.id as record_id,
                   b.name as book_title,
                   a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as book_author,
                   gb.given_date as issue_date,
                   gb.return_date as planned_return_date,
                   bc.copy_uid
            FROM given_book gb
            JOIN book b ON gb.book_id = b.id
            JOIN author a ON b.author_id = a.id
            LEFT JOIN book_copy bc ON bc.id = gb.book_copy_id
            WHERE gb.reader_id = ?
              AND b.isbn = ?
              AND gb.return_date_fact IS NULL
            LIMIT 1
            ''',
            (reader_id, isbn)
        )
        issue_record = cursor.fetchone()
        conn.close()
        if not issue_record:
            return jsonify({'error': 'Активная выдача не найдена'}), 404
        result = dict(issue_record)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book/return-v2', methods=['POST'])
def return_book_v2():
    try:
        data = request.get_json() or {}
        conn = db_conn()
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT gb.book_copy_id, gb.reader_id, gb.return_date
            FROM given_book gb
            WHERE gb.id = ? AND gb.return_date_fact IS NULL
            ''',
            (data['record_id'],)
        )
        issue_record = cursor.fetchone()
        if not issue_record:
            conn.close()
            return jsonify({'error': 'Выдача не найдена или книга уже возвращена'}), 400

        copy_id = issue_record['book_copy_id']
        reader_id = issue_record['reader_id']
        planned_return_date = issue_record['return_date']
        actual_return_date = data['actual_return_date']
        final_status = data.get('final_status', 'доступна')
        comment = data.get('comment', '')

        cursor.execute('UPDATE given_book SET return_date_fact = ?, return_comment = ? WHERE id = ?', (actual_return_date, comment, data['record_id']))
        if copy_id:
            cursor.execute('UPDATE book_copy SET status = ?, note = ? WHERE id = ?', (final_status, comment, copy_id))

        # Автоматический штраф за просрочку
        if actual_return_date > planned_return_date:
            penalty_points = (get_system_settings_data() or {'late_return_penalty': 10}).get('late_return_penalty', 10)
            cursor.execute('UPDATE reader SET penalty_points = penalty_points + ? WHERE id = ?', (penalty_points, reader_id))
            cursor.execute('INSERT INTO penalty_operation (reader_id, delta_points, reason, comment, employee_id) VALUES (?, ?, ?, ?, ?)', (reader_id, penalty_points, 'просрочка', 'Автоматическое начисление за просрочку', current_user.id))

        manual_penalty = int(data.get('manual_penalty', 0) or 0)
        if manual_penalty != 0:
            cursor.execute('UPDATE reader SET penalty_points = penalty_points + ? WHERE id = ?', (manual_penalty, reader_id))
            cursor.execute('INSERT INTO penalty_operation (reader_id, delta_points, reason, comment, employee_id) VALUES (?, ?, ?, ?, ?)', (reader_id, manual_penalty, data.get('penalty_reason', 'другое'), data.get('penalty_comment', ''), current_user.id))

        cursor.execute('INSERT INTO reader_action_log (reader_id, action_type, comment) VALUES (?, ?, ?)', (reader_id, 'return', f'Возврат книги, итоговый статус: {final_status}'))

        recalc_book_quantities(cursor)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/book/return', methods=['POST'])
def return_book():
    return return_book_v2()


# reports preview/export

def build_report_preview(report_type, start_date=None, end_date=None):
    conn = db_conn()
    cursor = conn.cursor()

    report_map = {
        'issued-books': {
            'headers': ['Читатель', 'Книга', 'Экземпляр', 'Дата выдачи', 'План возврата', 'Статус'],
            'query': '''
                SELECT r.last_name || ' ' || r.first_name,
                       b.name,
                       COALESCE(bc.copy_uid, '-'),
                       gb.given_date,
                       gb.return_date,
                       COALESCE(bc.status, '-')
                FROM given_book gb
                JOIN reader r ON r.id = gb.reader_id
                JOIN book b ON b.id = gb.book_id
                LEFT JOIN book_copy bc ON bc.id = gb.book_copy_id
                WHERE gb.return_date_fact IS NULL
                ORDER BY gb.given_date DESC
            '''
        },
        'overdue': {
            'headers': ['Читатель', 'Книга', 'План возврата', 'Дней просрочки'],
            'query': '''
                SELECT r.last_name || ' ' || r.first_name,
                       b.name,
                       gb.return_date,
                       CAST(julianday('now') - julianday(gb.return_date) AS INT)
                FROM given_book gb
                JOIN reader r ON r.id = gb.reader_id
                JOIN book b ON b.id = gb.book_id
                WHERE gb.return_date_fact IS NULL
                  AND date(gb.return_date) < date('now')
                ORDER BY gb.return_date ASC
            '''
        },
        'readers': {
            'headers': ['ID', 'Билет', 'ФИО', 'Статус', 'Активные выдачи', 'Просрочки', 'Штрафные баллы'],
            'query': '''
                SELECT r.id,
                       r.ticket_number,
                       r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, ''),
                       r.status,
                       (SELECT COUNT(*) FROM given_book gb WHERE gb.reader_id = r.id AND gb.return_date_fact IS NULL),
                       (SELECT COUNT(*) FROM given_book gb WHERE gb.reader_id = r.id AND gb.return_date_fact IS NULL AND date(gb.return_date) < date('now')),
                       r.penalty_points
                FROM reader r
                ORDER BY r.id
            '''
        },
        'book-popularity': {
            'headers': ['Книга', 'Количество выдач'],
            'query': '''
                SELECT b.name, COUNT(gb.id)
                FROM book b
                LEFT JOIN given_book gb ON gb.book_id = b.id
                GROUP BY b.id
                ORDER BY COUNT(gb.id) DESC, b.name
            '''
        },
        'penalties': {
            'headers': ['Читатель', 'Текущие штрафные баллы'],
            'query': '''
                SELECT r.last_name || ' ' || r.first_name, r.penalty_points
                FROM reader r
                WHERE r.penalty_points > 0
                ORDER BY r.penalty_points DESC
            '''
        },
        'write-off': {
            'headers': ['Акт', 'Дата', 'Экземпляр', 'Книга', 'Причина'],
            'query': '''
                SELECT wa.act_number, wa.date, bc.copy_uid, b.name, wi.reason
                FROM writeoff_item wi
                JOIN writeoff_act wa ON wa.id = wi.act_id
                JOIN book_copy bc ON bc.id = wi.book_copy_id
                JOIN book b ON b.id = bc.book_id
                ORDER BY wa.date DESC
            '''
        },
        'arrivals': {
            'headers': ['Акт', 'Дата', 'Поставщик', 'Книга', 'Количество'],
            'query': '''
                SELECT aa.act_number, aa.date, s.name, b.name, ai.quantity
                FROM acceptance_item ai
                JOIN acceptance_act aa ON aa.id = ai.act_id
                JOIN supplier s ON s.id = aa.supplier_id
                JOIN book b ON b.id = ai.book_id
                ORDER BY aa.date DESC
            '''
        }
    }

    if report_type not in report_map:
        conn.close()
        raise ValueError('Неизвестный тип отчета')

    cursor.execute(report_map[report_type]['query'])
    rows = [list(row) for row in cursor.fetchall()]
    summary = {'rows_count': len(rows)}
    conn.close()
    return {'headers': report_map[report_type]['headers'], 'rows': rows, 'summary': summary}


@app.route('/api/reports/preview', methods=['POST'])
@login_required
def reports_preview():
    try:
        data = request.get_json() or {}
        report = build_report_preview(data.get('report_type'), data.get('start_date'), data.get('end_date'))
        return jsonify({'success': True, **report})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/reports/export', methods=['POST'])
@login_required
def reports_export():
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type')
        report = build_report_preview(report_type, data.get('start_date'), data.get('end_date'))

        os.makedirs('reports', exist_ok=True)
        filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join('reports', filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(report['headers'])
            writer.writerows(report['rows'])

        return jsonify({'success': True, 'report_url': f'/reports_download/{filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report_api():
    # сохранение старого API: отдаём CSV-экспорт
    return reports_export()


@app.route('/reports_download/<filename>')
@login_required
def download_report(filename):
    try:
        return send_from_directory(os.path.join(app.root_path, 'reports'), filename, as_attachment=True)
    except Exception as e:
        return str(e), 500


# Supply module
@app.route('/api/suppliers', methods=['GET', 'POST'])
def suppliers_api():
    try:
        conn = db_conn()
        cursor = conn.cursor()
        if request.method == 'POST':
            d = request.get_json() or {}
            cursor.execute(
                '''
                INSERT INTO supplier (name, contact_person, phone, email, address, comment, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (d['name'], d.get('contact_person', ''), d.get('phone', ''), d.get('email', ''), d.get('address', ''), d.get('comment', ''), int(d.get('is_active', 1)))
            )
            conn.commit()

        cursor.execute('SELECT * FROM supplier ORDER BY id DESC')
        data = [dict(r) for r in cursor.fetchall()]
        for x in data:
            x['is_active'] = bool(x['is_active'])
        conn.close()
        return jsonify({'success': True, 'suppliers': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contracts', methods=['GET', 'POST'])
def contracts_api():
    try:
        conn = db_conn()
        cursor = conn.cursor()
        if request.method == 'POST':
            d = request.get_json() or {}
            cursor.execute(
                '''
                INSERT INTO supplier_contract (contract_number, signed_date, supplier_id, start_date, end_date, terms, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (d['contract_number'], d.get('signed_date'), d['supplier_id'], d.get('start_date'), d.get('end_date'), d.get('terms', ''), d.get('comment', ''))
            )
            conn.commit()

        cursor.execute(
            '''
            SELECT c.id, c.contract_number, c.signed_date, c.start_date, c.end_date, c.terms, c.comment, s.name AS supplier_name
            FROM supplier_contract c
            JOIN supplier s ON s.id = c.supplier_id
            ORDER BY c.id DESC
            '''
        )
        contracts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'contracts': contracts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/acceptance-acts', methods=['GET', 'POST'])
def acceptance_acts_api():
    try:
        conn = db_conn()
        cursor = conn.cursor()
        if request.method == 'POST':
            d = request.get_json() or {}
            cursor.execute(
                '''
                INSERT INTO acceptance_act (act_number, date, supplier_id, contract_id, employee_id, comment, confirmed)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ''',
                (d['act_number'], d.get('date'), d['supplier_id'], d.get('contract_id'), current_user.id if getattr(current_user, 'is_authenticated', False) else 1, d.get('comment', ''))
            )
            act_id = cursor.lastrowid
            for item in d.get('items', []):
                cursor.execute('INSERT INTO acceptance_item (act_id, book_id, quantity, price) VALUES (?, ?, ?, ?)', (act_id, item['book_id'], item['quantity'], item.get('price', 0)))
                for _ in range(int(item['quantity'])):
                    copy_uid = f"AC-{act_id}-{item['book_id']}-{uuid4().hex[:6]}"
                    cursor.execute(
                        '''
                        INSERT INTO book_copy (copy_uid, book_id, status, arrival_date, source_type, source_id, note)
                        VALUES (?, ?, 'доступна', ?, 'acceptance_act', ?, ?)
                        ''',
                        (copy_uid, item['book_id'], d.get('date'), act_id, d.get('comment', ''))
                    )
            recalc_book_quantities(cursor)
            conn.commit()

        cursor.execute(
            '''
            SELECT aa.id, aa.act_number, aa.date, aa.comment, s.name AS supplier_name
            FROM acceptance_act aa
            JOIN supplier s ON s.id = aa.supplier_id
            ORDER BY aa.id DESC
            '''
        )
        acts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'acts': acts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/writeoff-acts', methods=['GET', 'POST'])
def writeoff_acts_api():
    try:
        conn = db_conn()
        cursor = conn.cursor()
        if request.method == 'POST':
            d = request.get_json() or {}
            cursor.execute(
                '''
                INSERT INTO writeoff_act (act_number, date, basis, employee_id, comment, confirmed)
                VALUES (?, ?, ?, ?, ?, 1)
                ''',
                (d['act_number'], d.get('date'), d.get('basis', ''), current_user.id if getattr(current_user, 'is_authenticated', False) else 1, d.get('comment', ''))
            )
            act_id = cursor.lastrowid
            for item in d.get('items', []):
                cursor.execute('INSERT INTO writeoff_item (act_id, book_copy_id, reason) VALUES (?, ?, ?)', (act_id, item['book_copy_id'], item.get('reason', 'другое')))
                cursor.execute("UPDATE book_copy SET status='списана', note=? WHERE id=?", (f"Списано актом {d['act_number']}", item['book_copy_id']))
            recalc_book_quantities(cursor)
            conn.commit()

        cursor.execute('SELECT id, act_number, date, basis, comment FROM writeoff_act ORDER BY id DESC')
        acts = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'acts': acts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Settings

def get_system_settings_data():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT standart_rental_period, max_books_per_reader, late_return_penalty FROM system_settings ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'standart_rental_period': row['standart_rental_period'],
        'max_books_per_reader': row['max_books_per_reader'],
        'late_return_penalty': row['late_return_penalty']
    }


@app.route('/api/system/get', methods=['GET'])
def get_system_settings():
    try:
        system_settings = get_system_settings_data()
        if not system_settings:
            return jsonify({'error': 'Не заполнены системные настройки'}), 500
        return jsonify({'success': True, 'system_settings': system_settings}), 200
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500


@app.route('/api/system/update', methods=['POST'])
def load_system_settings():
    try:
        data = request.get_json() or {}
        required_fields = ['standart_rental_period', 'max_books_per_reader', 'late_return_penalty']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Не все обязательные поля заполнены'}), 400

        conn = db_conn()
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE system_settings
            SET standart_rental_period = ?, max_books_per_reader = ?, late_return_penalty = ?
            WHERE id = 1
            ''',
            (data['standart_rental_period'], data['max_books_per_reader'], data['late_return_penalty'])
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_user_by_login(login):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, login, password, position, first_name, last_name FROM employee WHERE login = ?', (login,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, login, password, position, first_name, last_name FROM employee WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        fill()
    app.run(debug=True)
