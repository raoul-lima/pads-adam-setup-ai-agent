# ADAM Agent - Developer Onboarding Guide

Welcome to the ADAM (Advertising Data Analysis & Management) Agent project! This guide will help you understand the codebase and start contributing.

## 🎯 Project Overview

**ADAM** is an AI-powered agent that helps analyze and manage advertising campaigns on platforms like DV360 (Display & Video 360). It can:
- Answer questions about campaign performance
- Detect anomalies in campaign setups
- Analyze budget pacing and spending
- Generate reports and recommendations
- Handle multi-lingual queries (English, French, Spanish, Dutch, Polish)

**Tech Stack:**
- **Backend**: Python, FastAPI, LangGraph, LangChain
- **Frontend**: Next.js, React, TypeScript
- **AI Models**: Google Gemini, OpenAI (for evaluations)
- **Data Storage**: PostgreSQL (conversation memory), Google Cloud Storage
- **APIs**: Google Sheets, BigQuery, DV360 API

---

## 🧠 Understanding LangGraph (10-Minute Primer)

### What is LangGraph?

**LangGraph** is a framework for building **stateful, multi-step AI agents**. Think of it as a workflow engine specifically designed for LLM-based applications.

### Key Concepts

#### 1. **Graph = Workflow**
A LangGraph graph is like a flowchart where each node is a step in your AI workflow.

```python
# Simple example
from langgraph.graph import StateGraph, START, END

graph = StateGraph(State)
graph.add_node("step1", step1_function)
graph.add_node("step2", step2_function)
graph.add_edge(START, "step1")
graph.add_edge("step1", "step2")
graph.add_edge("step2", END)
```

#### 2. **State = Shared Data**
State is a dictionary-like object that flows through your graph. Each node can read and update it.

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]  # Conversation history
    user_query: str                          # Current query
    analysis_result: dict                    # Analysis data
```

**Key Point**: `Annotated[list, add_messages]` is special - it **appends** new messages instead of replacing them.

#### 3. **Nodes = Functions**
Each node is a Python function that takes state as input and returns updated state.

```python
def my_node(state: State) -> State:
    # Do something with state
    user_query = state["user_query"]
    result = analyze(user_query)
    
    # Return updates (only what changed)
    return {
        "analysis_result": result,
        "messages": [AIMessage(content="Analysis complete!")]
    }
```

#### 4. **Edges = Flow Control**

**Simple Edge** (always goes to next node):
```python
graph.add_edge("node1", "node2")  # Always go from node1 to node2
```

**Conditional Edge** (decides where to go based on state):
```python
def router(state: State) -> str:
    if state["needs_analysis"]:
        return "analyze_node"
    else:
        return "response_node"

graph.add_conditional_edges("classify_node", router)
```

#### 5. **Checkpointing = Memory**
LangGraph can save state at each step, enabling:
- **Conversation history** (remember previous messages)
- **Human-in-the-loop** (pause for user input)
- **Error recovery** (resume from where you left off)

```python
# Enable checkpointing
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

# Use with a thread_id to maintain conversation
config = {"configurable": {"thread_id": "user_123"}}
result = graph.invoke({"messages": [user_message]}, config=config)
```

### LangGraph vs Traditional Code

**Traditional:**
```python
# Linear flow
def process_query(query):
    intent = classify_intent(query)
    if intent == "analysis":
        data = fetch_data(query)
        result = analyze_data(data)
    else:
        result = handle_other(query)
    return result
```

**LangGraph:**
```python
# Graph flow with state management
graph.add_node("classify", classify_intent)
graph.add_node("fetch_data", fetch_data)
graph.add_node("analyze", analyze_data)
graph.add_conditional_edges("classify", route_by_intent)

# Benefits:
# - State is managed automatically
# - Can pause/resume anywhere
# - Can visualize the flow
# - Can inspect state at each step
```

---

## 🏗️ ADAM Architecture

### High-Level Flow

```
User Query
    ↓
[Memory Agent] ← Loads conversation history
    ↓
[Entry Router] ← Determines if analysis or normal flow
    ↓
[Classify Intent] ← What does user want? (anomaly detection, DSP query, analysis)
    ↓
[Router] ← Conditional routing based on intent
    ↓
