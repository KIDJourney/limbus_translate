import json
import tempfile
from pathlib import Path

from limbus_translate.glossary import GlossaryTerm
from limbus_translate.lore import import_lore, match_lore, read_lore_cache, write_lore_cache


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


def test_import_markdown_lore_cache_roundtrip_and_match() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "world.md"
        cache = root / "world.json"
        source.write_text(
            "# 거울 던전\n\n"
            "关键词: 거울 던전, Mirror Dungeon\n\n"
            "거울 던전은 반복 전투와 자원 회수를 다루는 공간이다.\n",
            encoding="utf-8",
        )

        entries = import_lore(source)
        write_lore_cache(cache, entries)
        loaded = read_lore_cache(cache)

    matches = match_lore(
        "거울 던전에 들어간다.",
        loaded,
        terms=[make_term("거울 던전", "镜牢")],
    )
    assert loaded[0].title == "거울 던전"
    assert matches[0].title == "거울 던전"
    assert matches[0].score > 0


def test_import_json_lore_uses_anchors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "world.json"
        source.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "title": "단테",
                            "text": "시계 머리를 가진 관리자.",
                            "anchors": ["단테", "관리자"],
                            "tags": ["character"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        entries = import_lore(source)

    matches = match_lore("단테가 관리자에게 명령했다.", entries)
    assert matches[0].title == "단테"
    assert matches[0].tags == ["character"]


def test_import_lore_directory_skips_readme() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# 안내\n\n이 파일은 cache에 들어가면 안 된다.\n", encoding="utf-8")
        (root / "world.md").write_text("# 단테\n\n关键词: 단테\n\n단테는 관리자다.\n", encoding="utf-8")

        entries = import_lore(root)

    assert [entry.title for entry in entries] == ["단테"]


def test_match_lore_uses_ngram_similarity_without_anchor_hit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "world.json"
        source.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "title": "거울 던전",
                            "text": "거울 던전은 반복 전투와 자원 회수를 다루는 공간이다.",
                            "anchors": ["Mirror Dungeon"],
                        },
                        {
                            "title": "단테",
                            "text": "시계 머리를 가진 관리자.",
                            "anchors": ["관리자"],
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        entries = import_lore(source)

    matches = match_lore("반복 전투를 진행하고 자원을 회수한다.", entries)
    assert matches[0].title == "거울 던전"
    assert matches[0].score > 0
