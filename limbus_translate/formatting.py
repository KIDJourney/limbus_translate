from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


PLACEHOLDER_RE = re.compile(r"\{[0-9A-Za-z_]+\}|%[sdif]|\\n")
TAG_RE = re.compile(r"</?[^>\n]+>")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")


@dataclass(frozen=True)
class FormatProfile:
    source_hash: str
    placeholders: list[str]
    tags: list[str]
    numbers: list[str]
    line_breaks: int


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def profile_text(text: str) -> FormatProfile:
    return FormatProfile(
        source_hash=text_hash(text),
        placeholders=PLACEHOLDER_RE.findall(text),
        tags=TAG_RE.findall(text),
        numbers=NUMBER_RE.findall(text),
        line_breaks=text.count("\n"),
    )


def looks_internal_identifier(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if "_" in stripped:
        return True
    if re.fullmatch(r"[A-Za-z0-9_\-]+", stripped):
        return True
    # Short Korean labels without spacing are often internal event identifiers or speaker ids.
    if len(stripped) <= 12 and not re.search(r"[\s。！？!?，,.\n]", stripped):
        return True
    return False


def same_multiset(left: list[str], right: list[str]) -> bool:
    return sorted(left) == sorted(right)
