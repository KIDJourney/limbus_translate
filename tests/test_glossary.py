from limbus_translate.glossary import GlossaryTerm, match_terms


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
