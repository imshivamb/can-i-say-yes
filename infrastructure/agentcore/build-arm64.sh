#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${ECR_REPOSITORY:=can-i-say-yes}"
: "${IMAGE_TAG:=latest-arm64}"
: "${ROLE_NAME:=cisay-ec2-builder}"
: "${PROFILE_NAME:=cisay-ec2-builder}"
: "${SG_NAME:=cisay-api}"
: "${NAME_TAG:=cisay-arm64-builder}"
: "${INSTANCE_TYPE:=t4g.small}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRUST="${SCRIPT_DIR}/../ec2/instance-trust.json"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

if ! aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${TRUST}" >/dev/null
fi
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name cisay-ec2-builder \
  --policy-document "file://${SCRIPT_DIR}/builder-policy.json" >/dev/null

if ! aws iam get-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null 2>&1; then
  aws iam create-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null
  aws iam add-role-to-instance-profile \
    --instance-profile-name "${PROFILE_NAME}" \
    --role-name "${ROLE_NAME}" >/dev/null
  echo "Created builder instance profile; waiting for IAM"
  sleep 15
fi

aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null

VPC_ID="$(aws ec2 describe-vpcs --region "${AWS_REGION}" \
  --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)"
SG_ID="$(aws ec2 describe-security-groups --region "${AWS_REGION}" \
  --filters Name=group-name,Values="${SG_NAME}" Name=vpc-id,Values="${VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' --output text)"
SUBNET="$(aws ec2 describe-subnets --region "${AWS_REGION}" \
  --filters Name=vpc-id,Values="${VPC_ID}" Name=default-for-az,Values=true \
  --query 'Subnets[0].SubnetId' --output text)"
AMI="$(aws ec2 describe-images --region "${AWS_REGION}" --owners 099720109477 \
  --filters 'Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*' \
            'Name=state,Values=available' \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)"

EXISTING="$(aws ec2 describe-instances --region "${AWS_REGION}" \
  --filters "Name=tag:Name,Values=${NAME_TAG}" "Name=instance-state-name,Values=pending,running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)"
if [ "${EXISTING}" != "None" ] && [ -n "${EXISTING}" ]; then
  echo "Builder already running: ${EXISTING}"
  echo "${EXISTING}"
  exit 0
fi

USER_DATA_FILE="$(mktemp)"
trap 'rm -f "${USER_DATA_FILE}"' EXIT
cat > "${USER_DATA_FILE}" <<EOF
#!/bin/bash
set -eux
exec > /var/log/cisay-arm64-build.log 2>&1
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io git unzip curl
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip -o /tmp/awscliv2.zip
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install
systemctl start docker
aws ecr get-login-password --region ${AWS_REGION} \\
  | docker login --username AWS --password-stdin ${REGISTRY}
cd /tmp
git clone --depth 1 https://github.com/imshivamb/can-i-say-yes.git
cd can-i-say-yes
docker build -t ${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG} \\
  -f infrastructure/agentcore/Dockerfile .
docker push ${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
echo CISAY_ARM64_PUSHED
EOF

INSTANCE_ID="$(aws ec2 run-instances --region "${AWS_REGION}" \
  --image-id "${AMI}" \
  --instance-type "${INSTANCE_TYPE}" \
  --subnet-id "${SUBNET}" \
  --security-group-ids "${SG_ID}" \
  --iam-instance-profile "Name=${PROFILE_NAME}" \
  --user-data "file://${USER_DATA_FILE}" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${NAME_TAG}}]" \
  --metadata-options HttpTokens=required,HttpPutResponseHopLimit=2 \
  --query 'Instances[0].InstanceId' --output text)"

echo "Launched builder ${INSTANCE_ID} (${INSTANCE_TYPE} ${AMI})"
echo "${INSTANCE_ID}"
