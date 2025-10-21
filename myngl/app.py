#!/bin/env python3
"""
Myngl Agent (Demo)
"""

from typing import Any, Dict
import os
import time
import uuid
import asyncio
import json

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from smolagents import ToolCallingAgent, Tool
from smolagents import LiteLLMModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load .env from repository root
load_dotenv()

DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "claude-sonnet-4-20250514")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ENABLE_TRINO_MCP = os.getenv("ENABLE_TRINO_MCP", "false").lower() in {"1", "true", "yes"}
MCP_SERVER_COMMAND = os.getenv("MCP_SERVER_COMMAND", "")
MCP_SERVER_ARGS = os.getenv("MCP_SERVER_ARGS", "").split() if os.getenv("MCP_SERVER_ARGS") else []

app = Flask(__name__)


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


class MCPTool(Tool):
    """Wrapper to make MCP server tools available to smolagents."""
    
    def __init__(self, name: str, description: str, mcp_tool_name: str, session: ClientSession):
        self.name = name
        self.description = description
        self.mcp_tool_name = mcp_tool_name
        self.session = session
        self.inputs = {"args": {"type": "string", "description": "JSON string of arguments"}}
        self.output_type = "string"
    
    def forward(self, args: str) -> str:
        """Execute the MCP tool call."""
        try:
            # Parse arguments
            parsed_args = json.loads(args) if isinstance(args, str) else args
            
            # Call MCP tool asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.session.call_tool(self.mcp_tool_name, arguments=parsed_args)
                )
                return json.dumps(result.content)
            finally:
                loop.close()
        except Exception as e:
            return f"Error calling MCP tool: {str(e)}"


async def get_mcp_tools():
    """Connect to MCP server and get available tools."""
    if not MCP_SERVER_COMMAND:
        return []
    
    try:
        server_params = StdioServerParameters(
            command=MCP_SERVER_COMMAND,
            args=MCP_SERVER_ARGS,
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List available tools
                tools_list = await session.list_tools()
                
                # Create smolagents Tool wrappers
                mcp_tools = []
                for tool in tools_list.tools:
                    mcp_tool = MCPTool(
                        name=tool.name,
                        description=tool.description or f"MCP tool: {tool.name}",
                        mcp_tool_name=tool.name,
                        session=session
                    )
                    mcp_tools.append(mcp_tool)
                
                return mcp_tools
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        return []


def get_agent():
    """Create and cache a smolagents ToolCallingAgent with a LiteLLM model.

    Uses Anthropic via LiteLLM. Expects ANTHROPIC_API_KEY in env.
    """
    if ToolCallingAgent is None or LiteLLMModel is None:
        raise RuntimeError(
            "smolagents or LiteLLMModel not available. Ensure dependencies are installed."
        )

    tools = []
    
    # Add MCP tools if configured
    if MCP_SERVER_COMMAND:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                mcp_tools = loop.run_until_complete(get_mcp_tools())
                tools.extend(mcp_tools)
                print(f"Loaded {len(mcp_tools)} MCP tools")
            finally:
                loop.close()
        except Exception as e:
            print(f"Failed to load MCP tools: {e}")

    model = LiteLLMModel(model_id=DEFAULT_MODEL_ID, temperature=0.0)
    return ToolCallingAgent(tools=tools, model=model, max_steps=20)


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
        return jsonify({"error": str(exc)}), 500


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3030)  # 0.0.0.0 to ensure external connections work outside the docker
    
