import base64
import io
from flask import Flask, render_template, request, redirect, send_file, url_for, session, flash
from datetime import datetime, timedelta
import sqlite3
import qrcode
import pyotp
from database import init_db
from werkzeug.security import generate_password_hash, check_password_hash
from oauth import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_AUTHORIZE_URL, GOOGLE_TOKEN_URL, GOOGLE_USERINFO_URL
from urllib.parse import urlencode
import requests



# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'z4gbFxEngf'  # Please dont store the key in Production



@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve the login attempt count and time from the session
        login_attempts = session.get('login_attempts', 0)
        attempt_time = session.get('attempt_time')
        
        # If attempt_time is present and is offset-aware, convert it to offset-naive
        if attempt_time and attempt_time.tzinfo is not None:
            attempt_time = attempt_time.replace(tzinfo=None)
        
        # Compare with current time (offset-naive)
        current_time = datetime.now()

        # Check if the user has exceeded the attempt limit and if the time limit has not passed
        if login_attempts >= 3 and attempt_time and current_time < attempt_time + timedelta(minutes=1):
            flash('For mange mislykkede forsøk, prøv igjen om ett minutt.', 'error')
            return render_template('index.html')
            
              # Check if the user has successfully authenticated with Google OAuth2
        if 'access_token' in session:
            return redirect(url_for('main'))
        
        email = request.form['email']
        password = request.form['password']
        
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, password, totp_secret FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            # ... your code for successful login ...
            # Reset the attempt count on successful login
            session.pop('login_attempts', None)
            session.pop('attempt_time', None)
            return redirect(url_for('main'))
        else:
            session['login_attempts'] = login_attempts + 1
            session['attempt_time'] = datetime.now().replace(tzinfo=None)
            flash('Invalid credentials or TOTP', 'error')
            # Since this is an error case, we render the template again with the error message
            return render_template('index.html')
        
    return render_template('index.html')

@app.route("/google-callback")
def google_callback():
    # Check if the state matches
    if request.args.get('state') != session['oauth_state']:
        flash('State mismatch. Potential CSRF attack.', 'error')
        return redirect(url_for('login'))

    # Exchange authorization code for access token
    code = request.args.get('code')
    token_response = requests.post(GOOGLE_TOKEN_URL, data={
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': url_for('google_callback', _external=True),
        'grant_type': 'authorization_code'
    })
    token_json = token_response.json()
    access_token = token_json['access_token']

    # Fetch the user's profile information
    userinfo_response = requests.get(GOOGLE_USERINFO_URL, headers={
        'Authorization': f'Bearer {access_token}'
    })
    user_info = userinfo_response.json()

    # Store the user information in session and redirect to main
    session['email'] = user_info['email']
    session['access_token'] = access_token  # Storing access token in session (optional)
    
    # Redirect to the main page
    return redirect(url_for('main'))

@app.route("/google-login")
def google_login():
    # Generate a unique state value and store it in the session
    state = 'your_unique_state'
    session['oauth_state'] = state

    # Redirect the user to Google's authorization endpoint
    redirect_uri = url_for('google_callback', _external=True)
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid profile email',  # Adjust the scope as needed
        'redirect_uri': redirect_uri,
        'state': state,
    }
    auth_url = f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"
    return redirect(auth_url)


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
        qr_img.save(buf)  # Removed the format="PNG" argument
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
    session.clear()
    return redirect(url_for('login'))
# Initialize the database
# Assuming init_db(app) initializes the database as per your provided structure
init_db(app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")