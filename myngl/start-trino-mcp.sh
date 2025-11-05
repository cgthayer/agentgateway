#!/bin/bash

# https://github.com/tuannvm/mcp-trino
# brew install tuannvm/mcp/mcp-trino
# curl -fsSL https://raw.githubusercontent.com/tuannvm/mcp-trino/main/install.sh | bash

if [ ! "$TRINO_HOST" ]; then
    export TRINO_SCHEME=http
    export TRINO_HOST=172.17.0.1  # localhost, myngl-trino
    export TRINO_PORT=8080
    export TRINO_USER=AgentAlice
    echo "WARNING: set environment explicitly, since not provided::"
    set | grep TRINO
fi
mcp-trino
