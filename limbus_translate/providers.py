from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TranslationRequest:
    source_text: str
    glossary: list[tuple[str, str, str]]
    context: str


class TranslationProvider(Protocol):
    def translate(self, request: TranslationRequest) -> str:
        ...


class DryRunProvider:
    def translate(self, request: TranslationRequest) -> str:
        return f"[待译] {request.source_text}"


class OpenAIProvider:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4.1")

    def translate(self, request: TranslationRequest) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI provider requires `pip install '.[openai]'`.") from exc
        client = OpenAI()
        glossary_lines = "\n".join(f"- {src} => {dst} ({note})" for src, dst, note in request.glossary)
        prompt = {
            "task": "Translate Korean Limbus Company game text into Simplified Chinese.",
            "style": [
                "Keep the original placeholders, tags, punctuation intent, and line breaks.",
                "Use the glossary when applicable.",
                "Return only the translated Chinese text.",
            ],
            "context": request.context,
            "glossary": glossary_lines,
            "source": request.source_text,
        }
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "You are a professional Korean-to-Simplified-Chinese game localization translator.",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        return response.output_text.strip()


def get_provider(name: str) -> TranslationProvider:
    if name == "dry-run":
        return DryRunProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"unknown provider: {name}")
