#!/usr/bin/env python3
"""
Database migration script to add missing columns to call_logs table.
"""

import sqlite3
import os
import sys

# Use your actual database name
DB_NAME = "hedef.db"

def migrate_database():
    """Add missing columns to call_logs table"""
    
    if not os.path.exists(DB_NAME):
        print(f"✗ Database file '{DB_NAME}' not found!")
        print("  The database will be created automatically when you run the application.")
        return False
    
    print(f"Migrating database: {DB_NAME}")
    print("-" * 60)
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if call_logs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='call_logs'
        """)
        
        if not cursor.fetchone():
            print("ℹ️  call_logs table doesn't exist yet - it will be created on first run")
            conn.close()
            return True
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(call_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"✓ Found call_logs table with columns: {', '.join(columns)}")
        
        # Check and add missing columns
        migrations_needed = []
        
        if 'session_id' not in columns:
            migrations_needed.append(('session_id', 'VARCHAR(100)'))
        
        if 'intent' not in columns:
            migrations_needed.append(('intent', 'VARCHAR(50)'))
        
        if not migrations_needed:
            print("✓ Database schema is up to date - no migration needed!")
            conn.close()
            return True
        
        # Perform migrations
        print(f"\n📝 Adding {len(migrations_needed)} new column(s):")
        
        for column_name, column_type in migrations_needed:
            print(f"  - Adding column: {column_name} ({column_type})")
            cursor.execute(f"""
                ALTER TABLE call_logs 
                ADD COLUMN {column_name} {column_type}
            """)
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        print("-" * 60)
        print("\nYou can now restart your application.")
        return True
        
    except sqlite3.Error as e:
        print(f"\n✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def verify_schema():
    """Verify the database schema after migration"""
    if not os.path.exists(DB_NAME):
        return
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(call_logs)")
        columns = cursor.fetchall()
        
        print("\n📊 Current call_logs schema:")
        print("-" * 60)
        for col in columns:
            col_id, name, col_type, notnull, default, pk = col
            pk_marker = " [PRIMARY KEY]" if pk else ""
            null_marker = " [NOT NULL]" if notnull else ""
            print(f"  {name:20} {col_type:15} {pk_marker}{null_marker}")
        
        conn.close()
        
    except Exception as e:
        print(f"Could not verify schema: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("Database Migration Script")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        verify_schema()
        sys.exit(0)
    else:
        sys.exit(1)