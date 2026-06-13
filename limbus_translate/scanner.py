from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .formatting import looks_internal_identifier, profile_text, text_hash
from .json_paths import contains_hangul, get_path, is_translatable_path, iter_text_nodes


@dataclass(frozen=True)
class TranslationUnit:
    unit_id: str
    relative_file: str
    json_path: str
    source_text: str
    target_text: str | None
    reason: str
    source_hash: str
    target_hash: str | None
    placeholders: list[str]
    tags: list[str]
    numbers: list[str]
    line_breaks: int
    risk: str
    source_json_path: str = ""
    stable_key: str | None = None


@dataclass(frozen=True)
class ScanPolicyRule:
    name: str
    action: str
    relative_file: str = ""
    relative_file_prefix: str = ""
    json_path: str = ""
    json_path_suffix: str = ""
    key: str = ""
    source_contains: list[str] | None = None
    risk: str = ""


@dataclass(frozen=True)
class ScanPolicy:
    rules: list[ScanPolicyRule]

    def decision_for(self, relative_file: str, json_path: str, key: str, source_text: str) -> ScanPolicyRule | None:
        for rule in self.rules:
            if scan_policy_rule_matches(rule, relative_file, json_path, key, source_text):
                return rule
        return None


DEFAULT_SCAN_POLICY = ScanPolicy(rules=[])


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_scan_policy(path: Path) -> ScanPolicy:
    if not path.exists():
        return DEFAULT_SCAN_POLICY
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules: list[ScanPolicyRule] = []
    for row in payload.get("rules", []) if isinstance(payload, dict) else []:
        if not isinstance(row, dict):
            continue
        action = str(row.get("action", "")).strip().lower()
        if action not in {"include", "exclude"}:
            continue
        raw_contains = row.get("source_contains", [])
        if isinstance(raw_contains, str):
            source_contains = [raw_contains]
        elif isinstance(raw_contains, list):
            source_contains = [str(item) for item in raw_contains if str(item)]
        else:
            source_contains = []
        rules.append(
            ScanPolicyRule(
                name=str(row.get("name", "")),
                action=action,
                relative_file=str(row.get("relative_file", "")),
                relative_file_prefix=str(row.get("relative_file_prefix", "")),
                json_path=str(row.get("json_path", "")),
                json_path_suffix=str(row.get("json_path_suffix", "")),
                key=str(row.get("key", "")),
                source_contains=source_contains,
                risk=str(row.get("risk", "")),
            )
        )
    return ScanPolicy(rules=rules)


def read_changed_files(path: Path, *, source_root: Path, target_root: Path) -> set[str]:
    if not path.exists():
        return set()
    relative_files: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        normalized = normalize_changed_file(value, source_root=source_root, target_root=target_root)
        if normalized:
            relative_files.add(normalized)
    return relative_files


def normalize_changed_file(value: str, *, source_root: Path, target_root: Path) -> str:
    path = value.strip().replace("\\", "/")
    if not path or not path.endswith(".json"):
        return ""
    prefixes = [source_root.name, target_root.name, "KR", "LLC_zh-CN"]
    for prefix in prefixes:
        marker = f"{prefix}/"
        if path.startswith(marker):
            return path[len(marker) :]
    return path.lstrip("/")


def scan_policy_rule_matches(
    rule: ScanPolicyRule,
    relative_file: str,
    json_path: str,
    key: str,
    source_text: str,
) -> bool:
    if rule.relative_file and relative_file != rule.relative_file:
        return False
    if rule.relative_file_prefix and not relative_file.startswith(rule.relative_file_prefix):
        return False
    if rule.json_path and json_path != rule.json_path:
        return False
    if rule.json_path_suffix and not json_path.endswith(rule.json_path_suffix):
        return False
    if rule.key and key != rule.key:
        return False
    if rule.source_contains and not any(marker in source_text for marker in rule.source_contains):
        return False
    return True


def build_unit_id(relative_file: str, json_path: str, source_text: str) -> str:
    raw = f"{relative_file}\0{json_path}\0{source_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def get_data_list_match(data: Any, path: tuple[str, ...]) -> tuple[tuple[str, ...], int, tuple[str, ...], Any] | None:
    for index, part in enumerate(path[:-1]):
        if part != "dataList" or index + 1 >= len(path):
            continue
        record_index_part = path[index + 1]
        if not record_index_part.isdigit():
            continue
        prefix = path[: index + 1]
        record_index = int(record_index_part)
        try:
            records = get_path(data, prefix)
            record = records[record_index]
        except (KeyError, IndexError, ValueError, TypeError):
            return None
        if isinstance(record, dict) and "id" in record and record["id"] not in {-1, "-1", None, ""}:
            return prefix, record_index, path[index + 2 :], record["id"]
    return None


def id_is_unique(records: Any, record_id: Any) -> bool:
    if not isinstance(records, list):
        return False
    return sum(1 for record in records if isinstance(record, dict) and record.get("id") == record_id) == 1


def id_count(records: Any, record_id: Any) -> int:
    if not isinstance(records, list):
        return 0
    return sum(1 for record in records if isinstance(record, dict) and record.get("id") == record_id)


