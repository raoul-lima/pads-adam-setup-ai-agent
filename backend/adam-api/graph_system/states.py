from typing_extensions import TypedDict
from typing import Annotated, Optional, Union, List, Dict, Any
from langgraph.graph.message import add_messages


class SystemState(TypedDict):
    messages: Annotated[list, add_messages]
    internal_messages: list
    intent_category: Optional[str]
    intent_summary: Optional[str]
    cleared_intent: Optional[bool]
    code_gen_agent_briefing: Optional[str]
    code_gen_agent_breafing_ready: Optional[bool]
    code: Optional[str]
    result: Optional[Union[str, dict]]
    metadata: Optional[dict]
    debug_info: Optional[dict]
    final_response_ready: Optional[bool]
    user_language: Optional[str]
    result_query: Optional[str]
    user_id: Optional[str]
    advertiser_id: Optional[str]
    partner_name: Optional[str]
    partner_name: Optional[str]

    instruction_block: Optional[str]
    in_analysis: Optional[bool]
    in_dsp: Optional[bool]
    in_anomaly_det_run: Optional[bool]
    long_term_memory: Optional[dict]
    chat_history: Optional[List[Dict[str, str]]]
    
    # New fields for enhanced result processing
    processed_result: Optional[Dict[str, Any]]
    download_links: Optional[List[Dict[str, str]]]
    
    # Error handling and retry fields
    execution_error: Optional[str]
    retry_count: Optional[int]
    max_retries: Optional[int]
    anomaly_detection_completed: Optional[bool]
    
    # Advertiser context cache (session-based)
    advertiser_list: Optional[List[Dict[str, str]]]
    advertiser_list_fetched_at: Optional[str]


    