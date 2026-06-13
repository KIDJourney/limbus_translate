from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .formatting import profile_text, same_multiset
from .glossary import GlossaryTerm, match_terms
from .json_paths import contains_hangul, get_path
from .scanner import TranslationUnit, load_json


@dataclass(frozen=True)
class QaIssue:
    severity: str
    code: str
    relative_file: str
    json_path: str
    message: str


def check_pair(unit: TranslationUnit, translated_text: str, glossary: list[GlossaryTerm]) -> list[QaIssue]:
    issues: list[QaIssue] = []
    source_profile = profile_text(unit.source_text)
    target_profile = profile_text(translated_text)

    def issue(severity: str, code: str, message: str) -> None:
        issues.append(QaIssue(severity, code, unit.relative_file, unit.json_path, message))

    if not translated_text.strip():
        issue("error", "empty_translation", "译文为空")
    if translated_text == unit.source_text:
        issue("error", "same_as_source", "译文与韩文源文完全相同")
    elif contains_hangul(translated_text):
        issue("warning", "hangul_residue", "译文仍包含韩文字符")
    if not same_multiset(source_profile.placeholders, target_profile.placeholders):
        issue("error", "placeholder_mismatch", "占位符或换行转义不一致")
    if not same_multiset(source_profile.tags, target_profile.tags):
        issue("error", "tag_mismatch", "富文本标签不一致")
    if not same_multiset(source_profile.numbers, target_profile.numbers):
        issue("warning", "number_mismatch", "数字集合不一致")
    if source_profile.line_breaks != target_profile.line_breaks:
        issue("warning", "line_break_mismatch", "实际换行数量不一致")

    for term in match_terms(unit.source_text, glossary):
        if term.target and term.target not in translated_text:
            issue("warning", "term_miss", f"术语未命中: {term.source} => {term.target}")
    return issues


def qa_output(
    *,
    units: list[TranslationUnit],
    output_root: Path,
    glossary: list[GlossaryTerm],
) -> list[QaIssue]:
    issues: list[QaIssue] = []
    loaded: dict[str, object] = {}
    for unit in units:
        if unit.relative_file not in loaded:
            output_file = output_root / unit.relative_file
            if not output_file.exists():
                issues.append(
                    QaIssue("error", "missing_output_file", unit.relative_file, unit.json_path, "输出文件不存在")
                )
                continue
            loaded[unit.relative_file] = load_json(output_file)
        try:
            translated_text = get_path(loaded[unit.relative_file], tuple(unit.json_path.split(".")))
        except (KeyError, IndexError, ValueError):
            issues.append(QaIssue("error", "missing_output_path", unit.relative_file, unit.json_path, "输出路径不存在"))
            continue
        if not isinstance(translated_text, str):
            issues.append(QaIssue("error", "output_not_text", unit.relative_file, unit.json_path, "输出路径不是文本"))
            continue
        issues.extend(check_pair(unit, translated_text, glossary))
    return issues


def write_issues(path: Path, issues: list[QaIssue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(issue) for issue in issues], handle, ensure_ascii=False, indent=2)
        handle.write("\n")
