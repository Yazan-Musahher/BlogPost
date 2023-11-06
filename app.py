import base64
import io
from flask import Flask, render_template, request, redirect, send_file, url_for, session, flash
import sqlite3
import qrcode
import pyotp
from database import init_db
from werkzeug.security import generate_password_hash, check_password_hash


# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'z4gbFxEngf'  # Please dont store the key in Production


@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_totp = request.form['totp']
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, password, totp_secret FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user[1], password) and pyotp.TOTP(user[2]).verify(user_totp):
                session['user_id'] = user[0]  # Store user id in session
                session['email'] = email  # Store email in session
                flash('You are logged in!', 'success')
                return redirect(url_for('main'))
            else:
                flash('Invalid credentials or TOTP', 'error')
                return render_template('index.html')
    else:
        return render_template('index.html')
    

@app.route("/main", methods=['GET', 'POST'])
def main():
    if 'email' not in session:
        # If there is no email in session, redirect to the login page
        return redirect(url_for('login'))

    # Fetch the user_id from the session instead of the form
    user_id = session.get('user_id')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        # Connect to the database and insert the new post
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO posts (user_id, title, description) VALUES (?, ?, ?)", 
                           (user_id, title, description))
            db.commit()

        return redirect(url_for('main'))

    else:
        # Retrieve posts from the database to display
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM posts")
            posts = cursor.fetchall()

        # Display posts in main.html, including the user's email
        return render_template('main.html', email=session['email'], posts=posts)
 

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Connect to the database
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            # Check if email already exists
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            if cursor.fetchone():  # If there's a user with this email
                flash('Email already exists. Please try another one.', 'error')
                return redirect(url_for('register'))

            # Email doesn't exist, create new user with TOTP secret
            totp_secret = pyotp.random_base32()
            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (email, password, totp_secret) VALUES (?, ?, ?)",
                           (email, hashed_password, totp_secret))
            db.commit()
        
        # Redirect user to setup 2FA after registration
        session['user_id'] = cursor.lastrowid  # Store the new user id in session
        session['email'] = email  # Store email in session for 2FA setup
        return redirect(url_for('setup_2fa'))
    else:
        return render_template('register.html')
    

@app.route('/setup')
def setup_2fa():
    # Make sure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Retrieve the user's email from the session
    email = session.get('email')
    
    # Retrieve the TOTP secret from the database for the user
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("SELECT totp_secret FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user or not user[0]:  # Ensure the user and totp_secret exist
            flash('No user found for 2FA setup or missing TOTP secret', 'error')
            return redirect(url_for('login'))
        
        totp_secret = user[0]
        totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=email, issuer_name="Google Authenticator")
        qr_img = qrcode.make(totp_uri)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        data = base64.b64encode(buf.read()).decode('ascii')

    return render_template('setup_2fa.html', qr_code_data=data)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        db.commit()

    return redirect(url_for('main'))

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))
# Initialize the database
# Assuming init_db(app) initializes the database as per your provided structure
init_db(app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")