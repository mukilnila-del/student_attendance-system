import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, User  # noqa: E402


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as test_client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        yield test_client

    os.close(db_fd)
    os.unlink(db_path)


def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign In' in response.data


def test_login_with_correct_credentials(client):
    response = client.post(
        '/login',
        data={'username': 'admin', 'password': 'admin123'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Student Attendance System' in response.data


def test_login_with_wrong_password(client):
    response = client.post(
        '/login',
        data={'username': 'admin', 'password': 'wrongpass'},
        follow_redirects=True,
    )
    assert b'Invalid username or password' in response.data


def test_add_student_after_login(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    response = client.post(
        '/add_student',
        data={'name': 'Alice', 'roll_no': '101'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Alice' in response.data
