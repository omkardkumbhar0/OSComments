from app import db, app
from sqlalchemy import inspect

def migrate_database():
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        print("Dropped all existing tables")
        
        # Create new tables
        db.create_all()
        print("Created new tables")
        
        # Verify tables using inspector
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Available tables: {tables}")

if __name__ == '__main__':
    migrate_database()