from flask import Flask, render_template, request, redirect, url_for, session
from models import db, Student, Instructor, Lesson, Grade, Availability

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
    slots = Availability.query.filter_by(is_booked=False).all()
    return render_template('booking.html', slots=slots)

@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'student':
        return redirect(url_for('login'))
    
    student_id = session['user_id']
    grades = Grade.query.filter_by(student_id=student_id).all()
    student = Student.query.get(student_id)

    return render_template('progress.html', grades=grades, student=student)

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
    
    total_students = Student.query.count()
    total_instructors = Instructor.query.count()
    total_lessons = Lesson.query.count()
    total_grades = Grade.query.count()

    passed_students = Student.query.filter(Student.lessons_done>=30).count()

    if total_students > 0:
        pass_rate = round((passed_students/total_students)*100)
    else:
        pass_rate=0

    
    return render_template('admin.html',
        total_students=total_students,
        total_instructors=total_instructors,
        total_lessons=total_lessons,
        total_grades=total_grades,
        pass_rate=pass_rate)


@app.route('/setup')
def setup():
    instructor = Instructor(
        name='Test Instructor',
        email='instructor@gmail.com',
        password='password456'
    )
    db.session.add(instructor)
    db.session.commit()
    return 'Instructor created!'

@app.route('/setup-slots')
def setup_slots():
    instructor = Instructor.query.first()
    slots = [
        Availability(instructor_id=instructor.id, date='Monday 24 March', time='10:00'),
        Availability(instructor_id=instructor.id, date='Tuesday 25 March', time='14:00'),
        Availability(instructor_id=instructor.id, date='Friday 28 March', time='12:00'),
    ]
    for slot in slots:
        db.session.add(slot)
    db.session.commit()
    return 'Slots created!'

@app.route('/book/<int:slot_id>', methods = ['POST'])
def book_lesson(slot_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    slot = Availability.query.get(slot_id)

    if slot and not slot.is_booked:
        slot.is_booked = True

        new_lesson=Lesson(
            student_id=session['user_id'],
            instructor_id = slot.instructor_id,
            date = slot.date,
            time = slot.time,
            status='booked'
        )
        db.session.add(new_lesson)
        db.session.commit()
    return redirect(url_for('booking'))


@app.route('/instructor/grades')
def instructor_grades():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'instructor':
        return redirect(url_for('login'))
    
    lessons = Lesson.query.filter_by(instructor_id=session['user_id']).all()
    
    # Separate graded and ungraded lessons
    ungraded = []
    graded = []
    for lesson in lessons:
        grade = Grade.query.filter_by(lesson_id=lesson.id).first()
        if grade:
            graded.append((lesson, grade))
        else:
            ungraded.append(lesson)
    
    return render_template('instructor_grades.html', ungraded=ungraded, graded=graded)

@app.route('/grade/<int:lesson_id>', methods=['POST'])
def submit_grade(lesson_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    lesson = Lesson.query.get(lesson_id)
    
    if lesson:
        score = request.form['score']
        comment = request.form['comment']
        
        new_grade = Grade(
            student_id=lesson.student_id,
            lesson_id=lesson.id,
            score=score,
            comment=comment
        )
        db.session.add(new_grade)
        db.session.commit()
    
    return redirect(url_for('instructor_grades'))

@app.route('/setup-admin')
def setup_admin():
    # We store admin in session manually
    session['user'] = 'admin@gmail.com'
    session['role'] = 'admin'
    session['user_id'] = 0
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)


