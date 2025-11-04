#!/bin/env python3
"""
Myngl Agent (Demo)
"""

from typing import Any, Dict, List, Optional
import asyncio
import concurrent.futures
import inspect
import json
import logging
import os
import threading
import time
import types
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from smolagents import LiteLLMModel, Tool, ToolCallingAgent

# Load .env from repository root
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "claude-sonnet-4-20250514")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", str(Path(__file__).parent / "mcp-config.yaml"))

app = Flask(__name__)

# Global registry to keep MCP contexts alive and prevent garbage collection
_MCP_CONTEXTS_REGISTRY = []


class MCPTool(Tool):
    """Wrapper to make MCP server tools available to smolagents."""
    
    def __init__(self, name: str, description: str, input_schema: dict, mcp_tool_name: str, session: ClientSession, event_loop):
        self.name = name
        self.description = description
        self.mcp_tool_name = mcp_tool_name
        self.session = session
        self.event_loop = event_loop
        self.input_schema = input_schema
        
        # Convert MCP input schema to smolagents format
        self.output_type = "string"
        self.inputs = {}
        if input_schema and "properties" in input_schema:
            for prop_name, prop_info in input_schema["properties"].items():
                ptype = prop_info.get("type", "string")
                pdesc = prop_info.get("description", "")
                self.inputs[prop_name] = {"type": ptype, "description": pdesc}
                logger.info(f"Loaded input parameter: {prop_name} ({ptype}) - {pdesc}")
        
        self._setup_forward_method()
        self.is_initialized = True
    
    def _setup_forward_method(self):
        """Dynamically create forward method with parameters matching inputs.
                
        Each Tool has different arguments expected, which smolagents checks, 
        so we need to dynamically create the forward method for each tool
        with exactly the right signature.
        """
        # Create the proper signature
        params = [inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        for param_name in self.inputs.keys():
            params.append(
                inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            )
        sig = inspect.Signature(params)
        
        # Define the actual forward implementation
        def forward_impl(self, **kwargs):
            try:
                # Use the event loop that was used to create the session
                async def call_tool():
                    result = await self.session.call_tool(self.mcp_tool_name, arguments=kwargs)
                    
                    # Extract content from result
                    if hasattr(result, 'content') and result.content:
                        if isinstance(result.content, list):
                            return "\n".join(str(item.text) if hasattr(item, 'text') else str(item) for item in result.content)
                        return str(result.content)
                    return json.dumps(result)
                
                # Schedule the coroutine on the MCP session's event loop
                future = asyncio.run_coroutine_threadsafe(call_tool(), self.event_loop)
                result = future.result(timeout=30)  # secs
                return result
            except Exception as e:
                logger.error(f"Error calling MCP tool {self.mcp_tool_name}: {e}", exc_info=True)
                return f"Error calling MCP tool {self.mcp_tool_name}: {str(e)}"
        
        # Attach the signature to the method
        forward_impl.__signature__ = sig
        
        # Bind it to this instance
        self.forward = types.MethodType(forward_impl, self)


class MCPServerConnection:
    """Manages connection to a single MCP server."""
    
    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._stdio_context = None
        self._session_context = None
        self.event_loop = None
    
    async def connect(self) -> List[Tool]:
        """Connect to MCP server and return available tools.

        This is also complicated because MCP uses async context managers that create
        background tasks. We intentionally do NOT call __aexit__ on the contexts
        here because they need to remain alive for the duration of the application.
        Exiting them would trigger cleanup and close the connection.
        """
        # Store the event loop being used for this connection
        self.event_loop = asyncio.get_event_loop()
        
        # Merge environment variables
        server_env = os.environ.copy()
        server_env.update(self.env)
        
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=server_env
        )
        
        # Create and enter stdio_client context - keep reference to prevent cleanup
        self._stdio_context = stdio_client(server_params)
        self.read_stream, self.write_stream = await self._stdio_context.__aenter__()
        
        # Register context globally to prevent garbage collection
        _MCP_CONTEXTS_REGISTRY.append(self._stdio_context)
        
        # Create and enter session context - must use context manager for proper initialization
        self._session_context = ClientSession(self.read_stream, self.write_stream)
        self.session = await self._session_context.__aenter__()
        
        # Register session context globally to prevent garbage collection
        _MCP_CONTEXTS_REGISTRY.append(self._session_context)
        
        await self.session.initialize()
        
        # List available tools
        tools_list = await self.session.list_tools()
        
        # Create smolagents Tool wrappers
        mcp_tools = []
        for tool in tools_list.tools:
            logger.info(f"Loading tool: {tool.name}")
            mcp_tool = MCPTool(
                name=f"{self.name}_{tool.name}",
                description=tool.description or f"MCP tool: {tool.name}",
                input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                mcp_tool_name=tool.name,
                session=self.session,
                event_loop=self.event_loop
            )
            mcp_tools.append(mcp_tool)
        
        logger.info(f"Connected to '{self.name}' server, loaded {len(mcp_tools)} tools")
        return mcp_tools
    
    async def disconnect(self):
        """Disconnect from MCP server.
        
        Note: We intentionally do NOT call __aexit__ on the contexts here because
        they need to remain alive for the duration of the application. Exiting them
        from a different task/thread than they were entered causes errors.
        The contexts will be cleaned up when the event loop stops.
        """
        logger.info(f"Disconnect called for '{self.name}' (contexts kept alive)")


