from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .formatting import profile_text, same_multiset
from .glossary import GlossaryTerm, match_terms
from .json_paths import contains_hangul, get_path
from .scanner import TranslationUnit, load_json

TRADITIONAL_CHARS = set("體臺與為國門風龍後復發幾無萬廣東關開時會來對個聲長見點說這裡")
MQM_CATEGORY_BY_CODE = {
    "empty_translation": "accuracy",
    "same_as_source": "accuracy",
    "hangul_residue": "accuracy",
    "missing_output_file": "accuracy",
    "missing_output_path": "accuracy",
    "output_not_text": "accuracy",
    "term_miss": "terminology",
    "placeholder_mismatch": "format",
    "tag_mismatch": "format",
    "number_mismatch": "format",
    "line_break_mismatch": "format",
    "traditional_chinese": "locale_convention",
    "length_ratio_high": "design",
    "length_ratio_low": "design",
    "line_too_long": "design",
}


@dataclass(frozen=True)
class QaIssue:
    severity: str
    code: str
    relative_file: str
    json_path: str
    message: str
    category: str = "other"


def mqm_category(code: str) -> str:
    return MQM_CATEGORY_BY_CODE.get(code, "other")


@dataclass(frozen=True)
class LengthPolicy:
    max_line_length: int = 80
    max_ratio: float = 2.2
    min_ratio: float = 0.25
    min_source_length: int = 10


@dataclass(frozen=True)
class LengthPolicyRule:
    name: str
    policy: LengthPolicy
    relative_file: str = ""
    relative_file_prefix: str = ""
    json_path_suffix: str = ""
    risk: str = ""


@dataclass(frozen=True)
class LengthPolicySet:
    default: LengthPolicy
    rules: list[LengthPolicyRule]

    def policy_for(self, unit: TranslationUnit) -> LengthPolicy:
        for rule in self.rules:
            if rule_matches(rule, unit):
                return rule.policy
        return self.default


DEFAULT_LENGTH_POLICY_SET = LengthPolicySet(default=LengthPolicy(), rules=[])


def rule_matches(rule: LengthPolicyRule, unit: TranslationUnit) -> bool:
    if rule.relative_file and unit.relative_file != rule.relative_file:
        return False
    if rule.relative_file_prefix and not unit.relative_file.startswith(rule.relative_file_prefix):
        return False
    if rule.json_path_suffix and not unit.json_path.endswith(rule.json_path_suffix):
        return False
    if rule.risk and unit.risk != rule.risk:
        return False
    return True


def read_length_policy(path: Path) -> LengthPolicySet:
    if not path.exists():
        return DEFAULT_LENGTH_POLICY_SET
    payload = json.loads(path.read_text(encoding="utf-8"))
    default = _policy_from_raw(payload.get("default", {}) if isinstance(payload, dict) else {})
    rules: list[LengthPolicyRule] = []
    for row in payload.get("rules", []) if isinstance(payload, dict) else []:
        if not isinstance(row, dict):
            continue
        rules.append(
            LengthPolicyRule(
                name=str(row.get("name", "")),
                policy=_policy_from_raw(row, base=default),
                relative_file=str(row.get("relative_file", "")),
                relative_file_prefix=str(row.get("relative_file_prefix", "")),
                json_path_suffix=str(row.get("json_path_suffix", "")),
                risk=str(row.get("risk", "")),
            )
        )
    return LengthPolicySet(default=default, rules=rules)


def _policy_from_raw(raw: dict[str, Any], *, base: LengthPolicy | None = None) -> LengthPolicy:
    base = base or LengthPolicy()
    return LengthPolicy(
        max_line_length=int(raw.get("max_line_length", base.max_line_length)),
        max_ratio=float(raw.get("max_ratio", base.max_ratio)),
        min_ratio=float(raw.get("min_ratio", base.min_ratio)),
        min_source_length=int(raw.get("min_source_length", base.min_source_length)),
    )


