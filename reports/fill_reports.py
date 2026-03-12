from docxtpl import DocxTemplate
from docx import Document
from datetime import datetime
import sqlite3
import os
from typing import List, Dict, Optional, Union
from docx2pdf import convert as docx_to_pdf

from config import DB_PATH

def generate_universal_report(
    template_path: str,
    output_dir: str,
    employee_id: int,
    report_title: str,
    table_headers: List[str],
    table_data: List[Dict[str, str]],
    reporting_period: Optional[str] = None,
    db_path: str = DB_PATH
) -> str:
    """
    Генерирует универсальный отчет Word с таблицей.

    Args:
        template_path: Путь к шаблону Word (.docx)
        output_dir: Директория для сохранения отчета
        employee_id: ID сотрудника, формирующего отчет
        report_title: Название отчета
        table_headers: Заголовки столбцов таблицы
        table_data: Данные для таблицы (список словарей)
        reporting_period: Отчетный период (необязательный)
        db_path: Путь к БД (по умолчанию DB_PATH)

    Returns:
        Абсолютный путь к сгенерированному файлу
    """
    # Проверка и создание директории
    os.makedirs(output_dir, exist_ok=True)
    
    # Загрузка шаблона
    doc = DocxTemplate(template_path)
    
    # Получение данных о сотруднике
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_name, first_name, patronymic, position FROM employee WHERE id = ?", 
        (employee_id,)
    )
    employee = cursor.fetchone()
    conn.close()

    if not employee:
        raise ValueError("Сотрудник не найден")

    last_name, first_name, patronymic, position = employee
    employee_initials = f"{first_name[0]}.{patronymic[0]}." if patronymic else f"{first_name[0]}."

    # Подготовка контекста
    context = {
        "report_title": report_title,
        "report_date": datetime.now().strftime('%d/%m/%Y'),
        "reporting_period": "Отчётный период " + reporting_period if reporting_period else '',
        "table_headers": table_headers,
        "table_rows": table_data,
        "employee_position": position,
        "employee": last_name + " " + employee_initials
    }

    # Рендер и сохранение
    doc.render(context)
    
    output_filename = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    output_filepath = os.path.join(output_dir, output_filename)
    doc.save(output_filepath)
    table = doc.tables[1]
    if len(table.rows) > 1:  # Если в таблице больше одной строки
        table._tbl.remove(table.rows[-1]._tr)  # Удаляем последнюю строку
    column_index = len(table.columns) - 1
    
    for row in table.rows:
        if len(row.cells) > column_index:
            row._element.remove(row.cells[column_index]._element)
    doc.save(output_filepath)
    
    return output_filepath

def convert_docx_to_pdf(docx_filepath: str, output_dir: str) -> str:
    """
    Конвертирует DOCX файл в PDF.

    Args:
        docx_filepath: Абсолютный путь к DOCX файлу.
        output_dir: Директория для сохранения PDF файла.

    Returns:
        Абсолютный путь к сгенерированному PDF файлу.
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = os.path.splitext(os.path.basename(docx_filepath))[0] + ".pdf"
    pdf_filepath = os.path.join(output_dir, pdf_filename)
    docx_to_pdf(docx_filepath, pdf_filepath)
    return pdf_filepath


def generate_books_by_authors_report(employee_id: int, output_dir: str = "reports") -> str:
    """Генерирует отчет о книгах по авторам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Запрос для получения данных об авторах и книгах
    cursor.execute("""
        SELECT 
            a.id,
            a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as author,
            COUNT(b.id) as total_books,
            SUM(CASE WHEN gb.return_date_fact IS NULL THEN 1 ELSE 0 END) as on_hand,
            COUNT(b.id) - SUM(CASE WHEN gb.return_date_fact IS NULL THEN 1 ELSE 0 END) as available
        FROM author a
        LEFT JOIN book b ON a.id = b.author_id
        LEFT JOIN given_book gb ON b.id = gb.book_id AND gb.return_date_fact IS NULL
        GROUP BY a.id, a.last_name, a.first_name, a.patronymic
    """)
    
    data = cursor.fetchall()
    conn.close()
    
    # Подготовка данных для отчета
    table_headers = ["№", "Автор", "Количество книг", "Доступно", "На руках"]
    table_data = [
        {
            "id": str(idx + 1),
            "author": row[1],
            "total": str(row[2]),
            "available": str(row[4]),
            "on_hand": str(row[3])
        }
        for idx, row in enumerate(data)
    ]
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о книгах по авторам",
        table_headers=table_headers,
        table_data=table_data
    )

