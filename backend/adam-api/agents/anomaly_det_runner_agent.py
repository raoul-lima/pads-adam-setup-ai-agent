"""
Enhanced Anomaly Detection Runner Agent with Granular Check Selection
This version supports selective anomaly detection at check-level granularity.
"""

import re
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from typing import Dict, Any, Optional, List
import pandas as pd
import json
import logging

from graph_system.states import SystemState
from config.configs import llm_gemini_flash
from agents.language_detecter import detect_user_language
from utils.data_loader import load_data
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

AGENT_ANOMALY_DET_RUNNER_LLM = llm_gemini_flash

# Import the actual anomaly detection functions
from agents.tools.campaign_anomaly_detector_tool import (
    detect_campaign_anomalies as detect_campaign_anomalies_func,
    check_campaign_goal,
    check_kpi_configuration,
    check_frequency_capping
)
from agents.tools.li_anomaly_detector_tool import (
    detect_li_anomalies as detect_li_anomalies_func,
    check_li_safeguards,
    check_li_inventory_consistency,
    check_li_markup_consistency,
    check_li_naming_convention_batch,
    check_li_naming_vs_setup_batch
)
from agents.tools.io_anomaly_detector_tool import (
    detect_io_anomalies as detect_io_anomalies_func,
    check_naming_vs_kpi,
    check_kpi_vs_objective,
    check_kpi_vs_optimization,
    check_cpm_capping
)

from agents.prompts.anomaly_detection_prompt import anomaly_detection_prompt


# Global variables to store dataframes for tool access
_campaigns_df = None
_line_items_df = None
_insertion_orders_df = None


# Available check types for each entity
LINE_ITEM_CHECK_TYPES = {
    "safeguards": "Check for missing brand safety, environment targeting, viewability settings, etc.",
    "inventory": "Check for inventory consistency and exchange configuration",
    "markup": "Check markup consistency across line items",
    "naming": "Check naming convention format compliance",
    "naming_setup": "Check if naming convention matches actual setup/configuration"
}

INSERTION_ORDER_CHECK_TYPES = {
    "naming_kpi": "Check if naming-derived objective matches configured KPI",
    "kpi_objective": "Check if KPI aligns with insertion order objective",
    "kpi_optimization": "Check if KPI is consistent with optimization settings",
    "cpm_capping": "Check for excessive CPM cap settings",
    "naming": "Check naming convention compliance"
}

CAMPAIGN_CHECK_TYPES = {
    "goal": "Check if campaign goal is properly configured",
    "kpi": "Check if KPI configuration is correct",
    "frequency": "Check if frequency capping is properly set"
}


@tool
def detect_campaign_anomalies(
    check_types: Optional[List[str]] = None
) -> str:
    """
    Detect anomalies in campaign configurations with optional selective checking.
    
    Args:
        check_types: Optional list of specific checks to run. Available options:
            - "goal": Check campaign goal configuration
            - "kpi": Check KPI configuration  
            - "frequency": Check frequency capping
            If not provided or empty, all checks will run.
    
    Returns:
        JSON string with detected campaign anomalies
    """
    global _campaigns_df, _insertion_orders_df, _line_items_df
    if _campaigns_df is None:
        return json.dumps({"error": "Campaign data not loaded"})
    
    try:
        # If no specific checks requested, run all
        if not check_types or len(check_types) == 0:
            check_types = list(CAMPAIGN_CHECK_TYPES.keys())
        
        # Map check types to functions
        check_function_map = {
            "goal": check_campaign_goal,
            "kpi": check_kpi_configuration,
            "frequency": check_frequency_capping
        }
        
        # Filter to only requested checks
        check_functions = [
            check_function_map[check_type] 
            for check_type in check_types 
            if check_type in check_function_map
        ]
        
        # Run selective anomaly detection
        result = run_selective_campaign_detection(
            _campaigns_df, 
            _insertion_orders_df, 
            _line_items_df,
            check_functions
        )
        
        # Check if result is empty
        if result.empty:
            return json.dumps({
                "status": "success",
                "message": f"No campaign anomalies detected for checks: {', '.join(check_types)}",
                "checks_run": check_types,
                "count": 0
            })
        
        # Select relevant columns for display
        result = result[["Name", "Campaign Id", "dv360_link", "anomalies_description"]]
        
        # Convert to JSON for return
        return json.dumps({
            "status": "success",
            "checks_run": check_types,
            "count": len(result),
            "anomalies": result.to_dict('records')
        })
    except Exception as e:
        logger.error(f"Error detecting campaign anomalies: {str(e)}", exc_info=True)
        return json.dumps({"error": f"Error detecting campaign anomalies: {str(e)}"})


