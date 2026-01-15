#!/usr/bin/env python3
"""
PostgreSQL Table Migration Script

This script renames existing tables to add the 'adam_' prefix.
Use this if you have existing data with the old table names.

Usage:
    python backend/utils/migrate_table_names.py
"""

import psycopg2
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.constants import POSTGRES_CONFIG

def migrate_tables():
    """Rename existing tables to add 'adam_' prefix"""
    
    # Check if credentials are configured
    if not POSTGRES_CONFIG.get('user') or not POSTGRES_CONFIG.get('password'):
        print("Error: PostgreSQL credentials not configured.")
        print("Please set POSTGRES_USER and POSTGRES_PASSWORD environment variables.")
        return False
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=POSTGRES_CONFIG['host'],
            port=POSTGRES_CONFIG.get('port', 5432),
            database=POSTGRES_CONFIG['database'],
            user=POSTGRES_CONFIG['user'],
            password=POSTGRES_CONFIG['password']
        )
        
        print(f"Connected to PostgreSQL database: {POSTGRES_CONFIG['database']}")
        
        with conn.cursor() as cursor:
            # Check which tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('conversations', 'messages', 'user_preferences', 
                                  'adam_conversations', 'adam_messages', 'adam_user_preferences')
            """)
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            print(f"\nExisting tables: {existing_tables}")
            
            # Migration plan
            migrations = []
            
            # Check if old tables exist and new ones don't
            if 'conversations' in existing_tables and 'adam_conversations' not in existing_tables:
                migrations.append(('conversations', 'adam_conversations'))
            
            if 'messages' in existing_tables and 'adam_messages' not in existing_tables:
                migrations.append(('messages', 'adam_messages'))
            
            if 'user_preferences' in existing_tables and 'adam_user_preferences' not in existing_tables:
                migrations.append(('user_preferences', 'adam_user_preferences'))
            
            if not migrations:
                print("\nNo migrations needed! Tables are already properly named or don't exist.")
                return True
            
            # Perform migrations
            print(f"\nMigration plan: {migrations}")
            response = input("Do you want to proceed with the migration? (yes/no): ")
            
            if response.lower() != 'yes':
                print("Migration cancelled.")
                return False
            
            for old_name, new_name in migrations:
                print(f"\nRenaming table '{old_name}' to '{new_name}'...")
                
                # Rename table
                cursor.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
                print(f"✓ Table renamed successfully")
                
                # Update indices
                if old_name == 'messages':
                    # Rename message indices
                    try:
                        cursor.execute('ALTER INDEX IF EXISTS idx_messages_conversation_id RENAME TO idx_adam_messages_conversation_id')
                        cursor.execute('ALTER INDEX IF EXISTS idx_messages_timestamp RENAME TO idx_adam_messages_timestamp')
                        print("✓ Message indices renamed")
                    except Exception as e:
                        print(f"Note: Could not rename indices: {e}")
                
                elif old_name == 'conversations':
                    # Rename conversation index
                    try:
                        cursor.execute('ALTER INDEX IF EXISTS idx_conversations_user_id RENAME TO idx_adam_conversations_user_id')
                        print("✓ Conversation index renamed")
                    except Exception as e:
                        print(f"Note: Could not rename index: {e}")
            
            # Commit changes
            conn.commit()
            print("\n✅ Migration completed successfully!")
            
            # Verify new tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('adam_conversations', 'adam_messages', 'adam_user_preferences')
            """)
            
            new_tables = cursor.fetchall()
            print("\nTables after migration:")
            for table in new_tables:
                print(f"  - {table[0]}")
            
            return True
            
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    print("PostgreSQL Table Migration")
    print("=" * 40)
    print(f"Host: {POSTGRES_CONFIG['host']}")
    print(f"Port: {POSTGRES_CONFIG.get('port', 5432)}")
    print(f"Database: {POSTGRES_CONFIG['database']}")
    print(f"User: {POSTGRES_CONFIG['user']}")
    print("=" * 40)
    
    if migrate_tables():
        print("\nMigration completed!")
    else:
        print("\nMigration failed!")
        sys.exit(1) 