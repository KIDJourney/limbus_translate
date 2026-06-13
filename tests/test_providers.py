from __future__ import annotations

from types import SimpleNamespace

from limbus_translate.providers import (
    OpenAICompatibleChatProvider,
    QwenMTProvider,
    TranslationRequest,
    build_qwen_translation_options,
    get_provider,
)


class FakeChatCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="译文。"))])


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeChatCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def make_request() -> TranslationRequest:
    return TranslationRequest(
        source_text="단테가 말했다.",
        glossary=[("단테", "但丁", "name")],
        context=(
            '{"memory_examples":[{"source_text":"단테","target_text":"但丁"}],'
            '"lore":[{"title":"Limbus Company"}],"previous_target_text":"但丁说道。"}'
        ),
    )


def test_openai_compatible_chat_provider_sends_structured_prompt() -> None:
    client = FakeClient()
    provider = OpenAICompatibleChatProvider(model="custom-model", client=client)

    translated = provider.translate(make_request())

    call = client.completions.calls[0]
    assert translated == "译文。"
    assert call["model"] == "custom-model"
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"
    assert "단테" in call["messages"][1]["content"]
    assert "但丁" in call["messages"][1]["content"]


def test_qwen_mt_provider_uses_translation_options_without_system_message() -> None:
    client = FakeClient()
    provider = QwenMTProvider(model="qwen-mt-plus", client=client)

    translated = provider.translate(make_request())

    call = client.completions.calls[0]
    assert translated == "译文。"
    assert call["model"] == "qwen-mt-plus"
    assert call["messages"] == [{"role": "user", "content": "단테가 말했다."}]
    options = call["extra_body"]["translation_options"]
    assert options["source_lang"] == "Korean"
    assert options["target_lang"] == "Chinese"
    assert options["terms"] == [{"source": "단테", "target": "但丁"}]
    assert options["tm_list"] == [{"source": "단테", "target": "但丁"}]
    assert "Limbus Company" in options["domains"]
    assert "但丁说道。" in options["domains"]


def test_qwen_translation_options_tolerates_invalid_context() -> None:
    options = build_qwen_translation_options(
        TranslationRequest(source_text="안녕.", glossary=[("안녕", "你好", "")], context="not-json")
    )

    assert options["terms"] == [{"source": "안녕", "target": "你好"}]
    assert "tm_list" not in options


def test_get_provider_accepts_compatible_provider_specs() -> None:
    assert isinstance(get_provider("openai-chat:test-model"), OpenAICompatibleChatProvider)
    assert isinstance(get_provider("qwen-mt:qwen-mt-turbo"), QwenMTProvider)


def test_get_provider_rejects_missing_compatible_model() -> None:
    for spec in ["openai-chat:", "qwen-mt:"]:
        try:
            get_provider(spec)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {spec}")
