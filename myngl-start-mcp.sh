#!/bin/bash

# https://github.com/tuannvm/mcp-trino
# brew install tuannvm/mcp/mcp-trino
# curl -fsSL https://raw.githubusercontent.com/tuannvm/mcp-trino/main/install.sh | bash
TRINO_HOST=localhost TRINO_PORT=8080 TRINO_USER=AgentAnalyst mcp-trino
