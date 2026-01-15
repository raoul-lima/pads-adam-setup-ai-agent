import re
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from typing import Dict, Any
from datetime import datetime, timedelta

from graph_system.states import SystemState
from config.configs import llm_gemini_flash
from agents.prompts.analyser_prompt_creator import analyser_prompt
from agents.language_detecter import detect_user_language
from langchain_core.runnables import RunnableConfig

AGENT_ANALYSER_LLM = llm_gemini_flash

def agent_analyser(state: SystemState, config: RunnableConfig) -> dict:
    """Analyser the user's request and generate a structured briefing for the code generation agent"""

    configurable = config.get("configurable", {})
    user_email = configurable.get("user_email", "")
    partner_name = configurable.get("partner_name", "")

    metadata = state.get("metadata", {})
    
    # Get properly formatted conversation history
    chat_history = state.get("chat_history", [])
    long_term_memory = state.get("long_term_memory", {})
    intent_summary = state.get("intent_summary", "")

    # Extraire le message actuel et détecter la langue
    messages = state["messages"]
    user_msg_text = messages[-1].content
    user_language = detect_user_language(user_msg_text)
    
    # Add dynamic temporal context
    current_datetime = datetime.now()
    snapshot_date = (current_datetime - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Créer le prompt avec l'historique
    prompt_analyser = analyser_prompt.format_messages(
        instruction_block=state["instruction_block"],
        intent_summary=intent_summary,
        messages=messages,        
        metadata=metadata,
        chat_history=chat_history,
        long_term_memory=long_term_memory,
        user_language=user_language,
        user_email=user_email,
        partner_name=partner_name,
        current_datetime=current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        snapshot_date=snapshot_date
    )
    
    # Get response with tool calling
    ai_msg = AGENT_ANALYSER_LLM.invoke(prompt_analyser)
    
    internal_messages = state.get("internal_messages", [])
    internal_messages.append(ai_msg)

    if isinstance(ai_msg.content, str):
        match = re.search(r"<(.*?)>(.*?)</(.*?)>", ai_msg.content, re.DOTALL)
    else:
        match = None

    if match:
        
        new_state = {
            **state,
            "internal_messages": internal_messages,
            "code_gen_agent_briefing": ai_msg.content,
            "code_gen_agent_breafing_ready": True,
            "user_language": user_language,
            "in_analysis": False
        }
    else:
        # Fallback if no tool call (shouldn't happen with proper prompting)
        new_state = {
            **state,
            "messages": messages + [ai_msg],
            "internal_messages": internal_messages,
            "code_gen_agent_breafing_ready": False,
            "user_language": user_language,
            "in_analysis": True
        }
    
    return new_state