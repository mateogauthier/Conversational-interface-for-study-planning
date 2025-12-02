"""Tool registry with definitions for all available agent tools."""

from typing import Dict, List, Callable, Any, Optional
from app.agents.base import Tool, ToolSafety
from app.db.models import UserInDB


# Tool registry: Maps tool names to Tool definitions and executor functions
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "list_files": {
        "definition": Tool(
            name="list_files",
            description="List all files the user has access to (their private files + public files)",
            parameters_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage="list_files()"
        ),
        "executor": None  # Will be set by ToolExecutor
    },
    "search_documents": {
        "definition": Tool(
            name="search_documents",
            description="Search through documents using semantic search. Returns relevant text chunks about the query topic.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant information"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query"]
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage='search_documents(query="database prerequisites", n_results=5)'
        ),
        "executor": None
    },
    "get_file_info": {
        "definition": Tool(
            name="get_file_info",
            description="Get detailed information about a specific file (size, upload date, statistics)",
            parameters_schema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to get information about"
                    }
                },
                "required": ["filename"]
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage='get_file_info(filename="course_catalog.pdf")'
        ),
        "executor": None
    },
    "list_conversations": {
        "definition": Tool(
            name="list_conversations",
            description="List user's conversation history",
            parameters_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of conversations to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": []
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage="list_conversations(limit=10)"
        ),
        "executor": None
    },
    "get_conversation": {
        "definition": Tool(
            name="get_conversation",
            description="Get full conversation history with all messages",
            parameters_schema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "ID of the conversation to retrieve"
                    }
                },
                "required": ["conversation_id"]
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage='get_conversation(conversation_id="conv_123")'
        ),
        "executor": None
    },
    "get_user_stats": {
        "definition": Tool(
            name="get_user_stats",
            description="Get user's statistics (file count, query count, storage used, etc.)",
            parameters_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage="get_user_stats()"
        ),
        "executor": None
    },
    "delete_file": {
        "definition": Tool(
            name="delete_file",
            description="Delete a file from the system (REQUIRES USER CONFIRMATION)",
            parameters_schema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to delete"
                    }
                },
                "required": ["filename"]
            },
            safety=ToolSafety.REQUIRES_CONFIRM,
            required_role=None,
            example_usage='delete_file(filename="old_notes.pdf")'
        ),
        "executor": None
    },
    "delete_conversation": {
        "definition": Tool(
            name="delete_conversation",
            description="Delete a conversation and all its messages (REQUIRES USER CONFIRMATION)",
            parameters_schema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "ID of the conversation to delete"
                    }
                },
                "required": ["conversation_id"]
            },
            safety=ToolSafety.REQUIRES_CONFIRM,
            required_role=None,
            example_usage='delete_conversation(conversation_id="conv_123")'
        ),
        "executor": None
    },
    "web_search": {
        "definition": Tool(
            name="web_search",
            description="Search the web using DuckDuckGo to find current information not available in documents",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find information on the web"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (1-10)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage='web_search(query="latest AI developments 2025", max_results=5)'
        ),
        "executor": None
    },
    "read_file_content": {
        "definition": Tool(
            name="read_file_content",
            description="Read the full text content of a specific file. Use this when you found relevant information in search results from a specific file but need more complete information from that file. This retrieves ALL text content from the file.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to read (e.g., 'escolaridad mateo gauthier.pdf')"
                    }
                },
                "required": ["filename"]
            },
            safety=ToolSafety.SAFE,
            required_role=None,
            example_usage='read_file_content(filename="escolaridad mateo gauthier.pdf")'
        ),
        "executor": None
    },
}


def get_tool(tool_name: str) -> Optional[Tool]:
    """Get tool definition by name.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool definition or None if not found
    """
    tool_data = TOOL_REGISTRY.get(tool_name)
    if tool_data:
        return tool_data["definition"]
    return None


def get_user_tools(user: UserInDB) -> List[Tool]:
    """Get list of tools available to the user based on their role.

    Args:
        user: Authenticated user

    Returns:
        List of Tool definitions user can access
    """
    available_tools = []

    for tool_name, tool_data in TOOL_REGISTRY.items():
        tool_def = tool_data["definition"]

        # Check role requirement
        if tool_def.required_role:
            if user.role != tool_def.required_role:
                continue  # Skip tools user doesn't have permission for

        available_tools.append(tool_def)

    return available_tools


def get_tool_descriptions_for_llm(user: UserInDB) -> str:
    """Generate formatted tool descriptions for LLM prompt.

    Args:
        user: Authenticated user

    Returns:
        Formatted string with tool descriptions
    """
    tools = get_user_tools(user)

    if not tools:
        return "No tools available."

    descriptions = ["Available tools:"]
    for tool in tools:
        safety_note = ""
        if tool.safety == ToolSafety.REQUIRES_CONFIRM:
            safety_note = " (REQUIRES USER CONFIRMATION)"
        elif tool.safety == ToolSafety.ADMIN_ONLY:
            safety_note = " (ADMIN ONLY)"

        descriptions.append(f"\n- {tool.name}{safety_note}")
        descriptions.append(f"  Description: {tool.description}")
        if tool.example_usage:
            descriptions.append(f"  Example: {tool.example_usage}")

    return "\n".join(descriptions)
