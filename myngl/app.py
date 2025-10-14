#!/bin/env python3
"""
Myngl Agent (Demo)
"""

from typing import Any, Dict
import os
import time
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from smolagents import ToolCallingAgent
from smolagents import LiteLLMModel

# Load .env from repository root
load_dotenv()

DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "claude-sonnet-4-20250514")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ENABLE_TRINO_MCP = os.getenv("ENABLE_TRINO_MCP", "false").lower() in {"1", "true", "yes"}

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


def get_agent():
    """Create and cache a smolagents ToolCallingAgent with a LiteLLM model.

    Uses Anthropic via LiteLLM. Expects ANTHROPIC_API_KEY in env.
    """
    if ToolCallingAgent is None or LiteLLMModel is None:
        raise RuntimeError(
            "smolagents or LiteLLMModel not available. Ensure dependencies are installed."
        )

    # Optionally prepare tool list; stub MCP tool can be plugged later when ENABLE_TRINO_MCP is true.
    tools = []
    if ENABLE_TRINO_MCP:
        # Placeholder: real MCP tool integration to be added in Phase 2
        # For now, a simple no-op tool stub could be added here.
        pass

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


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)  # 0.0.0.0 to ensure external connections work outside the docker
    
