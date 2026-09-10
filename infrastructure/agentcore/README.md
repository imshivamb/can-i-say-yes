# AgentCore deployment

The container exposes the AgentCore-compatible contract:

- `GET /ping`
- `POST /invocations`
- port `8080`
- `linux/arm64`

Prerequisites:

1. An AWS account with Bedrock model access.
2. ECR and AgentCore permissions.
3. A verified SES sender and recipient.
4. OAuth access tokens for Gmail and Google Calendar.
5. Docker with ARM64 build support.

```bash
export AWS_REGION=us-east-1
export ECR_REPOSITORY=can-i-say-yes
./infrastructure/agentcore/deploy.sh
```

The runtime role should allow only Bedrock invocation, the required
operational storage, EventBridge event publishing, SES sending, and
CloudWatch/AgentCore observability. It must not have IAM or shell-host
permissions. Do not commit tokens or AWS credentials.