├─→ [DSP Agent] ← Handles Adsecura platform queries
├─→ [Anomaly Detector] ← Checks for campaign anomalies
└─→ [Analyser Agent] ← General analysis
        ↓
    [Code Generator] ← Generates Python code for data analysis
        ↓
    [Exec Code] ← Safely executes code
        ↓
    [Capture Result] ← Processes execution results
        ↓
    [Summarize] ← Creates summary
        ↓
    [Final Response] ← Generates user-facing response
        ↓
    END
```

### Directory Structure

```
testing-adam/
├── backend/
│   ├── agents/                  # AI agents (nodes in graph)
│   │   ├── memory_agent.py      # Conversation memory
│   │   ├── classifier_intent_agent.py
│   │   ├── analyser_agent.py
│   │   ├── code_generator_agent.py
│   │   ├── dsp_agent.py
│   │   ├── anomaly_det_runner_agent.py
│   │   ├── final_response_agent.py
│   │   ├── prompts/             # Agent prompts
│   │   └── tools/               # Agent tools (anomaly detection, etc.)
│   │
│   ├── graph_system/            # LangGraph structure
│   │   ├── initializer.py       # Graph setup (MOST IMPORTANT)
│   │   ├── node_builder.py      # Adds nodes to graph
│   │   ├── routes.py            # Conditional routing logic
│   │   ├── states.py            # State definition
│   │   └── nodes/               # Node implementations
│   │
│   ├── config/
│   │   └── configs.py           # LLM configs, metadata loading
│   │
│   ├── utils/
│   │   ├── constants.py         # Environment variables
│   │   ├── gcs_uploader.py      # Google Cloud Storage
│   │   └── postgres_storage.py  # Database for memory
│   │
│   ├── data/
│   │   ├── general_metadata.json  # Field metadata for campaigns
│   │   └── bm25/                  # Search indices
│   │
│   ├── main.py                  # FastAPI server (entry point)
│   └── evaluate_adam.py         # Evaluation system
│
├── frontend/                    # User chat interface
│   └── src/
│       ├── app/
│       ├── components/
│       └── services/
│
└── admin_app/                   # Admin dashboard
    └── src/
        ├── app/
        │   ├── dashboard/       # Feedback viewing
        │   └── evaluation/      # Run evaluations
        └── components/
```

---

## 🔍 Key Files Deep Dive

### 1. **`graph_system/initializer.py`** ⭐ START HERE

This is the **heart of ADAM**. It defines the entire workflow.

```python
def graph_init():
    """Initialize the ADAM agent graph"""
    graph_builder = node_builder()  # Creates graph with all nodes
    
    # Define the flow
    graph_builder.add_edge(START, "memory_agent")
    graph_builder.add_edge("memory_agent", "entry_router")
    
    # Conditional routing based on state
    graph_builder.add_conditional_edges(
        "classify_intent", 
        route_theme_known  # Function that decides next node
    )
    
    # ... more edges ...
    
    return graph_builder.compile()  # Returns executable graph
```

**What to look for:**
- `add_edge(from, to)` - Direct connections
- `add_conditional_edges(from, router_function)` - Decision points
- The order defines the flow

### 2. **`graph_system/states.py`**

Defines what data flows through the graph.

```python
class SystemState(TypedDict):
    """State shared across all nodes"""
    messages: Annotated[list, add_messages]  # Chat history
    user_query: str                          # Current question
    user_email: str                          # User identifier
    partner_name: str                        # Client context
    theme: str                               # Detected intent
    in_analysis: bool                        # Flow control flag
    code: str                                # Generated Python code
    code_result: str                         # Execution results
    final_response: str                      # Output to user
    download_links: list                     # Generated files
    metadata: dict                           # Campaign field metadata
    # ... more fields
```

**Key patterns:**
- Flags like `in_analysis`, `in_dsp`, `in_anomaly_det_run` control routing
- `metadata` provides context about DV360 fields
- `messages` accumulates the conversation

### 3. **`graph_system/routes.py`**

Contains routing logic (conditional edge functions).

```python
def route_after_analyser(state: SystemState) -> str:
    """Decides what to do after analysis"""
    if state.get("code_exec", False):
        return "code_generator"  # Need to execute code
    else:
        return "capture_result"  # Go directly to results
