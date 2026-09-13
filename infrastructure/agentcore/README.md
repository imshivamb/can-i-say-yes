# AgentCore + public API

The container exposes the AgentCore HTTP contract on port 8080:

- `GET /ping`
- `POST /invocations`

The [starter toolkit is deprecated](https://github.com/aws/bedrock-agentcore-starter-toolkit).
Use the current AgentCore control-plane API and the latest `@aws/agentcore` CLI
for new scaffolding. This repo already has a FastAPI agent, so launch uses
`create-agent-runtime` against the ARM64 image.

App Runner still runs AMD64, so `deploy.sh` publishes both tags from the same
Dockerfile.

```bash
export AWS_REGION=us-east-1
export CISAY_BEDROCK_MODEL=zai.glm-4.7-flash
./infrastructure/agentcore/deploy.sh
./infrastructure/observability/enable_transaction_search.sh
./infrastructure/agentcore/launch.sh
./infrastructure/agentcore/invoke.sh
CISAY_AGENTCORE_RUNTIME_ARN=<runtime-arn> \
CISAY_CORS_ORIGINS=https://your-app.vercel.app \
  ./infrastructure/apprunner/deploy.sh
```

Runtime env on AgentCore: `CISAY_RECORDED=0`, `CISAY_AGENTCORE_SELF=1`,
`CISAY_BEDROCK_MODEL`, `AWS_REGION`. Do not set `CISAY_AGENTCORE_RUNTIME_ARN`
on the runtime itself.

The product API calls `invoke_agent_runtime` when `CISAY_AGENTCORE_RUNTIME_ARN`
is set. If that call is not ready, App Runner still serves the live loop
in-process.
