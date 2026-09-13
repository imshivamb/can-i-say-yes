FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY agent ./agent
COPY adapters ./adapters
COPY domain ./domain
COPY data ./data
COPY infrastructure/agentcore/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir "aws-opentelemetry-distro>=0.19.0"

EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
