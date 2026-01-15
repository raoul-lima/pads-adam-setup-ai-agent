from langchain_core.messages import AIMessage
from graph_system.states import SystemState
from agents.tools.exec_code_tool import exec_code_tool
from langchain_core.runnables import RunnableConfig
import pandas as pd

def exec_code_node(state: SystemState, config: RunnableConfig) -> dict:
    code = state.get("code", "")
    if not code:
        return {
            **state,
            "messages": state["messages"],
            "internal_messages": state.get("internal_messages", []) + [AIMessage(content="No code generated.")],
            "execution_error": "No code generated"
        }
    
    result = exec_code_tool(code, config)
    
    # Check if the result is an error DataFrame
    execution_error = None
    if isinstance(result, pd.DataFrame) and 'error' in result.columns:
        # This is an error result
        error_msg = result['error'].iloc[0] if len(result) > 0 else "Unknown error"
        execution_error = error_msg
        print(f"🔄 [Execution Error Detected]: {error_msg[:200]}...")
    
    result_msg = AIMessage(content=f"Code execution result:\n\n{result}")
    internal_messages = state.get("internal_messages", [])
    internal_messages.append(result_msg)
    
    # Increment retry count if there's an error
    retry_count = state.get("retry_count", 0)
    if execution_error:
        retry_count += 1
    
    return {
        **state,
        "messages": state["messages"],
        "internal_messages": internal_messages,
        "result": result,
        "execution_error": execution_error,
        "retry_count": retry_count
    }