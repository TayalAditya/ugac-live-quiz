import os
import tempfile
import unittest
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / 'live_quiz_production_tests.db'
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ['APP_ENV'] = 'testing'
os.environ['DB_PATH'] = str(TEST_DB)
os.environ.pop('DATABASE_URL', None)
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['ADMIN_PASSWORD'] = 'test-admin-password'

from app import Answer, Quiz, QuizSession, SessionLocal, _lb_cache, app, socketio


QUESTIONS = [
    {
        'id': 0,
        'type': 'mcq',
        'q': 'Which answer is correct?',
        'options': ['Wrong', 'Correct'],
        'correct_option': 1,
    }
]

PROXY_HEADERS = {
    'Host': 'ugac.iitmandi.ac.in',
    'X-Forwarded-Host': 'ugac.iitmandi.ac.in',
    'X-Forwarded-Proto': 'https',
    'X-Forwarded-Prefix': '/quiz',
}


class ProductionConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)

    def setUp(self):
        db = SessionLocal()
        db.query(Answer).delete()
        db.query(QuizSession).delete()
        db.query(Quiz).delete()
        db.commit()
        db.close()
        _lb_cache.clear()

    def _create_quiz(self):
        quiz = Quiz(
            id='quiz-1',
            title='Test Quiz',
            pin='ABC123',
            admin_id='admin-1',
            questions_data=QUESTIONS,
            state='idle',
        )
        db = SessionLocal()
        db.add(quiz)
        db.commit()
        db.close()
        return quiz

    def test_prefix_aware_login_and_redirect(self):
        self._create_quiz()
        client = app.test_client()

        page = client.get('/', headers=PROXY_HEADERS)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'action="/quiz/join"', page.data)

        response = client.post(
            '/join',
            headers=PROXY_HEADERS,
            data={'quiz_pin': 'ABC123', 'username': 'B24186'},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/quiz/play')

    def test_open_question_hides_answer_key_and_submission_requires_open_question(self):
        quiz = self._create_quiz()
        admin_client = app.test_client()
        with admin_client.session_transaction() as admin_session:
            admin_session['admin'] = True
            admin_session['admin_id'] = 'admin-1'

        student_client = app.test_client()
        with student_client.session_transaction() as student_session:
            student_session['session_id'] = 'student-1'
            student_session['quiz_id'] = quiz.id
            student_session['username'] = 'B24186'

        db = SessionLocal()
        db.add(QuizSession(id='student-1', quiz_id=quiz.id, username='B24186'))
        db.commit()
        db.close()

        blocked = student_client.post(
            '/submit',
            json={'question_id': 0, 'answer': '1', 'time_taken': 2},
        )
        self.assertEqual(blocked.status_code, 409)

        socket_client = socketio.test_client(app, flask_test_client=admin_client)
        socket_client.emit('join_quiz', {'quiz_id': quiz.id})
        socket_client.get_received()

        opened = admin_client.post(f'/admin/quiz/{quiz.id}/question/open/0')
        self.assertEqual(opened.status_code, 200)
        events = socket_client.get_received()
        opened_event = next(event for event in events if event['name'] == 'question_opened')
        public_question = opened_event['args'][0]['question']
        self.assertNotIn('correct_option', public_question)
        self.assertNotIn('correct_answer', public_question)
        self.assertNotIn('correct_options', public_question)

        submitted = student_client.post(
            '/submit',
            json={'question_id': 0, 'answer': '1', 'time_taken': 2},
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertTrue(submitted.get_json()['is_correct'])

        closed = admin_client.post(f'/admin/quiz/{quiz.id}/question/close')
        self.assertEqual(closed.status_code, 200)
        late_submission = student_client.post(
            '/submit',
            json={'question_id': 0, 'answer': '1', 'time_taken': 2},
        )
        self.assertEqual(late_submission.status_code, 409)


if __name__ == '__main__':
    unittest.main()