def generate_issued_returned_books_report(employee_id: int, start_date: str, end_date: str, output_dir: str = "reports") -> str:
    """Генерирует отчет о выданных и возвращенных книгах за период"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            gb.id,
            b.name as book_name,
            a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as author,
            r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '') as reader,
            strftime('%d.%m.%Y', gb.given_date) as given_date,
            strftime('%d.%m.%Y', gb.return_date_fact) as return_date
        FROM given_book gb
        JOIN book b ON gb.book_id = b.id
        JOIN author a ON b.author_id = a.id
        JOIN reader r ON gb.reader_id = r.id
        WHERE (gb.given_date BETWEEN ? AND ?) 
           OR (gb.return_date_fact BETWEEN ? AND ?)
        ORDER BY gb.given_date
    """, (start_date, end_date, start_date, end_date))
    
    data = cursor.fetchall()
    conn.close()
    
    table_headers = ["№", "Название книги", "Автор", "Читатель", "Дата выдачи", "Дата возврата"]
    table_data = [
        {
            "id": str(idx + 1),
            "book_name": row[1],
            "author": row[2],
            "reader": row[3],
            "given_date": row[4],
            "return_date": row[5] if row[5] else "Не возвращена"
        }
        for idx, row in enumerate(data)
    ]
    
    reporting_period = f"{start_date} - {end_date}"
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о выданных и возвращенных книгах",
        table_headers=table_headers,
        table_data=table_data,
        reporting_period=reporting_period
    )

def generate_issued_books_report(employee_id: int, output_dir: str = "reports") -> str:
    """Генерирует отчет о выданных книгах (не возвращенных)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            gb.id,
            b.name as book_name,
            a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as author,
            r.last_name || ' ' || r.first_name || COALESCE(' ' || r.patronymic, '') as reader,
            strftime('%d.%m.%Y', gb.given_date) as given_date,
            strftime('%d.%m.%Y', gb.return_date) as return_date
        FROM given_book gb
        JOIN book b ON gb.book_id = b.id
        JOIN author a ON b.author_id = a.id
        JOIN reader r ON gb.reader_id = r.id
        WHERE gb.return_date_fact IS NULL
        ORDER BY gb.given_date
    """)
    
    data = cursor.fetchall()
    conn.close()
    
    table_headers = ["№", "Название книги", "Автор", "Читатель", "Дата выдачи", "Дата возврата"]
    table_data = [
        {
            "id": str(idx + 1),
            "book_name": row[1],
            "author": row[2],
            "reader": row[3],
            "given_date": row[4],
            "return_date": row[5]
        }
        for idx, row in enumerate(data)
    ]
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о выданных книгах",
        table_headers=table_headers,
        table_data=table_data
    )

def generate_books_by_genres_report(employee_id: int, output_dir: str = "reports") -> str:
    """Генерирует отчет о книгах по жанрам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            g.id,
            g.name as genre,
            COUNT(b.id) as total_books,
            SUM(CASE WHEN gb.return_date_fact IS NULL THEN 1 ELSE 0 END) as on_hand,
            COUNT(b.id) - SUM(CASE WHEN gb.return_date_fact IS NULL THEN 1 ELSE 0 END) as available
        FROM genre g
        LEFT JOIN book b ON g.id = b.genre_id
        LEFT JOIN given_book gb ON b.id = gb.book_id AND gb.return_date_fact IS NULL
        GROUP BY g.id, g.name
    """)
    
    data = cursor.fetchall()
    conn.close()
    
    table_headers = ["№", "Жанр", "Количество книг", "Доступно", "На руках"]
    table_data = [
        {
            "id": str(idx + 1),
            "genre": row[1],
            "total": str(row[2]),
            "available": str(row[4]),
            "on_hand": str(row[3])
        }
        for idx, row in enumerate(data)
    ]
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о книгах по жанрам",
        table_headers=table_headers,
        table_data=table_data
    )

def generate_book_collection_report(employee_id: int, output_dir: str = "reports") -> str:
    """Генерирует отчет о содержании книжного фонда"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            b.id,
            b.name as book_name,
            a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as author,
            g.name as genre,
            b.year,
            'Основной фонд' as location,
            CASE 
                WHEN EXISTS (SELECT 1 FROM given_book gb WHERE gb.book_id = b.id AND gb.return_date_fact IS NULL) 
                THEN 'На руках' 
                ELSE 'Доступна' 
            END as status
        FROM book b
        JOIN author a ON b.author_id = a.id
        JOIN genre g ON b.genre_id = g.id
        ORDER BY b.name
    """)
    
    data = cursor.fetchall()
    conn.close()
    
    table_headers = ["№", "Название книги", "Автор", "Жанр", "Год издания", "Место хранения", "Статус"]
    table_data = [
        {
            "id": str(idx + 1),
            "book_name": row[1],
            "author": row[2],
            "genre": row[3],
            "year": row[4],
            "location": row[5],
            "status": row[6]
        }
        for idx, row in enumerate(data)
    ]
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о содержании книжного фонда",
        table_headers=table_headers,
        table_data=table_data
    )

