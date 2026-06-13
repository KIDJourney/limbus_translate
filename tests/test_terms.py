import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.glossary import GlossaryTerm
from limbus_translate.scanner import TranslationUnit
from limbus_translate.terms import (
    RulesTermRefiner,
    TermCandidate,
    RefinedTerm,
    extract_term_candidates,
    get_term_refiner,
    glossary_terms_from_review_csv,
    is_approved,
    promote_refined_terms,
    read_refined_terms,
    write_term_review_pack,
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


def test_promote_refined_terms_exports_only_confirmed_terms() -> None:
    refined = [
        RefinedTerm(
            source="거울 던전",
            decision="term",
            suggested_target="镜牢",
            note="approved by reviewer",
            confidence=0.91,
            contexts=["StoryData/Sample.json::dataList.0.content"],
            provider="openai",
            count=3,
            sample_text="거울 던전으로 향했다.",
            reason="hangul_phrase",
            raw={"decision": "term"},
        ),
        RefinedTerm(
            source="지크프리트",
            decision="needs_review",
            suggested_target="齐格弗里德",
            note="needs human approval",
            confidence=0.8,
            contexts=[],
            provider="openai",
            count=1,
            sample_text="지크프리트가 말했다.",
            reason="marked_name",
            raw={},
        ),
        RefinedTerm(
            source="W2사",
            decision="term",
            suggested_target="",
            note="missing target",
            confidence=0.9,
            contexts=[],
            provider="rules",
            count=2,
            sample_text="W2사가 도착했다.",
            reason="contains_number",
            raw={},
        ),
    ]

    promoted = promote_refined_terms(refined, min_confidence=0.5)

    assert len(promoted) == 1
    assert promoted[0].source == "거울 던전"
    assert promoted[0].target == "镜牢"
    assert promoted[0].provider == "local-refined"
    assert promoted[0].source_lang == "ko"
    assert promoted[0].target_lang == "zh-cn"
    assert "approved by reviewer" in promoted[0].note
    assert promoted[0].raw["source"] == "거울 던전"


def test_write_term_review_pack_exports_review_and_paratranz_files() -> None:
    refined = [
        RefinedTerm(
            source="거울 던전",
            decision="term",
            suggested_target="镜牢",
            note="approved candidate",
            confidence=0.91,
            contexts=["StoryData/Sample.json::dataList.0.content"],
            provider="openai",
            count=3,
            sample_text="거울 던전으로 향했다.",
            reason="hangul_phrase",
            raw={},
        ),
        RefinedTerm(
            source="지크프리트",
            decision="needs_review",
            suggested_target="齐格弗里德",
            note="needs human approval",
            confidence=0.8,
            contexts=["StoryData/Sample.json::dataList.1.content"],
            provider="openai",
            count=1,
            sample_text="지크프리트가 말했다.",
            reason="marked_name",
            raw={},
        ),
        RefinedTerm(
            source="문장입니다",
            decision="not_term",
            suggested_target="",
            note="ordinary phrase",
            confidence=0.7,
            contexts=[],
            provider="rules",
            count=1,
            sample_text="문장입니다.",
            reason="long_phrase",
            raw={},
        ),
    ]

    with TemporaryDirectory() as temp_dir:
        summary = write_term_review_pack(Path(temp_dir), refined)
        with (Path(temp_dir) / "review.csv").open(encoding="utf-8-sig") as handle:
            review_rows = list(csv.DictReader(handle))
        with (Path(temp_dir) / "paratranz-import.csv").open(encoding="utf-8-sig") as handle:
            paratranz_rows = list(csv.DictReader(handle))
        jsonl_rows = [
            json.loads(line)
            for line in (Path(temp_dir) / "review.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]

    assert summary["selected"] == 2
    assert summary["paratranz_candidates"] == 1
    assert [row["source"] for row in review_rows] == ["거울 던전", "지크프리트"]
    assert review_rows[0]["approved"] == ""
    assert review_rows[0]["target"] == "镜牢"
    assert paratranz_rows == [
        {
            "term": "거울 던전",
            "translation": "镜牢",
            "note": "approved candidate; provider=openai; reason=hangul_phrase",
        }
    ]
    assert jsonl_rows[0]["source"] == "거울 던전"
    assert jsonl_rows[0]["approved"] == ""


def test_glossary_terms_from_review_csv_imports_only_approved_rows() -> None:
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "review.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["source", "target", "approved", "decision", "provider", "reason", "note"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "source": "거울 던전",
                    "target": "镜牢",
                    "approved": "yes",
                    "decision": "term",
                    "provider": "openai",
                    "reason": "hangul_phrase",
                    "note": "reviewed",
                }
            )
            writer.writerow(
                {
                    "source": "지크프리트",
                    "target": "齐格弗里德",
                    "approved": "",
                    "decision": "needs_review",
                    "provider": "openai",
                    "reason": "marked_name",
                    "note": "not approved yet",
                }
            )
            writer.writerow(
                {
                    "source": "W2사",
                    "target": "",
                    "approved": "通过",
                    "decision": "term",
                    "provider": "rules",
                    "reason": "contains_number",
                    "note": "missing target",
                }
            )
        terms = glossary_terms_from_review_csv(path)

    assert is_approved("yes")
    assert is_approved("通过")
    assert not is_approved("")
    assert len(terms) == 1
    assert terms[0].source == "거울 던전"
    assert terms[0].target == "镜牢"
    assert terms[0].provider == "local-reviewed"
    assert terms[0].raw["approved"] == "yes"
    assert "reviewed" in terms[0].note
    assert "source_provider=openai" in terms[0].note
