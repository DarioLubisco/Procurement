#!/usr/bin/env bash
# Evita segfault de docker-mcp con el Node embebido de Cursor (v22+).
set -euo pipefail
export PATH="/usr/bin:${PATH}"
exec /usr/bin/npx -y docker-mcp
