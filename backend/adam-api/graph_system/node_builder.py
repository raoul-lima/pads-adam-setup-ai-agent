from langgraph.graph import StateGraph

from .states import SystemState
from agents.analyser_agent import agent_analyser
from agents.dsp_agent import dsp_agent_with_state
from agents.code_generator_agent import code_generator_agent
from agents.classifier_intent_agent import classify_intent_agent
from agents.final_response_agent import final_response_agent
from graph_system.nodes.result_captor import capture_result
from graph_system.nodes.exec_code_node import exec_code_node
from graph_system.nodes.summary_result import summarize_result_node
from graph_system.nodes.retriever_instruction import retrieve_instruction
from agents.memory_agent import memory_agent
import logging

logger = logging.getLogger(__name__)

from agents.anomaly_det_runner_agent import anomaly_det_runner_agent
logger.info("Using standard LLM-based anomaly detection agent (v2)")

def entry_router(state: SystemState) -> dict:
    """Simply returns the current state - routing is handled in the graph edges"""
    return state

def node_builder():

    node_builder = StateGraph(SystemState)

    node_builder.add_node("memory_agent", memory_agent)
    node_builder.add_node("entry_router", entry_router)
    node_builder.add_node("dsp_agent", dsp_agent_with_state)
    node_builder.add_node("agent_analyser", agent_analyser)
    node_builder.add_node("code_generator", code_generator_agent)
    node_builder.add_node("exec_code", exec_code_node)
    node_builder.add_node("final_response", final_response_agent)
    node_builder.add_node("capture_result", capture_result)
    node_builder.add_node("summarize_result", summarize_result_node)

    node_builder.add_node("retrieve_instruction", retrieve_instruction)
    node_builder.add_node("classify_intent", classify_intent_agent)
    node_builder.add_node("anomaly_det_runner_agent", anomaly_det_runner_agent)

    return node_builder