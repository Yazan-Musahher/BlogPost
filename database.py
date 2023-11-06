import sqlite3

def init_db(app):
    with app.app_context():
        db = sqlite3.connect('database.db')
        db.execute('PRAGMA foreign_keys = ON')

        cursor = db.cursor()

        # Create a table for users if it doesn't exist, with an additional column for the TOTP secret
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                totp_secret TEXT
            );
        ''')

        # Create a table for posts if it doesn't exist with a foreign key that references the user's id.
        # Ensure the 'user_id' column matches the 'id' column in the 'users' table as specified by the foreign key.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        ''')

        # Optionally, clear out old data for a fresh start. Comment these out for production use.
        cursor.execute('DELETE FROM posts;')  # Deletes all existing posts.
        cursor.execute('DELETE FROM users;')  # Deletes all existing users.

        db.commit()
