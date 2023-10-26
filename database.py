import sqlite3

def init_db(app):  # Accept the app object as an argument
    with app.app_context():  # Use the app object here instead of current_app
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                title TEXT,
                description TEXT
            )
        ''')
        
        # Delete all old posts
        cursor.execute('DELETE FROM posts')
        
        db.commit()
