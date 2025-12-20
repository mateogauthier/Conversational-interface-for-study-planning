#!/usr/bin/env python3
"""Test the agent with specific queries."""

import asyncio
import sys
sys.path.insert(0, '/app')

from app.agents.react_langgraph_provider import ReActLangGraphProvider
from app.tools.http_executor import HTTPToolExecutor
from app.db.models import UserInDB
from datetime import datetime
from bson import ObjectId

async def test_query(query: str):
    """Test a specific query."""
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print('='*80)

    # Create test user
    user = UserInDB(
        id=ObjectId(),
        auth0_id="auth0|6913c92148b4221060971050",
        email="test@example.com",
        role="student",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Create ReAct agent
    tool_executor = HTTPToolExecutor(agent_api_url="http://agent-api:8002")
    agent = ReActLangGraphProvider(tool_executor=tool_executor)

    # Execute query
    result = await agent.execute_query(query=query, user=user)

    print("\n--- ANSWER ---")
    print(result.answer)

    print("\n--- AGENT STEPS ---")
    for step in result.agent_steps:
        print(f"{step.step_number}. [{step.step_type}] {step.content}")

    await tool_executor.close()

async def main():
    """Run tests."""
    queries = [
        "que materias estoy cursando?",
        "que materias tengo completadas?",
    ]

    for query in queries:
        await test_query(query)

if __name__ == "__main__":
    asyncio.run(main())
