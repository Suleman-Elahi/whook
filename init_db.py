#!/usr/bin/env python3
"""
Database initialization script
Run this after setting up your database to create tables
"""

from sqlalchemy import text, inspect, create_engine
import os
from dotenv import load_dotenv

load_dotenv()

def create_database_if_not_exists(db_url):
    """Create the database if it doesn't exist"""
    from urllib.parse import urlparse
    
    if db_url.startswith('sqlite'):
        # SQLite creates the file automatically
        return
    
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    
    if db_url.startswith('mysql'):
        # MySQL/MariaDB
        base_url = db_url.rsplit('/', 1)[0]
        temp_engine = create_engine(base_url)
        create_stmt = f"CREATE DATABASE IF NOT EXISTS `{db_name}`"
    elif db_url.startswith('postgresql'):
        # PostgreSQL - connect to 'postgres' database to create new one
        base_url = db_url.rsplit('/', 1)[0] + '/postgres'
        temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
        create_stmt = f"SELECT 'CREATE DATABASE {db_name}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')"
    else:
        return
    
    try:
        with temp_engine.connect() as conn:
            if db_url.startswith('postgresql'):
                # Check if database exists
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
                if not result.fetchone():
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    print(f"✅ Created database '{db_name}'")
                else:
                    print(f"✅ Database '{db_name}' already exists")
            else:
                conn.execute(text(create_stmt))
                conn.commit()
                print(f"✅ Database '{db_name}' ready")
        
        temp_engine.dispose()
    except Exception as e:
        print(f"Note: Could not auto-create database: {e}")


def init_database():
    """Initialize the database with tables and indexes"""
    db_url = os.getenv('DATABASE_URL', '')
    
    db_type = 'SQLite' if db_url.startswith('sqlite') else \
              'MySQL/MariaDB' if db_url.startswith('mysql') else \
              'PostgreSQL' if db_url.startswith('postgresql') else 'Unknown'
    
    print(f"🔧 Initializing {db_type} database...")
    
    # Create database if needed
    create_database_if_not_exists(db_url)
    
    # Now import and create tables
    from app.models import Base
    from app.core import engine
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📊 Created tables: {', '.join(tables)}")
        
        # Show indexes
        print("\n🔍 Created indexes:")
        for table in tables:
            indexes = inspector.get_indexes(table)
            for idx in indexes:
                print(f"  - {table}.{idx['name']}")
        
        print("\n✨ Database initialization complete!")
        print(f"📍 Database URL: {db_url}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_database()
