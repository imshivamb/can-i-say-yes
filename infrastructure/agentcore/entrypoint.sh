#!/bin/sh
set -eu

if [ "${CISAY_AGENTCORE_SELF:-}" = "1" ] && command -v opentelemetry-instrument >/dev/null 2>&1; then
  exec opentelemetry-instrument uvicorn agent.server:app --host 0.0.0.0 --port 8080
fi

exec uvicorn agent.server:app --host 0.0.0.0 --port 8080
