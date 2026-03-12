import os
import unittest

from instance.fill_db import fill
from app import app
from config import DB_PATH


class ReadersReportsSmokeTest(unittest.TestCase):
    def setUp(self):
        # Пересоздаем тестовые данные перед каждым тестом
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        fill()
        self.client = app.test_client()
        login = self.client.post('/api/login', json={'login': 'user2', 'password': 'pass'})
        self.assertEqual(login.status_code, 200)

    def test_readers_crud_penalty_flow(self):
        readers_resp = self.client.get('/api/readers')
        self.assertEqual(readers_resp.status_code, 200)
        self.assertTrue(readers_resp.get_json()['count'] >= 3)

        create_resp = self.client.post('/api/readers', json={
            'firstName': 'Тест',
            'lastName': 'Читатель',
            'patronymic': 'Тестович',
            'birthdate': '1995-06-01',
            'phone': '79991112233',
            'email': 'reader_test@example.com',
            'address': 'г. Тверь',
            'status': 'ACTIVE'
        })
        self.assertEqual(create_resp.status_code, 201)
        reader_id = create_resp.get_json()['readerId']

        details_resp = self.client.get(f'/api/readers/{reader_id}')
        self.assertEqual(details_resp.status_code, 200)
        self.assertTrue(details_resp.get_json()['reader']['ticket_number'].startswith('RB-'))

        update_resp = self.client.put(f'/api/readers/{reader_id}', json={
            'firstName': 'Обновленный',
            'lastName': 'Читатель',
            'patronymic': 'Тестович',
            'birthdate': '1995-06-01',
            'phone': '79991112234',
            'email': 'reader_test_new@example.com',
            'address': 'г. Тверь',
            'status': 'BLOCKED'
        })
        self.assertEqual(update_resp.status_code, 200)

        add_penalty_resp = self.client.post(f'/api/readers/{reader_id}/penalty', json={
            'delta_points': 4,
            'reason': 'rule_violation',
            'commentary': 'Нарушение правил'
        })
        self.assertEqual(add_penalty_resp.status_code, 200)
        self.assertEqual(add_penalty_resp.get_json()['penalty_points'], 4)

        reduce_penalty_resp = self.client.post(f'/api/readers/{reader_id}/penalty', json={
            'delta_points': -2,
            'reason': 'other',
            'commentary': 'Ручное списание'
        })
        self.assertEqual(reduce_penalty_resp.status_code, 200)
        self.assertEqual(reduce_penalty_resp.get_json()['penalty_points'], 2)

        delete_resp = self.client.delete(f'/api/readers/{reader_id}')
        self.assertEqual(delete_resp.status_code, 200)

    def test_reports_preview_and_export(self):
        preview_resp = self.client.post('/api/reports/preview', json={
            'report_type': 'issued-books',
            'start_date': '2020-01-01',
            'end_date': '2030-01-01'
        })
        self.assertEqual(preview_resp.status_code, 200)
        payload = preview_resp.get_json()['report']
        self.assertIn('columns', payload)
        self.assertIn('rows', payload)

        export_resp = self.client.post('/api/reports/export', json={
            'report_type': 'issued-books',
            'start_date': '2020-01-01',
            'end_date': '2030-01-01'
        })
        self.assertEqual(export_resp.status_code, 200)
        result = export_resp.get_json()
        self.assertTrue(result['report_url'].startswith('/reports_download/'))


if __name__ == '__main__':
    unittest.main()
