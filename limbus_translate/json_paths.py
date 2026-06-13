from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


TEXT_KEYS = {
    "abName",
    "add",
    "area",
    "behaveDesc",
    "chapter",
    "chaptertitle",
    "clue",
    "company",
    "content",
    "desc",
    "description",
    "dialog",
    "dlg",
    "eventDesc",
    "flavor",
    "message",
    "messageDesc",
    "min",
    "model",
    "name",
    "nameWithTitle",
    "nickName",
    "openCondition",
    "panicDescription",
    "panicName",
    "place",
    "prevDesc",
    "shortName",
    "simpleDesc",
    "story",
    "subDesc",
    "summary",
    "teller",
    "text",
    "title",
    "variation",
}


TRANSLATABLE_TEXT_KEYS = {
    "abName",
    "add",
    "area",
    "behaveDesc",
    "chapter",
    "chaptertitle",
    "clue",
    "company",
    "content",
    "desc",
    "description",
    "dialog",
    "dlg",
    "eventDesc",
    "flavor",
    "message",
    "messageDesc",
    "min",
    "name",
    "nameWithTitle",
    "nickName",
    "openCondition",
    "panicDescription",
    "panicName",
    "place",
    "shortName",
    "simpleDesc",
    "story",
    "subDesc",
    "summary",
    "teller",
    "text",
    "variation",
}


TRANSLATABLE_ARRAY_KEYS = {
    "result",
    "texts",
}


@dataclass(frozen=True)
class JsonText:
    path: tuple[str, ...]
    key: str
    value: str

    @property
    def path_id(self) -> str:
        return ".".join(self.path)


def contains_hangul(value: str) -> bool:
    return any("\uac00" <= ch <= "\ud7af" for ch in value)


def contains_cjk(value: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in value)


def iter_text_nodes(data: Any, *, text_keys: set[str] | None = None) -> Iterable[JsonText]:
    keys = text_keys or TEXT_KEYS

    def walk(node: Any, path: list[str]) -> Iterable[JsonText]:
        if isinstance(node, dict):
            for key, value in node.items():
                yield from walk(value, [*path, key])
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                yield from walk(value, [*path, str(idx)])
        elif isinstance(node, str) and path:
            key = path[-1]
            if node.strip() and (key in keys or contains_hangul(node)):
                yield JsonText(tuple(path), key, node)

    yield from walk(data, [])


def is_translatable_path(path: tuple[str, ...]) -> bool:
    if not path:
        return False
    key = path[-1]
    if key in TRANSLATABLE_TEXT_KEYS:
        return True
    return len(path) >= 2 and path[-2] in TRANSLATABLE_ARRAY_KEYS and key.isdigit()


def get_path(data: Any, path: tuple[str, ...]) -> Any:
    node = data
    for part in path:
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict):
            node = node[part]
        else:
            raise KeyError(".".join(path))
    return node


def set_path(data: Any, path: tuple[str, ...], value: Any) -> None:
    node = data
    for part in path[:-1]:
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict):
            node = node[part]
        else:
            raise KeyError(".".join(path))
    last = path[-1]
    if isinstance(node, list):
        node[int(last)] = value
    elif isinstance(node, dict):
        node[last] = value
    else:
        raise KeyError(".".join(path))
