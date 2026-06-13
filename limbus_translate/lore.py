from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .glossary import GlossaryTerm


@dataclass(frozen=True)
class LoreEntry:
    title: str
    text: str
    tags: list[str]
    source: str
    anchors: list[str]
    raw: dict[str, Any]


@dataclass(frozen=True)
class LoreMatch:
    title: str
    text: str
    tags: list[str]
    source: str
    anchors: list[str]
    score: float


def import_lore(path: Path) -> list[LoreEntry]:
    if path.is_dir():
        entries: list[LoreEntry] = []
        for child in sorted(path.rglob("*")):
            if child.name.lower() == "readme.md":
                continue
            if child.is_file() and child.suffix.lower() in {".md", ".json", ".jsonl", ".csv", ".txt"}:
                entries.extend(import_lore(child))
        return entries
    suffix = path.suffix.lower()
    if suffix == ".md":
        return _import_markdown(path)
    if suffix == ".json":
        return _import_json(path)
    if suffix == ".jsonl":
        return _import_jsonl(path)
    if suffix == ".csv":
        return _import_csv(path)
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8").strip()
        return [_entry(title=path.stem, text=text, source=str(path), raw={})] if text else []
    return []


def write_lore_cache(path: Path, entries: list[LoreEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    deduped: dict[tuple[str, str], LoreEntry] = {}
    for entry in entries:
        if not entry.title.strip() or not entry.text.strip():
            continue
        deduped[(entry.source, entry.title)] = entry
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(entry) for entry in deduped.values()], handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_lore_cache(path: Path) -> list[LoreEntry]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [_entry_from_row(row, default_source=str(path)) for row in rows if isinstance(row, dict)]


def match_lore(
    text: str,
    entries: list[LoreEntry],
    *,
    terms: list[GlossaryTerm] | None = None,
    limit: int = 5,
    max_text_length: int = 600,
) -> list[LoreMatch]:
    query = _norm(text)
    matched_terms = [term for term in terms or [] if term.source and _norm(term.source) in query]
    idf = _corpus_idf([_entry_search_text(entry) for entry in entries])
    scored: list[tuple[float, LoreEntry]] = []
    for entry in entries:
        score = _entry_score(query, entry, matched_terms, idf)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1].source, item[1].title))
    return [
        LoreMatch(
            title=entry.title,
            text=_clip(entry.text, max_text_length),
            tags=entry.tags,
            source=entry.source,
            anchors=entry.anchors,
            score=round(score, 4),
        )
        for score, entry in scored[:limit]
    ]


def _entry_score(query: str, entry: LoreEntry, terms: list[GlossaryTerm], idf: dict[str, float]) -> float:
    score = 0.0
    fields = [_norm(entry.title), *(_norm(tag) for tag in entry.tags), *(_norm(anchor) for anchor in entry.anchors)]
    lore_text = _entry_search_text(entry)
    for field in fields:
        if field and field in query:
            score += 2.0 if len(field) >= 2 else 0.5
    for term in terms:
        term_values = [term.source, term.target, *term.variants]
        if any(_norm(value) and _norm(value) in lore_text for value in term_values):
            score += 1.0
    if _shared_token_score(query, lore_text) >= 2:
        score += 0.5
    similarity = _tfidf_similarity(query, lore_text, idf)
    if similarity >= 0.08:
        score += similarity
    return score


def _import_markdown(path: Path) -> list[LoreEntry]:
    text = path.read_text(encoding="utf-8")
    sections: list[tuple[str, list[str]]] = []
    current_title = path.stem
    current_lines: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if heading:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = heading.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    entries = []
    for title, lines in sections:
        body = "\n".join(lines).strip()
        if body:
            entries.append(_entry(title=title, text=body, source=str(path), raw={"format": "markdown"}))
    return entries


def _import_json(path: Path) -> list[LoreEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("entries", payload) if isinstance(payload, dict) else payload
    return [_entry_from_row(row, default_source=str(path)) for row in rows if isinstance(row, dict)]


def _import_jsonl(path: Path) -> list[LoreEntry]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            entries.append(_entry_from_row(row, default_source=str(path)))
    return entries


def _import_csv(path: Path) -> list[LoreEntry]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [_entry_from_row(row, default_source=str(path)) for row in csv.DictReader(handle)]


def _entry_from_row(row: dict[str, Any], *, default_source: str) -> LoreEntry:
    return _entry(
        title=str(row.get("title") or row.get("name") or row.get("term") or ""),
        text=str(row.get("text") or row.get("body") or row.get("description") or row.get("note") or ""),
        tags=_list_field(row.get("tags", [])),
        source=str(row.get("source") or row.get("source_path") or default_source),
        anchors=_list_field(row.get("anchors", [])),
        raw=dict(row),
    )


def _entry(
    *,
    title: str,
    text: str,
    source: str,
    raw: dict[str, Any],
    tags: list[str] | None = None,
    anchors: list[str] | None = None,
) -> LoreEntry:
    title = title.strip()
    text = text.strip()
    inferred = [title, *_extract_anchor_markers(text)]
    return LoreEntry(
        title=title,
        text=text,
        tags=[item for item in tags or [] if item],
        source=source,
        anchors=[item for item in [*(anchors or []), *inferred] if item],
        raw=raw,
    )


def _extract_anchor_markers(text: str) -> list[str]:
    anchors: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(("anchors:", "keywords:", "키워드:", "关键词:")):
            _, value = stripped.split(":", 1)
            anchors.extend(_list_field(value))
    return anchors


def _list_field(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,，|/]", value) if part.strip()]
    return []


def _shared_token_score(left: str, right: str) -> int:
    left_tokens = {token for token in re.split(r"\s+", left) if len(token) >= 2}
    right_tokens = {token for token in re.split(r"\s+", right) if len(token) >= 2}
    return len(left_tokens & right_tokens)


def _entry_search_text(entry: LoreEntry) -> str:
    return _norm(f"{entry.title} {' '.join(entry.tags)} {' '.join(entry.anchors)} {entry.text}")


def _corpus_idf(texts: list[str]) -> dict[str, float]:
    document_count = len(texts)
    document_frequency: Counter[str] = Counter()
    for text in texts:
        document_frequency.update(set(_char_ngrams(text)))
    if document_count == 0:
        return {}
    return {token: math.log((document_count + 1) / (count + 1)) + 1.0 for token, count in document_frequency.items()}


def _tfidf_similarity(left: str, right: str, idf: dict[str, float]) -> float:
    left_vector = _tfidf_vector(left, idf)
    right_vector = _tfidf_vector(right, idf)
    if not left_vector or not right_vector:
        return 0.0
    dot = sum(weight * right_vector.get(token, 0.0) for token, weight in left_vector.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left_vector.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right_vector.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _tfidf_vector(text: str, idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(_char_ngrams(text))
    return {token: count * idf.get(token, 1.0) for token, count in counts.items()}


def _char_ngrams(text: str) -> list[str]:
    compact = re.sub(r"[^\w\uac00-\ud7af\u4e00-\u9fff]+", "", text.lower())
    grams: list[str] = []
    for size in (2, 3):
        if len(compact) >= size:
            grams.extend(compact[index : index + size] for index in range(0, len(compact) - size + 1))
    return grams


def _clip(text: str, limit: int) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 3, 0)].rstrip() + "..."


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())
