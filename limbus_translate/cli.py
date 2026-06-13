from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .evaluation import (
    apply_gold_review_csv,
    build_gold_cases,
    read_gold_cases,
    run_eval_comparison,
    run_gold_evaluation,
    sample_gold_cases,
    summarize_eval_comparison,
    summarize_eval,
    write_eval_comparison_report,
    write_eval_report,
    write_gold_cases,
    write_gold_review_pack,
)
from .glossary import fetch_paratranz_terms, import_terms, read_cache, write_cache
from .lore import import_lore, read_lore_cache, write_lore_cache
from .memory import build_memory, read_memory, write_memory
from .providers import get_provider
from .qa import qa_output, read_length_policy, summarize_issues, write_issues
from .scanner import TranslationUnit, scan_missing, write_units
from .state import UnitState, read_state, write_state
from .terms import (
    extract_term_candidates,
    get_term_refiner,
    glossary_terms_from_review_csv,
    promote_refined_terms,
    read_candidates,
    read_refined_terms,
    write_candidates,
    write_refined_terms,
    write_term_review_pack,
)
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
    lore_entries = read_lore_cache(Path(args.lore)) if args.lore else []
    states = read_state(Path(args.state)) if args.state else {}
    overlay_existing_target(source, target, output)
    count = translate_units(
        source_root=source,
        target_root=target,
        output_root=output,
        units=parsed_units,
        glossary=glossary,
        provider=get_provider(args.provider),
        memory=memory,
        lore_entries=lore_entries,
        states=states,
        limit=args.limit,
    )
    print(f"translate complete: {count} units -> {output}")
    return 0


def cmd_tm_build(args: argparse.Namespace) -> int:
    entries = build_memory(Path(args.source), Path(args.target))
    write_memory(Path(args.output), entries)
    print(f"tm build complete: {len(entries)} entries -> {args.output}")
    return 0


def cmd_lore_import(args: argparse.Namespace) -> int:
    entries = import_lore(Path(args.input))
    write_lore_cache(Path(args.output), entries)
    print(f"lore import complete: {len(entries)} entries -> {args.output}")
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    length_policy = read_length_policy(Path(args.length_policy)) if args.length_policy else None
    issues = qa_output(units=units, output_root=Path(args.output_root), glossary=glossary, length_policy=length_policy)
    write_issues(Path(args.report), issues)
    print(f"qa complete: {len(issues)} issues -> {args.report}")
    print(json.dumps(summarize_issues(issues), ensure_ascii=False, sort_keys=True))
    return 1 if any(issue.severity == "error" for issue in issues) and args.fail_on_error else 0


