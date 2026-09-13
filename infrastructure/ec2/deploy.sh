#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
: "${INSTANCE_TYPE:=t3.micro}"
: "${ROLE_NAME:=cisay-ec2-api}"
: "${PROFILE_NAME:=cisay-ec2-api}"
: "${SG_NAME:=cisay-api}"
: "${NAME_TAG:=cisay-api}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

if ! aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${SCRIPT_DIR}/instance-trust.json" >/dev/null
  aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name cisay-ec2-api \
    --policy-document "file://${SCRIPT_DIR}/instance-policy.json" >/dev/null
fi

if ! aws iam get-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null 2>&1; then
  aws iam create-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null
  aws iam add-role-to-instance-profile \
    --instance-profile-name "${PROFILE_NAME}" \
    --role-name "${ROLE_NAME}" >/dev/null
  echo "Created instance profile; waiting for IAM propagation"
  sleep 12
fi

VPC_ID="$(aws ec2 describe-vpcs --region "${AWS_REGION}" \
  --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)"
SG_ID="$(aws ec2 describe-security-groups --region "${AWS_REGION}" \
  --filters Name=group-name,Values="${SG_NAME}" Name=vpc-id,Values="${VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' --output text)"
if [ "${SG_ID}" = "None" ] || [ -z "${SG_ID}" ]; then
  SG_ID="$(aws ec2 create-security-group --region "${AWS_REGION}" \
    --group-name "${SG_NAME}" \
    --description "Can I Say Yes public API" \
    --vpc-id "${VPC_ID}" \
    --query GroupId --output text)"
  aws ec2 authorize-security-group-ingress --region "${AWS_REGION}" \
    --group-id "${SG_ID}" --protocol tcp --port 8080 --cidr 0.0.0.0/0 >/dev/null
fi

EXISTING="$(aws ec2 describe-instances --region "${AWS_REGION}" \
  --filters "Name=tag:Name,Values=${NAME_TAG}" "Name=instance-state-name,Values=pending,running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)"
if [ "${EXISTING}" != "None" ] && [ -n "${EXISTING}" ]; then
  PUBLIC_IP="$(aws ec2 describe-instances --region "${AWS_REGION}" \
    --instance-ids "${EXISTING}" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
  echo "Reusing ${EXISTING} at ${PUBLIC_IP}"
  echo "${PUBLIC_IP}"
  exit 0
fi

REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
USER_DATA_FILE="$(mktemp)"
trap 'rm -f "${USER_DATA_FILE}"' EXIT
python3 - "${SCRIPT_DIR}/user-data.sh" "${REPO_ROOT}" "${USER_DATA_FILE}" <<'PY'
from pathlib import Path
import base64
import gzip
import sys

template = Path(sys.argv[1]).read_text()
root = Path(sys.argv[2])
out = Path(sys.argv[3])
files = {
    "agent/server.py": root.joinpath("agent/server.py").read_bytes(),
    "domain/ids.py": root.joinpath("domain/ids.py").read_bytes(),
}
payload = {
    rel: base64.b64encode(gzip.compress(data)).decode() for rel, data in files.items()
}
overlay = (
    "python3.12 - <<'OVERLAY'\n"
    "import base64, gzip\n"
    "from pathlib import Path\n"
    f"files = {payload!r}\n"
    "for rel, blob in files.items():\n"
    "    path = Path('/opt/can-i-say-yes') / rel\n"
    "    path.write_bytes(gzip.decompress(base64.b64decode(blob)))\n"
    "OVERLAY\n"
)
if "python3.12 -m venv /opt/cisay-venv" not in template:
    raise SystemExit("user-data.sh venv marker missing")
out.write_text(
    template.replace("python3.12 -m venv /opt/cisay-venv", overlay + "python3.12 -m venv /opt/cisay-venv", 1)
)
PY

AMI="$(aws ec2 describe-images --region "${AWS_REGION}" --owners 099720109477 \
  --filters 'Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*' \
            'Name=state,Values=available' \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)"
SUBNET="$(aws ec2 describe-subnets --region "${AWS_REGION}" \
  --filters Name=vpc-id,Values="${VPC_ID}" Name=default-for-az,Values=true \
  --query 'Subnets[0].SubnetId' --output text)"

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

aws ec2 wait instance-running --region "${AWS_REGION}" --instance-ids "${INSTANCE_ID}"
PUBLIC_IP="$(aws ec2 describe-instances --region "${AWS_REGION}" \
  --instance-ids "${INSTANCE_ID}" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
echo "Launched ${INSTANCE_ID} at ${PUBLIC_IP}"
echo "${PUBLIC_IP}"
