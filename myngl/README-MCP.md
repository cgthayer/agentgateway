# MCP Integration Guide

## Overview

The Myngl agent now supports MCP (Model Context Protocol) tool integration via stdio. This allows the agent to use tools from any MCP-compliant server.

## Architecture

```
┌─────────────────┐
│   Flask App     │
│   (app.py)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  smolagents     │
│  ToolCallingAgent│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   MCPTool       │─────▶│  MCP Server      │
│   Wrapper       │      │  (stdio/npx)     │
└─────────────────┘      └──────────────────┘
```

## Key Components

### 1. `MCPTool` Class
- Wraps MCP server tools as `smolagents.Tool` instances
- Handles async execution of MCP tool calls
- Converts MCP input schemas to smolagents format
- Extracts and formats tool results

### 2. `MCPServerConnection` Class
- Manages lifecycle of a single MCP server connection
- Connects via stdio (subprocess)
- Maintains session state
- Provides cleanup/disconnect methods

### 3. Configuration System
- YAML-based configuration (`mcp-config.yaml`)
- Supports multiple MCP servers
- Per-server environment variables
- Enable/disable individual servers

## Configuration

### Environment Variables

Add to `.env`:
```bash
# Enable MCP tool loading
ENABLE_TRINO_MCP=true

# Optional: Custom config path
MCP_CONFIG_PATH=/path/to/mcp-config.yaml
```

### MCP Server Configuration

Edit `myngl/mcp-config.yaml`:

```yaml
servers:
  - name: trino
    enabled: true
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-trino"
    env:
      TRINO_HOST: localhost
      TRINO_PORT: 8080
    description: "Trino database query server"
```

#### Configuration Fields

- **name**: Unique identifier for the server (used as tool name prefix)
- **enabled**: Boolean to enable/disable the server
- **command**: Executable command (e.g., `npx`, `node`, `python`)
- **args**: List of command arguments
- **env**: Dictionary of environment variables for the server
- **description**: Human-readable description

## Installation

1. Install dependencies:
```bash
cd myngl
pip install -e .
```

2. Ensure Node.js is installed (for npx-based MCP servers):
```bash
node --version
npm --version
```

3. Configure your MCP servers in `mcp-config.yaml`

4. Enable MCP in `.env`:
```bash
ENABLE_TRINO_MCP=true
```

## Usage

### Starting the Server

```bash
cd myngl
python app.py
```

On startup, you'll see:
```
[MCP] Loaded config with 1 enabled server(s)
[MCP] Connected to 'trino' server, loaded 3 tools
[Agent] Initialized with 3 MCP tool(s)
```

### Making Requests

The agent will automatically use MCP tools when appropriate:

```bash
curl -X POST http://localhost:3030/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Query the database to show all tables"
  }'
```

### Tool Naming Convention

Tools are prefixed with their server name:
- Server: `trino`
- Tool: `execute_query`
- Final name: `trino_execute_query`

This prevents naming conflicts when using multiple MCP servers.

## Adding More MCP Servers

### Example: Filesystem Server

```yaml
servers:
  - name: filesystem
    enabled: true
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/path/to/allowed/directory"
    description: "Filesystem operations"
```

### Example: PostgreSQL Server

```yaml
servers:
  - name: postgres
    enabled: true
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-postgres"
    env:
      POSTGRES_CONNECTION_STRING: "postgresql://user:pass@localhost:5432/db"
    description: "PostgreSQL database"
```

### Example: Custom Python MCP Server

```yaml
servers:
  - name: custom
    enabled: true
    command: python
    args:
      - "/path/to/your/mcp_server.py"
    env:
      CUSTOM_API_KEY: "your-api-key"
    description: "Custom Python MCP server"
```

## Troubleshooting

### MCP Server Not Connecting

**Check logs:**
```
[MCP] Failed to connect to 'trino': [Errno 2] No such file or directory: 'npx'
```

**Solution:** Install Node.js and npm

### Tools Not Loading

**Check logs:**
```
[MCP] Config file not found: /path/to/mcp-config.yaml
```

**Solution:** Verify `MCP_CONFIG_PATH` or ensure `mcp-config.yaml` exists in `myngl/` directory

### Tool Call Failures

**Check logs:**
```
Error calling MCP tool execute_query: Connection refused
```

**Solutions:**
- Verify server environment variables are correct
- Check that the MCP server process is running
- Review server-specific logs

### MCP Disabled

**Check logs:**
```
[Agent] MCP tools disabled (ENABLE_TRINO_MCP=false)
```

**Solution:** Set `ENABLE_TRINO_MCP=true` in `.env`

## Development Notes

### Session Management

Currently, MCP server connections are established when the agent is created and stored in `app.config['mcp_connections']`. In production, you should:

1. Implement proper connection pooling
2. Add health checks for MCP servers
3. Handle reconnection on failure
4. Clean up connections on app shutdown

### Error Handling

The `MCPTool.forward()` method catches exceptions and returns error messages as strings. Consider:

1. Logging errors to a monitoring system
2. Implementing retry logic for transient failures
3. Adding timeout handling for long-running tools

### Performance Considerations

- Each tool call creates a new event loop (consider connection pooling)
- Async operations are wrapped in sync context (Flask limitation)
- Multiple MCP servers increase startup time

## Testing

### Test MCP Server Connection

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_connection():
    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-trino"]
    )
    
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

asyncio.run(test_connection())
```

### Test Tool Call

```bash
curl -X POST http://localhost:3030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [
      {"role": "user", "content": "Use the trino tools to list available catalogs"}
    ]
  }'
```

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [smolagents Documentation](https://huggingface.co/docs/smolagents)
