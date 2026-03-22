from flask import Flask, render_template, request, redirect, url_for, session
from models import db, Student, Instructor, Lesson, Grade

app = Flask(__name__)

app.secret_key = 'driving_school_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///driving_school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        student = Student.query.filter_by(email=email, password=password).first()
        if student:
            session['user'] = email
            session['role'] = 'student'
            session['user_id'] = student.id
            return redirect(url_for('dashboard'))

        instructor = Instructor.query.filter_by(email=email, password=password).first()
        if instructor:
            session['user'] = email
            session['role'] = 'instructor'
            session['user_id'] = instructor.id
            return redirect(url_for('instructor_dashboard'))

        return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['first-name'] + ' ' + request.form['last-name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")

        existing_user = Student.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error="Email already registered")

        new_student = Student(
            name=name,
            email=email,
            password=password,
            lessons_done=0
        )
        db.session.add(new_student)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/booking')
def booking():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('booking.html')

@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('progress.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/instructor')
def instructor_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'instructor':
        return redirect(url_for('login'))
    return render_template('instructor.html')

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)