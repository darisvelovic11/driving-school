import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Student, Instructor, Lesson, Grade, Availability, Cancellation
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')
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

        student = Student.query.filter_by(email=email).first()
        if student and bcrypt.check_password_hash(student.password, password):
            session['user'] = email
            session['role'] = 'student'
            session['user_id'] = student.id
            return redirect(url_for('dashboard'))

        instructor = Instructor.query.filter_by(email=email).first()
        if instructor and bcrypt.check_password_hash(instructor.password, password):
            session['user'] = email
            session['role'] = 'instructor'
            session['user_id'] = instructor.id
            return redirect(url_for('instructor_dashboard'))

        flash('Invalid email or password.', 'error')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['first-name'] + ' ' + request.form['last-name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        instructor_id = request.form['instructor_id']

        if password != confirm_password:
            instructors = Instructor.query.all()
            flash('Passwords do not match.', 'error')
            return render_template('register.html', instructors=instructors)

        existing_user = Student.query.filter_by(email=email).first()
        if existing_user:
            instructors = Instructor.query.all()
            flash('Email already registered.', 'error')
            return render_template('register.html', instructors=instructors)

        new_student = Student(
            name=name,
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            lessons_done=0,
            instructor_id=instructor_id
        )
        db.session.add(new_student)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    instructors = Instructor.query.all()
    return render_template('register.html', instructors=instructors)


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    student = db.session.get(Student, session['user_id'])

    upcoming_lesson = Lesson.query.filter_by(
        student_id=session['user_id'],
        status='booked'
    ).first()

    lesson_history = Lesson.query.filter_by(
        student_id=session['user_id']
    ).order_by(Lesson.id.desc()).all()

    return render_template('dashboard.html',
        student=student,
        upcoming_lesson=upcoming_lesson,
        lesson_history=lesson_history)


@app.route('/booking')
def booking():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    already_booked = Lesson.query.filter_by(
        student_id=session['user_id'],
        status='booked'
    ).first()

    student = db.session.get(Student, session['user_id'])
    slots = Availability.query.filter_by(is_booked=False, instructor_id=student.instructor_id).all()
    return render_template('booking.html', slots=slots, already_booked=already_booked)


@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    student_id = session['user_id']
    grades = Grade.query.filter_by(student_id=student_id).all()
    student = db.session.get(Student, student_id)

    return render_template('progress.html', grades=grades, student=student)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/instructor')
def instructor_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    students = Student.query.filter_by(instructor_id=session['user_id']).all()
    exam_requests = Student.query.filter_by(instructor_id=session['user_id'], exam_requested=True, exam_result=None).all()
    return render_template('instructor.html', students=students, exam_requests=exam_requests)


@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    total_students = Student.query.count()
    total_instructors = Instructor.query.count()
    total_lessons = Lesson.query.count()
    total_grades = Grade.query.count()

    passed_students = Student.query.filter(Student.lessons_done >= 30).count()

    if total_students > 0:
        pass_rate = round((passed_students / total_students) * 100)
    else:
        pass_rate = 0

    students = Student.query.all()
    instructors = Instructor.query.all()

    return render_template('admin.html',
        total_students=total_students,
        total_instructors=total_instructors,
        total_lessons=total_lessons,
        total_grades=total_grades,
        pass_rate=pass_rate,
        students=students,
        instructors=instructors)


@app.route('/admin/delete-student/<int:student_id>', methods=['POST'])
def admin_delete_student(student_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    student = db.session.get(Student, student_id)
    if student:
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted.', 'success')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add-instructor', methods=['POST'])
def admin_add_instructor():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    if Instructor.query.filter_by(email=email).first():
        flash('An instructor with that email already exists.', 'error')
        return redirect(url_for('admin_dashboard'))

    new_instructor = Instructor(
        name=name,
        email=email,
        password=bcrypt.generate_password_hash(password).decode('utf-8')
    )
    db.session.add(new_instructor)
    db.session.commit()
    flash('Instructor added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete-instructor/<int:instructor_id>', methods=['POST'])
def admin_delete_instructor(instructor_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    instructor = db.session.get(Instructor, instructor_id)
    if instructor:
        assigned_students = Student.query.filter_by(instructor_id=instructor_id).count()
        if assigned_students > 0:
            flash(f'Cannot delete instructor — they still have {assigned_students} student(s) assigned. Reassign them first.', 'error')
            return redirect(url_for('admin_dashboard'))
        db.session.delete(instructor)
        db.session.commit()
        flash('Instructor deleted.', 'success')

    return redirect(url_for('admin_dashboard'))


@app.route('/my-instructor')
def my_instructor():
    if 'user' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    student = db.session.get(Student, session['user_id'])
    instructor = db.session.get(Instructor, student.instructor_id) if student.instructor_id else None
    student_count = Student.query.filter_by(instructor_id=instructor.id).count() if instructor else 0
    return render_template('instructor_profile.html', instructor=instructor, student_count=student_count)


@app.route('/request-exam', methods=['POST'])
def request_exam():
    if 'user' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    student = db.session.get(Student, session['user_id'])
    if student.lessons_done >= 30 and not student.exam_requested and not student.exam_result:
        student.exam_requested = True
        db.session.commit()
        flash('Final exam requested! Your instructor will be in touch.', 'success')
    return redirect(url_for('progress'))


@app.route('/instructor/exam/<int:student_id>', methods=['POST'])
def submit_exam(student_id):
    if 'user' not in session or session.get('role') != 'instructor':
        return redirect(url_for('login'))

    student = db.session.get(Student, student_id)
    if student and student.instructor_id == session['user_id']:
        result = request.form.get('result')
        if result in ('pass', 'fail'):
            student.exam_result = result
            db.session.commit()
            flash(f'Exam result recorded: {result.upper()}', 'success')

    return redirect(url_for('instructor_dashboard'))


@app.route('/instructor/cancellations')
def instructor_cancellations():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    lessons = Lesson.query.filter_by(instructor_id=session['user_id']).all()
    lesson_ids = [lesson.id for lesson in lessons]

    cancellations = Cancellation.query.filter(
        Cancellation.lesson_id.in_(lesson_ids)
    ).all()

    return render_template('instructor_cancellations.html', cancellations=cancellations)


@app.route('/book/<int:slot_id>', methods=['POST'])
def book_lesson(slot_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    existing = Lesson.query.filter_by(
        student_id=session['user_id'],
        status='booked'
    ).first()
    if existing:
        flash('You already have a lesson booked. Cancel it first before booking a new one.', 'error')
        return redirect(url_for('booking'))

    slot = db.session.get(Availability, slot_id)
    if slot and not slot.is_booked:
        slot.is_booked = True
        new_lesson = Lesson(
            student_id=session['user_id'],
            instructor_id=slot.instructor_id,
            date=slot.date,
            time=slot.time,
            status='booked'
        )
        db.session.add(new_lesson)
        db.session.commit()
        flash('Lesson booked successfully!', 'success')
    else:
        flash('That slot is no longer available.', 'error')

    return redirect(url_for('booking'))


@app.route('/instructor/grades')
def instructor_grades():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    lessons = Lesson.query.filter_by(instructor_id=session['user_id']).all()

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
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    lesson = db.session.get(Lesson, lesson_id)

    if lesson and lesson.instructor_id == session['user_id']:
        existing_grade = Grade.query.filter_by(lesson_id=lesson.id).first()
        if existing_grade:
            flash('This lesson has already been graded.', 'error')
            return redirect(url_for('instructor_grades'))

        score = request.form['score']
        comment = request.form['comment']

        new_grade = Grade(
            student_id=lesson.student_id,
            lesson_id=lesson.id,
            score=score,
            comment=comment
        )
        db.session.add(new_grade)

        lesson.status = 'completed'
        student = db.session.get(Student, lesson.student_id)
        student.lessons_done += 1

        db.session.commit()
        flash('Grade submitted successfully!', 'success')

    return redirect(url_for('instructor_grades'))


@app.route('/cancel/<int:lesson_id>', methods=['GET', 'POST'])
def cancel_lesson(lesson_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    lesson = db.session.get(Lesson, lesson_id)

    if not lesson or lesson.student_id != session['user_id']:
        flash('Lesson not found.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        reason = request.form.get('reason', '')

        lesson.status = 'cancelled'

        slot = Availability.query.filter_by(
            date=lesson.date,
            time=lesson.time,
            instructor_id=lesson.instructor_id
        ).first()
        if slot:
            slot.is_booked = False

        cancellation = Cancellation(
            lesson_id=lesson.id,
            student_id=session['user_id'],
            reason=reason if reason else 'No reason provided',
            cancelled_at=datetime.now().strftime('%Y-%m-%d %H:%M')
        )
        db.session.add(cancellation)
        db.session.commit()

        flash('Lesson cancelled.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('cancel.html', lesson=lesson)


@app.route('/instructor/availability', methods=['GET', 'POST'])
def instructor_availability():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']

        new_slot = Availability(
            instructor_id=session['user_id'],
            date=date,
            time=time,
            is_booked=False
        )
        db.session.add(new_slot)
        db.session.commit()
        flash('Slot added successfully!', 'success')
        return redirect(url_for('instructor_availability'))

    slots = Availability.query.filter_by(instructor_id=session['user_id']).all()
    return render_template('instructor_availability.html', slots=slots)


@app.route('/instructor/delete-slot/<int:slot_id>', methods=['POST'])
def delete_slot(slot_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    slot = db.session.get(Availability, slot_id)
    if slot and not slot.is_booked and slot.instructor_id == session['user_id']:
        db.session.delete(slot)
        db.session.commit()
        flash('Slot deleted.', 'success')

    return redirect(url_for('instructor_availability'))


# --- Dev-only setup routes (only work when debug=True) ---

@app.route('/setup')
def setup():
    if not app.debug:
        return "Not available", 403
    existing = Instructor.query.filter_by(email='instructor@gmail.com').first()
    if existing:
        return "Instructor already exists"
    instructor = Instructor(
        name='Test Instructor',
        email='instructor@gmail.com',
        password=bcrypt.generate_password_hash('password456').decode('utf-8')
    )
    db.session.add(instructor)
    db.session.commit()
    return 'Instructor created!'


@app.route('/setup-slots')
def setup_slots():
    if not app.debug:
        return "Not available", 403
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


@app.route('/setup-admin')
def setup_admin():
    if not app.debug:
        return "Not available", 403
    session['user'] = 'admin@gmail.com'
    session['role'] = 'admin'
    session['user_id'] = 0
    return redirect(url_for('admin_dashboard'))


@app.route('/setup-complete-student')
def setup_complete_student():
    if not app.debug:
        return "Not available", 403
    student = Student.query.first()
    if not student:
        return "No students found"
    student.lessons_done = 30
    db.session.commit()
    return f'{student.name} now has 30 lessons done!'


@app.route('/db-check')
def db_check():
    if not app.debug:
        return "Not available", 403
    students = Student.query.count()
    instructors = Instructor.query.count()
    return f'Students: {students} | Instructors: {instructors}'


if __name__ == '__main__':
    app.run(debug=True)
