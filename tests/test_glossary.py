from limbus_translate.glossary import GlossaryTerm, audit_terms, match_terms


def test_match_terms_uses_source_and_variants() -> None:
    term = GlossaryTerm(
        provider="paratranz",
        project_id=6860,
        term_id=1,
        source_lang="ko",
        target_lang="zh-cn",
        source="수감자",
        target="罪人",
        note="Limbus Company character role",
        part_of_speech="noun",
        variants=["수감자들"],
        case_sensitive=False,
        created_at=None,
        updated_at=None,
        raw={},
        fetched_at="2026-06-13T00:00:00Z",
    )
    assert match_terms("대부분의 수감자들이 마음 아프다는 표정을 지었다.", [term])[0].target == "罪人"


def test_audit_terms_reports_conflicts_and_invalid_rows() -> None:
    terms = [
        make_term(1, "수감자", "罪人"),
        make_term(2, "수감자", "囚人"),
        make_term(3, "단테", "단테"),
        make_term(4, "", "空源"),
        make_term(5, "No Hangul", ""),
        make_term(6, "버스", "巴士"),
        make_term(7, "버스", "巴士"),
    ]
    report = audit_terms(terms)
    codes = {issue.code for issue in report.issues}
    assert report.total_terms == 7
    assert "source_target_conflict" in codes
    assert "target_contains_hangul" in codes
    assert "empty_source" in codes
    assert "source_without_hangul" in codes
    assert "empty_target" in codes
    assert "duplicate_term_pair" in codes
    assert report.by_code["target_same_as_source"] == 1
    assert report.by_code["target_contains_hangul"] == 1
    assert report.by_code["empty_source"] == 1
    assert report.by_severity["warning"] >= 4


def make_term(term_id: int, source: str, target: str) -> GlossaryTerm:
    return GlossaryTerm(
        provider="paratranz",
        project_id=6860,
        term_id=term_id,
        source_lang="ko",
        target_lang="zh-cn",
        source=source,
        target=target,
        note="",
        part_of_speech="noun",
        variants=[],
        case_sensitive=False,
        created_at=None,
        updated_at=None,
        raw={},
        fetched_at="2026-06-13T00:00:00Z",
    )
