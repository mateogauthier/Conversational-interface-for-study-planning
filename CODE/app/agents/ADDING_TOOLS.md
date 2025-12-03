# How to Add New Tools to the LangGraph Agent

The LangGraph agent makes it **extremely easy** to add new capabilities. This guide shows you how.

## Quick Start: Adding a Simple Tool

### Step 1: Create Your Tool Node Function

Create a new file in `app/agents/tools/` (e.g., `my_custom_tool.py`):

```python
from typing import Dict, Any
import logging
from app.agents.langgraph_provider import AgentState
from app.agents.base import AgentStep, ToolCall

logger = logging.getLogger(__name__)


async def my_custom_tool_node(state: AgentState) -> Dict[str, Any]:
    """Your custom tool logic.

    This function will be called as a node in the LangGraph workflow.
    It receives the current state and returns updates to that state.
    """
    step_num = len(state["agent_steps"]) + 1

    # Add thinking step
    thinking_step = AgentStep(
        step_number=step_num,
        step_type="thought",
        content="Executing my custom tool"
    )

    try:
        # YOUR LOGIC HERE
        result = do_something_useful()

        # Add tool execution step
        tool_step = AgentStep(
            step_number=step_num + 1,
            step_type="tool_call",
            content="Executing my_custom_tool",
            tool_call=ToolCall(
                tool_name="my_custom_tool",
                parameters={}
            )
        )

        # Add result step
        result_step = AgentStep(
            step_number=step_num + 2,
            step_type="result",
            content=f"Tool completed: {result}",
            tool_call=ToolCall(
                tool_name="my_custom_tool",
                parameters={},
                result=result
            )
        )

        return {
            "my_tool_data": result,  # Add to state
            "agent_steps": [thinking_step, tool_step, result_step],
            "tools_executed": ["my_custom_tool"]
        }

    except Exception as e:
        logger.error(f"Tool failed: {e}")
        error_step = AgentStep(
            step_number=step_num + 1,
            step_type="error",
            content=f"Tool failed: {str(e)}"
        )
        return {
            "agent_steps": [thinking_step, error_step],
            "error": str(e)
        }
```

### Step 2: Add Your Tool to the Workflow Graph

Edit `app/agents/langgraph_provider.py` in the `_build_graph()` method:

```python
def _build_graph(self) -> StateGraph:
    """Build the agent workflow graph."""
    workflow = StateGraph(AgentState)

    # Add existing nodes
    workflow.add_node("search_documents", self._search_documents_node)
    workflow.add_node("read_file_content", self._read_file_content_node)
    workflow.add_node("generate_answer", self._generate_answer_node)

    # ADD YOUR NEW TOOL NODE
    workflow.add_node("my_custom_tool", my_custom_tool_node)

    # Set entry point
    workflow.set_entry_point("search_documents")

    # Add routing (when to call your tool)
    workflow.add_conditional_edges(
        "search_documents",
        self._should_use_custom_tool,  # Your routing logic
        {
            "use_custom": "my_custom_tool",
            "read_file": "read_file_content",
            "generate": "generate_answer"
        }
    )

    # Connect your tool to the next step
    workflow.add_edge("my_custom_tool", "generate_answer")

    return workflow.compile()
```

### Step 3: Add Routing Logic (Optional)

If your tool should be conditionally executed, add routing logic:

```python
def _should_use_custom_tool(self, state: AgentState) -> str:
    """Decide if we should use the custom tool.

    This is deterministic logic - no LLM needed!
    """
    # Example: Use custom tool if query contains specific keyword
    if "weather" in state["query"].lower():
        return "use_custom"

    # Otherwise, follow existing flow
    if state.get("file_content"):
        return "generate"

    search_results = state.get("search_results")
    if search_results and search_results.get("n_chunks_found", 0) > 0:
        return "read_file"

    return "generate"
```

That's it! Your tool is now integrated.

## Example: Adding an API Tool

Here's a complete example of adding a weather API tool:

