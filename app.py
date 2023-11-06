from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
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
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, password FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]  # Store user id in session
                session['email'] = email  # Store email in session
                return redirect(url_for('main'))
            else:
                # If login is invalid, you can redirect back to login page with a message
                # Or handle it by showing an error message on the same login page
                return render_template('index.html', error="Invalid credentials")
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
            cursor.execute("INSERT INTO posts (users_id, title, description) VALUES (?, ?, ?)", 
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
        hashed_password = generate_password_hash(password)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
            user_id = cursor.lastrowid  # Get the auto-generated ID
            db.commit()

            print(f"New user ID: {user_id}")  # Add this line for debugging

        return redirect(url_for('login'))
    else:
        return render_template('register.html')
 

@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        db.commit()

    return redirect(url_for('main'))

# Initialize the database
# Assuming init_db(app) initializes the database as per your provided structure
init_db(app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")