def load_mcp_config() -> List[dict]:
    """Load MCP server configuration from YAML file."""
    config_path = Path(MCP_CONFIG_PATH)
    
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return []
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        servers = config.get('servers', [])
        enabled_servers = [s for s in servers if s.get('enabled', False)]
        
        logger.info(f"Loaded config with {len(enabled_servers)} enabled server(s)")
        return enabled_servers
    except Exception as e:
        logger.error(f"Error loading config: {e}", exc_info=True)
        return []


async def load_all_mcp_tools_async() -> List[Tool]:
    """Load tools from all configured MCP servers."""
    server_configs = load_mcp_config()
    
    if not server_configs:
        return []
    
    all_tools = []
    connections = []
    
    for server_config in server_configs:
        try:
            connection = MCPServerConnection(
                name=server_config['name'],
                command=server_config['command'],
                args=server_config.get('args', []),
                env=server_config.get('env', {})
            )
            
            tools = await connection.connect()
            all_tools.extend(tools)
            connections.append(connection)
            
        except Exception as e:
            logger.error(f"Failed to connect to '{server_config['name']}': {e}", exc_info=True)
    
    # Store connections globally for cleanup (in production, use proper lifecycle management)
    app.config['mcp_connections'] = connections
    
    return all_tools


def load_all_mcp_tools() -> List[Tool]:
    """Synchronous wrapper to load MCP tools in a background thread with persistent event loop."""
    # Create a new event loop in a background thread
    loop = asyncio.new_event_loop()
    
    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    # Start the event loop in a daemon thread
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    
    # Load tools using the background loop
    future = asyncio.run_coroutine_threadsafe(load_all_mcp_tools_async(), loop)
    tools = future.result(timeout=60)
    
    # Store the loop for later use
    app.config['mcp_event_loop'] = loop
    
    return tools


def get_agent():
    """Create and cache a smolagents ToolCallingAgent with a LiteLLM model.

    Uses Anthropic via LiteLLM. Expects ANTHROPIC_API_KEY in env.
    """
    if ToolCallingAgent is None or LiteLLMModel is None:
        raise RuntimeError(
            "smolagents or LiteLLMModel not available. Ensure dependencies are installed."
        )

    tools = []
    
    # Load MCP tools from config
    try:
        mcp_tools = load_all_mcp_tools()
        tools.extend(mcp_tools)
        if mcp_tools:
            logger.info(f"Initialized with {len(mcp_tools)} MCP tool(s)")
        else:
            logger.info("No MCP tools loaded (check mcp-config.yaml)")
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)

    model = LiteLLMModel(model_id=DEFAULT_MODEL_ID, temperature=0.0)
    return ToolCallingAgent(tools=tools, model=model, max_steps=20)


def build_openai_like_response(content: str, model: str) -> Dict[str, Any]:
    now = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
    }


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Missing 'prompt'"}), 400

    # Validate key presence early for clearer error
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500

    try:
        agent = get_agent()
        content = agent.run(prompt)  # returns a string in basic use
        resp = build_openai_like_response(content=content, model=DEFAULT_MODEL_ID)
        return jsonify(resp)
    except Exception as exc:  # pragma: no cover - basic error surface
        logger.error(f"Error in /chat endpoint: {exc}", exc_info=True)
        return jsonify({"error": str(exc)}), 500


@app.post("/v1/chat/completions")
def chat_completions():
    """OpenAI-compatible chat completions endpoint."""
    data = request.get_json(silent=True) or {}
    
    # Extract messages array
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "Missing or invalid 'messages' array"}), 400
    
    # Get the last user message as the prompt
    user_messages = [msg for msg in messages if msg.get("role") == "user"]
    if not user_messages:
        return jsonify({"error": "No user message found in messages array"}), 400
    
    prompt = user_messages[-1].get("content", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Empty or invalid user message content"}), 400
    
    # Get model from request or use default
    model = data.get("model", DEFAULT_MODEL_ID)
    
    # Validate key presence early for clearer error
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500
    
    try:
        agent = get_agent()
        content = agent.run(prompt)  # returns a string in basic use
        resp = build_openai_like_response(content=content, model=model)
        return jsonify(resp)
    except Exception as exc:  # pragma: no cover - basic error surface
        logger.error(f"Error in /v1/chat/completions endpoint: {exc}", exc_info=True)
        return jsonify({"error": str(exc)}), 500


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3030)  # 0.0.0.0 to ensure external connections work outside the docker
    
