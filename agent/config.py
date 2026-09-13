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


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()
