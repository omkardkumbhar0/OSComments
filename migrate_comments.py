from app import db, Comment, app
import sqlite3
from datetime import datetime

def migrate_comments():
    with app.app_context():
        try:
            # Connect to old SQLite database
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            
            # Get all comments from old table
            c.execute('SELECT * FROM comments')
            old_comments = c.fetchall()
            
            # Migrate to new SQLAlchemy model
            for old_comment in old_comments:
                new_comment = Comment(
                    id=old_comment[0],
                    section_id=old_comment[1],
                    blog_url=old_comment[2],
                    username=old_comment[3],
                    comment=old_comment[4],
                    timestamp=datetime.strptime(old_comment[5], '%Y-%m-%d %H:%M:%S'),
                    user_ip=old_comment[6],
                    parent_id=old_comment[7],
                    is_owner=bool(old_comment[8]),
                    likes_count=old_comment[9]
                )
                db.session.add(new_comment)
            
            db.session.commit()
            print("Comments migrated successfully")
            
        except Exception as e:
            print(f"Migration error: {str(e)}")
            db.session.rollback()
        finally:
            conn.close()

if __name__ == '__main__':
    migrate_comments()