```

**Pattern:**
- Takes `state` as input
- Returns a string (node name to go to)
- Uses state flags to decide

### 4. **`agents/`** - Individual Agent Logic

Each agent is a node in the graph. Example:

```python
# agents/analyser_agent.py
def agent_analyser(state: SystemState) -> SystemState:
    """Analyzes user query and decides if code execution is needed"""
    
    # Get context from state
    user_query = state["user_query"]
    metadata = state["metadata"]
    
    # Call LLM to analyze
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest")
    prompt = create_analysis_prompt(user_query, metadata)
    response = llm.invoke(prompt)
    
    # Update state
    return {
        "code_exec": response.needs_code,
        "analysis_plan": response.plan,
        "messages": [AIMessage(content=response.explanation)]
    }
```

**Pattern:**
- Function name = node name
- Takes `SystemState`, returns `SystemState`
- Only returns fields that changed
- Can call LLMs, tools, or any Python code

### 5. **`main.py`** - API Entry Point

FastAPI server that receives user requests and runs the graph.

```python
@app.post("/chat/message")
async def process_message(message: ChatMessage):
    """Main endpoint that runs ADAM"""
    
    # Get the compiled graph (singleton)
    graph = get_graph()
    
    # Create config with user context
    config = {
        "configurable": {
            "thread_id": f"thread_{user_id}",
            "user_id": user_id,
            "user_email": message.user_email,
            "partner_name": message.partner
        }
    }
    
    # Run the graph
    final_state = {}
    async for event in graph.astream(
        {"messages": [HumanMessage(content=message.content)], 
         "metadata": metadata},
        config,
        stream_mode="values"
    ):
        final_state = event
    
    # Extract response
    return final_state["final_response"]
```

---

## 🎓 Common Tasks

### Task 1: Add a New Node

**Example: Add a "Translator" node**

1. **Create the agent function** (`agents/translator_agent.py`):
```python
from graph_system.states import SystemState
from langchain_core.messages import AIMessage

def translator_agent(state: SystemState) -> SystemState:
    """Translates response to user's language"""
    response = state["final_response"]
    target_language = state.get("user_language", "en")
    
    # Translation logic here
    translated = translate(response, target_language)
    
    return {
        "final_response": translated,
        "messages": [AIMessage(content="Translated response")]
    }
```

2. **Add to node builder** (`graph_system/node_builder.py`):
```python
from agents.translator_agent import translator_agent

def node_builder():
    graph_builder = StateGraph(SystemState)
    # ... existing nodes ...
    graph_builder.add_node("translator", translator_agent)
    return graph_builder
```

3. **Add to graph flow** (`graph_system/initializer.py`):
```python
def graph_init():
    graph_builder = node_builder()
    # ... existing edges ...
    graph_builder.add_edge("summarize_result", "translator")
    graph_builder.add_edge("translator", "final_response")
    return graph_builder.compile()
```

### Task 2: Modify Routing Logic

**Example: Route to translator only for non-English users**

1. **Create router function** (`graph_system/routes.py`):
```python
def route_after_summarize(state: SystemState) -> str:
    """Route based on user language"""
    user_language = state.get("user_language", "en")
    if user_language != "en":
        return "translator"
    else:
        return "final_response"
```

2. **Use in graph** (`graph_system/initializer.py`):
```python
graph_builder.add_conditional_edges(
    "summarize_result",
    route_after_summarize  # Instead of direct edge
)
```

### Task 3: Add State Fields

**Example: Track query complexity**

1. **Add to state definition** (`graph_system/states.py`):
```python
class SystemState(TypedDict):
    # ... existing fields ...
    query_complexity: str  # "simple" | "medium" | "complex"
```

2. **Set in agent** (`agents/classifier_intent_agent.py`):
```python
def classify_intent(state: SystemState) -> SystemState:
    # ... classification logic ...
    
    return {
        "theme": detected_theme,
        "query_complexity": assess_complexity(state["user_query"])
    }
```

3. **Use in routing** (`graph_system/routes.py`):
```python
def route_by_complexity(state: SystemState) -> str:
    if state["query_complexity"] == "simple":
        return "simple_handler"
    else:
        return "complex_handler"
```

### Task 4: Debug the Graph

**Enable detailed logging:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect state at each step:**

```python
# In main.py or when testing
for event in graph.stream(input_data, config):
    print(f"State after {event['node']}: {event['state']}")