def cmd_terms_extract(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    candidates = extract_term_candidates(units, glossary, min_count=args.min_count)
    write_candidates(Path(args.output), candidates)
    print(f"terms extract complete: {len(candidates)} candidates -> {args.output}")
    return 0


def cmd_terms_refine(args: argparse.Namespace) -> int:
    candidates = read_candidates(Path(args.candidates))
    refined = get_term_refiner(args.provider).refine(candidates)
    write_refined_terms(Path(args.output), refined)
    by_decision: dict[str, int] = {}
    for term in refined:
        by_decision[term.decision] = by_decision.get(term.decision, 0) + 1
    print(f"terms refine complete: {len(refined)} candidates -> {args.output}")
    print(json.dumps(by_decision, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_terms_promote(args: argparse.Namespace) -> int:
    refined = read_refined_terms(Path(args.refined))
    promoted = promote_refined_terms(refined, min_confidence=args.min_confidence)
    merged = [*read_cache(Path(args.merge))] if args.merge else []
    write_cache(Path(args.output), [*merged, *promoted])
    print(f"terms promote complete: {len(promoted)} promoted -> {args.output}")
    if args.merge:
        print(f"merged with existing glossary: {len(merged)} terms")
    return 0


def cmd_terms_review_pack(args: argparse.Namespace) -> int:
    refined = read_refined_terms(Path(args.refined))
    summary = write_term_review_pack(
        Path(args.output_dir),
        refined,
        include_not_term=args.include_not_term,
        min_confidence=args.min_confidence,
    )
    print(f"terms review-pack complete: {summary['selected']} terms -> {args.output_dir}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_terms_apply_review(args: argparse.Namespace) -> int:
    reviewed = glossary_terms_from_review_csv(Path(args.review), provider=args.provider)
    merged = [*read_cache(Path(args.merge))] if args.merge else []
    write_cache(Path(args.output), [*merged, *reviewed])
    print(f"terms apply-review complete: {len(reviewed)} approved terms -> {args.output}")
    if args.merge:
        print(f"merged with existing glossary: {len(merged)} terms")
    return 0


def cmd_state_init(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    states = [
        UnitState(
            unit_id=unit.unit_id,
            source_hash=unit.source_hash,
            stable_key=unit.stable_key,
            status=args.status,
            target_text=unit.target_text if args.keep_target else None,
            note=args.note,
        )
        for unit in units
    ]
    write_state(Path(args.output), states)
    print(f"state init complete: {len(states)} states -> {args.output}")
    return 0


def cmd_eval_run(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    results = run_gold_evaluation(cases, get_provider(args.provider), min_similarity=args.min_similarity)
    write_eval_report(Path(args.report), results)
    summary = summarize_eval(results)
    print(f"eval complete: {summary['total']} cases -> {args.report}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 1 if summary["pass_rate"] < args.fail_under else 0


def cmd_eval_compare(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    providers = [(label, get_provider(spec)) for label, spec in parse_provider_specs(args.provider)]
    comparisons = run_eval_comparison(cases, providers, min_similarity=args.min_similarity)
    write_eval_comparison_report(Path(args.report), comparisons)
    summary = summarize_eval_comparison(comparisons)
    print(f"eval compare complete: {summary['providers']} providers -> {args.report}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    best = summary["rankings"][0] if summary["rankings"] else {"pass_rate": 0.0}
    return 1 if float(best["pass_rate"]) < args.fail_under else 0


def cmd_eval_build_gold(args: argparse.Namespace) -> int:
    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    cases = build_gold_cases(
        source_root=Path(args.source),
        target_root=Path(args.target),
        glossary=glossary,
        limit=args.limit,
        min_source_length=args.min_source_length,
        max_source_length=args.max_source_length,
    )
    write_gold_cases(Path(args.output), cases)
    by_tag: dict[str, int] = {}
    for case in cases:
        for tag in case.tags:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    print(f"gold build complete: {len(cases)} cases -> {args.output}")
    print(json.dumps({"by_tag": by_tag, "total": len(cases)}, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_eval_sample_gold(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    sampled = sample_gold_cases(
        cases,
        limit=args.limit,
        per_group=args.per_group,
        group_by=args.group_by,
        seed=args.seed,
    )
    write_gold_cases(Path(args.output), sampled)
    by_tag: dict[str, int] = {}
    for case in sampled:
        for tag in case.tags:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    print(f"gold sample complete: {len(sampled)} cases -> {args.output}")
    print(
        json.dumps(
            {"by_tag": dict(sorted(by_tag.items())), "group_by": args.group_by, "seed": args.seed, "total": len(sampled)},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def cmd_eval_review_pack(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    summary = write_gold_review_pack(Path(args.output_dir), cases)
    print(f"gold review-pack complete: {summary['selected']} cases -> {args.output_dir}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_eval_apply_review(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    curated = apply_gold_review_csv(Path(args.review), cases)
    write_gold_cases(Path(args.output), curated)
    print(f"gold apply-review complete: {len(curated)} approved cases -> {args.output}")
    return 0


def parse_provider_specs(values: list[str]) -> list[tuple[str, str]]:
    providers: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, value in enumerate(values, start=1):
        if "=" in value:
            label, spec = value.split("=", 1)
            label = label.strip()
            spec = spec.strip()
        else:
            spec = value.strip()
            label = spec or f"provider-{index}"
        if not label or not spec:
            raise ValueError(f"invalid provider spec: {value}")
        if label in seen:
            raise ValueError(f"duplicate provider label: {label}")
        seen.add(label)
        providers.append((label, spec))
    return providers


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
    translate.add_argument("--lore", default="")
    translate.add_argument("--state", default="")
    translate.add_argument("--output", default="build/LLC_zh-CN")
    translate.add_argument("--provider", default="dry-run")
    translate.add_argument("--limit", type=int, default=None)
    translate.set_defaults(func=cmd_translate)

    tm = sub.add_parser("tm", help="Build or inspect translation memory.")
    tm_sub = tm.add_subparsers(required=True)
    tm_build = tm_sub.add_parser("build")
    tm_build.add_argument("--source", required=True)
    tm_build.add_argument("--target", required=True)
    tm_build.add_argument("--output", default="cache/tm/exact.json")
    tm_build.set_defaults(func=cmd_tm_build)

    lore = sub.add_parser("lore", help="Import worldbuilding notes for translation context.")
    lore_sub = lore.add_subparsers(required=True)
    lore_import = lore_sub.add_parser("import")
    lore_import.add_argument("--input", required=True, help="Markdown, JSON, JSONL, CSV, TXT, or a directory.")
    lore_import.add_argument("--output", default="cache/lore/world.json")
    lore_import.set_defaults(func=cmd_lore_import)

    qa = sub.add_parser("qa", help="Check translated output against source units.")
    qa.add_argument("--units", default="build/missing-units.json")
    qa.add_argument("--output-root", default="build/LLC_zh-CN")
    qa.add_argument("--glossary", default="")
    qa.add_argument("--report", default="build/qa-report.json")
    qa.add_argument("--length-policy", default="")
    qa.add_argument("--fail-on-error", action="store_true")
    qa.set_defaults(func=cmd_qa)

    evaluation = sub.add_parser("eval", help="Run provider regression on a gold translation set.")
    eval_sub = evaluation.add_subparsers(required=True)
    eval_run = eval_sub.add_parser("run")
    eval_run.add_argument("--gold", required=True)
    eval_run.add_argument("--provider", default="dry-run")
    eval_run.add_argument("--report", default="build/eval-report.json")
    eval_run.add_argument("--min-similarity", type=float, default=0.75)
    eval_run.add_argument("--fail-under", type=float, default=0.0, help="Fail if pass_rate is below this value.")
    eval_run.set_defaults(func=cmd_eval_run)
    eval_compare = eval_sub.add_parser("compare")
    eval_compare.add_argument("--gold", required=True)
    eval_compare.add_argument(
        "--provider",
        action="append",
        required=True,
        help="Provider spec, optionally label=spec. Examples: dry=dry-run, gpt41=openai:gpt-4.1.",
    )
    eval_compare.add_argument("--report", default="build/eval-compare-report.json")
    eval_compare.add_argument("--min-similarity", type=float, default=0.75)
    eval_compare.add_argument("--fail-under", type=float, default=0.0, help="Fail if the best pass_rate is below this value.")
    eval_compare.set_defaults(func=cmd_eval_compare)
    eval_build = eval_sub.add_parser("build-gold")
    eval_build.add_argument("--source", required=True)
    eval_build.add_argument("--target", required=True)
    eval_build.add_argument("--glossary", default="")
    eval_build.add_argument("--output", default="cache/eval/gold-set.json")
    eval_build.add_argument("--limit", type=int, default=None)
    eval_build.add_argument("--min-source-length", type=int, default=2)
    eval_build.add_argument("--max-source-length", type=int, default=500)
    eval_build.set_defaults(func=cmd_eval_build_gold)
    eval_sample = eval_sub.add_parser("sample-gold")
    eval_sample.add_argument("--gold", required=True)
    eval_sample.add_argument("--output", default="cache/eval/gold-sample.json")
    eval_sample.add_argument("--limit", type=int, default=None)
    eval_sample.add_argument("--per-group", type=int, default=None)
    eval_sample.add_argument("--group-by", choices=["tag", "risk", "file"], default="tag")
    eval_sample.add_argument("--seed", type=int, default=1)
    eval_sample.set_defaults(func=cmd_eval_sample_gold)
    eval_review_pack = eval_sub.add_parser("review-pack")
    eval_review_pack.add_argument("--gold", required=True)
    eval_review_pack.add_argument("--output-dir", default="build/gold-review")
    eval_review_pack.set_defaults(func=cmd_eval_review_pack)
    eval_apply_review = eval_sub.add_parser("apply-review")
    eval_apply_review.add_argument("--gold", required=True)
    eval_apply_review.add_argument("--review", default="build/gold-review/review.csv")
    eval_apply_review.add_argument("--output", default="cache/eval/gold-curated.json")
    eval_apply_review.set_defaults(func=cmd_eval_apply_review)

    terms = sub.add_parser("terms", help="Extract and cache candidate glossary terms.")
    terms_sub = terms.add_subparsers(required=True)
    terms_extract = terms_sub.add_parser("extract")
    terms_extract.add_argument("--units", default="build/missing-units.json")
    terms_extract.add_argument("--glossary", default="")
    terms_extract.add_argument("--output", default="cache/terms/candidates.json")
    terms_extract.add_argument("--min-count", type=int, default=1)
    terms_extract.set_defaults(func=cmd_terms_extract)
    terms_refine = terms_sub.add_parser("refine")
    terms_refine.add_argument("--candidates", default="cache/terms/candidates.json")
    terms_refine.add_argument("--output", default="cache/terms/refined.json")
    terms_refine.add_argument("--provider", choices=["rules", "openai"], default="rules")
    terms_refine.set_defaults(func=cmd_terms_refine)
    terms_promote = terms_sub.add_parser("promote")
    terms_promote.add_argument("--refined", default="cache/terms/refined.json")
    terms_promote.add_argument("--output", default="cache/glossary/local-refined.json")
    terms_promote.add_argument("--merge", default="", help="Optional existing glossary cache to merge before writing.")
    terms_promote.add_argument("--min-confidence", type=float, default=0.0)
    terms_promote.set_defaults(func=cmd_terms_promote)
    terms_review_pack = terms_sub.add_parser("review-pack")
    terms_review_pack.add_argument("--refined", default="cache/terms/refined.json")
    terms_review_pack.add_argument("--output-dir", default="build/term-review")
    terms_review_pack.add_argument("--include-not-term", action="store_true")
    terms_review_pack.add_argument("--min-confidence", type=float, default=0.0)
    terms_review_pack.set_defaults(func=cmd_terms_review_pack)
    terms_apply_review = terms_sub.add_parser("apply-review")
    terms_apply_review.add_argument("--review", default="build/term-review/review.csv")
    terms_apply_review.add_argument("--output", default="cache/glossary/local-reviewed.json")
    terms_apply_review.add_argument("--merge", default="", help="Optional existing glossary cache to merge before writing.")
    terms_apply_review.add_argument("--provider", default="local-reviewed")
    terms_apply_review.set_defaults(func=cmd_terms_apply_review)

    state = sub.add_parser("state", help="Create or manage unit review state.")
    state_sub = state.add_subparsers(required=True)
    state_init = state_sub.add_parser("init")
    state_init.add_argument("--units", default="build/missing-units.json")
    state_init.add_argument("--output", default="cache/state/units.json")
    state_init.add_argument("--status", choices=["new", "reviewed", "locked"], default="new")
    state_init.add_argument("--keep-target", action="store_true")
    state_init.add_argument("--note", default="")
    state_init.set_defaults(func=cmd_state_init)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
