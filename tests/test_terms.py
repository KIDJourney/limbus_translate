from limbus_translate.glossary import GlossaryTerm
from limbus_translate.scanner import TranslationUnit
from limbus_translate.terms import extract_term_candidates


def make_unit(text: str) -> TranslationUnit:
    return TranslationUnit(
        unit_id="u",
        relative_file="StoryData/Sample.json",
        json_path="dataList.0.content",
        source_text=text,
        target_text="",
        reason="missing_target_text",
        source_hash="hash",
        target_hash=None,
        placeholders=[],
        tags=[],
        numbers=[],
        line_breaks=0,
        risk="high",
    )


def test_extract_term_candidates_excludes_known_glossary() -> None:
    known = GlossaryTerm(
        provider="paratranz",
        project_id=6860,
        term_id=1,
        source_lang="ko",
        target_lang="zh-cn",
        source="수감자",
        target="罪人",
        note="",
        part_of_speech="noun",
        variants=[],
        case_sensitive=False,
        created_at=None,
        updated_at=None,
        raw={},
        fetched_at="2026-06-13T00:00:00Z",
    )
    candidates = extract_term_candidates([make_unit("수감자들과 지크프리트가 거울 던전으로 향했다.")], [known])
    sources = {candidate.source for candidate in candidates}
    assert "수감자들과" not in sources
    assert any("지크프리트" in source for source in sources)
