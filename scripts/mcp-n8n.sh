#!/bin/bash
# Cursor MCP launcher: load synapse.credentials then start n8n-mcp.
# N8N_API_KEY comes from credentials; N8N_API_URL may come from mcp.json env.
set -euo pipefail
exec /home/synapse/.zcode/mcp-wrapper.sh npx -y n8n-mcp
