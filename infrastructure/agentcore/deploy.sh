#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${ECR_REPOSITORY:?Set ECR_REPOSITORY}"
: "${IMAGE_TAG:=latest}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPOSITORY}" >/dev/null
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY}"

docker buildx build \
  --platform linux/arm64 \
  --tag "${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}" \
  --push \
  -f infrastructure/agentcore/Dockerfile .

echo "Pushed ${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo "Create/update the AgentCore Runtime with infrastructure/agentcore/runtime.json."
