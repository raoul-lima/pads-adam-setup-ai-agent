import psycopg2
from psycopg2.extras import RealDictCursor, Json
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import os
from contextlib import contextmanager
from utils.json_utils import ensure_json_serializable

logger = logging.getLogger(__name__)


class PostgreSQLStorage:
    """PostgreSQL storage backend for conversation history"""
    
    _initialized = False  # Class-level flag to track if tables have been initialized
    
    def __init__(self, connection_config: Dict[str, str]):
        """
        Initialize PostgreSQL storage
        
        Args:
            connection_config: Dictionary with keys: host, port, database, user, password
        """
        self.connection_config = connection_config
        # Only initialize database tables once (even if multiple instances are created)
        if not PostgreSQLStorage._initialized:
            self._init_database()
            PostgreSQLStorage._initialized = True
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.connection_config['host'],
                port=self.connection_config.get('port', 5432),
                database=self.connection_config['database'],
                user=self.connection_config['user'],
                password=self.connection_config['password']
            )
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Initialize database tables if they don't exist"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create conversations table
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS adam_user_preferences (
                        user_id VARCHAR(255) PRIMARY KEY,
                        user_email VARCHAR(255) NOT NULL,
                        preferences JSONB DEFAULT '{}'::jsonb,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create feedback table
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
                
                # Add notes column if it doesn't exist (migration for existing tables)
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='adam_feedback' AND column_name='notes'
                        ) THEN
                            ALTER TABLE adam_feedback ADD COLUMN notes TEXT DEFAULT '';
                        END IF;
                    END $$;
                """)
                
                # Create indices for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_messages_conversation_id ON adam_messages(conversation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_messages_timestamp ON adam_messages(timestamp DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_conversations_user_partner ON adam_conversations(user_id, partner_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_user_email ON adam_feedback(user_email)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_partner_name ON adam_feedback(partner_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_sentiment ON adam_feedback(sentiment)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_status ON adam_feedback(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_created_at ON adam_feedback(created_at DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_adam_feedback_user_partner ON adam_feedback(user_email, partner_name)")
                
                logger.info("Database tables initialized successfully")
    
    def get_or_create_conversation(self, user_id: str, user_email: str, partner_name: str) -> str:
        """Get existing conversation or create a new one for a user-partner combination"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Try to get existing conversation for this user-partner combination
                cursor.execute("""
                    SELECT conversation_id FROM adam_conversations 
                    WHERE user_id = %s AND partner_name = %s
                """, (user_id, partner_name))
                
                result = cursor.fetchone()
                if result:
                    return str(result[0])
                
                # Create new conversation for this user-partner combination
                cursor.execute("""
                    INSERT INTO adam_conversations (user_id, user_email, partner_name)
                    VALUES (%s, %s, %s)
                    RETURNING conversation_id
                """, (user_id, user_email, partner_name))
                
                result = cursor.fetchone()
                if result:
                    return str(result[0])
                else:
                    raise Exception("Failed to create conversation")
    
    def save_messages(self, conversation_id: str, messages: List[Dict[str, Any]], metadata: Dict[str, Any]):
        """Save messages to the database"""
        if not messages:
            return
        
        # Ensure all data is JSON serializable upfront
        try:
            messages = ensure_json_serializable(messages)
            metadata = ensure_json_serializable(metadata)
        except Exception as e:
            logger.error(f"Failed to clean data for JSON serialization: {e}")
            # Create minimal fallback data
            messages = [{"type": "error", "content": "Failed to save message", "additional_kwargs": {}}]
            metadata = {}
        
        # Validate and clean messages
        clean_messages = []
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                logger.error(f"Message {i} is not a dict: {type(msg)}")
                continue
            
            # Ensure all message fields are serializable
            clean_msg = {}
            for key, value in msg.items():
                try:
                    json.dumps(value)
                    clean_msg[key] = value
                except (TypeError, ValueError) as e:
                    logger.warning(f"Message {i} has non-serializable field '{key}': {type(value)}")
                    if key == 'additional_kwargs':
                        clean_msg[key] = {}
                    else:
                        clean_msg[key] = str(value) if value else ""
            clean_messages.append(clean_msg)
        
        messages = clean_messages
        
        # Debug: Check what's in metadata
        try:
            json.dumps(metadata)
        except (TypeError, ValueError) as e:
            logger.error(f"Metadata is not JSON serializable: {e}")
            # Log the problematic metadata
            for key, value in metadata.items():
                try:
                    json.dumps(value)
                except:
                    logger.error(f"Non-serializable metadata['{key}']: {type(value)} = {repr(value)[:100]}")
            # Clean metadata using our safe JSON utilities
            metadata = ensure_json_serializable(metadata)
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update conversation timestamp
                    cursor.execute("""
                        UPDATE adam_conversations 
                        SET updated_at = CURRENT_TIMESTAMP 
                        WHERE conversation_id = %s
                    """, (conversation_id,))
                    
                    # Insert messages
                    for msg in messages:
                        try:
                            # Get message data
                            msg_type = msg.get('type', 'unknown')
                            msg_content = msg.get('content', '')
                            additional_kwargs = msg.get('additional_kwargs', {})
                            
                            # Ensure content is a string
                            if not isinstance(msg_content, str):
                                msg_content = str(msg_content)
                            
                            # Clean additional_kwargs
                            clean_kwargs = {}
                            if isinstance(additional_kwargs, dict):
                                for k, v in additional_kwargs.items():
                                    try:
                                        json.dumps(v)
                                        clean_kwargs[k] = v
                                    except:
                                        logger.debug(f"Skipping non-serializable additional_kwargs['{k}']")
                            
                            cursor.execute("""
                                INSERT INTO adam_messages (
                                    conversation_id, message_type, content, 
                                    metadata, additional_kwargs, timestamp
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                conversation_id,
                                msg_type,
                                msg_content,
                                Json(metadata),
                                Json(clean_kwargs),
                                datetime.now()
                            ))
                        except Exception as e:
                            logger.error(f"Failed to save message: {e}")
                            logger.error(f"Message data: type={msg.get('type')}, content_length={len(str(msg.get('content', '')))}")
                            # Try saving with minimal data
                            try:
                                cursor.execute("""
                                    INSERT INTO adam_messages (
                                        conversation_id, message_type, content, 
                                        metadata, additional_kwargs, timestamp
                                    ) VALUES (%s, %s, %s, %s, %s, %s)
                                """, (
                                    conversation_id,
                                    msg.get('type', 'unknown'),
                                    str(msg.get('content', 'Error saving message')),
                                    Json({}),
                                    Json({}),
                                    datetime.now()
                                ))
                            except Exception as e2:
                                logger.error(f"Failed to save even minimal message: {e2}")
        except Exception as e:
            logger.error(f"Error in save_messages: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def load_conversation(self, user_id: str, partner_name: str, limit: int = 50) -> Dict[str, Any]:
        """Load conversation history for a user-partner combination"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get conversation info for this user-partner combination
                cursor.execute("""
                    SELECT conversation_id, user_email 
                    FROM adam_conversations 
                    WHERE user_id = %s AND partner_name = %s
                """, (user_id, partner_name))
                
                conv_info = cursor.fetchone()
                if not conv_info:
                    return {"conversation_id": str(uuid.uuid4()), "conversations": []}
                
                conversation_id = str(conv_info['conversation_id'])
                
                # Get messages with limit
                cursor.execute("""
                    SELECT message_id, message_type, content, metadata, 
                           additional_kwargs, timestamp
                    FROM adam_messages 
                    WHERE conversation_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (conv_info['conversation_id'], limit))
                
                messages = cursor.fetchall()
                
                # Group messages by timestamp (session)
                conversations = []
                if messages:
                    # Reverse to get chronological order
                    messages.reverse()
                    
                    # Group messages into conversation sessions
                    current_session = {
                        "timestamp": messages[0]['timestamp'],
                        "messages": [],
                        "metadata": messages[0]['metadata'] or {}
                    }
                    
                    for msg in messages:
                        msg_data = {
                            "type": msg['message_type'],
                            "content": msg['content'],
                            "additional_kwargs": msg['additional_kwargs'] or {}
                        }
                        
                        # Check if this is a new session (more than 30 minutes gap)
                        time_diff = (msg['timestamp'] - current_session['timestamp']).total_seconds()
                        if time_diff > 1800:  # 30 minutes
                            conversations.append(current_session)
                            current_session = {
                                "timestamp": msg['timestamp'],
                                "messages": [msg_data],
                                "metadata": msg['metadata'] or {}
                            }
                        else:
                            current_session['messages'].append(msg_data)
                            if msg['metadata']:
                                current_session['metadata'] = msg['metadata']
                    
                    conversations.append(current_session)
                
                return {
                    "conversation_id": conversation_id,
                    "conversations": conversations
                }
    
    def delete_all_conversations(self, user_id: str, partner_name: Optional[str] = None) -> bool:
        """Delete conversations for a user (optionally filtered by partner)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if partner_name:
                    # Delete conversation for specific user-partner combination
                    cursor.execute("""
                        DELETE FROM adam_conversations 
                        WHERE user_id = %s AND partner_name = %s
                    """, (user_id, partner_name))
                else:
                    # Delete all conversations for user across all partners
                    cursor.execute("""
                        DELETE FROM adam_conversations 
                        WHERE user_id = %s
                    """, (user_id,))
                
                return cursor.rowcount > 0
    
    def save_user_preferences(self, user_id: str, user_email: str, preferences: Dict[str, Any]):
        """Save user preferences (long-term memory)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO adam_user_preferences (user_id, user_email, preferences, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        preferences = %s,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, user_email, Json(preferences), Json(preferences)))
    
    def load_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Load user preferences (long-term memory)"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT preferences 
                    FROM adam_user_preferences 
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                return result['preferences'] if result else {}
    
    def get_active_users_count(self) -> int:
        """Get count of active users"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM adam_conversations")
                result = cursor.fetchone()
                return result[0] if result else 0
    
    # ========== Feedback Methods ==========
    
    def save_feedback(
        self, 
        user_email: str, 
        partner_name: str, 
        user_query: str,
        ai_response: str,
        feedback: str,
        sentiment: str,
        agent_name: str = "Adam Setup",
        timestamp: Optional[str] = None
    ) -> str:
        """Save user feedback to database"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if timestamp:
                    # Use provided timestamp (for migration)
                    cursor.execute("""
                        INSERT INTO adam_feedback (
                            user_email, partner_name, agent_name,
                            user_query, ai_response, feedback,
                            sentiment, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING feedback_id
                    """, (
                        user_email, partner_name, agent_name,
                        user_query, ai_response, feedback,
                        sentiment, timestamp
                    ))
                else:
                    # Use current timestamp
                    cursor.execute("""
                        INSERT INTO adam_feedback (
                            user_email, partner_name, agent_name,
                            user_query, ai_response, feedback,
                            sentiment
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING feedback_id
                    """, (
                        user_email, partner_name, agent_name,
                        user_query, ai_response, feedback,
                        sentiment
                    ))
                
                result = cursor.fetchone()
                feedback_id = str(result[0]) if result else None
                logger.info(f"Feedback saved with ID: {feedback_id}")
                return feedback_id
    
    def get_feedback(
        self,
        offset: int = 0,
        limit: int = 50,
        sentiment: Optional[str] = None,
        status: Optional[str] = None,
        partner_name: Optional[str] = None,
        user_email: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get feedback with filters and pagination"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build query with filters
                query = "SELECT * FROM adam_feedback WHERE 1=1"
                params = []
                
                if sentiment:
                    query += " AND sentiment = %s"
                    params.append(sentiment)
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                if partner_name:
                    query += " AND partner_name = %s"
                    params.append(partner_name)
                
                if user_email:
                    query += " AND user_email = %s"
                    params.append(user_email)
                
                if start_date:
                    query += " AND created_at >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND created_at <= %s"
                    params.append(end_date)
                
                # Get total count before adding sorting and pagination
                count_query = query.replace("SELECT *", "SELECT COUNT(*)")
                cursor.execute(count_query, params)
                total = cursor.fetchone()['count']
                
                # Add sorting
                valid_sort_fields = ["created_at", "sentiment", "status", "user_email", "partner_name"]
                if sort_by in valid_sort_fields:
                    sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
                    query += f" ORDER BY {sort_by} {sort_direction}"
                else:
                    query += " ORDER BY created_at DESC"
                
                # Add pagination
                query += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                # Execute query
                cursor.execute(query, params)
                feedback_list = cursor.fetchall()
                
                # Convert to list of dicts and handle UUIDs
                results = []
                for item in feedback_list:
                    feedback_dict = dict(item)
                    feedback_dict['feedback_id'] = str(feedback_dict['feedback_id'])
                    # Ensure notes is always a string (convert NULL to empty string)
                    feedback_dict['notes'] = feedback_dict.get('notes') or ''
                    results.append(feedback_dict)
                
                return {
                    "feedback": results,
                    "total": total,
                    "offset": offset,
                    "limit": limit,
                    "has_more": (offset + limit) < total
                }
    
    def get_feedback_stats(
        self,
        partner_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get feedback statistics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build base query with filters
                where_clauses = []
                params = []
                
                if partner_name:
                    where_clauses.append("partner_name = %s")
                    params.append(partner_name)
                
                if start_date:
                    where_clauses.append("created_at >= %s")
                    params.append(start_date)
                
                if end_date:
                    where_clauses.append("created_at <= %s")
                    params.append(end_date)
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Get overall stats
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE sentiment = 'positive') as positive,
                        COUNT(*) FILTER (WHERE sentiment = 'negative') as negative,
                        COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral,
                        COUNT(*) FILTER (WHERE status = 'To Consider') as to_consider,
                        COUNT(*) FILTER (WHERE status = 'Considered') as considered,
                        COUNT(*) FILTER (WHERE status = 'Ignored') as ignored
                    FROM adam_feedback
                    WHERE {where_clause}
                """, params)
                
                stats = cursor.fetchone()
                
                # Get stats by partner
                cursor.execute(f"""
                    SELECT 
                        partner_name,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE sentiment = 'positive') as positive,
                        COUNT(*) FILTER (WHERE sentiment = 'negative') as negative,
                        COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral
                    FROM adam_feedback
                    WHERE {where_clause}
                    GROUP BY partner_name
                """, params)
                
                by_partner = cursor.fetchall()
                
                return {
                    "total": stats['total'],
                    "positive": stats['positive'],
                    "negative": stats['negative'],
                    "neutral": stats['neutral'],
                    "to_consider": stats['to_consider'],
                    "considered": stats['considered'],
                    "ignored": stats['ignored'],
                    "by_partner": {
                        item['partner_name']: {
                            "total": item['total'],
                            "positive": item['positive'],
                            "negative": item['negative'],
                            "neutral": item['neutral']
                        }
                        for item in by_partner
                    }
                }
    
    def update_feedback_status(self, feedback_id: str, status: str) -> bool:
        """Update feedback status"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE adam_feedback 
                    SET status = %s 
                    WHERE feedback_id = %s
                """, (status, feedback_id))
                
                return cursor.rowcount > 0
    
    def update_feedback_notes(self, feedback_id: str, notes: str) -> bool:
        """Update feedback notes"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE adam_feedback 
                    SET notes = %s 
                    WHERE feedback_id = %s
                """, (notes, feedback_id))
                
                return cursor.rowcount > 0
    
    def delete_feedback(self, feedback_id: str) -> bool:
        """Delete feedback (admin operation)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM adam_feedback 
                    WHERE feedback_id = %s
                """, (feedback_id,))
                
                return cursor.rowcount > 0
    
    def get_feedback_count(self) -> int:
        """Get total count of feedback entries"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM adam_feedback")
                result = cursor.fetchone()
                return result[0] if result else 0 