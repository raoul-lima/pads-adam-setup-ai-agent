import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import concurrent.futures
import uuid

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from graph_system.states import SystemState
from langchain.prompts import ChatPromptTemplate
from config.configs import llm_gpt, llm_gemini_flash
from utils.gcs_uploader import read_json_from_gcs, upload_json_to_gcs
from utils.constants import USE_POSTGRES_STORAGE, POSTGRES_CONFIG, MAX_CONVERSATION_HISTORY, DATA_BUCKET_NAME
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread pool executor for background tasks
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Storage backend selection
if USE_POSTGRES_STORAGE:
    from utils.postgres_storage import PostgreSQLStorage
    # Initialize PostgreSQL storage
    try:
        storage_backend = PostgreSQLStorage(POSTGRES_CONFIG)
        logger.info("Using PostgreSQL storage backend")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL storage: {e}")
        logger.warning("Falling back to in-memory storage")
        USE_POSTGRES_STORAGE = False
        in_memory_storage = {}
else:
    # In-memory storage for backward compatibility
    in_memory_storage = {}
    logger.info("Using in-memory storage backend")

class EnhancedMemoryAgent:
    """
    Enhanced memory agent with configurable conversation history limit.
    
    The conversation history limit can be configured via:
    1. Environment variable: MAX_CONVERSATION_HISTORY (default: 10)
    2. Constructor parameter: max_history (overrides environment variable)
    
    Conversations are isolated by user_id AND partner_name combination.
    """
    
    def __init__(self, user_id: str, user_email: str, partner_name: str, max_history: Optional[int] = None, enable_long_term_memory: bool = True):
        self.user_id = user_id
        self.user_email = user_email
        self.partner_name = partner_name
        self.max_history = max_history if max_history is not None else MAX_CONVERSATION_HISTORY
        self.enable_long_term_memory = enable_long_term_memory
        self.long_term_memory_path = f"adam_agent_users/{self.user_email}/long_term_memory.json"
        
        # Create unique key for user-partner combination
        self.conversation_key = f"{self.user_id}:{self.partner_name}"
        
        # Initialize storage based on backend
        if USE_POSTGRES_STORAGE:
            # PostgreSQL handles initialization in the storage class
            pass
        else:
            # Initialize in-memory storage with user-partner key
            if self.conversation_key not in in_memory_storage:
                in_memory_storage[self.conversation_key] = {
                    "conversation_id": str(uuid.uuid4()),
                    "conversations": []
                }
    
    def get_conversation_limit(self) -> int:
        """Get the current conversation history limit for this agent"""
        return self.max_history
    
    @staticmethod
    def get_default_conversation_limit() -> int:
        """Get the default conversation history limit from configuration"""
        return MAX_CONVERSATION_HISTORY
    
    def load_long_term_memory(self) -> Dict:
        """Loads long-term user preferences from GCS."""
        if not self.enable_long_term_memory:
            return {}
        
        if USE_POSTGRES_STORAGE:
            # Load from PostgreSQL
            try:
                return storage_backend.load_user_preferences(self.user_id)
            except Exception as e:
                logger.error(f"Error loading long-term memory from PostgreSQL: {e}")
                return {}
        else:
            # Load from GCS (existing implementation)
            try:
                long_term_memory = read_json_from_gcs(DATA_BUCKET_NAME, self.long_term_memory_path)
                logger.info(f"Long-term memory loaded for user {self.user_id}: {long_term_memory}")
                return long_term_memory
            except FileNotFoundError:
                return {}  # Return empty dict if no preferences exist yet
            except Exception as e:
                print(f"Error loading long-term memory: {e}")
                return {}

    def save_long_term_memory(self, preferences: Dict) -> None:
        """Saves long-term user preferences to GCS."""
        if not self.enable_long_term_memory:
            return
        
        if USE_POSTGRES_STORAGE:
            # Save to PostgreSQL
            try:
                storage_backend.save_user_preferences(self.user_id, self.user_email, preferences)
            except Exception as e:
                logger.error(f"Error saving long-term memory to PostgreSQL: {e}")
        else:
            # Save to GCS (existing implementation)
            try:
                upload_json_to_gcs(DATA_BUCKET_NAME, self.long_term_memory_path, preferences)
            except Exception as e:
                print(f"Error saving long-term memory: {e}")

    def _update_long_term_memory(self, conversation_text: str, existing_preferences: Dict) -> Dict:
        """
        Uses an LLM to extract user preferences from the conversation and update them.
        """
        if not self.enable_long_term_memory:
            return existing_preferences
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are an expert at analyzing conversations to extract user preferences and details.
Based on the provided conversation, extract or update the following information in a JSON format:
- "user_name": The user's name if mentioned.
- "preferred_analysis": Any specific types of analysis the user asks for (e.g., "performance", "budget").
- "naming_conventions": Any specific naming conventions the user mentions for campaigns, line items, etc.
- "other_details": Any other recurring requests or important details.
Update the existing preferences with the information provided in the conversation. And if the user wants to make keep track of something, add it to the "other_details" field.
Respect the user when they want to remove something from the preferences, the my also want to remove the entire data, want you not to remember it.
             
