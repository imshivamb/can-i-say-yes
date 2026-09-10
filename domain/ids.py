from __future__ import annotations

import secrets
from typing import Literal

IdPrefix = Literal[
    "req",
    "cmt",
    "asm",
    "dec",
    "evd",
    "evt",
    "per",
    "prj",
    "eml",
    "doc",
    "sup",
    "cal",
    "alt",
    "rsn",
    "cli",
    "ast",
    "wi",
    "con",
    "aud",
]

_PREFIXES: frozenset[str] = frozenset(
    {
        "req",
        "cmt",
        "asm",
        "dec",
        "evd",
        "evt",
        "per",
        "prj",
        "eml",
        "doc",
        "sup",
        "cal",
        "alt",
        "rsn",
        "cli",
        "ast",
        "wi",
        "con",
        "aud",
    }
)


def new_id(prefix: IdPrefix) -> str:
    if prefix not in _PREFIXES:
        raise ValueError(f"unknown id prefix: {prefix}")
    return f"{prefix}_{secrets.token_hex(4)}"


def has_prefix(value: str, prefix: IdPrefix) -> bool:
    return value.startswith(f"{prefix}_")
