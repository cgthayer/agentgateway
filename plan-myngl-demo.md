# Plan Myngl Demo

- this will be a python service in the myngl directory
- set it up as a python project with a pyproject.toml
- create a flask service that responds to simple openAI chat completion requests for a single prompt and response.
- respond using HF smolagents, and include an MCP connection tool.
- have the python read the dotenv (`.env`) file for environment variables.
- the agent will use anthropic claude-sonnet-4 and LiteLLM
- run this service on port 9000
- provide file `test-myngl-agent.sh` that's a bash script to send it a prompt using curl. e.g. running `./test-myngl-agent.sh "What are the days of the week?"` should work
- we will connect this to an MCP tool for using Trino, but this can initially be stubbed out.

## Decisions (Phase 1)

- Python: Any Python 3.x is acceptable. Use `uv` for dependency management and a PEP 621 `pyproject.toml`.
- Endpoint: Start with a simple `POST /chat` endpoint that accepts a single prompt. Keep payloads minimal.
- Response format: Return a minimal, OpenAI-compatible JSON shape (e.g., `choices[0].message.content`).
- Model/provider: Use Anthropic via LiteLLM. Default model identifier: `claude-sonnet-4-20250514` (per LiteLLM’s Anthropic supported models). Allow overriding via env, e.g., `MODEL_ID`.
- API keys: Read `ANTHROPIC_API_KEY` from the repository root `.env` using `python-dotenv`/`dotenv`.
- Agent: Use HF `smolagents` regular LLM agent (not CodeAgent), configured for future tool use even in single-turn mode.
- MCP tool: Stub a Trino MCP tool, gated by an environment flag `ENABLE_TRINO_MCP=false` by default. For later, see https://github.com/alaturqua/mcp-trino-python
- Networking: Bind to `127.0.0.1:9000`. No CORS needed yet.
- Docker: Add a `myngl` service to `docker-compose-myngl.yaml` alongside Jaeger.
- Layout: Keep implementation under the `myngl/` directory with clear filenames (no separate deep agent directory for now).
- Test script: Provide `test-myngl-agent.sh` to send a prompt with curl, e.g. `./test-myngl-agent.sh "What are the days of the week?"`.

## Phase 2 (Placeholder)

- Expand API to add an OpenAI-compatible `POST /v1/chat/completions` endpoint while keeping `/chat`.
- Implement real MCP tool integration for Trino (replace stub with https://github.com/alaturqua/mcp-trino-python).
- Add streaming responses (server-sent events) and request/response prompt guard policies if needed.
- Add basic observability (OpenTelemetry traces/logs/metrics) and integrate with Jaeger.
- Introduce configuration schema and validation (e.g., Pydantic settings) and add CORS rules if a UI is added.