def check_pair(
    unit: TranslationUnit,
    translated_text: str,
    glossary: list[GlossaryTerm],
    *,
    length_policy: LengthPolicySet | None = None,
) -> list[QaIssue]:
    issues: list[QaIssue] = []
    source_profile = profile_text(unit.source_text)
    target_profile = profile_text(translated_text)
    policy = (length_policy or DEFAULT_LENGTH_POLICY_SET).policy_for(unit)

    def issue(severity: str, code: str, message: str) -> None:
        issues.append(QaIssue(severity, code, unit.relative_file, unit.json_path, message, mqm_category(code)))

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
    traditional_hits = sorted({ch for ch in translated_text if ch in TRADITIONAL_CHARS})
    if traditional_hits:
        issue("warning", "traditional_chinese", f"疑似包含繁体字: {''.join(traditional_hits[:10])}")
    if len(unit.source_text) >= policy.min_source_length:
        ratio = len(translated_text) / max(len(unit.source_text), 1)
        if ratio > policy.max_ratio:
            issue("warning", "length_ratio_high", f"译文长度比例过高: {ratio:.2f}")
        elif ratio < policy.min_ratio:
            issue("warning", "length_ratio_low", f"译文长度比例过低: {ratio:.2f}")
    longest_line = max((len(line) for line in translated_text.splitlines()), default=len(translated_text))
    if longest_line > policy.max_line_length:
        issue("warning", "line_too_long", f"最长行 {longest_line} 字，超过策略上限 {policy.max_line_length}")

    for term in match_terms(unit.source_text, glossary):
        if term.target and term.target not in translated_text:
            issue("warning", "term_miss", f"术语未命中: {term.source} => {term.target}")
    return issues


def qa_output(
    *,
    units: list[TranslationUnit],
    output_root: Path,
    glossary: list[GlossaryTerm],
    length_policy: LengthPolicySet | None = None,
) -> list[QaIssue]:
    issues: list[QaIssue] = []
    loaded: dict[str, object] = {}
    for unit in units:
        if unit.relative_file not in loaded:
            output_file = output_root / unit.relative_file
            if not output_file.exists():
                issues.append(
                    QaIssue(
                        "error",
                        "missing_output_file",
                        unit.relative_file,
                        unit.json_path,
                        "输出文件不存在",
                        mqm_category("missing_output_file"),
                    )
                )
                continue
            loaded[unit.relative_file] = load_json(output_file)
        try:
            translated_text = get_path(loaded[unit.relative_file], tuple(unit.json_path.split(".")))
        except (KeyError, IndexError, ValueError):
            issues.append(
                QaIssue(
                    "error",
                    "missing_output_path",
                    unit.relative_file,
                    unit.json_path,
                    "输出路径不存在",
                    mqm_category("missing_output_path"),
                )
            )
            continue
        if not isinstance(translated_text, str):
            issues.append(
                QaIssue(
                    "error",
                    "output_not_text",
                    unit.relative_file,
                    unit.json_path,
                    "输出路径不是文本",
                    mqm_category("output_not_text"),
                )
            )
            continue
        issues.extend(check_pair(unit, translated_text, glossary, length_policy=length_policy))
    return issues


def summarize_issues(issues: list[QaIssue]) -> dict[str, dict[str, int]]:
    summary = {"by_severity": {}, "by_category": {}, "by_code": {}}
    for issue in issues:
        summary["by_severity"][issue.severity] = summary["by_severity"].get(issue.severity, 0) + 1
        summary["by_category"][issue.category] = summary["by_category"].get(issue.category, 0) + 1
        summary["by_code"][issue.code] = summary["by_code"].get(issue.code, 0) + 1
    for values in summary.values():
        ordered = dict(sorted(values.items()))
        values.clear()
        values.update(ordered)
    return summary


def write_issues(path: Path, issues: list[QaIssue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(issue) for issue in issues], handle, ensure_ascii=False, indent=2)
        handle.write("\n")
