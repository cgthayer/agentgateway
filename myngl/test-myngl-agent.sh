#!/usr/bin/env bash
set -euo pipefail

if [ ${#@} -lt 1 ]; then
  echo "Usage: $0 \"<prompt>\"" >&2
  exit 1
fi

PROMPT="$1"
# URL="http://127.0.0.1:3030/v1/chat/completions"
URL="http://127.0.0.1:3010"  # via agentgateway

# OpenAI-compatible chat completions format
set -x
curl -v \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"claude-sonnet-4-20250514\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"${PROMPT//\"/\\\"}\"
      }
    ]
  }" \
  "$URL" 2>&1 | tee output.json

# jq . output.json || cat output.json
# cat output.json

