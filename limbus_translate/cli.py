from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .glossary import fetch_paratranz_terms, import_terms, read_cache, write_cache
from .memory import build_memory, read_memory, write_memory
from .providers import get_provider
from .qa import qa_output, write_issues
from .scanner import TranslationUnit, scan_missing, write_units
from .translator import overlay_existing_target, translate_units


def cmd_scan(args: argparse.Namespace) -> int:
    units = scan_missing(Path(args.source), Path(args.target), include_internal=args.include_internal)
    write_units(Path(args.output), units)
    print(f"scan complete: {len(units)} units -> {args.output}")
    by_reason: dict[str, int] = {}
    for unit in units:
        by_reason[unit.reason] = by_reason.get(unit.reason, 0) + 1
    print(json.dumps(by_reason, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_glossary_sync(args: argparse.Namespace) -> int:
    terms = fetch_paratranz_terms(project_id=args.project_id, page_size=args.page_size)
    write_cache(Path(args.output), terms)
    print(f"glossary sync complete: {len(terms)} terms -> {args.output}")
    return 0


def cmd_glossary_import(args: argparse.Namespace) -> int:
    terms = import_terms(Path(args.input))
    write_cache(Path(args.output), terms)
    print(f"glossary import complete: {len(terms)} terms -> {args.output}")
    return 0


def cmd_translate(args: argparse.Namespace) -> int:
    source = Path(args.source)
    target = Path(args.target)
    output = Path(args.output)
    units_path = Path(args.units)
    parsed_units = [TranslationUnit(**row) for row in json.loads(units_path.read_text(encoding="utf-8"))]
    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    memory = read_memory(Path(args.memory)) if args.memory else {}
    overlay_existing_target(source, target, output)
    count = translate_units(
        source_root=source,
        target_root=target,
        output_root=output,
        units=parsed_units,
        glossary=glossary,
        provider=get_provider(args.provider),
        memory=memory,
        limit=args.limit,
    )
    print(f"translate complete: {count} units -> {output}")
    return 0


def cmd_tm_build(args: argparse.Namespace) -> int:
    entries = build_memory(Path(args.source), Path(args.target))
    write_memory(Path(args.output), entries)
    print(f"tm build complete: {len(entries)} entries -> {args.output}")
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    issues = qa_output(units=units, output_root=Path(args.output_root), glossary=glossary)
    write_issues(Path(args.report), issues)
    by_severity: dict[str, int] = {}
    for issue in issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
    print(f"qa complete: {len(issues)} issues -> {args.report}")
    print(json.dumps(by_severity, ensure_ascii=False, sort_keys=True))
    return 1 if any(issue.severity == "error" for issue in issues) and args.fail_on_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="limbus-translate")
    sub = parser.add_subparsers(required=True)

    scan = sub.add_parser("scan", help="Find Korean text missing from a Chinese target tree.")
    scan.add_argument("--source", required=True, help="KR directory")
    scan.add_argument("--target", required=True, help="LLC_zh-CN directory")
    scan.add_argument("--output", default="build/missing-units.json")
    scan.add_argument("--include-internal", action="store_true", help="Include likely internal identifiers.")
    scan.set_defaults(func=cmd_scan)

    glossary = sub.add_parser("glossary", help="Sync or import glossary terms.")
    glossary_sub = glossary.add_subparsers(required=True)
    sync = glossary_sub.add_parser("sync-paratranz")
    sync.add_argument("--project-id", type=int, default=6860)
    sync.add_argument("--page-size", type=int, default=500)
    sync.add_argument("--output", default="cache/glossary/paratranz-6860.json")
    sync.set_defaults(func=cmd_glossary_sync)
    imp = glossary_sub.add_parser("import")
    imp.add_argument("--input", required=True)
    imp.add_argument("--output", default="cache/glossary/imported.json")
    imp.set_defaults(func=cmd_glossary_import)

    translate = sub.add_parser("translate", help="Translate a scan result into an output tree.")
    translate.add_argument("--source", required=True)
    translate.add_argument("--target", required=True)
    translate.add_argument("--units", default="build/missing-units.json")
    translate.add_argument("--glossary", default="")
    translate.add_argument("--memory", default="")
    translate.add_argument("--output", default="build/LLC_zh-CN")
    translate.add_argument("--provider", choices=["dry-run", "openai"], default="dry-run")
    translate.add_argument("--limit", type=int, default=None)
    translate.set_defaults(func=cmd_translate)

    tm = sub.add_parser("tm", help="Build or inspect translation memory.")
    tm_sub = tm.add_subparsers(required=True)
    tm_build = tm_sub.add_parser("build")
    tm_build.add_argument("--source", required=True)
    tm_build.add_argument("--target", required=True)
    tm_build.add_argument("--output", default="cache/tm/exact.json")
    tm_build.set_defaults(func=cmd_tm_build)

    qa = sub.add_parser("qa", help="Check translated output against source units.")
    qa.add_argument("--units", default="build/missing-units.json")
    qa.add_argument("--output-root", default="build/LLC_zh-CN")
    qa.add_argument("--glossary", default="")
    qa.add_argument("--report", default="build/qa-report.json")
    qa.add_argument("--fail-on-error", action="store_true")
    qa.set_defaults(func=cmd_qa)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
