#!/usr/bin/env bash
# Wrapper MCP n8n: carga synapse.credentials (N8N_API_URL + N8N_API_KEY).
set -euo pipefail
CRED="${SYNAPSE_CREDENTIALS:-/home/synapse/source/N8N/synapse.credentials}"
set -a
# shellcheck disable=SC1090
source "$CRED"
set +a
export N8N_API_URL="http://${DEBIAN_HOST:-10.147.18.4}:5678"
export N8N_API_KEY="${N8N_API_KEY:?N8N_API_KEY missing in synapse.credentials}"
export WEBHOOK_SECURITY_MODE=permissive
export MCP_MODE=stdio
export LOG_LEVEL=error
export DISABLE_CONSOLE_OUTPUT=true
exec npx -y n8n-mcp