@tool
def detect_line_item_anomalies(
    check_types: Optional[List[str]] = None,
    naming_convention: Optional[str] = None,
    expected_markup: Optional[float] = None
) -> str:
    """
    Detect anomalies in line items with optional selective checking.
    
    Args:
        check_types: Optional list of specific checks to run. Available options:
            - "safeguards": Check for missing brand safety and targeting safeguards
            - "inventory": Check inventory consistency
            - "markup": Check markup consistency (requires expected_markup parameter)
            - "naming": Check naming convention format compliance (uses naming_convention parameter)
            - "naming_setup": Check if naming matches actual setup/configuration (validates name vs actual targeting)
            If not provided or empty, all applicable checks will run.
        naming_convention: Optional custom naming convention (e.g., 'Country - Device - Targeting')
        expected_markup: Optional expected markup percentage for consistency check
    
    Returns:
        JSON string with detected line item anomalies
    """
    global _campaigns_df, _line_items_df, _insertion_orders_df
    if _line_items_df is None:
        return json.dumps({"error": "Line items data not loaded"})
    
    try:
        # Determine which checks to run
        if not check_types or len(check_types) == 0:
            # If no check_types specified, run all applicable checks
            check_types = ["safeguards", "inventory", "naming_setup"]
            if expected_markup is not None:
                check_types.append("markup")
            if naming_convention is not None:
                check_types.append("naming")
        
        # Run selective anomaly detection
        result = run_selective_li_detection(
            _line_items_df,
            _campaigns_df,
            _insertion_orders_df,
            check_types=check_types,
            naming_convention=naming_convention,
            expected_markup=expected_markup
        )
        
        # Check if result is empty
        if result.empty:
            return json.dumps({
                "status": "success",
                "message": f"No line item anomalies detected for checks: {', '.join(check_types)}",
                "checks_run": check_types,
                "count": 0
            })
        
        # Select relevant columns for display
        result = result[["Name", "Line Item Id", "dv360_link", "anomalies_description"]]
        
        # Convert to JSON for return
        return json.dumps({
            "status": "success",
            "checks_run": check_types,
            "count": len(result),
            "anomalies": result.head(50).to_dict('records')  # Limit to 50 for response size
        })
    except Exception as e:
        logger.error(f"Error detecting line item anomalies: {str(e)}", exc_info=True)
        return json.dumps({"error": f"Error detecting line item anomalies: {str(e)}"})


