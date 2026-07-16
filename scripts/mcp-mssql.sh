#!/usr/bin/env bash
set -euo pipefail
CRED="${SYNAPSE_CREDENTIALS:-/home/synapse/source/N8N/synapse.credentials}"
set -a
# shellcheck disable=SC1090
source "$CRED"
set +a
export DB_SERVER="${DB_SERVER}"
export DB_DATABASE="${DB_DATABASE:-EnterpriseAdmin_AMC}"
export DB_USER="${DB_USER:-sa}"
export DB_PASSWORD="${DB_PASSWORD}"
export DB_TRUST_SERVER_CERTIFICATE=true
unset DB_PORT || true
exec npx -y mssql-mcp@latest
