# Myngl Agent (Demo)

A minimal Flask service exposing `POST /chat`, backed by Hugging Face smolagents using LiteLLM to call Anthropic Claude Sonnet 4. Returns a minimal OpenAI-compatible JSON response.

## Requirements

- Python 3.x
- `uv` for dependency management: https://github.com/astral-sh/uv
- An `.env` file at the repo root containing `ANTHROPIC_API_KEY=...`

## Setup (Local)

```bash
# From the repository root
cd myngl

# Create virtual env and install deps via uv
uv venv
source .venv/bin/activate
uv pip install -e .

# Run server (binds to 127.0.0.1:9000)
python app.py
```

## Configuration

Environment variables (read by `python-dotenv` from repo root `.env`):

- `ANTHROPIC_API_KEY`: required
- `MODEL_ID`: optional, defaults to `claude-sonnet-4-20250514`
- `ENABLE_TRINO_MCP`: optional, `false` by default

The file `config-myngl.yaml` is an example of how to configure this agent in agentgateway.
* See [Example AI Prompt Guard](examples/ai-prompt-guard/README.md)


## API

- `POST /chat`
  - Request JSON: `{ "prompt": "..." }`
  - Response JSON (OpenAI-like minimal): `choices[0].message.content`

## Test Script

From the repository root:

```bash
./test-myngl-agent.sh "What are the days of the week?"
```

## Docker

```bash
# Build
docker build -t myngl-agent:dev -f myngl/Dockerfile myngl

# Run (expects .env with ANTHROPIC_API_KEY in current directory)
docker run --rm --env-file .env -p 127.0.0.1:9000:9000 myngl-agent:dev
```

Or use `docker-compose-myngl.yaml` which includes the `myngl` service.
