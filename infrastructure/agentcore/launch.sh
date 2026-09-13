#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${ECR_REPOSITORY:=can-i-say-yes}"
: "${IMAGE_TAG:=latest}"
: "${AGENT_RUNTIME_NAME:=CanISayYes}"
: "${CISAY_BEDROCK_MODEL:=zai.glm-4.7-flash}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}-arm64"
ROLE_NAME="cisay-agentcore-runtime"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${SCRIPT_DIR}/runtime-trust.json" >/dev/null
  aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name cisay-agentcore-runtime \
    --policy-document "file://${SCRIPT_DIR}/runtime-policy.json" >/dev/null
  echo "Created ${ROLE_ARN}; waiting for IAM propagation"
  sleep 12
fi

if aws bedrock-agentcore-control list-agent-runtimes --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_RUNTIME_NAME}'].agentRuntimeId" \
  --output text | grep -q .; then
  RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes --region "${AWS_REGION}" \
    --query "agentRuntimes[?agentRuntimeName=='${AGENT_RUNTIME_NAME}'].agentRuntimeId" \
    --output text | awk '{print $1}')"
  aws bedrock-agentcore-control update-agent-runtime \
    --region "${AWS_REGION}" \
    --agent-runtime-id "${RUNTIME_ID}" \
    --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${IMAGE_URI}\"}}" \
    --role-arn "${ROLE_ARN}" \
    --network-configuration '{"networkMode":"PUBLIC"}' \
    --protocol-configuration '{"serverProtocol":"HTTP"}' \
    --environment-variables "CISAY_RECORDED=0,CISAY_AGENTCORE_SELF=1,CISAY_BEDROCK_MODEL=${CISAY_BEDROCK_MODEL},AWS_REGION=${AWS_REGION}"
else
  aws bedrock-agentcore-control create-agent-runtime \
    --region "${AWS_REGION}" \
    --agent-runtime-name "${AGENT_RUNTIME_NAME}" \
    --description "Can I Say Yes Investigator and Monitor" \
    --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${IMAGE_URI}\"}}" \
    --role-arn "${ROLE_ARN}" \
    --network-configuration '{"networkMode":"PUBLIC"}' \
    --protocol-configuration '{"serverProtocol":"HTTP"}' \
    --lifecycle-configuration idleRuntimeSessionTimeout=900,maxLifetime=1800 \
    --environment-variables "CISAY_RECORDED=0,CISAY_AGENTCORE_SELF=1,CISAY_BEDROCK_MODEL=${CISAY_BEDROCK_MODEL},AWS_REGION=${AWS_REGION}"
fi

aws bedrock-agentcore-control list-agent-runtimes --region "${AWS_REGION}" \
  --query "agentRuntimes[?agentRuntimeName=='${AGENT_RUNTIME_NAME}'].[agentRuntimeArn,status]" \
  --output table