```python
# app/agents/tools/weather_tool.py
import httpx
from typing import Dict, Any
from app.agents.langgraph_provider import AgentState
from app.agents.base import AgentStep, ToolCall

async def weather_api_node(state: AgentState) -> Dict[str, Any]:
    """Call external weather API."""
    step_num = len(state["agent_steps"]) + 1

    # Extract city from query (simple example)
    query = state["query"].lower()
    city = "montevideo"  # Default
    if "weather in" in query:
        city = query.split("weather in")[1].strip().split()[0]

    thinking_step = AgentStep(
        step_number=step_num,
        step_type="thought",
        content=f"Fetching weather for {city}"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://wttr.in/{city}?format=j1"
            )
            response.raise_for_status()
            weather_data = response.json()

        tool_step = AgentStep(
            step_number=step_num + 1,
            step_type="tool_call",
            content="Executing weather_api",
            tool_call=ToolCall(
                tool_name="weather_api",
                parameters={"city": city}
            )
        )

        result_step = AgentStep(
            step_number=step_num + 2,
            step_type="result",
            content=f"Weather data retrieved for {city}",
            tool_call=ToolCall(
                tool_name="weather_api",
                parameters={"city": city},
                result=weather_data
            )
        )

        return {
            "weather_data": weather_data,
            "agent_steps": [thinking_step, tool_step, result_step],
            "tools_executed": ["weather_api"]
        }

    except Exception as e:
        error_step = AgentStep(
            step_number=step_num + 1,
            step_type="error",
            content=f"Weather API failed: {str(e)}"
        )
        return {
            "agent_steps": [thinking_step, error_step],
            "error": str(e)
        }
```

## Advanced: Adding State Fields

If your tool needs to store data in the agent state:

1. Update `AgentState` in `langgraph_provider.py`:

```python
class AgentState(TypedDict):
    # ... existing fields ...

    # Add your custom field
    weather_data: Optional[Dict[str, Any]]  # NEW
```

2. Your tool can now read/write this field:

```python
async def weather_api_node(state: AgentState) -> Dict[str, Any]:
    # ... tool logic ...
    return {
        "weather_data": result,  # Stored in state
        # ... rest of updates ...
    }
```

3. Other nodes can access it:

```python
async def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    weather = state.get("weather_data")  # Access stored data
    # Use it to generate answer
```

## Benefits of This Approach

✅ **Deterministic** - No LLM deciding when to call tools (more reliable)
✅ **Stateful** - LangGraph manages state automatically
✅ **Debuggable** - Clear execution flow, easy to trace
✅ **Extensible** - Add tools without modifying existing code
✅ **Production-Ready** - LangGraph is battle-tested

## Common Patterns

### Pattern 1: Sequential Tools
```python
workflow.add_edge("tool_a", "tool_b")  # A always followed by B
workflow.add_edge("tool_b", "generate_answer")
```

### Pattern 2: Conditional Branching
```python
workflow.add_conditional_edges(
    "tool_a",
    lambda state: "path_1" if condition else "path_2",
    {
        "path_1": "tool_b",
        "path_2": "tool_c"
    }
)
```

### Pattern 3: Parallel Execution
```python
# Execute tools in parallel (advanced - requires subgraphs)
# See LangGraph documentation for details
```

## Debugging Tips

1. **Check agent_steps** - Every step is logged in the response
2. **Use logger.info()** - Add logging to your tool nodes
3. **Visualize the graph** - LangGraph can generate visual diagrams
4. **Test tools independently** - Tools are just async functions

## Migration from Old Agent

The old agent used LLM-based decision making which was unreliable.
The new LangGraph agent uses deterministic routing which is much more reliable:

**Old way (unreliable)**:
- LLM decides: "Do I need more tools?"
- LLM extracts parameters from text
- Prone to loops and wrong decisions

**New way (reliable)**:
- Deterministic logic: `if condition: use_tool`
- Structured parameters (no parsing needed)
- Clear termination conditions

## Next Steps

- Check `tools/example_api_tool.py` for more examples
- Read LangGraph documentation: https://langchain-ai.github.io/langgraph/
- Test your tools with real queries
- Add more tools as needed!
