# Adding New Tools to the Agent

This guide explains how to add new tools to the LangGraph agent system, following the clean architecture used in this project.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tool Types and Safety Levels](#tool-types-and-safety-levels)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Complete Example: Adding a Calculator Tool](#complete-example-adding-a-calculator-tool)
5. [Testing Your Tool](#testing-your-tool)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The agent tool system follows a **3-layer architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                          │
│              (CODE/app/agents/langgraph_provider.py)        │
│  - Orchestrates workflow                                    │
│  - Routes between tools                                     │
│  - Generates final answers                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Calls via HTTPToolExecutor
                 │
┌────────────────▼────────────────────────────────────────────┐
│                  Agent API (FastAPI)                        │
│              (AGENT_API/app/api/routes/tools.py)            │
│  - Exposes tools as HTTP endpoints                          │
│  - Validates requests                                       │
│  - Handles errors and returns responses                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Delegates to service layer
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   Tool Services                             │
│            (AGENT_API/app/services/tool_services.py)        │
│  - Implements business logic                                │
│  - Interacts with databases, APIs, files                    │
│  - Returns structured data                                  │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **LangGraph Agent** determines which tool to use based on query analysis
2. **HTTPToolExecutor** (`CODE/app/tools/http_executor.py`) calls the Agent API endpoint
3. **Agent API route** validates the request and delegates to service
4. **Tool Service** executes the actual logic (database query, API call, file operation, etc.)
5. Results flow back up through the layers to the LangGraph agent
6. Agent generates a final answer using LLM + tool results

---

## Tool Types and Safety Levels

Tools are categorized by their **safety level** (defined in `CODE/app/agents/base.py`):

### 1. **SAFE** - Auto-executed without confirmation
- **Examples**: `search_documents`, `list_files`, `get_user_stats`, `web_search`
- **Use for**: Read-only operations, searches, lookups
- **No user confirmation required**

### 2. **REQUIRES_CONFIRM** - Requires user approval before execution
- **Examples**: `delete_file`, `delete_conversation`
- **Use for**: Write operations, deletions, modifications
- **User must explicitly approve via confirmation endpoint**

### 3. **ADMIN_ONLY** - Only accessible to admin users
- **Examples**: System-wide operations, user management
- **Use for**: Administrative actions
- **Role-based access control enforced**

---

## Step-by-Step Guide

### Step 1: Define the Tool in the Registry

**File**: `CODE/app/tools/registry.py`

Add your tool definition to the `TOOL_REGISTRY` dictionary:

```python
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ... existing tools ...

    "your_tool_name": {
        "definition": Tool(
            name="your_tool_name",
            description="Clear description of what this tool does",
            parameters_schema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of parameter 1"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "Description of parameter 2",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["param1"]  # List required parameters
            },
            safety=ToolSafety.SAFE,  # or REQUIRES_CONFIRM, ADMIN_ONLY
            required_role=None,  # or "admin"
            example_usage='your_tool_name(param1="value", param2=5)'
        ),
        "executor": None  # Will be set by ToolExecutor
    },
}
```

**Key Points**:
- `name`: Must match the endpoint path in Agent API
- `description`: Shown to LLM to help decide when to use this tool
- `parameters_schema`: JSON Schema defining parameters
- `safety`: Determines if confirmation is needed
- `required_role`: Set to `"admin"` for admin-only tools
- `example_usage`: Helps users understand how to call the tool

---

### Step 2: Implement the Service Logic

**File**: `AGENT_API/app/services/tool_services.py`

Add a new method to the `AgentToolService` class:

```python
class AgentToolService:
    # ... existing methods ...

    async def your_tool_name(
        self,
        param1: str,
        param2: int,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Description of what this tool does.

        Args:
            param1: Description of parameter 1
            param2: Description of parameter 2
            user_id: User's database ID
            user_auth0_id: User's Auth0 ID
            user_role: User's role (student/admin)

        Returns:
            Dict containing the tool results

        Raises:
            ValueError: If parameters are invalid
            Exception: If operation fails
        """
        logger.info(f"Your tool called by {user_auth0_id}: param1={param1}, param2={param2}")

        try:
            # Implement your tool logic here
            # Examples:
            # - Query database
            # - Call external API
            # - Process files
            # - Perform calculations

            result = {
                "success": True,
                "data": "your result data",
                "message": "Operation completed successfully"
            }

            logger.info(f"Your tool completed for user {user_auth0_id}")
            return result

        except ValueError as e:
            logger.error(f"Invalid parameters for your_tool_name: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in your_tool_name: {e}", exc_info=True)
            raise Exception(f"Tool execution failed: {str(e)}")
```

**Best Practices for Service Methods**:
- Always log tool invocation with user ID
- Validate parameters early
- Use descriptive error messages
- Return structured dictionaries
- Handle exceptions gracefully
- Include success indicators in response

---

### Step 3: Create the API Endpoint

**File**: `AGENT_API/app/api/routes/tools.py`

Add a new route for your tool:

```python
# Import your request/response models
from app.models.requests import YourToolRequest
from app.models.responses import YourToolResponse

@router.post("/your_tool_name", response_model=YourToolResponse)
async def your_tool_name(request: YourToolRequest):
    """
    Description of what this endpoint does.

    Args:
        request: Request model containing tool parameters

    Returns:
        Response model with tool results

    Raises:
        HTTPException: 400 for invalid parameters, 500 for server errors
    """
    try:
        result = await agent_tool_service.your_tool_name(
            param1=request.param1,
            param2=request.param2,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return YourToolResponse(
            success=True,
            message="Tool executed successfully",
            **result
        )

    except ValueError as e:
        logger.error(f"Invalid request for your_tool_name: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in your_tool_name endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Step 4: Define Request/Response Models

**File**: `AGENT_API/app/models/requests.py`

```python
class YourToolRequest(BaseModel):
    """Request model for your_tool_name."""
    param1: str = Field(..., description="Description of parameter 1")
    param2: int = Field(10, ge=1, le=100, description="Description of parameter 2")

    # Standard fields for all tools
    user_id: str
    user_auth0_id: str
    user_role: str
```

**File**: `AGENT_API/app/models/responses.py`

```python
class YourToolResponse(BaseModel):
    """Response model for your_tool_name."""
    success: bool
    message: str
    data: Optional[Any] = None  # Your custom result data
    # Add any other fields your tool returns
```

---

### Step 5: Register the Endpoint in HTTPToolExecutor

**File**: `CODE/app/tools/http_executor.py`

Add your endpoint to the `endpoint_map`:

```python
endpoint_map = {
    "search_documents": "/tools/search_documents",
    "list_files": "/tools/list_files",
    # ... existing endpoints ...
    "your_tool_name": "/tools/your_tool_name",  # ADD THIS
}
```

---

### Step 6: Add Tool to LangGraph Available Tools

**File**: `CODE/app/agents/langgraph_provider.py`

If your tool should be listed in `/agent/tools` endpoint, add it to `get_available_tools()`:

```python
async def get_available_tools(self, user: UserInDB) -> List[Tool]:
    """Get list of tools available to the user."""
    return [
        Tool(
            name="search_documents",
            description="Search through uploaded documents using RAG to find relevant information",
            parameters={"query": "Search query text"}
        ),
        # ... existing tools ...
        Tool(
            name="your_tool_name",
            description="Description of your tool",
            parameters={"param1": "Description", "param2": "Description (default: 10)"}
        ),
    ]
```

---

## Complete Example: Adding a Calculator Tool

Let's walk through adding a simple calculator tool that performs basic arithmetic operations.

### 1. Define in Registry

**File**: `CODE/app/tools/registry.py`

```python
"calculator": {
    "definition": Tool(
        name="calculator",
        description="Perform basic arithmetic operations (add, subtract, multiply, divide)",
        parameters_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["operation", "a", "b"]
        },
        safety=ToolSafety.SAFE,
        required_role=None,
        example_usage='calculator(operation="add", a=5, b=3)'
    ),
    "executor": None
}
```

### 2. Implement Service

**File**: `AGENT_API/app/services/tool_services.py`

```python
async def calculator(
    self,
    operation: str,
    a: float,
    b: float,
    user_id: str,
    user_auth0_id: str,
    user_role: str
) -> Dict[str, Any]:
    """
    Perform basic arithmetic operations.

    Args:
        operation: Operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
        user_id: User's database ID
        user_auth0_id: User's Auth0 ID
        user_role: User's role

    Returns:
        Dict containing the calculation result

    Raises:
        ValueError: If operation is invalid or division by zero
    """
    logger.info(f"Calculator called by {user_auth0_id}: {operation}({a}, {b})")

    try:
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
        else:
            raise ValueError(f"Invalid operation: {operation}")

        return {
            "operation": operation,
            "operands": {"a": a, "b": b},
            "result": result,
            "expression": f"{a} {operation} {b} = {result}"
        }

    except ValueError as e:
        logger.error(f"Calculator error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected calculator error: {e}", exc_info=True)
        raise Exception(f"Calculator failed: {str(e)}")
```

### 3. Create API Endpoint

**File**: `AGENT_API/app/api/routes/tools.py`

```python
@router.post("/calculator", response_model=CalculatorResponse)
async def calculator(request: CalculatorRequest):
    """
    Perform basic arithmetic operations.

    Supports: add, subtract, multiply, divide
    """
    try:
        result = await agent_tool_service.calculator(
            operation=request.operation,
            a=request.a,
            b=request.b,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return CalculatorResponse(
            success=True,
            message="Calculation completed successfully",
            **result
        )

    except ValueError as e:
        logger.error(f"Invalid calculator request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Calculator error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Define Models

**File**: `AGENT_API/app/models/requests.py`

```python
class CalculatorRequest(BaseModel):
    """Request model for calculator tool."""
    operation: str = Field(..., description="Operation: add, subtract, multiply, divide")
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")

    user_id: str
    user_auth0_id: str
    user_role: str

    @validator('operation')
    def validate_operation(cls, v):
        allowed = ['add', 'subtract', 'multiply', 'divide']
        if v not in allowed:
            raise ValueError(f"Operation must be one of: {', '.join(allowed)}")
        return v
```

**File**: `AGENT_API/app/models/responses.py`

```python
class CalculatorResponse(BaseModel):
    """Response model for calculator tool."""
    success: bool
    message: str
    operation: str
    operands: Dict[str, float]
    result: float
    expression: str
```

### 5. Register Endpoint

**File**: `CODE/app/tools/http_executor.py`

```python
endpoint_map = {
    # ... existing endpoints ...
    "calculator": "/tools/calculator",
}
```

### 6. Add to Available Tools

**File**: `CODE/app/agents/langgraph_provider.py`

```python
async def get_available_tools(self, user: UserInDB) -> List[Tool]:
    return [
        # ... existing tools ...
        Tool(
            name="calculator",
            description="Perform basic arithmetic operations (add, subtract, multiply, divide)",
            parameters={"operation": "add/subtract/multiply/divide", "a": "number", "b": "number"}
        ),
    ]
```

---

## Testing Your Tool

### 1. Unit Test the Service

**File**: `AGENT_API/tests/test_tool_services.py`

```python
import pytest
from app.services.tool_services import agent_tool_service

@pytest.mark.asyncio
async def test_calculator_add():
    result = await agent_tool_service.calculator(
        operation="add",
        a=5,
        b=3,
        user_id="test_user",
        user_auth0_id="auth0|test",
        user_role="student"
    )
    assert result["result"] == 8
    assert result["operation"] == "add"

@pytest.mark.asyncio
async def test_calculator_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        await agent_tool_service.calculator(
            operation="divide",
            a=10,
            b=0,
            user_id="test_user",
            user_auth0_id="auth0|test",
            user_role="student"
        )
```

### 2. Test the API Endpoint

```bash
# Test via curl
curl -X POST "http://localhost:8002/tools/calculator" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "add",
    "a": 5,
    "b": 3,
    "user_id": "test",
    "user_auth0_id": "test",
    "user_role": "student"
  }'

# Expected response:
# {
#   "success": true,
#   "message": "Calculation completed successfully",
#   "operation": "add",
#   "operands": {"a": 5, "b": 3},
#   "result": 8,
#   "expression": "5 add 3 = 8"
# }
```

### 3. Test via Agent

```bash
# Test through the LangGraph agent
curl -X POST "http://localhost:8000/agent/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "prompt": "What is 5 + 3?",
    "enable_agent": true
  }'

# The agent should:
# 1. Detect that this is a calculation query
# 2. Call the calculator tool
# 3. Return the result in natural language
```

### 4. Check Logs

```bash
# Agent API logs
docker logs study-planning-agent-api --tail 50 | grep calculator

# Main API logs
docker logs study-planning-api --tail 50 | grep calculator
```

---

## Best Practices

### 1. **Naming Conventions**
- Use **snake_case** for tool names (`search_documents`, `web_search`)
- Use **descriptive names** that clearly indicate the tool's purpose
- Avoid abbreviations unless widely understood

### 2. **Error Handling**
- **Always validate inputs** in the service layer
- **Use specific exceptions**: `ValueError` for invalid parameters, `Exception` for execution errors
- **Return HTTP 400** for user errors, **HTTP 500** for server errors
- **Log all errors** with context (user ID, parameters)

### 3. **Security**
- **Never trust user input** - validate everything
- **Use role-based access control** for sensitive operations
- **Log all tool invocations** for audit trails
- **Sanitize file paths** and database queries
- **Rate limit** expensive operations

### 4. **Documentation**
- **Clear descriptions** for LLM and humans
- **Example usage** helps LLM understand when to use the tool
- **Document all parameters** with types and constraints
- **Explain return values** and error conditions

### 5. **Performance**
- **Use async/await** for I/O operations
- **Set timeouts** for external API calls
- **Cache results** when appropriate
- **Paginate large results** instead of returning everything

### 6. **Response Format**
- **Always include** `success` boolean
- **Provide descriptive** `message` field
- **Structure data** for easy parsing
- **Include metadata** (execution time, count, etc.)

---

## Troubleshooting

### Tool Not Showing in `/agent/tools`

**Problem**: Tool doesn't appear in the list of available tools

**Solution**:
1. Check that it's added to `TOOL_REGISTRY` in `registry.py`
2. Verify it's added to `get_available_tools()` in `langgraph_provider.py`
3. Ensure `required_role` allows the user to access it

### HTTPToolExecutor Can't Find Endpoint

**Problem**: `Unknown tool: your_tool_name`

**Solution**:
1. Add endpoint mapping in `http_executor.py`
2. Ensure endpoint path matches: `"/tools/your_tool_name"`
3. Rebuild and restart containers

### Agent Not Calling Your Tool

**Problem**: Agent doesn't use the tool even when appropriate

**Solution**:
1. Improve the tool's **description** - be very specific about when to use it
2. Add **routing keywords** if needed (see `_route_after_search` in LangGraph)
3. Check if **example_usage** is clear
4. Ensure the tool is marked as **SAFE** (REQUIRES_CONFIRM needs user approval)

### Tool Returns Error

**Problem**: Tool execution fails with exception

**Solution**:
1. Check **Agent API logs**: `docker logs study-planning-agent-api --tail 100`
2. Verify **parameters** match the schema
3. Test **service method directly** with unit tests
4. Check **database connectivity** or external API availability
5. Look for **validation errors** in request models

### Rate Limiting Issues

**Problem**: External API rate limits (like DuckDuckGo)

**Solution**:
1. **Catch rate limit exceptions** and return HTTP 503
2. **Implement caching** to reduce API calls
3. **Add retry logic** with exponential backoff
4. **Use alternative APIs** with higher rate limits
5. **Document limitations** in tool description

---

## Advanced Topics

### Adding Routing Logic for Your Tool

If your tool should be automatically selected for certain query types, add routing logic in `langgraph_provider.py`:

```python
def _route_after_search(self, state: AgentState) -> str:
    query_lower = state["query"].lower()

    # Add keywords for your tool
    calculator_keywords = ["calculate", "compute", "math", "add", "subtract", "multiply", "divide"]
    needs_calculator = any(keyword in query_lower for keyword in calculator_keywords)

    if needs_calculator:
        logger.info(f"Query requires calculator tool")
        return "calculator"  # Create a calculator node

    # ... existing routing logic ...
```

### Creating Multi-Step Tools

For complex operations requiring multiple steps:

1. **Break into atomic operations** - each step is a separate tool
2. **Use LangGraph workflow** - chain multiple tool calls
3. **Store intermediate results** - use AgentState to pass data between steps
4. **Handle partial failures** - implement rollback logic if needed

### Integrating External APIs

When calling external APIs:

```python
import httpx

async def external_api_tool(self, query: str, user_id: str, ...) -> Dict[str, Any]:
    """Call external API with proper error handling."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://api.example.com/endpoint",
                params={"q": query},
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise Exception("External API request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception("API rate limit exceeded")
            raise Exception(f"API error: {e.response.status_code}")
```

---

## Summary Checklist

When adding a new tool, ensure you've completed:

- [ ] Defined tool in `CODE/app/tools/registry.py`
- [ ] Implemented service method in `AGENT_API/app/services/tool_services.py`
- [ ] Created API endpoint in `AGENT_API/app/api/routes/tools.py`
- [ ] Defined request model in `AGENT_API/app/models/requests.py`
- [ ] Defined response model in `AGENT_API/app/models/responses.py`
- [ ] Added endpoint mapping in `CODE/app/tools/http_executor.py`
- [ ] Added to available tools in `CODE/app/agents/langgraph_provider.py`
- [ ] Written unit tests for service method
- [ ] Tested API endpoint directly
- [ ] Tested via LangGraph agent
- [ ] Documented tool behavior and limitations
- [ ] Rebuilt and restarted Docker containers

---

## Additional Resources

- **Tool Registry**: `CODE/app/tools/registry.py`
- **Base Tool Classes**: `CODE/app/agents/base.py`
- **HTTPToolExecutor**: `CODE/app/tools/http_executor.py`
- **LangGraph Provider**: `CODE/app/agents/langgraph_provider.py`
- **Agent API Routes**: `AGENT_API/app/api/routes/tools.py`
- **Tool Services**: `AGENT_API/app/services/tool_services.py`
- **Web Search Integration Example**: `WEB_SEARCH_INTEGRATION.md`

---

**Need Help?** Check the existing tools (`web_search`, `read_file_content`, `search_documents`) as reference implementations.
