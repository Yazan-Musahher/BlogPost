from flask import Flask, render_template, request, redirect, url_for
from database import init_db  # Import the init_db function from database.py
import sqlite3

# Initialize Flask app
app = Flask(__name__)

# Initialize the database
init_db(app)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user = request.form['user']
        title = request.form['title']
        description = request.form['description']

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO posts (user, title, description) VALUES (?, ?, ?)", (user, title, description))
            db.commit()

        return redirect(url_for('index'))

    else:
        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM posts")
            posts = cursor.fetchall()

        return render_template('index.html', posts=posts)

@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        db.commit()

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
