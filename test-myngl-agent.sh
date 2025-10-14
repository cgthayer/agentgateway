#!/usr/bin/env bash
set -euo pipefail

if [ ${#@} -lt 1 ]; then
  echo "Usage: $0 \"<prompt>\"" >&2
  exit 1
fi

PROMPT="$1"
URL="http://127.0.0.1:9000/chat"

curl -sS -X POST \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"${PROMPT//\"/\\\"}\"}" \
  "$URL" | jq '.'