def resolve_target_path_by_id(source_data: Any, target_data: Any, source_path: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    match = get_data_list_match(source_data, source_path)
    if match is None:
        return "path", source_path
    prefix, _record_index, suffix, record_id = match
    try:
        source_records = get_path(source_data, prefix)
    except (KeyError, IndexError, ValueError):
        return "path", source_path
    if not id_is_unique(source_records, record_id):
        return "path", source_path
    try:
        target_records = get_path(target_data, prefix)
    except (KeyError, IndexError, ValueError):
        return "missing_record", source_path
    target_count = id_count(target_records, record_id)
    if target_count == 0:
        return "missing_record", source_path
    if target_count > 1:
        return "path", source_path
    if not isinstance(target_records, list):
        return "missing_record", source_path
    for idx, record in enumerate(target_records):
        if isinstance(record, dict) and record.get("id") == record_id:
            return "id", (*prefix, str(idx), *suffix)
    return "missing_record", source_path


def build_stable_key(source_data: Any, source_path: tuple[str, ...]) -> str | None:
    match = get_data_list_match(source_data, source_path)
    if match is None:
        return None
    prefix, _record_index, suffix, record_id = match
    suffix_text = ".".join(suffix)
    base = f"{'.'.join(prefix)}[id={record_id}]"
    return f"{base}.{suffix_text}" if suffix_text else base


def classify_risk(relative_file: str, json_path: str, source_text: str) -> str:
    if relative_file.startswith("StoryData/") or ".content" in json_path or ".dlg" in json_path:
        return "high"
    if ".desc" in json_path or ".message" in json_path or ".story" in json_path:
        return "medium"
    if looks_internal_identifier(source_text):
        return "internal"
    return "low"


def is_script_direction(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith("//"):
        return True
    if stripped in {"(더미)", "더미"}:
        return True
    if "에피소드" in stripped and ("S" in stripped or "_" in stripped):
        return True
    return False


def should_suppress_same_source(relative_file: str, json_path: str, source_text: str) -> bool:
    key = json_path.split(".")[-1]
    if key in {"name", "title", "subDesc", "prevDesc", "teller", "summary"} and looks_internal_identifier(source_text):
        return True
    if key == "subDesc" and any(marker in source_text for marker in ["사용 안하는", "subDesc"]):
        return True
    if key == "summary" and source_text in {"표시용"}:
        return True
    if key == "name" and any(marker in source_text for marker in ["선택지", "이벤트", "버프 이름", "사용하지않는", "번역x"]):
        return True
    if key == "name" and any(marker in source_text for marker in ["이펙트", "효과"]):
        return True
    if key == "desc" and source_text in {"사용 안하는 텍스트", "적 잡몹", "더미"}:
        return True
    if key == "desc" and any(marker in source_text for marker in ["표시용", "번역해주세요"]):
        return True
    if key == "desc" and looks_internal_identifier(source_text):
        return True
    if key == "desc" and relative_file.startswith("BattleSpeechBubbleDlg"):
        return True
    if key == "content" and is_script_direction(source_text):
        return True
    return False


def scan_missing(
    source_root: Path,
    target_root: Path,
    *,
    include_internal: bool = False,
    scan_policy: ScanPolicy | None = None,
    include_files: set[str] | None = None,
) -> list[TranslationUnit]:
    units: list[TranslationUnit] = []
    policy = scan_policy or DEFAULT_SCAN_POLICY
    for source_file in sorted(source_root.rglob("*.json")):
        relative = source_file.relative_to(source_root).as_posix()
        if include_files is not None and relative not in include_files:
            continue
        target_file = target_root / relative
        source_data = load_json(source_file)
        target_data = load_json(target_file) if target_file.exists() else None
        for text_node in iter_text_nodes(source_data):
            policy_rule = policy.decision_for(relative, text_node.path_id, text_node.key, text_node.value)
            if policy_rule is not None and policy_rule.action == "exclude":
                continue
            if not is_translatable_path(text_node.path) and not (policy_rule is not None and policy_rule.action == "include"):
                continue
            if not contains_hangul(text_node.value):
                continue
            target_text: str | None = None
            reason = "missing_target_file"
            target_path = text_node.path
            target_path_mode = "path"
            if target_data is not None:
                target_path_mode, target_path = resolve_target_path_by_id(source_data, target_data, text_node.path)
                if target_path_mode == "missing_record":
                    reason = "missing_target_record"
                    target_path = text_node.path
                    candidate = None
                else:
                    candidate = None
                try:
                    if target_path_mode != "missing_record":
                        candidate = get_path(target_data, target_path)
                    if isinstance(candidate, str):
                        target_text = candidate
                        if candidate.strip() and candidate != text_node.value:
                            continue
                        if candidate == text_node.value and not include_internal:
                            if should_suppress_same_source(relative, text_node.path_id, text_node.value):
                                continue
                        reason = "target_same_as_source" if candidate.strip() else "missing_target_text"
                    else:
                        if target_path_mode != "missing_record":
                            reason = "target_path_not_text"
                except (KeyError, IndexError, ValueError):
                    reason = "missing_target_path"
            risk = policy_rule.risk if policy_rule is not None and policy_rule.risk else classify_risk(relative, text_node.path_id, text_node.value)
            source_profile = profile_text(text_node.value)
            units.append(
                TranslationUnit(
                    unit_id=build_unit_id(relative, text_node.path_id, text_node.value),
                    relative_file=relative,
                    json_path=".".join(target_path),
                    source_text=text_node.value,
                    target_text=target_text,
                    reason=reason,
                    source_hash=source_profile.source_hash,
                    target_hash=text_hash(target_text) if target_text is not None else None,
                    placeholders=source_profile.placeholders,
                    tags=source_profile.tags,
                    numbers=source_profile.numbers,
                    line_breaks=source_profile.line_breaks,
                    risk=risk,
                    source_json_path=text_node.path_id,
                    stable_key=build_stable_key(source_data, text_node.path),
                )
            )
    return units


def write_units(path: Path, units: list[TranslationUnit]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(unit) for unit in units]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
