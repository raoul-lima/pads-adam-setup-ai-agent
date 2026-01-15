from typing import Dict, Any
import json
from datetime import datetime, timedelta
import logging

from graph_system.states import SystemState
from agents.prompts.clarify_intent_prompt import clarify_intent_prompt
from config.configs import llm_gemini_flash
from langchain_core.runnables import RunnableConfig
from utils.advertiser_cache import AdvertiserCache

logger = logging.getLogger(__name__)

async def classify_intent_agent(state: SystemState, config: RunnableConfig) -> Dict[str, Any]:
    configurable = config.get("configurable", {})
    user_email = configurable.get("user_email", "")
    partner_name = configurable.get("partner_name", "")

    last_user_msg = state["messages"][-1].content.strip()
    chat_history = state.get("chat_history", [])
    long_term_memory = state.get("long_term_memory", {})
    
    # Add dynamic temporal context
    current_datetime = datetime.now()
    snapshot_date = (current_datetime - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Load advertiser list with session + partner-specific cache
    advertiser_list = state.get("advertiser_list")
    if advertiser_list is None:
        logger.info(f"Fetching advertiser list for partner '{partner_name}' (first time in session)")
        try:
            advertiser_list = await AdvertiserCache.get_advertisers(user_email, partner_name)
            state["advertiser_list"] = advertiser_list
            state["advertiser_list_fetched_at"] = current_datetime.isoformat()
            logger.info(f"Advertiser list cached in session for partner '{partner_name}': {len(advertiser_list)} advertisers")
        except Exception as e:
            logger.error(f"Failed to fetch advertiser list: {e}")
            advertiser_list = []
    else:
        logger.debug(f"Using session-cached advertiser list: {len(advertiser_list)} advertisers")
    
    # Format advertiser context for prompt (limit to top 50 to save tokens)
    if advertiser_list:
        advertiser_names = [adv["advertiser_name"] for adv in advertiser_list[:50]]
        advertiser_context = f"Available advertisers ({len(advertiser_list)} total, showing top 50):\n" + \
                           "\n".join(f"- {name}" for name in advertiser_names)
    else:
        advertiser_context = "No advertiser data available."
    
    # Get previous code context for better follow-up understanding
    previous_code = state.get("code", "")
    previous_briefing = state.get("code_gen_agent_briefing", "")
    
    # Format code context (truncate if too long to save tokens)
    if previous_code:
        # Extract key information from the code (e.g., what dataframes/filters were used)
        code_preview = previous_code[:800] + "..." if len(previous_code) > 800 else previous_code
        code_context = f"```python\n{code_preview}\n```"
    else:
        code_context = "No previous analysis in this session."
    
    chain = clarify_intent_prompt | llm_gemini_flash
    response = chain.invoke(
        {
            "user_email": user_email,
            "partner_name": partner_name,
            "messages": last_user_msg,
            "chat_history": chat_history,
            "long_term_memory": long_term_memory,
            "current_datetime": current_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "snapshot_date": snapshot_date,
            "advertiser_context": advertiser_context,
            "previous_code_context": code_context
        }
    )
    raw_content = response.content

    try:
        if "```json" in raw_content:
            json_only = raw_content.split("```json", 1)[1].split("```", 1)[0].strip()
        else:
            json_only = raw_content.strip()
        parsed = json.loads(json_only)
        intent_category = parsed.get("intent_category", None)
        intent_summary = parsed.get("intent_summary", None)

        if intent_category in {"targeting_check", "budget_check", "quality_check", "other_check", "dsp_support", "anomaly_det_run"}:
            new_state = {
                **state,
                "intent_category": intent_category,
                "intent_summary": intent_summary,
                "cleared_intent": True
            }
        else:
            new_state = {
                **state,
                "messages": state["messages"] + [response],
                "intent_category": None,
                "intent_summary": None,
                "cleared_intent": False
            }

    except json.JSONDecodeError:
        new_state = {
            **state,
            "messages": state["messages"] + [response],
            "intent_category": None,
            "intent_summary": None,
            "cleared_intent": False
        }
    return new_state
