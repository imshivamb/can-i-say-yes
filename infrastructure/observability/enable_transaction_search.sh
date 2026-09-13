#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:=us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
POLICY_NAME="CISAYTransactionSearchXRayToCWLogs"
POLICY_DOC="$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TransactionSearchXRayToCWLogs",
      "Effect": "Allow",
      "Principal": { "Service": "xray.amazonaws.com" },
      "Action": "logs:PutLogEvents",
      "Resource": [
        "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:aws/spans:*",
        "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/aws/spans:*"
      ],
      "Condition": {
        "StringEquals": { "aws:SourceAccount": "${ACCOUNT_ID}" },
        "ArnLike": { "aws:SourceArn": "arn:aws:xray:${AWS_REGION}:${ACCOUNT_ID}:*" }
      }
    }
  ]
}
EOF
)"

aws logs put-resource-policy \
  --region "${AWS_REGION}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document "${POLICY_DOC}" >/dev/null

aws xray update-trace-segment-destination \
  --region "${AWS_REGION}" \
  --destination CloudWatchLogs

aws xray get-trace-segment-destination --region "${AWS_REGION}"