@tool
def detect_insertion_order_anomalies(
    check_types: Optional[List[str]] = None,
    naming_convention: Optional[str] = None,
    default_cpm_cap: Optional[float] = 5.0
) -> str:
    """
    Detect anomalies in insertion orders with optional selective checking.
    
    Args:
        check_types: Optional list of specific checks to run. Available options:
            - "naming_kpi": Check naming vs KPI alignment
            - "kpi_objective": Check KPI vs objective consistency
            - "kpi_optimization": Check KPI vs optimization alignment
            - "cpm_capping": Check CPM cap settings (uses default_cpm_cap parameter)
            - "naming": Check naming convention compliance (uses naming_convention parameter)
            If not provided or empty, all applicable checks will run.
        naming_convention: Optional custom naming convention
        default_cpm_cap: Default CPM cap value to check against (default: $5.0)
    
    Returns:
        JSON string with detected insertion order anomalies
    """
    global _campaigns_df, _line_items_df, _insertion_orders_df
    if _insertion_orders_df is None:
        return json.dumps({"error": "Insertion orders data not loaded"})
    
    try:
        # Determine which checks to run
        if not check_types or len(check_types) == 0:
            # If no check_types specified, run all checks
            check_types = ["naming_kpi", "kpi_objective", "kpi_optimization", "cpm_capping"]
            if naming_convention is not None:
                check_types.append("naming")
        
        # Run selective anomaly detection
        result = run_selective_io_detection(
            _insertion_orders_df,
            _campaigns_df,
            _line_items_df,
            check_types=check_types,
            naming_convention=naming_convention,
            default_cpm_cap=default_cpm_cap
        )
        
        # Check if result is empty
        if result.empty:
            return json.dumps({
                "status": "success",
                "message": f"No insertion order anomalies detected for checks: {', '.join(check_types)}",
                "checks_run": check_types,
                "count": 0
            })
        
        # Select relevant columns for display
        result = result[["Name", "Io Id", "dv360_link", "anomalies_description"]]
        
        # Convert to JSON for return
        return json.dumps({
            "status": "success",
            "checks_run": check_types,
            "count": len(result),
            "anomalies": result.to_dict('records')
        })
    except Exception as e:
        logger.error(f"Error detecting insertion order anomalies: {str(e)}", exc_info=True)
        return json.dumps({"error": f"Error detecting insertion order anomalies: {str(e)}"})


def run_selective_campaign_detection(
    campaigns_df: pd.DataFrame,
    insertion_orders_df: pd.DataFrame,
    line_items_df: pd.DataFrame,
    check_functions: List
) -> pd.DataFrame:
    """Run only selected campaign checks"""
    df = campaigns_df.copy()
    
    is_abnormal_list = []
    anomalies_descriptions = []
    
    for idx, row in df.iterrows():
        row_anomalies = []
        row_is_abnormal = False
        
        for check_func in check_functions:
            try:
                is_abnormal, description = check_func(row, insertion_orders_df, line_items_df)
                if is_abnormal:
                    row_is_abnormal = True
                    row_anomalies.append(description)
            except Exception as e:
                logger.error(f"Error in {check_func.__name__} for row {idx}: {str(e)}")
                continue
        
        is_abnormal_list.append(row_is_abnormal)
        anomalies_str = '; '.join(row_anomalies) if row_anomalies else ''
        anomalies_descriptions.append(anomalies_str)
    
    df['is_abnormal'] = is_abnormal_list
    df['anomalies_description'] = anomalies_descriptions
    
    abnormal_campaigns = df[df['is_abnormal']].copy()
    abnormal_campaigns = abnormal_campaigns.drop('is_abnormal', axis=1)
    
    return abnormal_campaigns


