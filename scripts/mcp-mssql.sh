#!/bin/bash
# Cursor MCP launcher: load synapse.credentials then start mssql-mcp.
# Non-secret DB_* connection params may also come from mcp.json env.
set -euo pipefail
exec /home/synapse/.zcode/mcp-wrapper.sh npx -y mssql-mcp@latest
