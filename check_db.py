from app import app, db, User, Section
from sqlalchemy import inspect

def check_database():
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("\nDatabase Tables:")
        for table_name in inspector.get_table_names():
            print(f"\nTable: {table_name}")
            for column in inspector.get_columns(table_name):
                print(f"- {column['name']}: {column['type']}")

if __name__ == '__main__':
    check_database()