def run_selective_li_detection(
    line_items_df: pd.DataFrame,
    campaigns_df: pd.DataFrame,
    insertion_orders_df: pd.DataFrame,
    check_types: List[str],
    naming_convention: Optional[str] = None,
    expected_markup: Optional[float] = None
) -> pd.DataFrame:
    """Run only selected line item checks"""
    df = line_items_df.copy()
    
    # Build check functions list based on requested types
    check_functions = []
    if "safeguards" in check_types:
        check_functions.append(check_li_safeguards)
    if "inventory" in check_types:
        check_functions.append(check_li_inventory_consistency)
    if "markup" in check_types and expected_markup is not None:
        check_functions.append(
            lambda li, campaigns, ios: check_li_markup_consistency(li, campaigns, ios, expected_markup)
        )
    
    # Handle naming convention check separately (batch operation)
    naming_anomalies = {}
    if "naming" in check_types and naming_convention is not None:
        try:
            naming_anomalies = check_li_naming_convention_batch(df, naming_convention)
        except Exception as e:
            logger.error(f"Error in naming convention check: {str(e)}")
            naming_anomalies = {}
    
    # Handle naming vs setup compliance check separately (batch operation)
    naming_setup_anomalies = {}
    if "naming_setup" in check_types:
        try:
            naming_setup_anomalies = check_li_naming_vs_setup_batch(df, naming_convention or "Country/Language - Targeting/Publisher - Device (Opt)")
        except Exception as e:
            logger.error(f"Error in naming vs setup compliance check: {str(e)}")
            naming_setup_anomalies = {}
    
    # Apply checks
    is_abnormal_list = []
    anomalies_descriptions = []
    
    for idx, row in df.iterrows():
        row_anomalies = []
        row_is_abnormal = False
        
        for check_func in check_functions:
            try:
                is_abnormal, description = check_func(row, campaigns_df, insertion_orders_df)
                if is_abnormal:
                    row_is_abnormal = True
                    row_anomalies.append(description)
            except Exception as e:
                logger.error(f"Error in check function for row {idx}: {str(e)}")
                continue
        
        # Add naming convention anomalies if present
        li_name = row.get('Name', '')
        if li_name in naming_anomalies:
            row_is_abnormal = True
            row_anomalies.append(naming_anomalies[li_name])
        
        # Add naming vs setup compliance anomalies if present
        if li_name in naming_setup_anomalies:
            row_is_abnormal = True
            row_anomalies.append(naming_setup_anomalies[li_name])
        
        is_abnormal_list.append(row_is_abnormal)
        anomalies_str = '; '.join(row_anomalies) if row_anomalies else ''
        anomalies_descriptions.append(anomalies_str)
    
    df['is_abnormal'] = is_abnormal_list
    df['anomalies_description'] = anomalies_descriptions
    
    abnormal_lis = df[df['is_abnormal']].copy()
    abnormal_lis = abnormal_lis.drop('is_abnormal', axis=1)
    
    return abnormal_lis


def run_selective_io_detection(
    insertion_orders_df: pd.DataFrame,
    campaigns_df: pd.DataFrame,
    line_items_df: pd.DataFrame,
    check_types: List[str],
    naming_convention: Optional[str] = None,
    default_cpm_cap: float = 5.0
) -> pd.DataFrame:
    """Run only selected insertion order checks"""
    df = insertion_orders_df.copy()
    
    # Build check functions list based on requested types
    check_functions = []
    if "naming_kpi" in check_types:
        check_functions.append(check_naming_vs_kpi)
    if "kpi_objective" in check_types:
        check_functions.append(check_kpi_vs_objective)
    if "kpi_optimization" in check_types:
        check_functions.append(check_kpi_vs_optimization)
    if "cpm_capping" in check_types:
        check_functions.append(
            lambda io, campaigns, lis: check_cpm_capping(io, campaigns, lis, default_cpm_cap)
        )
    
    # Handle naming convention check separately (would be batch operation if implemented)
    naming_anomalies = {}
    # Note: IO naming convention batch check is currently commented out in original code
    
    # Apply checks
    is_abnormal_list = []
    anomalies_descriptions = []
    
    for idx, row in df.iterrows():
        row_anomalies = []
        row_is_abnormal = False
        
        for check_func in check_functions:
            try:
                is_abnormal, description = check_func(row, campaigns_df, line_items_df)
                if is_abnormal:
                    row_is_abnormal = True
                    row_anomalies.append(description)
            except Exception as e:
                logger.error(f"Error in check function for row {idx}: {str(e)}")
                continue
        
        # Add naming convention anomalies if present
        io_name = row.get('Name', '')
        if io_name in naming_anomalies:
            row_is_abnormal = True
            row_anomalies.append(naming_anomalies[io_name])
        
        is_abnormal_list.append(row_is_abnormal)
        anomalies_str = '; '.join(row_anomalies) if row_anomalies else ''
        anomalies_descriptions.append(anomalies_str)
    
    df['is_abnormal'] = is_abnormal_list
    df['anomalies_description'] = anomalies_descriptions
    
    abnormal_ios = df[df['is_abnormal']].copy()
    abnormal_ios = abnormal_ios.drop('is_abnormal', axis=1)
    
    return abnormal_ios


