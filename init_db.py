#!/usr/bin/env python3
"""
Database initialization script for PostgreSQL
Run this after setting up PostgreSQL to create tables
"""

from app.models import Base
from app.core import engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize the database with tables and indexes"""
    print("🔧 Initializing PostgreSQL database...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            
            print(f"\n📊 Created tables: {', '.join(tables)}")
            
            # Show indexes
            result = conn.execute(text("""
                SELECT 
                    tablename,
                    indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """))
            
            print("\n🔍 Created indexes:")
            for row in result:
                print(f"  - {row[0]}.{row[1]}")
        
        print("\n✨ Database initialization complete!")
        print(f"📍 Database URL: {os.getenv('DATABASE_URL', 'Not set')}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_database()
