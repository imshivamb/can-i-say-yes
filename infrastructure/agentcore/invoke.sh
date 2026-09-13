#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${AGENT_RUNTIME_NAME:=CanISayYes}"

ARN="$(aws bedrock-agentcore-control list-agent-runtimes --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_RUNTIME_NAME}'].agentRuntimeArn" \
  --output text | awk '{print $1}')"

if [ -z "${ARN}" ] || [ "${ARN}" = "None" ]; then
  echo "No AgentCore runtime named ${AGENT_RUNTIME_NAME}" >&2
  exit 1
fi

ARN="${ARN}" AWS_REGION="${AWS_REGION}" python - <<'PY'
import json
import os
import uuid

import boto3

arn = os.environ["ARN"]
region = os.environ.get("AWS_REGION", "us-east-1")
client = boto3.client("bedrock-agentcore", region_name=region)
payload = {
    "input": {
        "kind": "parse_request",
        "prompt": "Acme Foods wants 12 social creatives, a landing page and three short videos by 18 September for 420000 INR.",
    }
}
response = client.invoke_agent_runtime(
    agentRuntimeArn=arn,
    runtimeSessionId=str(uuid.uuid4()),
    qualifier="DEFAULT",
    contentType="application/json",
    accept="application/json",
    payload=json.dumps(payload).encode(),
)
chunks = []
stream = response["response"]
if hasattr(stream, "read"):
    chunks.append(stream.read())
else:
    chunks.extend(chunk for chunk in stream if chunk)
print(b"".join(chunk if isinstance(chunk, bytes) else str(chunk).encode() for chunk in chunks).decode())
PY
