import os
import sys
import logging
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from graph_system.states import SystemState
from config.configs import llm_gemini_flash
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agents.prompts.dsp_prompt import dsp_prompt
from agents.tools.dsp_tools import adsecura,dv360,sa360,cm360,amz,amc,amz_api,xandr,ga4,tagmanager

AGENT_DSP_LLM = llm_gemini_flash


def dsp_agent(user_message: str = None, conversation_history: str = "") -> str:
    if not user_message:
        return "Please provide a message to process."

    # Create tools list
    tools = [adsecura, dv360, sa360,cm360,amz,amc,amz_api,xandr,ga4,tagmanager]
    llm_with_tools = AGENT_DSP_LLM.bind_tools(tools)

    # Create the initial message and format prompt with conversation history
    messages = [HumanMessage(content=user_message)]
    prompt_dsp = dsp_prompt.format_messages(
        messages=messages,
        chat_history=conversation_history
    )

    try:
        # Get initial response using the formatted prompt
        response = llm_with_tools.invoke(prompt_dsp)
        
        # If the LLM wants to use tools
        if hasattr(response, 'tool_calls') and response.tool_calls:
            messages.append(response)
            
            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                tool_functions = {
                    'adsecura': adsecura,
                    'dv360': dv360,
                    'sa360': sa360,
                    'cm360': cm360,
                    'ga4': ga4,
                    'amz': amz,
                    'amc': amc,
                    'amz_api': amz_api,
                    'xandr': xandr,
                    'tagmanager': tagmanager
                }
                
                if tool_name in tool_functions:
                    try:
                        tool_result = tool_functions[tool_name].invoke(tool_args)
                        messages.append(ToolMessage(
                            content=tool_result,
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as tool_error:
                        logging.error(f"Error executing tool {tool_name}: {str(tool_error)}")
                        messages.append(ToolMessage(
                            content=f"Error executing tool {tool_name}: {str(tool_error)}",
                            tool_call_id=tool_call["id"]
                        ))
                else:
                    logging.warning(f"Unknown tool: {tool_name}")
                    messages.append(ToolMessage(
                        content=f"Tool {tool_name} not found",
                        tool_call_id=tool_call["id"]
                    ))
            
            # Get final response using updated messages with tool results
            final_prompt = dsp_prompt.format_messages(
                messages=messages,
                chat_history=conversation_history
            )
            final_response = llm_with_tools.invoke(final_prompt)
            
            
            if hasattr(final_response, 'content'):
                return final_response.content or "I couldn't process the tool results properly. Please try again."
            else:
                logging.error("No content in final response")
                return "There was an issue processing the tool results. Please try again."
            
        else:
            # Direct response without tool calls
            logging.info("No tool calls detected, returning direct response")
            if hasattr(response, 'content'):
                return response.content or "I couldn't understand your request. Please try rephrasing it."
            else:
                return "I couldn't process your request properly. Please try again."
            
    except Exception as e:
        logging.error(f"Error in DSP agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"An error occurred while processing your request: {str(e)}. Please try again or contact support if the issue persists."

def dsp_agent_with_state(state: SystemState) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return state
    
    # Extract conversation history
    conversation_history = ""
    
    # First check if chat_history is already in state (from memory_agent)
    if "chat_history" in state:
        conversation_history = state["chat_history"]
    
    # If still no history, create a simple history from current messages
    if not conversation_history and len(messages) > 1:
        history_lines = []
        for msg in messages[:-1]:  # Exclude the last message (current query)
            if isinstance(msg, HumanMessage):
                history_lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                history_lines.append(f"Assistant: {msg.content[:500]}...")  # Truncate long responses
        conversation_history = "\n".join(history_lines[-10:])  # Keep last 10 exchanges
    
    last_message = messages[-1]
    user_message = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Log conversation history usage
    if conversation_history:
        logging.info(f"DSP Agent using conversation history ({len(conversation_history)} chars)")
    else:
        logging.info("DSP Agent running without conversation history")
    
    # Call dsp_agent with conversation history
    response = dsp_agent(user_message, conversation_history)
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response)]
    }
