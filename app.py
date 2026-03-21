from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

app.secret_key = 'driving_school_secret_key'

users = {
    "student@gmail.com": {
        "password": "password123",
        "role": "student"
    },
    "instructor@gmail.com": {
        "password": "password456",
        "role": "instructor"
    },
    "admin@gmail.com": {
        "password": "admin123",
        "role": "admin"
    }
}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        if email in users and users[email]['password'] == password:
            session['user'] = email
            session['role'] = users[email]['role']

            role = session['role']
            if role == 'student':
                return redirect(url_for('dashboard'))
            elif role == 'instructor':
                return redirect(url_for('instructor_dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')

@app.route('/register')
def register():
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