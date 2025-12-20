"""Agent system with pluggable providers.

This module provides an abstraction layer for agentic capabilities.
Supports ReAct-based agent (recommended) and external API integration.
"""

from app.agents.base import AgentProvider, AgentResponse, AgentStep, ToolCall, PendingConfirmation
from app.agents.react_langgraph_provider import ReActLangGraphProvider
from app.agents.api_provider import APIAgentProvider

__all__ = [
    "AgentProvider",
    "AgentResponse",
    "AgentStep",
    "ToolCall",
    "PendingConfirmation",
    "ReActLangGraphProvider",
    "APIAgentProvider",
]