def anomaly_det_runner_agent(state: SystemState, config: RunnableConfig) -> dict:
    """Run the anomaly detection tools based on the user's request with granular check selection"""
    global _campaigns_df, _line_items_df, _insertion_orders_df
    
    # Get properly formatted conversation history
    chat_history = state.get("chat_history", [])
    long_term_memory = state.get("long_term_memory", {})
    
    # Extract current message and detect language
    messages = state["messages"]
    user_msg_text = messages[-1].content
    user_language = detect_user_language(user_msg_text)
    
    # Load data
    user_email = config["configurable"]["user_email"]
    partner_name = config["configurable"]["partner_name"]
    _line_items_df, _campaigns_df, _insertion_orders_df = load_data(user_email, partner_name)
    
    # Bind tools to the LLM
    tools = [
        detect_campaign_anomalies,
        detect_line_item_anomalies,
        detect_insertion_order_anomalies
    ]
    llm_with_tools = AGENT_ANOMALY_DET_RUNNER_LLM.bind_tools(tools)
    
    # Create prompt with history
    prompt_anomaly = anomaly_detection_prompt.format_messages(
        messages=messages,
        chat_history=chat_history,
        long_term_memory=long_term_memory,
        user_language=user_language,
        intent_summary=state.get("intent_summary", "Detect anomalies in the advertising data"),
        user_email=user_email,
        partner_name=partner_name
    )
    
    # Get response with tool calling
    ai_msg = llm_with_tools.invoke(prompt_anomaly)
    
    internal_messages = state.get("internal_messages", [])
    internal_messages.append(ai_msg)

    results = {}
    
    # Process the response based on tool calls
    if ai_msg.tool_calls:
        # Process tool calls and collect results
        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            
            # Execute the tool and get result
            if tool_name == "detect_campaign_anomalies":
                logger.info(f"Running campaign anomaly detection with args: {tool_args}")
                result_json = detect_campaign_anomalies.invoke(tool_args)
                result_data = json.loads(result_json)
                if result_data.get("status") == "success" and result_data.get("count", 0) > 0:
                    anomalies_df = pd.DataFrame(result_data["anomalies"])
                    results["Campaign anomalies"] = anomalies_df
                    
            elif tool_name == "detect_line_item_anomalies":
                logger.info(f"Running line item anomaly detection with args: {tool_args}")
                result_json = detect_line_item_anomalies.invoke(tool_args)
                result_data = json.loads(result_json)
                if result_data.get("status") == "success" and result_data.get("count", 0) > 0:
                    anomalies_df = pd.DataFrame(result_data["anomalies"])
                    results["Line items anomalies"] = anomalies_df
                    
            elif tool_name == "detect_insertion_order_anomalies":
                logger.info(f"Running insertion order anomaly detection with args: {tool_args}")
                result_json = detect_insertion_order_anomalies.invoke(tool_args)
                result_data = json.loads(result_json)
                if result_data.get("status") == "success" and result_data.get("count", 0) > 0:
                    anomalies_df = pd.DataFrame(result_data["anomalies"])
                    results["Insertion orders anomalies"] = anomalies_df
        
        # Create a summary message
        summary_parts = []
        if results:
            summary_parts.append("Anomaly detection completed. Found issues in:")
            for key, df in results.items():
                summary_parts.append(f"- {key}: {len(df)} anomalies detected")
        else:
            summary_parts.append("Anomaly detection completed. No anomalies detected.")
        
        summary_message = "\n".join(summary_parts)
        
        # If no results, return empty dict instead of dict with string message
        # This ensures compatibility with downstream nodes expecting DataFrames
        new_state = {
            **state,
            "result": results if results else {},
            "code_gen_agent_briefing": summary_message,
            "user_language": user_language,
            "internal_messages": internal_messages,
            "anomaly_detection_completed": True
        }
    else: # No tool calls
        new_state = {
            **state,
            "messages": messages + [ai_msg],
            "internal_messages": internal_messages,
            "user_language": user_language,
            "anomaly_detection_completed": False
        }
    
    # Clean up global variables
    _campaigns_df = None
    _line_items_df = None
    _insertion_orders_df = None
    
    return new_state

