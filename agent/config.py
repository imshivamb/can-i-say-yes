from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Bedrock Mantle Chat Completions model. Override with CISAY_BEDROCK_MODEL.
DEFAULT_MODEL_ID = "zai.glm-4.7-flash"
DEFAULT_REGION = "us-east-1"

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def model_id() -> str:
    return os.getenv("CISAY_BEDROCK_MODEL", DEFAULT_MODEL_ID)


def aws_region() -> str:
    return os.getenv("AWS_REGION", DEFAULT_REGION)


def agentcore_runtime_arn() -> str:
    return os.getenv("CISAY_AGENTCORE_RUNTIME_ARN", "").strip()


def is_agentcore_self() -> bool:
    return os.getenv("CISAY_AGENTCORE_SELF", "").lower() in {"1", "true", "yes"}


def cors_origins() -> list[str]:
    raw = os.getenv(
        "CISAY_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://localhost:3000"]


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()
