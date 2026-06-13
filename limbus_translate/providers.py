from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol


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
                "If context.previous_target_text is present, revise that existing Chinese translation to match the new Korean source.",
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


class OpenAICompatibleChatProvider:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        env_prefix: str = "OPENAI_COMPATIBLE",
        default_model: str = "gpt-4.1",
        client: Any | None = None,
    ) -> None:
        self.model = model or os.environ.get(f"{env_prefix}_MODEL", default_model)
        self.base_url = base_url or os.environ.get(f"{env_prefix}_BASE_URL", "")
        self.api_key = api_key or os.environ.get(f"{env_prefix}_API_KEY", "")
        self._client = client
        self._env_prefix = env_prefix

    def translate(self, request: TranslationRequest) -> str:
        client = self._client or make_openai_client(
            api_key=self.api_key,
            base_url=self.base_url,
            provider_label=self._env_prefix.lower().replace("_", "-"),
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional Korean-to-Simplified-Chinese game localization translator.",
                },
                {"role": "user", "content": json.dumps(build_prompt_payload(request), ensure_ascii=False)},
            ],
        )
        return chat_completion_text(response)


class QwenMTProvider(OpenAICompatibleChatProvider):
    def __init__(self, *, model: str | None = None, client: Any | None = None) -> None:
        api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY", "")
        base_url = os.environ.get("QWEN_MT_BASE_URL") or os.environ.get(
            "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        default_model = os.environ.get("QWEN_MT_MODEL", "qwen-mt-plus")
        super().__init__(
            model=model,
            base_url=base_url,
            api_key=api_key,
            env_prefix="QWEN_MT",
            default_model=default_model,
            client=client,
        )

    def translate(self, request: TranslationRequest) -> str:
        client = self._client or make_openai_client(
            api_key=self.api_key,
            base_url=self.base_url,
            provider_label="qwen-mt",
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": request.source_text}],
            extra_body={"translation_options": build_qwen_translation_options(request)},
        )
        return chat_completion_text(response)


def build_prompt_payload(request: TranslationRequest) -> dict[str, object]:
    glossary_lines = "\n".join(f"- {src} => {dst} ({note})" for src, dst, note in request.glossary)
    return {
        "task": "Translate Korean Limbus Company game text into Simplified Chinese.",
        "style": [
            "Keep the original placeholders, tags, punctuation intent, and line breaks.",
            "Use the glossary when applicable.",
            "If context.previous_target_text is present, revise that existing Chinese translation to match the new Korean source.",
            "Return only the translated Chinese text.",
        ],
        "context": request.context,
        "glossary": glossary_lines,
        "source": request.source_text,
    }


def build_qwen_translation_options(request: TranslationRequest) -> dict[str, object]:
    context = parse_request_context(request.context)
    terms = [{"source": src, "target": dst} for src, dst, _note in request.glossary if src and dst]
    memory = []
    for item in context.get("memory_examples", []):
        if isinstance(item, dict) and item.get("source_text") and item.get("target_text"):
            memory.append({"source": item["source_text"], "target": item["target_text"]})
    domains = [
        "Limbus Company game localization",
        "science-fiction dark fantasy",
        "Simplified Chinese fan translation",
    ]
    for item in context.get("lore", []):
        if isinstance(item, dict) and item.get("title"):
            domains.append(str(item["title"]))
    if context.get("previous_target_text"):
        domains.append(f"Revise from existing Chinese translation: {context['previous_target_text']}")
    options: dict[str, object] = {
        "source_lang": "Korean",
        "target_lang": "Chinese",
        "domains": "; ".join(domains),
    }
    if terms:
        options["terms"] = terms
    if memory:
        options["tm_list"] = memory[:10]
    return options


def parse_request_context(context: str) -> dict[str, Any]:
    try:
        parsed = json.loads(context) if context else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def make_openai_client(*, api_key: str, base_url: str, provider_label: str):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(f"{provider_label} provider requires `pip install '.[openai]'`.") from exc
    kwargs: dict[str, str] = {}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def chat_completion_text(response: Any) -> str:
    choice = response.choices[0]
    message = choice["message"] if isinstance(choice, dict) else choice.message
    content = message["content"] if isinstance(message, dict) else message.content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                text_parts.append(str(item.get("text", "")))
            else:
                text_parts.append(str(getattr(item, "text", "")))
        return "".join(text_parts).strip()
    return str(content).strip()


def get_provider(name: str) -> TranslationProvider:
    if name == "dry-run":
        return DryRunProvider()
    if name == "openai":
        return OpenAIProvider()
    if name.startswith("openai:"):
        model = name.split(":", 1)[1].strip()
        if not model:
            raise ValueError("openai provider spec requires a model after `openai:`.")
        return OpenAIProvider(model=model)
    if name == "openai-chat":
        return OpenAICompatibleChatProvider(default_model=os.environ.get("OPENAI_COMPATIBLE_MODEL", "gpt-4.1"))
    if name.startswith("openai-chat:"):
        model = name.split(":", 1)[1].strip()
        if not model:
            raise ValueError("openai-chat provider spec requires a model after `openai-chat:`.")
        return OpenAICompatibleChatProvider(model=model)
    if name == "qwen-mt":
        return QwenMTProvider()
    if name.startswith("qwen-mt:"):
        model = name.split(":", 1)[1].strip()
        if not model:
            raise ValueError("qwen-mt provider spec requires a model after `qwen-mt:`.")
        return QwenMTProvider(model=model)
    raise ValueError(f"unknown provider: {name}")
