#!/usr/bin/env python3
"""
PostgreSQL Database Initialization Script

This script initializes the PostgreSQL database schema for conversation history storage.
Run this script to set up the required tables and indices.

Usage:
    python backend/utils/init_postgres_db.py
"""

import psycopg2
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.constants import POSTGRES_CONFIG

def init_database():
    """Initialize the PostgreSQL database with required tables"""
    
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
            # Create conversations table
            print("Creating adam_conversations table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adam_conversations (
                    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    partner_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, partner_name)
                )
            """)
            
            # Create messages table
            print("Creating adam_messages table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adam_messages (
                    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES adam_conversations(conversation_id) ON DELETE CASCADE,
                    message_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    additional_kwargs JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Create user preferences table for long-term memory
            print("Creating adam_user_preferences table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adam_user_preferences (
                    user_id VARCHAR(255) PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    preferences JSONB DEFAULT '{}'::jsonb,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create feedback table
            print("Creating adam_feedback table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adam_feedback (
                    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_email VARCHAR(255) NOT NULL,
                    partner_name VARCHAR(255) NOT NULL,
                    agent_name VARCHAR(100) DEFAULT 'Adam Setup',
                    user_query TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    feedback TEXT NOT NULL,
                    sentiment VARCHAR(20) NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),
                    status VARCHAR(20) DEFAULT 'To Consider' CHECK (status IN ('To Consider', 'Considered', 'Ignored')),
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Create indices for better performance
            print("Creating indices...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_messages_conversation_id ON adam_messages(conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_messages_timestamp ON adam_messages(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_conversations_user_partner ON adam_conversations(user_id, partner_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_user_email ON adam_feedback(user_email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_partner_name ON adam_feedback(partner_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_sentiment ON adam_feedback(sentiment)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_status ON adam_feedback(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_created_at ON adam_feedback(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_user_partner ON adam_feedback(user_email, partner_name)")
            
            # Commit changes
            conn.commit()
            
            # Verify tables were created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('adam_conversations', 'adam_messages', 'adam_user_preferences', 'adam_feedback')
            """)
            
            tables = cursor.fetchall()
            print("\nTables created successfully:")
            for table in tables:
                print(f"  - {table[0]}")
                
            return True
            
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    print("PostgreSQL Database Initialization")
    print("=" * 40)
    print(f"Host: {POSTGRES_CONFIG['host']}")
    print(f"Port: {POSTGRES_CONFIG.get('port', 5432)}")
    print(f"Database: {POSTGRES_CONFIG['database']}")
    print(f"User: {POSTGRES_CONFIG['user']}")
    print("=" * 40)
    print()
    
    if init_database():
        print("\nDatabase initialization completed successfully!")
    else:
        print("\nDatabase initialization failed!")
        sys.exit(1) 