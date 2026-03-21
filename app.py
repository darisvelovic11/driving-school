from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

app.secret_key = 'driving_school_secret_key'

users = {
    "student@gmail.com": "password123",
    "instructor@gmail.com": "password456"
}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        if email in users and users[email] == password:
            session['user'] = email
            return redirect(url_for('dashboard'))
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
    return render_template('dashboard.html')

@app.route('/booking')
def booking():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('booking.html')

@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('progress.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)