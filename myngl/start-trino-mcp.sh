#!/bin/bash

# https://github.com/tuannvm/mcp-trino
# brew install tuannvm/mcp/mcp-trino
# curl -fsSL https://raw.githubusercontent.com/tuannvm/mcp-trino/main/install.sh | bash

# TRINO_HOST=localhost
# TRINO_PORT=8080
export TRINO_USER=AgentAnalyst
# http://myngl-trino:8080/
# 172.17.0.1

export TRINO_SCHEME=http
export TRINO_HOST=172.18.0.1
export TRINO_PORT=8080
export TRINO_USER=AgentAlice
mcp-trino
