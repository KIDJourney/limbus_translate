from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.glossary import GlossaryTerm
from limbus_translate.scanner import TranslationUnit
from limbus_translate.terms import (
    RulesTermRefiner,
    TermCandidate,
    extract_term_candidates,
    get_term_refiner,
    read_refined_terms,
    write_refined_terms,
)


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


def test_rules_refiner_classifies_core_decisions() -> None:
    candidates = [
        TermCandidate(
            source="거울 던전",
            count=2,
            contexts=["StoryData/Sample.json::dataList.0.content"],
            sample_text="거울 던전으로 향했다.",
            reason="hangul_phrase",
        ),
        TermCandidate(
            source="지크프리트",
            count=1,
            contexts=["StoryData/Sample.json::dataList.0.content"],
            sample_text="지크프리트가 거울 던전으로 향했다.",
            reason="marked_name",
        ),
        TermCandidate(
            source="거울 던전으로 향했다",
            count=1,
            contexts=["StoryData/Sample.json::dataList.1.content"],
            sample_text="거울 던전으로 향했다.",
            reason="long_phrase",
        ),
    ]

    refined = RulesTermRefiner().refine(candidates)
    by_source = {term.source: term for term in refined}

    assert by_source["거울 던전"].decision == "term"
    assert by_source["지크프리트"].decision == "needs_review"
    assert by_source["거울 던전으로 향했다"].decision == "not_term"
    for term in refined:
        assert term.provider == "rules"
        assert 0.0 <= term.confidence <= 1.0
        assert term.contexts
        assert term.count >= 1
        assert term.sample_text
        assert term.reason


def test_refined_terms_cache_roundtrip() -> None:
    refined = RulesTermRefiner().refine(
        [
            TermCandidate(
                source="W2사",
                count=2,
                contexts=["StoryData/Sample.json::dataList.0.content"],
                sample_text="W2사가 도착했다.",
                reason="contains_number",
            )
        ]
    )

    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "refined.json"
        write_refined_terms(path, refined)
        loaded = read_refined_terms(path)

    assert loaded == refined


def test_get_term_refiner_resolves_supported_providers() -> None:
    assert get_term_refiner("rules").name == "rules"
    assert get_term_refiner("openai").name == "openai"
    try:
        get_term_refiner("unknown")
    except ValueError as exc:
        assert "unknown term refiner" in str(exc)
    else:
        raise AssertionError("unknown provider should raise ValueError")