def generate_new_books_report(employee_id: int, start_date: str, end_date: str, output_dir: str = "reports") -> str:
    """Генерирует отчет о поступлении книг за период"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            lb.id,
            strftime('%d.%m.%Y', lb.date) as supply_date,
            b.name as book_name,
            a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as author,
            b.year,
            '1000' as price,  -- Заглушка для цены
            orq.quantity,
            orq.quantity * 1000 as total_price  -- Заглушка для расчета
        FROM lading_bill lb
        JOIN order_request orq ON lb.order_request_id = orq.id
        JOIN book b ON lb.book_id = b.id
        JOIN author a ON b.author_id = a.id
        WHERE lb.date BETWEEN ? AND ?
        ORDER BY lb.date
    """, (start_date, end_date))
    
    data = cursor.fetchall()
    conn.close()
    
    table_headers = ["№", "Дата поставки", "Название книги", "Автор", "Год издания", "Цена", "Количество", "Стоимость"]
    table_data = [
        {
            "id": str(idx + 1),
            "supply_date": row[1],
            "book_name": row[2],
            "author": row[3],
            "year": row[4],
            "price": row[5],
            "quantity": row[6],
            "total_price": row[7]
        }
        for idx, row in enumerate(data)
    ]
    
    reporting_period = f"{start_date} - {end_date}"
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о поступлении книг",
        table_headers=table_headers,
        table_data=table_data,
        reporting_period=reporting_period
    )

def generate_debited_books_report(employee_id: int, output_dir: str = "reports") -> str:
    """Генерирует отчет о списанных книгах"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            da.id,
            b.name as book_name,
            a.last_name || ' ' || a.first_name || COALESCE(' ' || a.patronymic, '') as author,
            b.year,
            da.commentary as reason
        FROM debiting_act da
        JOIN book b ON da.book_id = b.id
        JOIN author a ON b.author_id = a.id
        ORDER BY da.date
    """)
    
    data = cursor.fetchall()
    conn.close()
    
    table_headers = ["№", "Название", "Автор", "Год издания", "Причина списания"]
    table_data = [
        {
            "id": str(idx + 1),
            "book_name": row[1],
            "author": row[2],
            "year": row[3],
            "reason": row[4]
        }
        for idx, row in enumerate(data)
    ]
    
    return generate_universal_report(
        template_path="reports/шаблон.docx",
        output_dir=output_dir,
        employee_id=employee_id,
        report_title="Отчет о списанных книгах",
        table_headers=table_headers,
        table_data=table_data
    )


# Пример использования всех функций для генерации отчетов
if __name__ == "__main__":
    # Заглушка для employee_id
    employee_id = 1
    
    # 1. Отчет о книгах по авторам
    report_path = generate_books_by_authors_report(employee_id)
    print(f"Отчет о книгах по авторам сгенерирован: {report_path}")
    
    # 2. Отчет о выданных и возвращенных книгах (за последний месяц)
    start_date = "01.01.2025"
    end_date = "31.01.2025"
    report_path = generate_issued_returned_books_report(employee_id, start_date, end_date)
    print(f"Отчет о выданных и возвращенных книгах сгенерирован: {report_path}")
    
    # 3. Отчет о выданных книгах (не возвращенных)
    report_path = generate_issued_books_report(employee_id)
    print(f"Отчет о выданных книгах сгенерирован: {report_path}")
    
    # 4. Отчет о книгах по жанрам
    report_path = generate_books_by_genres_report(employee_id)
    print(f"Отчет о книгах по жанрам сгенерирован: {report_path}")
    
    # 5. Отчет о содержании книжного фонда
    report_path = generate_book_collection_report(employee_id)
    print(f"Отчет о содержании книжного фонда сгенерирован: {report_path}")
    
    # 6. Отчет о поступлении книг (за последний месяц)
    report_path = generate_new_books_report(employee_id, start_date, end_date)
    print(f"Отчет о поступлении книг сгенерирован: {report_path}")
    
    # 7. Отчет о списанных книгах
    report_path = generate_debited_books_report(employee_id)
    print(f"Отчет о списанных книгах сгенерирован: {report_path}")