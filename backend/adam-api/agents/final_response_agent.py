from langchain_core.messages import HumanMessage, AIMessage

from graph_system.states import SystemState
from agents.prompts.final_result_prompt import prompt_final_result
from config.configs import llm_gemini_flash

def final_response_agent(state: SystemState) -> dict:
    """Agent de réponse finale avec gestion de mémoire améliorée et support des liens de téléchargement"""
    
    # Get properly formatted conversation history
    chat_history = state.get("chat_history", [])
    last_user_msg = state["messages"][-1].content if state["messages"] else ""
    
    code_gen_agent_briefing = state.get("code_gen_agent_briefing", "No code gen agent briefing found.")
    user_language = state.get("user_language", "english")
    result_query = state.get("result_query", "No result query found.")
    intent_summary = state.get("intent_summary", "No intent summary found.")
    
    # Get structured result information
    processed_result = state.get("processed_result", {})
    download_links = state.get("download_links", [])
    
    result_type_info = ""
    if processed_result:
        result_type = processed_result.get("type", "unknown")
        status = processed_result.get("status", "unknown")
        result_type_info = f"\n\nResult Type: {result_type} (Status: {status})"
        
        # Handle error status specially
        if status == "error":
            error_details = processed_result.get("error_details", "Unknown error")
            result_type_info += f"\n\n⚠️ IMPORTANT: The code execution failed after multiple retry attempts."
            result_type_info += f"\nError Details: {error_details[:200]}..." if len(error_details) > 200 else f"\nError Details: {error_details}"
            result_type_info += "\n\nPlease inform the user that their request could not be completed due to technical issues and suggest they may need to:"
            result_type_info += "\n- Provide more specific requirements"
            result_type_info += "\n- Check if the data is available and properly formatted"
            result_type_info += "\n- Try a simpler version of the analysis"
        
        elif result_type == "dataframe":
            rows_count = processed_result.get("rows_count", 0)
            columns_count = processed_result.get("columns_count", 0)
            result_type_info += f"\nDataFrame Info: {rows_count} rows, {columns_count} columns"

        elif result_type in ["list", "dict", "conformance"]:
            items_count = processed_result.get("items_count", len(processed_result.get("processed_items", [])))
            result_type_info += f"\nContains: {items_count} items"
    
    # Enhanced prompt with structured information
    enhanced_prompt = prompt_final_result.format(
        user_language=user_language,
        code_gen_agent_briefing=code_gen_agent_briefing,
        intent_summary=intent_summary,
        result_query=result_query,
        chat_history=chat_history
    ) + result_type_info
    
    # Add instructions for handling download links
    if download_links:
        enhanced_prompt += "\n\nIMPORTANT: The user's data has been processed and uploaded to cloud storage. Make sure to tell the user to get them using the links below."
    
    response = llm_gemini_flash.invoke([HumanMessage(content=enhanced_prompt)])

    # Attach download_links to the AI message without exposing them to the model
    # Preserve any existing additional_kwargs and add download_links for persistence and retrieval in history
    if download_links:
        existing_kwargs = getattr(response, "additional_kwargs", {}) or {}
        additional_kwargs = existing_kwargs.copy()
        additional_kwargs["download_links"] = download_links
        appended_message = AIMessage(
            content=str(getattr(response, "content", "")),
            additional_kwargs=additional_kwargs
        )
    else:
        appended_message = response

    final_state = {
        **state,
        "messages": state["messages"] + [appended_message]
    }
    return final_state