If no information is found, or there is no user conversation, return the existing preferences.

Current preferences are:
{existing_preferences}

Respond ONLY with the updated JSON object. If no new information is found, return the existing preferences.
"""),
            ("human", conversation_text)
        ])
        
        chain = prompt | llm_gemini_flash
        try:
            response = chain.invoke({
                "existing_preferences": json.dumps(existing_preferences, indent=2),
                "conversation_text": conversation_text
            })
            # Clean the response to ensure it's valid JSON
            if hasattr(response, 'content'):
                cleaned_response = str(response.content).strip().replace("```json", "").replace("```", "")
            else:
                cleaned_response = str(response).strip().replace("```json", "").replace("```", "")
            updated_prefs = json.loads(cleaned_response)
            return updated_prefs
        except Exception as e:
            print(f"Error updating long-term memory with LLM: {e}")
            return existing_preferences
    
    def _serialize_messages(self, messages: List[BaseMessage]) -> List[Dict]:
        """Serialize BaseMessage objects to JSON-compatible dictionaries"""
        serialized = []
        for msg in messages:
            # Safely handle additional_kwargs - only include serializable content
            additional_kwargs = {}
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                # Filter out non-serializable items
                for key, value in msg.additional_kwargs.items():
                    try:
                        # Test if the value is JSON serializable
                        json.dumps(value)
                        additional_kwargs[key] = value
                    except (TypeError, ValueError):
                        # Skip non-serializable values
                        logger.debug(f"Skipping non-serializable additional_kwargs[{key}]")
                        pass
            
            serialized.append({
                "type": type(msg).__name__,
                "content": msg.content,
                "additional_kwargs": additional_kwargs
            })
        return serialized
    
    def _deserialize_messages(self, messages_data: List[Dict]) -> List[BaseMessage]:
        messages = []
        for msg_data in messages_data:
            if msg_data["type"] == "HumanMessage":
                messages.append(
                    HumanMessage(
                        content=msg_data["content"],
                        additional_kwargs=msg_data.get("additional_kwargs", {})
                    )
                )
            elif msg_data["type"] == "AIMessage":
                messages.append(
                    AIMessage(
                        content=msg_data["content"],
                        additional_kwargs=msg_data.get("additional_kwargs", {})
                    )
                )
        return messages
    
    def get_conversation_id(self) -> str:
        """Get the conversation ID for this user-partner combination"""
        if USE_POSTGRES_STORAGE:
            return storage_backend.get_or_create_conversation(self.user_id, self.user_email, self.partner_name)
        else:
            user_data = in_memory_storage.get(self.conversation_key, {})
            return user_data.get("conversation_id", str(uuid.uuid4()))
    
    def get_formatted_conversation_history(self) -> List[Dict[str, str]]:
        """Get properly formatted and deduplicated conversation history for prompts"""
        try:
            conversation_data = self.load_conversation()
            messages = []
            
            if conversation_data and "conversation_history" in conversation_data:
                # Collect all messages with their conversation timestamps
                all_messages_with_timestamps = []
                
                # Sort conversations by timestamp (oldest first for proper message ordering)
                sorted_conversations = sorted(
                    conversation_data["conversation_history"], 
                    key=lambda x: x["timestamp"]
                )
                
                for conversation in sorted_conversations:
                    conversation_timestamp = conversation["timestamp"]
                    for msg in conversation["messages"]:
                        message_data = {
                            "type": "human" if isinstance(msg, HumanMessage) else "ai",
                            "content": msg.content,
                            "timestamp": conversation_timestamp
                        }
                        all_messages_with_timestamps.append(message_data)
                
                # Deduplicate messages based on content and type while preserving order
                seen_messages = set()
                for message_data in all_messages_with_timestamps:
                    # Create a unique key for deduplication
                    message_key = (message_data["type"], message_data["content"])
                    if message_key not in seen_messages:
                        seen_messages.add(message_key)
                        messages.append(message_data)
            
            return messages
        except Exception as e:
            print(f"Error getting formatted conversation history: {str(e)}")
            return []
    
    def get_conversation_history_for_prompt(self) -> str:
        """Get conversation history formatted as a string for prompt inclusion"""
        try:
            messages = self.get_formatted_conversation_history()
            
            if not messages:
                return "No conversation history available"
            
            formatted_history = []
            for msg in messages:
                role = "Human" if msg["type"] == "human" else "Assistant"
                formatted_history.append(f"{role}: {msg['content']}")
            
            return "\n".join(formatted_history)
        except Exception as e:
            print(f"Error formatting conversation history for prompt: {str(e)}")
            return "No conversation history available"

    def _save_(self, state: Dict[str, Any]) -> None:
        """Save conversation state. Long-term memory updates run in the background."""
        try:
            # Debug: Check state for non-serializable content
            for key, value in state.items():
                if value is not None:
                    # Special check for AIMessage objects
                    if hasattr(value, '__class__') and 'AIMessage' in str(type(value)):
                        logger.warning(f"Found AIMessage in state['{key}']! This should not be in metadata.")
                        continue
                    try:
                        json.dumps(value)
                    except (TypeError, ValueError) as e:
                        logger.debug(f"State['{key}'] is not JSON serializable: {type(value)} - {str(e)[:100]}")
            
            state_copy = state.copy()
            
            if "internal_messages" in state_copy:
                del state_copy["internal_messages"]
            
            all_messages = []
            if "messages" in state_copy:
                messages = state_copy["messages"]
                for msg in messages:
                    if isinstance(msg, (HumanMessage, AIMessage)):
                        all_messages.append(msg)
            
            # Skip saving if no messages to save
            if not all_messages:
                return
                
            serialized_msgs = self._serialize_messages(all_messages)
            
            # Build metadata - ensure all values are JSON serializable
            metadata = {}
            metadata_fields = {
                "theme": state.get("theme"),
                "code_gen_agent_breafing_ready": state.get("code_gen_agent_breafing_ready", False),
                "in_analysis": state.get("in_analysis", False),
                "user_language": state.get("user_language"),
                "advertiser_id": state.get("advertiser_id"),
                "partner_name": state.get("partner_name")
            }
            
            # Filter out non-serializable values
            for key, value in metadata_fields.items():
                try:
                    # Test if the value is JSON serializable
                    json.dumps(value)
                    metadata[key] = value
                except (TypeError, ValueError):
                    logger.warning(f"Skipping non-serializable metadata field '{key}': {type(value)}")
                    metadata[key] = None
            
            # Save short-term memory synchronously (fast operation)
            if USE_POSTGRES_STORAGE:
                # PostgreSQL storage
                conversation_id = self.get_conversation_id()
                
                # Transform messages to the format expected by PostgreSQL storage
                messages_for_db = []
                for msg in serialized_msgs:
                    msg_type = "human" if msg["type"] == "HumanMessage" else "ai"
                    messages_for_db.append({
                        "type": msg_type,
                        "content": msg["content"],
                        "additional_kwargs": msg.get("additional_kwargs", {})
                    })
                
                storage_backend.save_messages(conversation_id, messages_for_db, metadata)
            else:
                # In-memory storage (using conversation_key for user-partner combination)
                # Check if this exact conversation state was already saved (prevent duplicates)
                user_data = in_memory_storage.get(self.conversation_key, {"conversation_id": str(uuid.uuid4()), "conversations": []})
                
                # Check if the last saved conversation has the same messages
                if user_data["conversations"]:
                    last_conversation = user_data["conversations"][0]  # Most recent is first
                    if last_conversation["messages"] == serialized_msgs:
                        # Same messages already saved, skip
                        return
                
                conversation_data = {
                    "timestamp": datetime.now(),
                    "messages": serialized_msgs,
                    "metadata": metadata
                }
                
                user_data["conversations"].append(conversation_data)
                
                # Keep only the most recent N conversations
                user_data["conversations"].sort(key=lambda x: x["timestamp"], reverse=True)
                user_data["conversations"] = user_data["conversations"][:self.max_history]
                
                in_memory_storage[self.conversation_key] = user_data

            # --- Long-Term Memory Update (run in background if enabled) ---
            if self.enable_long_term_memory:
                # Submit long-term memory update to background thread
                future = _executor.submit(
                    self._update_long_term_memory_async,
                    serialized_msgs[-4:],  # Last 4 messages
                    state
                )
                
                # Log any exceptions from the background task
                def log_exception(future):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in background long-term memory update: {e}")
                
                future.add_done_callback(log_exception)

        except Exception as e:
            print(f"Error in save_conversation: {str(e)}")
            raise e
    
    def _update_long_term_memory_async(self, recent_messages: List[Dict], state: Dict[str, Any]) -> None:
        """Background task to update long-term memory"""
        try:
            conversation_text = "\n".join([f"{msg['type']}: {msg['content']}" for msg in recent_messages])
            
            long_term_memory = self.load_long_term_memory()
            updated_long_term_memory = self._update_long_term_memory(conversation_text, long_term_memory)
            
            if updated_long_term_memory != long_term_memory:
                logger.info(f"Long-term memory updated for user {self.user_id}")
                self.save_long_term_memory(updated_long_term_memory)
                # Note: We can't update the state here as it's in a background thread
                # The next conversation turn will pick up the updated long-term memory
        except Exception as e:
            logger.error(f"Error in background long-term memory update: {e}")

    def load_conversation(self) -> Dict[str, Any]:
        try:
            if USE_POSTGRES_STORAGE:
                # Load from PostgreSQL for this user-partner combination
                pg_data = storage_backend.load_conversation(self.user_id, self.partner_name, self.max_history)
                
                if not pg_data.get("conversations"):
                    return {"conversation_id": pg_data.get("conversation_id", str(uuid.uuid4()))}
                
                all_messages = []
                all_metadata = []
                conversation_history = []
                
                for conv in pg_data["conversations"]:
                    # Deserialize messages
                    messages = []
                    for msg in conv["messages"]:
                        if msg["type"] == "human":
                            messages.append(
                                HumanMessage(
                                    content=msg["content"],
                                    additional_kwargs=msg.get("additional_kwargs", {})
                                )
                            )
                        elif msg["type"] == "ai":
                            messages.append(
                                AIMessage(
                                    content=msg["content"],
                                    additional_kwargs=msg.get("additional_kwargs", {})
                                )
                            )
                    
                    all_messages.extend(messages)
                    all_metadata.append(conv["metadata"])
                    
                    conversation_history.append({
                        "timestamp": str(conv["timestamp"]),
                        "messages": messages,
                        "metadata": conv["metadata"]
                    })
                
                latest_metadata = all_metadata[0] if all_metadata else {}
                
                return {
                    "conversation_id": pg_data["conversation_id"],
                    "messages": all_messages,
                    "metadata": latest_metadata,
                    "theme": latest_metadata.get("theme"),
                    "code_gen_agent_breafing_ready": latest_metadata.get("code_gen_agent_breafing_ready", False),
                    "in_analysis": latest_metadata.get("in_analysis", False),
                    "user_language": latest_metadata.get("user_language"),
                    "advertiser_id": latest_metadata.get("advertiser_id"),
                    "partner_name": latest_metadata.get("partner_name"),
                    "conversation_history": conversation_history
                }
            else:
                # In-memory storage (using conversation_key for user-partner combination)
                user_data = in_memory_storage.get(self.conversation_key, {"conversation_id": str(uuid.uuid4()), "conversations": []})
                user_memories = user_data.get("conversations", [])
                conversation_id = user_data.get("conversation_id", str(uuid.uuid4()))
                
                if not user_memories:
                    return {"conversation_id": conversation_id}

                all_messages = []
                all_metadata = []
                
                for memory in user_memories:
                    messages = self._deserialize_messages(memory["messages"])
                    all_messages.extend(messages)
                    all_metadata.append(memory["metadata"])
                
                latest_metadata = all_metadata[0] if all_metadata else {}
                
                return {
                    "conversation_id": conversation_id,
                    "messages": all_messages,
                    "metadata": latest_metadata,
                    "theme": latest_metadata.get("theme"),
                    "code_gen_agent_breafing_ready": latest_metadata.get("code_gen_agent_breafing_ready", False),
                    "in_analysis": latest_metadata.get("in_analysis", False),
                    "user_language": latest_metadata.get("user_language"),
                    "advertiser_id": latest_metadata.get("advertiser_id"),
                    "partner_name": latest_metadata.get("partner_name"),
                    "conversation_history": [
                        {
                            "timestamp": str(memory["timestamp"]),
                            "messages": self._deserialize_messages(memory["messages"]),
                            "metadata": memory["metadata"]
                        }
                        for memory in user_memories
                    ]
                }
        except Exception as e:
            print(f"Error in load_conversation: {str(e)}")
            return {"conversation_id": str(uuid.uuid4())}

    def delete_all_conversations(self) -> bool:
        """Delete conversation for this user-partner combination"""
        if USE_POSTGRES_STORAGE:
            return storage_backend.delete_all_conversations(self.user_id, self.partner_name)
        else:
            if self.conversation_key in in_memory_storage:
                # Reset to fresh state with new conversation_id
                in_memory_storage[self.conversation_key] = {
                    "conversation_id": str(uuid.uuid4()),
                    "conversations": []
                }
                return True
            return False

    def close(self):
        """Close any resources (placeholder for future use)"""
        pass
    
    def __del__(self):
        self.close()

def memory_agent(state: SystemState, config: RunnableConfig) -> Dict[str, Any]:
    configurable = config.get("configurable", {})
    user_id = configurable.get("user_id", "")
    user_email = configurable.get("user_email", "")
    partner_name = configurable.get("partner_name", "Default Partner")
    enable_long_term_memory = configurable.get("enable_long_term_memory", True)
    
    # Check if memory usage is disabled (e.g. for evaluations)
    use_memory = configurable.get("use_memory", True)
    
    updated_state = state.copy()
    
    if not use_memory:
        logger.info(f"Memory usage disabled for request (User: {user_email})")
        # Return empty history and long term memory
        updated_state["chat_history"] = []
        updated_state["long_term_memory"] = {}
        return dict(updated_state)
    
    memory = EnhancedMemoryAgent(user_id, user_email, partner_name, enable_long_term_memory=enable_long_term_memory)
    
    # Load short-term and long-term memory
    long_term_memory = memory.load_long_term_memory()
    
    # Get properly formatted conversation history for agents to use
    chat_history = memory.get_formatted_conversation_history()
    updated_state["chat_history"] = chat_history

    # Add long-term memory to the state (will be empty dict if disabled)
    updated_state["long_term_memory"] = long_term_memory
    
    # Don't save here - saving happens once at the end in main.py after all processing
    # This prevents duplicate message saves
    
    return dict(updated_state)

def shutdown_memory_executor():
    """Shutdown the thread pool executor. Call this when the application exits."""
    _executor.shutdown(wait=True)
    logger.info("Memory agent executor shutdown complete")