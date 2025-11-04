# MCP Integration Architecture

## Overview

This document explains how the Model Context Protocol (MCP) integration works in the myngl agent application, particularly focusing on the event loop and context manager lifecycle management.

## The Challenge

MCP servers communicate via stdio (standard input/output) using an async protocol. The challenge is integrating this async MCP protocol with:
1. **smolagents** - A synchronous tool-calling framework
2. **Flask** - A synchronous web framework
3. **Cross-thread execution** - Tools called from Flask request handlers need to execute MCP calls on a different thread's event loop

## Architecture Components

### 1. Background Event Loop Thread

```python
def load_all_mcp_tools() -> List[Tool]:
    # Create a new event loop in a background thread
    loop = asyncio.new_event_loop()
    
    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    # Start the event loop in a daemon thread
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
```

**Key Points:**
- A dedicated event loop runs in a daemon thread for the application's lifetime
- This loop handles all MCP communication (connection setup, tool calls)
- The loop never stops until the application exits

### 2. MCP Connection Lifecycle

```python
async def connect(self) -> List[Tool]:
    # Enter stdio_client context
    self._stdio_context = stdio_client(server_params)
    self.read_stream, self.write_stream = await self._stdio_context.__aenter__()
    
    # Register globally to prevent garbage collection
    _MCP_CONTEXTS_REGISTRY.append(self._stdio_context)
    
    # Enter session context
    self._session_context = ClientSession(self.read_stream, self.write_stream)
    self.session = await self._session_context.__aenter__()
    
    # Register globally to prevent garbage collection
    _MCP_CONTEXTS_REGISTRY.append(self._session_context)
```

**Critical Insights:**

1. **Context Managers Must Stay Open**: MCP uses async context managers that create background tasks. These contexts must remain "entered" (never call `__aexit__`) for the connection to stay alive.

2. **Garbage Collection Problem**: Python's garbage collector will try to clean up context managers, triggering `__aexit__` from a different task than `__aenter__`, which causes:
   ```
   RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
   ```

3. **Solution - Global Registry**: Keep strong references to all context managers in a global list:
   ```python
   _MCP_CONTEXTS_REGISTRY = []
   ```
   This prevents garbage collection and keeps contexts alive for the application's lifetime.

### 3. Tool Execution Bridge

```python
def forward_impl(self, **kwargs):
    async def call_tool():
        result = await self.session.call_tool(self.mcp_tool_name, arguments=kwargs)
        # ... extract content ...
    
    # Schedule on the MCP event loop from any thread
    future = asyncio.run_coroutine_threadsafe(call_tool(), self.event_loop)
    result = future.result(timeout=30)
    return result
```

**How It Works:**
1. smolagents calls `tool.forward()` synchronously from a Flask request handler
2. We create an async function that calls the MCP tool
3. `asyncio.run_coroutine_threadsafe()` schedules this on the background event loop
4. We block waiting for the result with a timeout
5. Return the result synchronously to smolagents

### 4. Dynamic Method Signatures

```python
def _setup_forward_method(self):
    # Create signature matching the tool's inputs
    params = [inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    for param_name in self.inputs.keys():
        params.append(
            inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
    
    sig = inspect.Signature(params)
    forward_impl.__signature__ = sig
```

**Why This Matters:**
- smolagents validates that tool method signatures match their `inputs` dictionary
- MCP tools have dynamic parameters (e.g., `query` for SQL execution)
- We dynamically create the `forward()` method signature using `inspect` to match each tool's parameters

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Flask Request Handler (Main Thread)                            │
│   ↓                                                             │
│ smolagents.ToolCallingAgent.run()                              │
│   ↓                                                             │
│ MCPTool.forward(query="SELECT * FROM table")                   │
│   ↓                                                             │
│ asyncio.run_coroutine_threadsafe(call_tool(), event_loop)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Background Event Loop Thread                                    │
│   ↓                                                             │
│ session.call_tool("execute_query", {"query": "SELECT..."})    │
│   ↓                                                             │
│ MCP Protocol (JSON-RPC over stdio)                            │
│   ↓                                                             │
│ Trino MCP Server Process                                       │
│   ↓                                                             │
│ Execute query and return results                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         Return result
                              ↓
                    Flask response to client
```

## Key Takeaways

1. **Never exit MCP context managers** - They must stay open for the application lifetime
2. **Use a global registry** - Prevents garbage collection from triggering cleanup
3. **Background event loop** - Dedicated thread for all async MCP operations
4. **Thread-safe bridging** - `run_coroutine_threadsafe()` connects sync and async worlds
5. **Dynamic signatures** - Use `inspect` to match tool parameters to method signatures

## Configuration

MCP servers are configured in `mcp-config.yaml`:

```yaml
servers:
  - name: trino
    enabled: true
    command: bash
    args:
      - "start-trino-mcp.sh"
    env:
      TRINO_HOST: localhost
      TRINO_PORT: "8080"
```

Each enabled server:
- Spawns as a subprocess via `stdio_client`
- Connects using the background event loop
- Exposes tools that become available to smolagents

## Debugging Tips

1. **Event loop errors**: Usually means contexts are being exited - check the global registry
2. **Timeouts**: Increase timeout in `forward_impl` or check MCP server logs
3. **Tool not found**: Verify tool name matches MCP server's exposed tools
4. **Signature errors**: Check that `inputs` dictionary matches tool parameters
