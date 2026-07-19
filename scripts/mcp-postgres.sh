#!/bin/bash
# Cursor MCP launcher: load synapse.credentials then start postgres MCP.
set -euo pipefail
# Literal $VAR so mcp-wrapper.sh expands it after sourcing credentials.
exec /home/synapse/.zcode/mcp-wrapper.sh \
  npx -y @modelcontextprotocol/server-postgres \
  "\$POSTGRES_CONNECTION_STRING"
