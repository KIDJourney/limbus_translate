import json
import tempfile
from pathlib import Path

from limbus_translate.formatting import text_hash
from limbus_translate.glossary import GlossaryTerm
from limbus_translate.lore import LoreEntry, build_lore_index
from limbus_translate.memory import MemoryEntry
from limbus_translate.providers import TranslationRequest
from limbus_translate.scanner import scan_missing
from limbus_translate.translator import overlay_existing_target, translate_units


class CapturingProvider:
    def __init__(self) -> None:
        self.requests: list[TranslationRequest] = []

    def translate(self, request: TranslationRequest) -> str:
        self.requests.append(request)
        return "新的战斗开始了。"


def make_term(source: str, target: str) -> GlossaryTerm:
    return GlossaryTerm(
        provider="test",
        project_id=None,
        term_id=None,
        source_lang="ko",
        target_lang="zh-cn",
        source=source,
        target=target,
        note="approved",
        part_of_speech="noun",
        variants=[],
        case_sensitive=False,
        created_at=None,
        updated_at=None,
        raw={},
        fetched_at="2026-06-13T00:00:00Z",
    )


def test_translate_provider_receives_structured_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "out"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps(
                {
                    "dataList": [
                        {
                            "id": 1,
                            "name": "단테",
                            "desc": "새 전투가 시작된다.",
                            "summary": "전투 기록을 확인했다.",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps(
                {
                    "dataList": [
                        {
                            "id": 1,
                            "name": "但丁",
                            "desc": "",
                            "summary": "确认了战斗记录。",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
        provider = CapturingProvider()
        memory = {
            "example": MemoryEntry(
                source_hash=text_hash("전투 기록을 확인했다."),
                source_text="전투 기록을 확인했다.",
                target_text="确认了战斗记录。",
                relative_file="Sample.json",
                json_path="dataList.0.summary",
            )
        }
        lore = [
            LoreEntry(
                title="전투",
                text="전투는 죄수들이 환상체와 맞서는 핵심 진행 단위다.",
                tags=["system"],
                source="fixture",
                anchors=["전투"],
                raw={},
            )
        ]

        overlay_existing_target(source, target, output)
        count = translate_units(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            glossary=[make_term("전투", "战斗")],
            provider=provider,
            memory=memory,
            lore_entries=lore,
            lore_index=build_lore_index(lore),
        )

    assert count == 1
    assert len(provider.requests) == 1
    context = json.loads(provider.requests[0].context)
    assert context["relative_file"] == "Sample.json"
    assert context["risk"] == "medium"
    assert context["terms"][0]["source"] == "전투"
    assert context["terms"][0]["target"] == "战斗"
    assert any(item["target_text"] == "但丁" for item in context["neighbors"])
    assert any(item["target_text"] == "确认了战斗记录。" for item in context["neighbors"])
    assert context["memory_examples"][0]["source_text"] == "전투 기록을 확인했다."
    assert context["lore"][0]["title"] == "전투"


def test_context_includes_cross_file_similar_memory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "out"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "거울 던전에 들어간다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": ""}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        provider = CapturingProvider()
        memory = {
            "similar": MemoryEntry(
                source_hash=text_hash("거울 던전으로 들어간다."),
                source_text="거울 던전으로 들어간다.",
                target_text="进入镜牢。",
                relative_file="Other.json",
                json_path="dataList.0.desc",
            ),
            "unrelated": MemoryEntry(
                source_hash=text_hash("버스가 멈췄다."),
                source_text="버스가 멈췄다.",
                target_text="巴士停下了。",
                relative_file="Other.json",
                json_path="dataList.1.desc",
            ),
        }

        units = scan_missing(source, target)
        overlay_existing_target(source, target, output)
        translate_units(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            glossary=[],
            provider=provider,
            memory=memory,
        )

    context = json.loads(provider.requests[0].context)
    examples = context["memory_examples"]
    assert examples[0]["role"] == "similar_memory"
    assert examples[0]["source_text"] == "거울 던전으로 들어간다."
    assert examples[0]["target_text"] == "进入镜牢。"
    assert examples[0]["score"] >= 0.35
    assert all(item["target_text"] != "巴士停下了。" for item in examples)