```

**Visualize the graph:**

```python
from IPython.display import Image, display

# Generate graph visualization
display(Image(graph.get_graph().draw_mermaid_png()))
```

---

## 🧪 Testing & Development

### Running Locally

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your_key"
export OPENAI_API_KEY="your_key"
# ... other vars

python main.py
```

### Testing Individual Agents

```python
# test_agent.py
from agents.analyser_agent import agent_analyser
from graph_system.states import SystemState

# Create test state
test_state = SystemState(
    user_query="Check anomalies in campaign 12345",
    metadata={"campaigns": {...}},
    messages=[],
    # ... other required fields
)

# Run agent
result = agent_analyser(test_state)
print(result)
```

### Testing the Full Graph

```python
# test_graph.py
from graph_system.initializer import graph_init
from langchain_core.messages import HumanMessage

graph = graph_init()

result = graph.invoke({
    "messages": [HumanMessage(content="Analyze campaign 12345")],
    "metadata": metadata,
    "user_email": "test@example.com",
    "partner_name": "test_partner"
})

print(result["final_response"])
```

### Running Evaluations

```bash
cd backend
python evaluate_adam.py --preview  # Preview test cases
python evaluate_adam.py            # Run full evaluation
```

---

## 📚 Key Concepts to Remember

### 1. **State is Immutable (per node)**
Nodes return NEW state dicts; they don't modify the input state directly.

### 2. **Messages Always Append**
Using `Annotated[list, add_messages]` means new messages are added to the list, not replacing it.

### 3. **Routing Happens at Compile Time**
The graph structure is defined once at startup. Conditional edges evaluate at runtime but the possible paths are fixed.

### 4. **Thread ID = Conversation**
Same thread_id = same conversation history. Different thread_id = fresh start.

### 5. **Config Passes Context**
The `config` dict passes user context (email, partner, thread_id) through the entire graph.

---

## 🐛 Common Pitfalls

### Pitfall 1: Forgetting to Return State Updates

❌ **Wrong:**
```python
def my_node(state):
    state["new_field"] = "value"  # Modifies input, doesn't return
```

✅ **Correct:**
```python
def my_node(state):
    return {"new_field": "value"}  # Returns updates
```

### Pitfall 2: Circular Dependencies

❌ **Wrong:**
```python
graph.add_edge("node1", "node2")
graph.add_edge("node2", "node1")  # Infinite loop!
```

✅ **Correct:**
```python
graph.add_conditional_edges("node1", router)  # Router can decide to go back
```

### Pitfall 3: Missing State Fields

If a node tries to access `state["field"]` that doesn't exist, it crashes. Use:
```python
value = state.get("field", default_value)  # Safe access
```

---

## 🎯 Next Steps for New Developers

### Week 1: Understand the Flow
1. Read `graph_system/initializer.py` - understand the graph structure
2. Trace a simple query through the code
3. Run the backend locally and send test queries
4. Use debugger to step through nodes

### Week 2: Make Small Changes
1. Modify a prompt in `agents/prompts/`
2. Add a log statement in an agent
3. Change a routing condition
4. Test your changes

### Week 3: Add Features
1. Add a new agent node
2. Modify the state with new fields
3. Create a new routing path
4. Write tests for your changes

---

## 📖 Additional Resources

### LangGraph
- [Official Docs](https://langchain-ai.github.io/langgraph/)
- [Tutorials](https://langchain-ai.github.io/langgraph/tutorials/)
- [How-to Guides](https://langchain-ai.github.io/langgraph/how-tos/)

### Our Codebase
- `/backend/README.md` - Backend setup and configuration
- `/EVALUATION_INTEGRATION.md` - Evaluation system
- `/docs/flow.excalidraw` - Visual flow diagram

### Getting Help
- Check the code comments - most complex parts are documented
- Look at similar agents for patterns
- Ask in the team channel
- Review PRs for examples of changes

---

## 🤝 Contributing

1. **Branch naming**: `feature/your-feature` or `fix/bug-description`
2. **Commit messages**: Clear and descriptive
3. **Test locally**: Run evaluations before pushing
4. **Code review**: At least one approval required
5. **Documentation**: Update this guide if adding major features

---

**Welcome to the team! 🎉**

Questions? Start by exploring `graph_system/initializer.py` and trace a query through the code. The architecture will click once you see one full execution!

