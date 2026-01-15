"""
Chat Routes
===========
Endpoints for conversation management and message processing.
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import logging
import asyncio

from .models import ChatMessage, AdamChatResponse, HistoryRequest, ResetRequest
from utils.helpers import get_user_id_from_email
from agents.memory_agent import EnhancedMemoryAgent
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

# These will be injected by main.py
_get_graph = None
_get_metadata = None


def init_dependencies(get_graph_func, get_metadata_func):
    """Initialize dependencies from main.py"""
    global _get_graph, _get_metadata
    _get_graph = get_graph_func
    _get_metadata = get_metadata_func


@router.post(
    "/message", 
    response_model=AdamChatResponse,
    summary="Process Chat Message",
    description="""
    Process a user message through the Adam Setup multi-agent system.
    
    This endpoint:
    - Processes the message through multiple AI agents
    - Maintains conversation context and history
    - Returns AI response with any generated download links
    - Tracks conversation for the specific user
    
    The system uses advanced AI agents for DV360 data analysis and setup automation.
    """
)
async def process_message(message: ChatMessage):
    """Process a chat message through the multi-agent system"""
    try:
        user_email = message.user_email
        user_id = get_user_id_from_email(user_email)
        partner_name = message.partner
        
        # Get cached graph (singleton - compiled once at startup)
        graph = _get_graph()
        
        # Get conversation_id from memory agent (isolated by user-partner combination)
        memory_agent = EnhancedMemoryAgent(user_id, user_email, partner_name)
        conversation_id = memory_agent.get_conversation_id()
        
        # Create human message
        human_message = HumanMessage(content=message.content)
        
        # Create thread ID and config
        # Include partner_name in thread_id to ensure proper isolation between user-partner combinations
        # This prevents state interference if checkpointing is enabled in the future
        thread_id = f"thread_{user_id}_{partner_name}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "user_email": user_email,
                "partner_name": partner_name,
                "use_memory": message.use_memory
            }
        }
        
        # Process through the graph using ASYNC streaming
        # CRITICAL for Cloud Run: async allows handling multiple concurrent requests
        final_state = {}
        async for event in graph.astream(
            {"messages": [human_message], "metadata": _get_metadata()},
            config,
            stream_mode="values"
        ):
            final_state = event
        
        # Save the conversation state in BACKGROUND (non-blocking)
        # Only if memory is enabled
        # This improves user-perceived latency by ~50-200ms
        if message.use_memory:
            asyncio.create_task(
                asyncio.to_thread(memory_agent._save_, final_state)
            )

        # Check if the final state is valid
        if not final_state:
            raise HTTPException(status_code=500, detail="Graph execution did not return a final state.")
        
        # Extract final response message and download links from the final state and return it to the user (if the graph execution is successful)   
        all_messages = final_state.get("messages", [])
        final_ai_message = next((msg for msg in reversed(all_messages) if isinstance(msg, AIMessage)), None)
        final_response = final_ai_message.content if final_ai_message else "No response generated"
        download_links = final_state.get("download_links", [])
        
        logger.info(f"Processed message for user {user_email} (ID: {user_id})")
        
        # Ensure download_links is properly serializable
        serializable_download_links = []
        if download_links:
            for link in download_links:
                if isinstance(link, dict):
                    serializable_download_links.append(link)
                else:
                    logger.warning(f"Skipping non-dict download link: {type(link)}")
        
        return AdamChatResponse(
            response=final_response,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            download_links=serializable_download_links
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.post(
    "/history",
    summary="Get Conversation History",
    description="""
    Retrieve the complete conversation history for a specific user.
    
    Returns:
    - All previous messages in chronological order
    - Message types (human/ai) with timestamps
    - Download links associated with AI responses
    - Conversation ID for tracking
    
    Useful for restoring chat context or reviewing past interactions.
    """
)
async def get_conversation_history(request: HistoryRequest):
    """Get conversation history for a given user email and partner combination."""
    try:
        user_id = get_user_id_from_email(request.user_email)
        user_email = request.user_email
        partner_name = request.partner
        
        # Create memory agent to load full conversation history for this user-partner combination
        memory_agent = EnhancedMemoryAgent(user_id, user_email, partner_name)
        conversation_data = memory_agent.load_conversation()
        
        messages = []
        
        # If we have conversation history from memory agent
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
                    # Include download_links stored in additional_kwargs for AI messages only
                    if not isinstance(msg, HumanMessage):
                        additional = getattr(msg, "additional_kwargs", {}) or {}
                        links = additional.get("download_links")
                        if isinstance(links, list):
                            # Basic validation of links structure
                            clean_links = []
                            for link in links:
                                if isinstance(link, dict) and "url" in link and "label" in link:
                                    clean_links.append({"url": link["url"], "label": link["label"]})
                            if clean_links:
                                message_data["download_links"] = clean_links
                    all_messages_with_timestamps.append(message_data)
            
            # Deduplicate messages based on content, type and download links while preserving order
            seen_messages = set()
            for message_data in all_messages_with_timestamps:
                # Create a unique key for deduplication
                links_key = tuple(
                    (link.get("url"), link.get("label"))
                    for link in message_data.get("download_links", [])
                ) if message_data.get("download_links") else None
                message_key = (message_data["type"], message_data["content"], links_key)
                if message_key not in seen_messages:
                    seen_messages.add(message_key)
                    messages.append(message_data)
        
        # Get conversation_id from memory agent
        conversation_id = conversation_data.get("conversation_id")
        
        # If no conversation history found, return empty with conversation_id
        if not messages:
            return {"messages": [], "conversation_id": conversation_id}
        
        return {
            "messages": messages,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversation history"
        )


@router.post(
    "/reset",
    summary="Reset Conversation",
    description="""
    Reset/clear the conversation history for a specific user.
    
    This endpoint:
    - Deletes all conversation history for the user
    - Clears memory agent state
    - Starts fresh conversation context
    
    Use when user wants to start a new conversation without previous context.
    """
)
async def reset_conversation(request: ResetRequest):
    """Reset conversation for a given user email and partner combination."""
    try:
        user_email = request.user_email
        user_id = get_user_id_from_email(user_email)
        partner_name = request.partner
        
        # Clean up memory agent for this user-partner combination
        memory_agent = EnhancedMemoryAgent(user_id, user_email, partner_name)
        memory_agent.delete_all_conversations()
        memory_agent.close()
        
        logger.info(f"Reset conversation for user {user_email} (ID: {user_id})")
        
        return {"message": "Conversation reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting conversation"
        )

