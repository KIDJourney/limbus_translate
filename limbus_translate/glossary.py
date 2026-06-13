from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PARATRANZ_PROJECT_ID = 6860
PARATRANZ_API = "https://paratranz.cn/api/projects/{project_id}/terms"


@dataclass(frozen=True)
class GlossaryTerm:
    provider: str
    project_id: int | None
    term_id: int | None
    source_lang: str
    target_lang: str
    source: str
    target: str
    note: str
    part_of_speech: str
    variants: list[str]
    case_sensitive: bool
    created_at: str | None
    updated_at: str | None
    raw: dict[str, Any]
    fetched_at: str


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _field(raw: dict[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        if name in raw and raw[name] is not None:
            return raw[name]
    return default


def from_paratranz(raw: dict[str, Any], *, project_id: int, fetched_at: str) -> GlossaryTerm:
    variants = _field(raw, "variants", "variantsList", default=[])
    if isinstance(variants, str):
        variants = [part.strip() for part in variants.replace("\n", "|").split("|") if part.strip()]
    if not isinstance(variants, list):
        variants = []
    return GlossaryTerm(
        provider="paratranz",
        project_id=project_id,
        term_id=_field(raw, "id", "termId", default=None),
        source_lang="ko",
        target_lang="zh-cn",
        source=str(_field(raw, "term", "source", "src", default="")),
        target=str(_field(raw, "translation", "target", "dst", default="")),
        note=str(_field(raw, "note", "desc", "comment", default="")),
        part_of_speech=str(_field(raw, "pos", "partOfSpeech", default="")),
        variants=[str(item) for item in variants],
        case_sensitive=bool(_field(raw, "caseSensitive", "case_sensitive", default=False)),
        created_at=_field(raw, "createdAt", "created_at", default=None),
        updated_at=_field(raw, "updatedAt", "updated_at", default=None),
        raw=raw,
        fetched_at=fetched_at,
    )


def fetch_paratranz_terms(
    *,
    project_id: int = PARATRANZ_PROJECT_ID,
    page_size: int = 500,
    order_by: str = "-updatedAt",
    timeout: int = 30,
) -> list[GlossaryTerm]:
    terms: list[GlossaryTerm] = []
    page = 1
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    while True:
        params = urllib.parse.urlencode({"page": page, "pageSize": page_size, "orderBy": order_by})
        url = f"{PARATRANZ_API.format(project_id=project_id)}?{params}"
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload.get("results", payload if isinstance(payload, list) else [])
        if not rows:
            break
        terms.extend(from_paratranz(row, project_id=project_id, fetched_at=fetched_at) for row in rows)
        page_count = int(payload.get("pageCount", page)) if isinstance(payload, dict) else page
        if page >= page_count:
            break
        page += 1
    return terms


def import_terms(path: Path) -> list[GlossaryTerm]:
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
    terms: list[GlossaryTerm] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        variants = _field(row, "variants", default=[])
        if isinstance(variants, str):
            variants = [part.strip() for part in variants.replace("\n", "|").split("|") if part.strip()]
        terms.append(
            GlossaryTerm(
                provider=str(_field(row, "provider", default="offline")),
                project_id=_field(row, "projectId", "project_id", default=PARATRANZ_PROJECT_ID),
                term_id=_field(row, "id", "termId", "term_id", default=index),
                source_lang=str(_field(row, "sourceLang", "source_lang", default="ko")),
                target_lang=str(_field(row, "targetLang", "target_lang", default="zh-cn")),
                source=str(_field(row, "term", "source", "src", default="")),
                target=str(_field(row, "translation", "target", "dst", default="")),
                note=str(_field(row, "note", "desc", default="")),
                part_of_speech=str(_field(row, "pos", "partOfSpeech", default="")),
                variants=[str(item) for item in variants],
                case_sensitive=bool(_field(row, "caseSensitive", "case_sensitive", default=False)),
                created_at=_field(row, "createdAt", "created_at", default=None),
                updated_at=_field(row, "updatedAt", "updated_at", default=None),
                raw=row,
                fetched_at=fetched_at,
            )
        )
    return terms


def write_cache(path: Path, terms: list[GlossaryTerm]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    deduped: dict[tuple[str, str, str], GlossaryTerm] = {}
    for term in terms:
        if not term.source.strip():
            continue
        key = (term.source_lang, term.target_lang, normalize_text(term.source))
        current = deduped.get(key)
        if current is None or str(term.updated_at or "") >= str(current.updated_at or ""):
            deduped[key] = term
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(term) for term in deduped.values()], handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_cache(path: Path) -> list[GlossaryTerm]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [GlossaryTerm(**row) for row in rows]


def match_terms(text: str, terms: list[GlossaryTerm], *, limit: int = 20) -> list[GlossaryTerm]:
    matched: list[GlossaryTerm] = []
    lowered = text.lower()
    for term in terms:
        candidates = [term.source, *term.variants]
        for candidate in candidates:
            if not candidate:
                continue
            haystack = text if term.case_sensitive else lowered
            needle = candidate if term.case_sensitive else candidate.lower()
            if needle in haystack:
                matched.append(term)
                break
        if len(matched) >= limit:
            break
    return matched
