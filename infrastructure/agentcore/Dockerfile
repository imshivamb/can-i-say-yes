FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY agent ./agent
COPY adapters ./adapters
COPY domain ./domain
COPY data ./data
COPY docs ./docs

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8080
CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "8080"]
