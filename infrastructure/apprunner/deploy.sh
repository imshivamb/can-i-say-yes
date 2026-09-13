#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${ECR_REPOSITORY:=can-i-say-yes}"
: "${IMAGE_TAG:=latest}"
: "${SERVICE_NAME:=can-i-say-yes}"
: "${CISAY_BEDROCK_MODEL:=zai.glm-4.7-flash}"
: "${CISAY_CORS_ORIGINS:=http://localhost:3000}"
: "${CISAY_AGENTCORE_RUNTIME_ARN:=}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}-amd64"
ACCESS_ROLE="cisay-apprunner-ecr"
INSTANCE_ROLE="cisay-apprunner-instance"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ensure_role() {
  local name="$1"
  local trust="$2"
  local policy="$3"
  local arn="arn:aws:iam::${ACCOUNT_ID}:role/${name}"
  if ! aws iam get-role --role-name "${name}" >/dev/null 2>&1; then
    aws iam create-role \
      --role-name "${name}" \
      --assume-role-policy-document "file://${trust}" >/dev/null
    aws iam put-role-policy \
      --role-name "${name}" \
      --policy-name "${name}" \
      --policy-document "file://${policy}" >/dev/null
    echo "Created ${arn}; waiting for IAM propagation"
    sleep 12
  fi
  printf '%s\n' "${arn}"
}

ACCESS_ROLE_ARN="$(ensure_role "${ACCESS_ROLE}" "${SCRIPT_DIR}/ecr-trust.json" "${SCRIPT_DIR}/ecr-policy.json")"
INSTANCE_ROLE_ARN="$(ensure_role "${INSTANCE_ROLE}" "${SCRIPT_DIR}/instance-trust.json" "${SCRIPT_DIR}/instance-policy.json")"

EXISTING_ARN="$(aws apprunner list-services --region "${AWS_REGION}" \
  --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceArn" \
  --output text)"

if [ -n "${EXISTING_ARN}" ] && [ "${EXISTING_ARN}" != "None" ]; then
  aws apprunner update-service \
    --region "${AWS_REGION}" \
    --service-arn "${EXISTING_ARN}" \
    --source-configuration "{
      \"AuthenticationConfiguration\": {\"AccessRoleArn\": \"${ACCESS_ROLE_ARN}\"},
      \"AutoDeploymentsEnabled\": true,
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${IMAGE_URI}\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"8080\",
          \"RuntimeEnvironmentVariables\": {
            \"AWS_REGION\": \"${AWS_REGION}\",
            \"CISAY_RECORDED\": \"0\",
            \"CISAY_BEDROCK_MODEL\": \"${CISAY_BEDROCK_MODEL}\",
            \"CISAY_CORS_ORIGINS\": \"${CISAY_CORS_ORIGINS}\",
            \"CISAY_AGENTCORE_RUNTIME_ARN\": \"${CISAY_AGENTCORE_RUNTIME_ARN}\"
          }
        }
      }
    }" \
    --instance-configuration "{\"Cpu\":\"1 vCPU\",\"Memory\":\"2 GB\",\"InstanceRoleArn\":\"${INSTANCE_ROLE_ARN}\"}"
else
  aws apprunner create-service \
    --region "${AWS_REGION}" \
    --service-name "${SERVICE_NAME}" \
    --source-configuration "{
      \"AuthenticationConfiguration\": {\"AccessRoleArn\": \"${ACCESS_ROLE_ARN}\"},
      \"AutoDeploymentsEnabled\": true,
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${IMAGE_URI}\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"8080\",
          \"RuntimeEnvironmentVariables\": {
            \"AWS_REGION\": \"${AWS_REGION}\",
            \"CISAY_RECORDED\": \"0\",
            \"CISAY_BEDROCK_MODEL\": \"${CISAY_BEDROCK_MODEL}\",
            \"CISAY_CORS_ORIGINS\": \"${CISAY_CORS_ORIGINS}\",
            \"CISAY_AGENTCORE_RUNTIME_ARN\": \"${CISAY_AGENTCORE_RUNTIME_ARN}\"
          }
        }
      }
    }" \
    --instance-configuration "{\"Cpu\":\"1 vCPU\",\"Memory\":\"2 GB\",\"InstanceRoleArn\":\"${INSTANCE_ROLE_ARN}\"}" \
    --health-check-configuration "{\"Protocol\":\"HTTP\",\"Path\":\"/ping\",\"Interval\":10,\"Timeout\":5,\"HealthyThreshold\":1,\"UnhealthyThreshold\":5}"
fi

aws apprunner list-services --region "${AWS_REGION}" \
  --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].[ServiceUrl,Status]" \
  --output table
