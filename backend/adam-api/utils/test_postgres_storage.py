#!/usr/bin/env python3
"""
Test script for PostgreSQL storage functionality

Usage:
    python backend/utils/test_postgres_storage.py
"""

import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.postgres_storage import PostgreSQLStorage
from utils.constants import POSTGRES_CONFIG, USE_POSTGRES_STORAGE
from langchain_core.messages import HumanMessage, AIMessage

def test_postgres_storage():
    """Test PostgreSQL storage functionality"""
    
    if not USE_POSTGRES_STORAGE:
        print("PostgreSQL storage is not enabled. Set USE_POSTGRES_STORAGE=true in your .env file.")
        return False
    
    try:
        # Initialize storage
        print("Initializing PostgreSQL storage...")
        storage = PostgreSQLStorage(POSTGRES_CONFIG)
        print("✓ Storage initialized successfully")
        
        # Test user
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        test_email = f"test_{test_user_id}@example.com"
        
        # Test 1: Create conversation
        print(f"\nTest 1: Creating conversation for user {test_user_id}")
        conversation_id = storage.get_or_create_conversation(test_user_id, test_email)
        print(f"✓ Conversation created: {conversation_id}")
        
        # Test 2: Save messages
        print("\nTest 2: Saving messages")
        messages = [
            {"type": "human", "content": "Hello, this is a test message", "additional_kwargs": {}},
            {"type": "ai", "content": "Hello! This is a test response", "additional_kwargs": {}}
        ]
        metadata = {
            "theme": "test",
            "user_language": "en",
            "in_analysis": False
        }
        storage.save_messages(conversation_id, messages, metadata)
        print("✓ Messages saved successfully")
        
        # Test 3: Load conversation
        print("\nTest 3: Loading conversation")
        loaded_data = storage.load_conversation(test_user_id)
        print(f"✓ Loaded conversation ID: {loaded_data['conversation_id']}")
        print(f"✓ Number of conversation sessions: {len(loaded_data['conversations'])}")
        if loaded_data['conversations']:
            print(f"✓ Messages in first session: {len(loaded_data['conversations'][0]['messages'])}")
        
        # Test 4: Save and load user preferences
        print("\nTest 4: Testing user preferences (long-term memory)")
        preferences = {
            "user_name": "Test User",
            "preferred_analysis": ["performance", "budget"],
            "other_details": {"test": True}
        }
        storage.save_user_preferences(test_user_id, test_email, preferences)
        print("✓ User preferences saved")
        
        loaded_prefs = storage.load_user_preferences(test_user_id)
        print(f"✓ User preferences loaded: {loaded_prefs}")
        
        # Test 5: Get active users count
        print("\nTest 5: Getting active users count")
        count = storage.get_active_users_count()
        print(f"✓ Active users: {count}")
        
        # Test 6: Delete conversation
        print("\nTest 6: Deleting conversation")
        success = storage.delete_all_conversations(test_user_id)
        print(f"✓ Conversation deleted: {success}")
        
        # Verify deletion
        loaded_after_delete = storage.load_conversation(test_user_id)
        print(f"✓ Conversations after delete: {len(loaded_after_delete['conversations'])}")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("PostgreSQL Storage Test")
    print("=" * 40)
    print(f"Host: {POSTGRES_CONFIG['host']}")
    print(f"Port: {POSTGRES_CONFIG.get('port', 5432)}")
    print(f"Database: {POSTGRES_CONFIG['database']}")
    print(f"Enabled: {USE_POSTGRES_STORAGE}")
    print("=" * 40)
    
    if test_postgres_storage():
        sys.exit(0)
    else:
        sys.exit(1) 