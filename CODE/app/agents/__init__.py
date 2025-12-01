"""Agent system with pluggable providers.

This module provides an abstraction layer for agentic capabilities.
Supports local implementation (using existing services) and external API integration.
"""

from app.agents.base import AgentProvider, AgentResponse, AgentStep, ToolCall, PendingConfirmation
from app.agents.local_provider import LocalAgentProvider
from app.agents.api_provider import APIAgentProvider

__all__ = [
    "AgentProvider",
    "AgentResponse",
    "AgentStep",
    "ToolCall",
    "PendingConfirmation",
    "LocalAgentProvider",
    "APIAgentProvider",
]
