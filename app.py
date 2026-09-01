import os
from datetime import date

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------- Models ----------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    roll_no = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='Absent')  # 'Present' or 'Absent'
    date_marked = db.Column(db.String(20), default=lambda: date.today().isoformat())


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Routes ----------

@app.route('/')
@login_required
def dashboard():
    students = Student.query.order_by(Student.name).all()
    present_count = sum(1 for s in students if s.status == 'Present')
    absent_count = sum(1 for s in students if s.status == 'Absent')
    return render_template(
        'dashboard.html',
        students=students,
        present_count=present_count,
        absent_count=absent_count,
        total_count=len(students),
        today=date.today().isoformat(),
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    name = request.form.get('name', '').strip()
    roll_no = request.form.get('roll_no', '').strip()

    if name and roll_no:
        student = Student(name=name, roll_no=roll_no, status='Absent')
        db.session.add(student)
        db.session.commit()
        flash(f'Added {name} to the roster.')
    else:
        flash('Please provide both a name and a roll number.')

    return redirect(url_for('dashboard'))


@app.route('/toggle/<int:student_id>')
@login_required
def toggle_status(student_id):
    student = Student.query.get_or_404(student_id)
    student.status = 'Absent' if student.status == 'Present' else 'Present'
    student.date_marked = date.today().isoformat()
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/delete/<int:student_id>')
@login_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash(f'Removed {student.name} from the roster.')
    return redirect(url_for('dashboard'))


# ---------- Setup helpers ----------

def create_default_admin():
    """Creates a default admin login (admin / admin123) if none exists."""
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


with app.app_context():
    db.create_all()
    create_default_admin()


if __name__ == '__main__':
    app.run(debug=True)
