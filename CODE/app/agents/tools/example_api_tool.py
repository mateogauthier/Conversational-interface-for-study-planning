"""
Example: How to add a new API tool to the agent.

This shows how easy it is to extend the agent with new capabilities.
Just define the function, decorate it, and it's ready to use!
"""
from typing import Dict, Any
import httpx
import logging

from app.agents.tools import register_tool
from app.agents.langgraph_provider import AgentState
from app.agents.base import AgentStep, ToolCall

logger = logging.getLogger(__name__)


@register_tool(
    name="call_weather_api",
    description="Get weather information from an external API",
    requires_params=["city"]
)
async def call_weather_api(state: AgentState, city: str) -> Dict[str, Any]:
    """
    Example tool: Call an external weather API.

    To use this tool in your agent:
    1. Add a node in _build_graph(): workflow.add_node("weather", call_weather_api_node)
    2. Add routing logic to decide when to call it
    3. That's it!

    Args:
        state: Current agent state
        city: City name to get weather for

    Returns:
        Updated state with weather data
    """
    step_num = len(state["agent_steps"]) + 1

    thinking_step = AgentStep(
        step_number=step_num,
        step_type="thought",
        content=f"Calling weather API for {city}"
    )

    try:
        # Call external API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": "YOUR_API_KEY"}
            )
            response.raise_for_status()
            weather_data = response.json()

        # Create tool execution steps
        tool_step = AgentStep(
            step_number=step_num + 1,
            step_type="tool_call",
            content=f"Executing call_weather_api",
            tool_call=ToolCall(
                tool_name="call_weather_api",
                parameters={"city": city}
            )
        )

        result_step = AgentStep(
            step_number=step_num + 2,
            step_type="result",
            content=f"Weather data retrieved for {city}",
            tool_call=ToolCall(
                tool_name="call_weather_api",
                parameters={"city": city},
                result=weather_data
            )
        )

        return {
            "weather_data": weather_data,
            "agent_steps": [thinking_step, tool_step, result_step],
            "tools_executed": ["call_weather_api"]
        }

    except Exception as e:
        logger.error(f"Weather API call failed: {e}")
        error_step = AgentStep(
            step_number=step_num + 1,
            step_type="error",
            content=f"Weather API failed: {str(e)}"
        )
        return {
            "agent_steps": [thinking_step, error_step],
            "error": str(e)
        }


@register_tool(
    name="call_custom_api",
    description="Call any custom API endpoint",
    requires_params=["endpoint", "method"]
)
async def call_custom_api(
    state: AgentState,
    endpoint: str,
    method: str = "GET",
    data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Example tool: Call any custom API endpoint.

    This shows how you can create a generic API caller that works with any endpoint.

    Args:
        state: Current agent state
        endpoint: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        data: Optional request data

    Returns:
        Updated state with API response
    """
    step_num = len(state["agent_steps"]) + 1

    thinking_step = AgentStep(
        step_number=step_num,
        step_type="thought",
        content=f"Calling {method} {endpoint}"
    )

    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(endpoint)
            elif method.upper() == "POST":
                response = await client.post(endpoint, json=data)
            elif method.upper() == "PUT":
                response = await client.put(endpoint, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(endpoint)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            result_data = response.json()

        tool_step = AgentStep(
            step_number=step_num + 1,
            step_type="tool_call",
            content=f"Executing call_custom_api",
            tool_call=ToolCall(
                tool_name="call_custom_api",
                parameters={"endpoint": endpoint, "method": method}
            )
        )

        result_step = AgentStep(
            step_number=step_num + 2,
            step_type="result",
            content=f"API call successful: {method} {endpoint}",
            tool_call=ToolCall(
                tool_name="call_custom_api",
                parameters={"endpoint": endpoint, "method": method},
                result=result_data
            )
        )

        return {
            "api_response": result_data,
            "agent_steps": [thinking_step, tool_step, result_step],
            "tools_executed": ["call_custom_api"]
        }

    except Exception as e:
        logger.error(f"API call failed: {e}")
        error_step = AgentStep(
            step_number=step_num + 1,
            step_type="error",
            content=f"API call failed: {str(e)}"
        )
        return {
            "agent_steps": [thinking_step, error_step],
            "error": str(e)
        }
