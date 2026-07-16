#!/usr/bin/env bash
set -euo pipefail
CRED="${SYNAPSE_CREDENTIALS:-/home/synapse/source/N8N/synapse.credentials}"
set -a
# shellcheck disable=SC1090
source "$CRED"
set +a
export POSTGRES_CONNECTION_STRING="postgresql://${POSTGRES_GLOBAL_USER:-postgres}:${POSTGRES_GLOBAL_PASSWORD}@${DEBIAN_HOST:-10.147.18.4}:5432/postgres"
exec npx -y @modelcontextprotocol/server-postgres "$POSTGRES_CONNECTION_STRING"
