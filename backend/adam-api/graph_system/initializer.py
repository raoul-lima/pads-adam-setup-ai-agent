from langgraph.graph import START, END
from .routes import route_after_analyser, route_theme_known, route_after_exec_code, route_after_anomaly_det_run
from .node_builder import node_builder


def graph_init():
    """Initialize a graph with user-specific checkpointing"""    

    graph_builder = node_builder()

    graph_builder.add_edge(START, "memory_agent")
    graph_builder.add_edge("memory_agent", "entry_router")
  
    graph_builder.add_conditional_edges(
        "entry_router",
        lambda state: "agent_analyser" if state.get("in_analysis", False) else "classify_intent"
    )

    graph_builder.add_conditional_edges("classify_intent", route_theme_known)

    graph_builder.add_conditional_edges(
        "retrieve_instruction",
        lambda state: "anomaly_det_runner_agent" if state.get("in_anomaly_det_run", False) else "dsp_agent" if state.get("in_dsp", False) else "agent_analyser"
    )
    graph_builder.add_conditional_edges("anomaly_det_runner_agent", route_after_anomaly_det_run)
    graph_builder.add_edge("dsp_agent", END)
    graph_builder.add_conditional_edges("agent_analyser", route_after_analyser)

    graph_builder.add_edge("code_generator", "exec_code")
    graph_builder.add_conditional_edges("exec_code", route_after_exec_code)
    graph_builder.add_edge("capture_result", "summarize_result")
    graph_builder.add_edge("summarize_result", "final_response")
    graph_builder.add_edge("final_response", END)

    graph = graph_builder.compile()

    return graph
