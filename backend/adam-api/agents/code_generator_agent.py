from langchain_core.messages import HumanMessage

from graph_system.states import SystemState
from agents.prompts.code_gen_prompt import code_gen_prompt
from config.configs import llm_gemini_flash

AGENT_CODE_GENERATOR_LLM = llm_gemini_flash

def code_generator_agent(state: SystemState) -> dict:
    code_gen_agent_briefing = state['code_gen_agent_briefing']
    metadata = state.get("metadata")
    
    # Check if this is a retry due to an error
    execution_error = state.get("execution_error")
    previous_code = state.get("code", "")
    retry_count = state.get("retry_count", 0)
    
    # Build the prompt
    base_prompt = code_gen_prompt.format(
        code_gen_agent_briefing=code_gen_agent_briefing,
        metadata=metadata
    )
    
    # If there's an error, add context about the previous failure
    if execution_error and previous_code:
        error_context = f"""
        
        ----------------- IMPORTANT: CODE EXECUTION ERROR -----------------
        The previous code execution failed with the following error:
        
        Error: {execution_error}
        
        Previous code that failed:
        ```python
        {previous_code}
        ```
        
        Please analyze the error and generate a corrected version of the code that:
        1. Fixes the specific error mentioned above
        2. Maintains the same functionality as intended
        3. Follows all the rules and requirements specified
        4. Includes error handling if appropriate
        
        Common issues to check:
        - Column names: Ensure all column names exist in the DataFrames
        - Data types: Check for type mismatches and handle them appropriately
        - Empty DataFrames: Handle cases where DataFrames might be empty
        - Index errors: Ensure indices exist before accessing them
        - Missing values: Handle NaN/None values appropriately
        
        This is retry attempt {retry_count}. Please generate the corrected code below:
        """
        
        prompt = base_prompt + error_context
        print(f"\n🔄 [Code Generator - Retry {retry_count}] Attempting to fix error...")
    else:
        prompt = base_prompt
        print("\n🧠 [Code Generator] Generating initial code...")
    

    msg = AGENT_CODE_GENERATOR_LLM.invoke([HumanMessage(content=prompt)])
    print("\n🧠 [Generated Code]:\n", msg.content[:500] + "..." if len(msg.content) > 500 else msg.content)

    code_content = msg.content
    if "```python" in code_content and "```" in code_content.split("```python", 1)[1]:
        code_only = code_content.split("```python", 1)[1].split("```", 1)[0].strip()
    else:
        code_only = code_content
    
    # Store message internally, don't show to user
    internal_messages = state.get("internal_messages", [])
    internal_messages.append(msg)

    return {
        **state,
        "messages": state["messages"],
        "internal_messages": internal_messages,
        "code": code_only,
        "execution_error": None  # Clear the error for the new attempt
    }