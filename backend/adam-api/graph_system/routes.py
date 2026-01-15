from langgraph.graph import END
from .states import SystemState


def route_after_analyser(state: SystemState):
    if state.get("code_gen_agent_breafing_ready") is True:
        # Analysis complete, move to code generation
        return "code_generator"
    elif state.get("code_gen_agent_breafing_ready") is False:
        # Still in analysis, stay in the analyser node
        return END  # Return to user for more input, then next turn will go to analyser again
    return END

def route_after_anomaly_det_run(state: SystemState):
    if state.get("anomaly_detection_completed") is True:
        # Analysis complete, move to code generation
        return "capture_result"
    elif state.get("anomaly_detection_completed") is False:
        # Still in analysis, stay in the analyser node
        return END  # Return to user for more input, then next turn will go to anomaly detection again
    return END

def route_theme_known(state: SystemState):
    if state.get("cleared_intent") is True:
        return "retrieve_instruction"
    elif state.get("cleared_intent") is False:
        return END

def route_after_exec_code(state: SystemState):
    """Route after code execution to handle errors and retries"""
    execution_error = state.get("execution_error")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)  # Default to 2 retries
    
    if execution_error and retry_count < max_retries:
        # There's an error and we haven't exceeded max retries
        print(f"🔄 Retrying code generation (attempt {retry_count}/{max_retries})")
        return "code_generator"
    else:
        # No error or max retries reached, continue to capture result
        if execution_error:
            print(f"⚠️ Max retries ({max_retries}) reached. Proceeding with error result.")
        return "capture_result"


        