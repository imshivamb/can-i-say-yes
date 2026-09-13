#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${ECR_REPOSITORY:=can-i-say-yes}"
: "${IMAGE_TAG:=latest}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPOSITORY}" >/dev/null
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY}"

# AgentCore requires linux/arm64. App Runner still runs linux/amd64.
for PLATFORM in linux/arm64 linux/amd64; do
  ARCH="${PLATFORM##*/}"
  docker buildx build \
    --platform "${PLATFORM}" \
    --tag "${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}-${ARCH}" \
    --push \
    -f infrastructure/agentcore/Dockerfile .
done

docker buildx imagetools create \
  --tag "${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}" \
  "${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}-arm64" \
  "${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}-amd64"

echo "Pushed ${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo "arm64 tag: ${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}-arm64"
echo "amd64 tag: ${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}-amd64"
