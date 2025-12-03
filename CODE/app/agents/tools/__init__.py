"""
Tool registry system for LangGraph agent.

Adding a new tool is as simple as:

1. Create a new file in this directory (e.g., api_tool.py)
2. Define a tool function:

    @register_tool(
        name="call_weather_api",
        description="Get weather information from external API"
    )
    async def call_weather_api(state: AgentState, city: str) -> Dict[str, Any]:
        # Your tool logic here
        response = await httpx.get(f"https://api.weather.com/{city}")
        return {
            "weather_data": response.json(),
            "tools_executed": ["call_weather_api"]
        }

3. Import it in __init__.py
4. LangGraph automatically handles the rest!
"""
from typing import Dict, Any, Callable, List
import logging

logger = logging.getLogger(__name__)

# Global tool registry
_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    requires_params: List[str] = None
):
    """Decorator to register a tool in the global registry.

    Args:
        name: Tool name (used in workflow graph)
        description: Human-readable description
        requires_params: List of required parameters

    Example:
        @register_tool(name="search_web", description="Search the web")
        async def search_web(state: AgentState, query: str):
            # Implementation
            pass
    """
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = {
            "function": func,
            "description": description,
            "requires_params": requires_params or []
        }
        logger.info(f"Registered tool: {name}")
        return func
    return decorator


def get_tool(name: str) -> Dict[str, Any]:
    """Get a registered tool by name."""
    return _TOOL_REGISTRY.get(name)


def get_all_tools() -> Dict[str, Dict[str, Any]]:
    """Get all registered tools."""
    return _TOOL_REGISTRY.copy()


def list_tool_names() -> List[str]:
    """List all registered tool names."""
    return list(_TOOL_REGISTRY.keys())
