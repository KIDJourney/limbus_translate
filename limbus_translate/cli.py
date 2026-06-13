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
from .glossary import (
    audit_terms,
    fetch_paratranz_terms,
    import_terms,
    merge_glossary_terms,
    read_cache,
    write_audit_report,
    write_cache,
)
from .lore import (
    build_lore_index,
    import_lore,
    match_lore_index,
    read_lore_cache,
    read_lore_index,
    write_lore_cache,
    write_lore_index,
)
from .localize import make_translation_patch, prepare_localize_update, prepared_update_payload
from .memory import build_memory, evaluate_memory_retrieval, read_memory, write_memory, write_memory_evaluation_report
from .providers import get_provider
from .qa import qa_output, read_length_policy, summarize_issues, write_issues
from .review import (
    apply_translation_review_csv,
    merge_state_rows,
    read_qa_issues,
    read_state_rows,
    write_translation_review_pack,
)
from .scanner import (
    TranslationUnit,
    collect_changed_source_paths,
    read_changed_files,
    read_scan_policy,
    scan_missing,
    write_units,
)
from .state import UnitState, read_state, summarize_state_coverage, write_state
from .terms import (
    extract_term_candidates,
    get_term_refiner,
    glossary_terms_from_review_csv,
    merge_refined_term_cache,
    promote_refined_terms,
    read_candidates,
    read_refined_terms,
    refine_candidates_with_cache,
    write_candidates,
    write_refined_terms,
    write_term_review_pack,
)
from .translation_cache import (
    read_translation_cache,
    summarize_request_usage,
    write_translation_cache,
    write_translation_request_log,
    write_translation_trace,
)
from .translator import apply_state_translations, overlay_existing_target, translate_units


def cmd_scan(args: argparse.Namespace) -> int:
    source = Path(args.source)
    target = Path(args.target)
    scan_policy = read_scan_policy(Path(args.scan_policy)) if args.scan_policy else None
    include_files = (
        read_changed_files(Path(args.changed_files), source_root=source, target_root=target) if args.changed_files else None
    )
    include_source_paths = (
        collect_changed_source_paths(
            Path(args.source_baseline),
            source,
            scan_policy=scan_policy,
            include_files=include_files,
        )
        if args.source_baseline
        else None
    )
    units = scan_missing(
        source,
        target,
        include_internal=args.include_internal,
        scan_policy=scan_policy,
        include_files=include_files,
        include_source_paths=include_source_paths,
    )
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


def cmd_glossary_merge(args: argparse.Namespace) -> int:
    term_groups = [read_cache(Path(path)) for path in args.input]
    merged = merge_glossary_terms(term_groups)
    input_terms = sum(len(group) for group in term_groups)
    write_cache(Path(args.output), merged)
    print(f"glossary merge complete: {input_terms} input terms -> {len(merged)} merged terms -> {args.output}")
    print(
        json.dumps(
            {"inputs": len(args.input), "input_terms": input_terms, "merged_terms": len(merged)},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def cmd_glossary_audit(args: argparse.Namespace) -> int:
    terms = read_cache(Path(args.input))
    report = audit_terms(terms)
    write_audit_report(Path(args.report), report)
    print(f"glossary audit complete: {len(report.issues)} issues -> {args.report}")
    print(json.dumps({"by_code": report.by_code, "by_severity": report.by_severity, "total_terms": report.total_terms}, ensure_ascii=False, sort_keys=True))
    if args.fail_on == "error" and report.by_severity.get("error", 0):
        return 1
    if args.fail_on == "warning" and (report.by_severity.get("error", 0) or report.by_severity.get("warning", 0)):
        return 1
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
    lore_index = read_lore_index(Path(args.lore_index)) if args.lore_index else None
    states = read_state(Path(args.state)) if args.state else {}
    candidate_cache = read_translation_cache(Path(args.candidate_cache)) if args.candidate_cache else {}
    candidate_cache_updates = []
    request_log = []
    trace = []
    overlay_existing_target(source, target, output)
    provider = get_provider(args.provider)
    count = translate_units(
        source_root=source,
        target_root=target,
        output_root=output,
        units=parsed_units,
        glossary=glossary,
        provider=provider,
        memory=memory,
        lore_entries=lore_entries,
        lore_index=lore_index,
        states=states,
        candidate_cache=candidate_cache,
        candidate_cache_updates=candidate_cache_updates,
        request_log=request_log if args.request_log else None,
        trace=trace if args.trace else None,
        provider_name=args.provider,
        limit=args.limit,
    )
    if args.candidate_cache:
        merged_cache = dict(candidate_cache)
        for entry in candidate_cache_updates:
            merged_cache[entry.cache_key] = entry
        write_translation_cache(Path(args.candidate_cache), merged_cache)
        print(f"candidate cache updated: +{len(candidate_cache_updates)} -> {args.candidate_cache}")
    if args.trace:
        write_translation_trace(Path(args.trace), trace)
        print(f"translation trace written: {len(trace)} rows -> {args.trace}")
    if args.request_log:
        write_translation_request_log(Path(args.request_log), request_log)
        print(f"translation request log written: {len(request_log)} rows -> {args.request_log}")
    print(f"translate complete: {count} units -> {output}")
    return 0


def cmd_workflow_run(args: argparse.Namespace) -> int:
    source = Path(args.source)
    target = Path(args.target)
    output = Path(args.output)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    localize_update = None
    changed_files_arg = args.changed_files
    source_baseline_arg = args.source_baseline
    if args.localize_repo:
        localize_update = prepare_localize_update(
            repo=Path(args.localize_repo),
            base=args.localize_base,
            head=args.localize_head,
            work_dir=work_dir / "localize-update",
            language_dir=args.localize_language_dir,
        )
        if not changed_files_arg:
            changed_files_arg = localize_update.changed_files
        if not source_baseline_arg:
            source_baseline_arg = localize_update.source_baseline

    scan_policy = read_scan_policy(Path(args.scan_policy)) if args.scan_policy else None
    include_files = (
        read_changed_files(Path(changed_files_arg), source_root=source, target_root=target) if changed_files_arg else None
    )
    include_source_paths = (
        collect_changed_source_paths(
            Path(source_baseline_arg),
            source,
            scan_policy=scan_policy,
            include_files=include_files,
        )
        if source_baseline_arg
        else None
    )
    units = scan_missing(
        source,
        target,
        include_internal=args.include_internal,
        scan_policy=scan_policy,
        include_files=include_files,
        include_source_paths=include_source_paths,
    )
    units_path = work_dir / "missing-units.json"
    write_units(units_path, units)

    memory_entries = build_memory(source, target)
    tm_path = work_dir / "tm.json"
    write_memory(tm_path, memory_entries)
    memory = {entry.source_hash: entry for entry in memory_entries}

    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    glossary_audit_path: Path | None = None
    glossary_audit_summary: dict[str, object] = {}
    if glossary:
        glossary_audit = audit_terms(glossary)
        glossary_audit_path = work_dir / "glossary-audit.json"
        write_audit_report(glossary_audit_path, glossary_audit)
        glossary_audit_summary = {
            "total_terms": glossary_audit.total_terms,
            "issues": len(glossary_audit.issues),
            "by_code": glossary_audit.by_code,
            "by_severity": glossary_audit.by_severity,
        }
    states = read_state(Path(args.state)) if args.state else {}

    terms_summary: dict[str, object] = {}
    term_candidates_path: Path | None = None
    refined_terms_path: Path | None = None
    terms_cache_path: Path | None = None
    term_review_summary: dict[str, int | str] = {}
    if not args.skip_terms:
        candidates = extract_term_candidates(units, glossary, min_count=args.terms_min_count)
        term_candidates_path = work_dir / "term-candidates.json"
        write_candidates(term_candidates_path, candidates)
        cached_refined_terms = []
        if args.terms_cache:
            terms_cache_path = Path(args.terms_cache)
            cached_refined_terms = read_refined_terms(terms_cache_path) if terms_cache_path.exists() else []
        refined_terms, new_refined_terms, reused_terms = refine_candidates_with_cache(
            candidates,
            get_term_refiner(args.terms_provider),
            cached_refined_terms,
        )
        refined_terms_path = work_dir / "refined-terms.json"
        write_refined_terms(refined_terms_path, refined_terms)
        merged_refined_terms = merge_refined_term_cache(cached_refined_terms, refined_terms)
        if terms_cache_path is not None:
            write_refined_terms(terms_cache_path, merged_refined_terms)
        term_review_dir = Path(args.terms_review_dir) if args.terms_review_dir else work_dir / "term-review"
        term_review_summary = write_term_review_pack(
            term_review_dir,
            refined_terms,
            include_not_term=args.terms_include_not_term,
            min_confidence=args.terms_min_confidence,
        )
        by_decision: dict[str, int] = {}
        for term in refined_terms:
            by_decision[term.decision] = by_decision.get(term.decision, 0) + 1
        terms_summary = {
            "candidates": len(candidates),
            "refined": len(refined_terms),
            "cache": {
                "path": str(terms_cache_path) if terms_cache_path else "",
                "existing": len(cached_refined_terms),
                "reused": reused_terms if terms_cache_path is not None else 0,
                "added": len(new_refined_terms) if terms_cache_path is not None else 0,
                "total": len(merged_refined_terms) if terms_cache_path is not None else 0,
            },
            "by_decision": dict(sorted(by_decision.items())),
            "review": term_review_summary,
        }

    lore_entries = read_lore_cache(Path(args.lore)) if args.lore else []
    lore_path = Path(args.lore) if args.lore else None
    if args.lore_input:
        lore_entries = import_lore(Path(args.lore_input))
        lore_path = work_dir / "lore.json"
        write_lore_cache(lore_path, lore_entries)

    lore_index = read_lore_index(Path(args.lore_index)) if args.lore_index else None
    lore_index_path = Path(args.lore_index) if args.lore_index else None
    if lore_entries and lore_index is None:
        lore_index = build_lore_index(lore_entries, dimensions=args.lore_dimensions)
        lore_index_path = work_dir / "lore-index.json"
        write_lore_index(lore_index_path, lore_index)

    overlay_existing_target(source, target, output)
    candidate_cache_path = Path(args.candidate_cache) if args.candidate_cache else work_dir / "translation-candidates.json"
    candidate_cache = read_translation_cache(candidate_cache_path)
    candidate_cache_updates = []
    translation_request_log = []
    translation_trace = []
    provider = get_provider(args.provider)
    translated = translate_units(
        source_root=source,
        target_root=target,
        output_root=output,
        units=units,
        glossary=glossary,
        provider=provider,
        memory=memory,
        lore_entries=lore_entries,
        lore_index=lore_index,
        states=states,
        candidate_cache=candidate_cache,
        candidate_cache_updates=candidate_cache_updates,
        request_log=translation_request_log,
        trace=translation_trace,
        provider_name=args.provider,
        limit=args.limit,
    )
    merged_candidate_cache = dict(candidate_cache)
    for entry in candidate_cache_updates:
        merged_candidate_cache[entry.cache_key] = entry
    write_translation_cache(candidate_cache_path, merged_candidate_cache)
    translation_trace_path = work_dir / "translation-trace.jsonl"
    write_translation_trace(translation_trace_path, translation_trace)
    translation_request_log_path = work_dir / "translation-requests.jsonl"
    write_translation_request_log(translation_request_log_path, translation_request_log)

    length_policy = read_length_policy(Path(args.length_policy)) if args.length_policy else None
    qa_units = units[: args.limit] if args.limit is not None else units
    issues = qa_output(units=qa_units, output_root=output, glossary=glossary, length_policy=length_policy)
    qa_path = work_dir / "qa-report.json"
    write_issues(qa_path, issues)
    qa_summary = summarize_issues(issues)
    translation_review_summary = write_translation_review_pack(
        work_dir / "translation-review",
        units=qa_units,
        output_root=output,
        issues=issues,
    )

    by_reason: dict[str, int] = {}
    for unit in units:
        by_reason[unit.reason] = by_reason.get(unit.reason, 0) + 1
    summary = {
        "units": len(units),
        "translated": translated,
        "qa_issues": len(issues),
        "by_reason": dict(sorted(by_reason.items())),
        "localize_update": prepared_update_payload(localize_update) if localize_update is not None else {},
        "source_baseline": {
            "path": source_baseline_arg,
            "changed_files": len(include_source_paths or {}),
            "changed_paths": sum(len(paths) for paths in (include_source_paths or {}).values()),
        },
        "qa": qa_summary,
        "glossary_audit": glossary_audit_summary,
        "terms": terms_summary,
        "translation_review": translation_review_summary,
        "translation_cache": {
            "path": str(candidate_cache_path),
            "existing": len(candidate_cache),
            "added": len(candidate_cache_updates),
            "total": len(merged_candidate_cache),
        },
        "translation_trace": {
            "path": str(translation_trace_path),
            "rows": len(translation_trace),
        },
        "translation_requests": {
            "path": str(translation_request_log_path),
            "rows": len(translation_request_log),
            "usage": summarize_request_usage(translation_request_log),
        },
        "artifacts": {
            "units": str(units_path),
            "tm": str(tm_path),
            "glossary_audit": str(glossary_audit_path) if glossary_audit_path else "",
            "translation_candidates": str(candidate_cache_path),
            "translation_requests": str(translation_request_log_path),
            "translation_trace": str(translation_trace_path),
            "term_candidates": str(term_candidates_path) if term_candidates_path else "",
            "refined_terms": str(refined_terms_path) if refined_terms_path else "",
            "refined_terms_cache": str(terms_cache_path) if terms_cache_path else "",
            "term_review_csv": str(term_review_summary.get("review_csv", "")),
            "term_review_jsonl": str(term_review_summary.get("review_jsonl", "")),
            "term_review_paratranz_csv": str(term_review_summary.get("paratranz_csv", "")),
            "translation_review_csv": str(translation_review_summary.get("review_csv", "")),
            "translation_review_jsonl": str(translation_review_summary.get("review_jsonl", "")),
            "lore": str(lore_path) if lore_path else "",
            "lore_index": str(lore_index_path) if lore_index_path else "",
            "output": str(output),
            "qa_report": str(qa_path),
        },
    }
    summary_path = work_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"workflow complete: {translated}/{len(units)} units -> {output}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    has_error = any(issue.severity == "error" for issue in issues)
    return 1 if has_error and args.fail_on_error else 0


def cmd_workflow_finalize(args: argparse.Namespace) -> int:
    source = Path(args.source)
    target = Path(args.target)
    output = Path(args.output)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    finalize_units = units[: args.limit] if args.limit is not None else units
    states = read_state(Path(args.state))
    state_summary = summarize_state_coverage(finalize_units, states)

    overlay_existing_target(source, target, output)
    applied = apply_state_translations(
        source_root=source,
        target_root=target,
        output_root=output,
        units=finalize_units,
        states=states,
        limit=args.limit,
    )

    glossary = read_cache(Path(args.glossary)) if args.glossary else []
    length_policy = read_length_policy(Path(args.length_policy)) if args.length_policy else None
    issues = qa_output(units=finalize_units, output_root=output, glossary=glossary, length_policy=length_policy)
    qa_summary = summarize_issues(issues)

    state_status_path = work_dir / "state-status.json"
    qa_path = work_dir / "qa-report.json"
    summary_path = work_dir / "summary.json"
    state_status_path.write_text(json.dumps(state_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_issues(qa_path, issues)

    patch_result = None
    patch_output = Path(args.patch_output) if args.patch_output else work_dir / "localize-translation.patch"
    if args.localize_repo:
        patch_result = make_translation_patch(
            repo=Path(args.localize_repo),
            units=finalize_units,
            states=states,
            patch_path=patch_output,
            target_dir=args.patch_target_dir,
        )

    summary = {
        "units": len(finalize_units),
        "applied": applied,
        "qa_issues": len(issues),
        "state": state_summary,
        "qa": qa_summary,
        "localize_patch": asdict(patch_result) if patch_result is not None else {},
        "artifacts": {
            "output": str(output),
            "state_status": str(state_status_path),
            "qa_report": str(qa_path),
            "summary": str(summary_path),
            "localize_patch": str(patch_output) if patch_result is not None else "",
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"workflow finalize complete: {applied}/{len(finalize_units)} reviewed units -> {output}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    has_error = any(issue.severity == "error" for issue in issues)
    if args.fail_if_pending and state_summary["pending_units"]:
        return 1
    if args.fail_on_error and has_error:
        return 1
    return 0


def cmd_tm_build(args: argparse.Namespace) -> int:
    entries = build_memory(Path(args.source), Path(args.target))
    write_memory(Path(args.output), entries)
    print(f"tm build complete: {len(entries)} entries -> {args.output}")
    return 0


def cmd_tm_evaluate(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    memory = read_memory(Path(args.memory))
    thresholds = parse_float_list(args.thresholds)
    report = evaluate_memory_retrieval(
        cases=cases,
        memory=memory,
        top_k=args.top_k,
        min_similarity=args.min_similarity,
        thresholds=thresholds,
        include_exact=args.include_exact,
    )
    write_memory_evaluation_report(Path(args.report), report)
    summary = report["summary"]
    print(f"tm evaluate complete: {summary['with_match']}/{summary['total']} cases -> {args.report}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_lore_import(args: argparse.Namespace) -> int:
    entries = import_lore(Path(args.input))
    write_lore_cache(Path(args.output), entries)
    print(f"lore import complete: {len(entries)} entries -> {args.output}")
    return 0


def cmd_localize_prepare_update(args: argparse.Namespace) -> int:
    update = prepare_localize_update(
        repo=Path(args.repo),
        base=args.base,
        head=args.head,
        work_dir=Path(args.work_dir),
        language_dir=args.language_dir,
    )
    payload = prepared_update_payload(update)
    print(f"localize update prepared: {update.changed_count} changed files -> {args.work_dir}")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_localize_make_patch(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    result = make_translation_patch(
        repo=Path(args.repo),
        units=units,
        states=read_state(Path(args.state)),
        patch_path=Path(args.output),
        target_dir=args.target_dir,
    )
    payload = asdict(result)
    print(f"localize patch complete: {result.replacements} replacements across {len(result.changed_files)} files -> {args.output}")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_lore_index(args: argparse.Namespace) -> int:
    entries = read_lore_cache(Path(args.lore))
    index = build_lore_index(entries, dimensions=args.dimensions)
    write_lore_index(Path(args.output), index)
    print(f"lore index complete: {len(index.records)} entries -> {args.output}")
    print(json.dumps({"dimensions": index.dimensions, "entries": len(index.records)}, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_lore_search(args: argparse.Namespace) -> int:
    index = read_lore_index(Path(args.index))
    matches = match_lore_index(args.query, index, limit=args.limit)
    payload = [asdict(match) for match in matches]
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"lore search complete: {len(matches)} matches -> {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
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


def cmd_review_pack(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    issues = read_qa_issues(Path(args.qa_report)) if args.qa_report else []
    summary = write_translation_review_pack(
        Path(args.output_dir),
        units=units,
        output_root=Path(args.output_root),
        issues=issues,
    )
    print(f"review pack complete: {summary['selected']} units -> {args.output_dir}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_review_apply(args: argparse.Namespace) -> int:
    reviewed = apply_translation_review_csv(Path(args.review), status=args.status)
    existing = read_state_rows(Path(args.merge)) if args.merge else []
    states = merge_state_rows(existing, reviewed) if existing else reviewed
    write_state(Path(args.output), states)
    print(f"review apply complete: {len(reviewed)} approved units -> {args.output}")
    if args.merge:
        print(f"merged with existing state: {len(existing)} rows")
    return 0


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
    cached_refined_terms = []
    cache_path = Path(args.cache) if args.cache else None
    if cache_path is not None and cache_path.exists():
        cached_refined_terms = read_refined_terms(cache_path)
    refined, new_refined_terms, reused_terms = refine_candidates_with_cache(
        candidates,
        get_term_refiner(args.provider),
        cached_refined_terms,
    )
    write_refined_terms(Path(args.output), refined)
    if cache_path is not None:
        write_refined_terms(cache_path, merge_refined_term_cache(cached_refined_terms, refined))
    by_decision: dict[str, int] = {}
    for term in refined:
        by_decision[term.decision] = by_decision.get(term.decision, 0) + 1
    print(f"terms refine complete: {len(refined)} candidates -> {args.output}")
    if cache_path is not None:
        print(f"terms refine cache: reused={reused_terms} added={len(new_refined_terms)} -> {cache_path}")
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


def cmd_state_apply(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    source = Path(args.source)
    target = Path(args.target)
    output = Path(args.output)
    overlay_existing_target(source, target, output)
    applied = apply_state_translations(
        source_root=source,
        target_root=target,
        output_root=output,
        units=units,
        states=read_state(Path(args.state)),
        limit=args.limit,
    )
    print(f"state apply complete: {applied} reviewed units -> {args.output}")
    return 0


def cmd_state_status(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.units).read_text(encoding="utf-8"))
    units = [TranslationUnit(**row) for row in rows]
    summary = summarize_state_coverage(units, read_state(Path(args.state)))
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"state status: {summary['ready_units']}/{summary['total_units']} ready")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 1 if args.fail_if_pending and summary["pending_units"] else 0


def cmd_eval_run(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    candidate_cache_path = Path(args.candidate_cache) if args.candidate_cache else None
    candidate_cache = read_translation_cache(candidate_cache_path) if candidate_cache_path is not None else {}
    candidate_cache_updates = []
    request_log = []
    results = run_gold_evaluation(
        cases,
        get_provider(args.provider),
        min_similarity=args.min_similarity,
        provider_name=args.provider,
        candidate_cache=candidate_cache,
        candidate_cache_updates=candidate_cache_updates if candidate_cache_path is not None else None,
        request_log=request_log if args.request_log else None,
    )
    if candidate_cache_path is not None:
        merged_cache = dict(candidate_cache)
        for entry in candidate_cache_updates:
            merged_cache[entry.cache_key] = entry
        write_translation_cache(candidate_cache_path, merged_cache)
        print(f"eval candidate cache updated: +{len(candidate_cache_updates)} -> {candidate_cache_path}")
    if args.request_log:
        write_translation_request_log(Path(args.request_log), request_log)
        print(f"eval request log written: {len(request_log)} rows -> {args.request_log}")
    usage_summary = summarize_request_usage(request_log)
    write_eval_report(Path(args.report), results, usage_summary=usage_summary if args.request_log else None)
    summary = summarize_eval(results)
    if args.request_log:
        summary["usage"] = usage_summary
    print(f"eval complete: {summary['total']} cases -> {args.report}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 1 if summary["pass_rate"] < args.fail_under else 0


def cmd_eval_compare(args: argparse.Namespace) -> int:
    cases = read_gold_cases(Path(args.gold))
    provider_specs = parse_provider_specs(args.provider)
    providers = [(label, spec, get_provider(spec)) for label, spec in provider_specs]
    candidate_cache_path = Path(args.candidate_cache) if args.candidate_cache else None
    candidate_cache = read_translation_cache(candidate_cache_path) if candidate_cache_path is not None else {}
    candidate_cache_updates = []
    request_log = []
    comparisons = run_eval_comparison(
        cases,
        providers,
        min_similarity=args.min_similarity,
        candidate_cache=candidate_cache,
        candidate_cache_updates=candidate_cache_updates if candidate_cache_path is not None else None,
        request_log=request_log if args.request_log else None,
    )
    if candidate_cache_path is not None:
        merged_cache = dict(candidate_cache)
        for entry in candidate_cache_updates:
            merged_cache[entry.cache_key] = entry
        write_translation_cache(candidate_cache_path, merged_cache)
        print(f"eval candidate cache updated: +{len(candidate_cache_updates)} -> {candidate_cache_path}")
    if args.request_log:
        write_translation_request_log(Path(args.request_log), request_log)
        print(f"eval request log written: {len(request_log)} rows -> {args.request_log}")
    usage_summary = summarize_request_usage(request_log)
    write_eval_comparison_report(Path(args.report), comparisons, usage_summary=usage_summary if args.request_log else None)
    summary = summarize_eval_comparison(comparisons)
    if args.request_log:
        summary["usage"] = usage_summary
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


def parse_float_list(value: str) -> list[float]:
    items = []
    for raw in value.split(","):
        raw = raw.strip()
        if raw:
            items.append(float(raw))
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="limbus-translate")
    sub = parser.add_subparsers(required=True)

    scan = sub.add_parser("scan", help="Find Korean text missing from a Chinese target tree.")
    scan.add_argument("--source", required=True, help="KR directory")
    scan.add_argument("--target", required=True, help="LLC_zh-CN directory")
    scan.add_argument("--output", default="build/missing-units.json")
    scan.add_argument("--include-internal", action="store_true", help="Include likely internal identifiers.")
    scan.add_argument("--scan-policy", default="", help="Optional JSON policy for file/path-specific include/exclude rules.")
    scan.add_argument("--changed-files", default="", help="Optional newline-delimited changed file list from git diff --name-only.")
    scan.add_argument("--source-baseline", default="", help="Optional previous KR directory for JSON path-level source diff.")
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
    merge = glossary_sub.add_parser("merge")
    merge.add_argument(
        "--input",
        action="append",
        required=True,
        help="Glossary cache path. Later inputs override earlier terms with the same source.",
    )
    merge.add_argument("--output", default="cache/glossary/merged.json")
    merge.set_defaults(func=cmd_glossary_merge)
    audit = glossary_sub.add_parser("audit")
    audit.add_argument("--input", default="cache/glossary/paratranz-6860.json")
    audit.add_argument("--report", default="build/glossary-audit.json")
    audit.add_argument("--fail-on", choices=["never", "error", "warning"], default="never")
    audit.set_defaults(func=cmd_glossary_audit)

    translate = sub.add_parser("translate", help="Translate a scan result into an output tree.")
    translate.add_argument("--source", required=True)
    translate.add_argument("--target", required=True)
    translate.add_argument("--units", default="build/missing-units.json")
    translate.add_argument("--glossary", default="")
    translate.add_argument("--memory", default="")
    translate.add_argument("--lore", default="")
    translate.add_argument("--lore-index", default="")
    translate.add_argument("--state", default="")
    translate.add_argument("--candidate-cache", default="", help="Optional provider candidate cache JSON to read and update.")
    translate.add_argument("--trace", default="", help="Optional JSONL path for per-unit translation provenance.")
    translate.add_argument("--request-log", default="", help="Optional JSONL path for provider request payloads.")
    translate.add_argument("--output", default="build/LLC_zh-CN")
    translate.add_argument("--provider", default="dry-run")
    translate.add_argument("--limit", type=int, default=None)
    translate.set_defaults(func=cmd_translate)

    workflow = sub.add_parser("workflow", help="Run the update translation workflow end to end.")
    workflow_sub = workflow.add_subparsers(required=True)
    workflow_run = workflow_sub.add_parser("run")
    workflow_run.add_argument("--source", required=True)
    workflow_run.add_argument("--target", required=True)
    workflow_run.add_argument("--output", default="build/LLC_zh-CN")
    workflow_run.add_argument("--work-dir", default="build/workflow")
    workflow_run.add_argument("--localize-repo", default="", help="Optional LocalizeLimbusCompany checkout to prepare update inputs from.")
    workflow_run.add_argument("--localize-base", default="HEAD~1", help="Base commit for automatic Localize update preparation.")
    workflow_run.add_argument("--localize-head", default="HEAD", help="Head commit for automatic Localize update preparation.")
    workflow_run.add_argument("--localize-language-dir", default="KR", help="Source language directory archived from localize-base.")
    workflow_run.add_argument("--scan-policy", default="")
    workflow_run.add_argument("--changed-files", default="")
    workflow_run.add_argument("--source-baseline", default="")
    workflow_run.add_argument("--include-internal", action="store_true")
    workflow_run.add_argument("--glossary", default="")
    workflow_run.add_argument("--state", default="")
    workflow_run.add_argument("--candidate-cache", default="", help="Optional persistent provider candidate cache JSON.")
    workflow_run.add_argument("--lore", default="")
    workflow_run.add_argument("--lore-input", default="")
    workflow_run.add_argument("--lore-index", default="")
    workflow_run.add_argument("--lore-dimensions", type=int, default=256)
    workflow_run.add_argument("--length-policy", default="")
    workflow_run.add_argument("--provider", default="dry-run")
    workflow_run.add_argument("--terms-provider", default="rules")
    workflow_run.add_argument("--terms-cache", default="", help="Optional persistent refined term cache JSON.")
    workflow_run.add_argument("--terms-min-count", type=int, default=1)
    workflow_run.add_argument("--terms-review-dir", default="")
    workflow_run.add_argument("--terms-include-not-term", action="store_true")
    workflow_run.add_argument("--terms-min-confidence", type=float, default=0.0)
    workflow_run.add_argument("--skip-terms", action="store_true")
    workflow_run.add_argument("--limit", type=int, default=None)
    workflow_run.add_argument("--fail-on-error", action="store_true")
    workflow_run.set_defaults(func=cmd_workflow_run)
    workflow_finalize = workflow_sub.add_parser("finalize")
    workflow_finalize.add_argument("--source", required=True)
    workflow_finalize.add_argument("--target", required=True)
    workflow_finalize.add_argument("--units", default="build/missing-units.json")
    workflow_finalize.add_argument("--state", required=True)
    workflow_finalize.add_argument("--output", default="build/LLC_zh-CN-reviewed")
    workflow_finalize.add_argument("--work-dir", default="build/finalize")
    workflow_finalize.add_argument("--glossary", default="")
    workflow_finalize.add_argument("--length-policy", default="")
    workflow_finalize.add_argument("--localize-repo", default="", help="Optional LocalizeLimbusCompany checkout for git patch generation.")
    workflow_finalize.add_argument("--patch-output", default="", help="Patch path when --localize-repo is provided. Defaults to work-dir/localize-translation.patch.")
    workflow_finalize.add_argument("--patch-target-dir", default="LLC_zh-CN")
    workflow_finalize.add_argument("--limit", type=int, default=None)
    workflow_finalize.add_argument("--fail-if-pending", action="store_true")
    workflow_finalize.add_argument("--fail-on-error", action="store_true")
    workflow_finalize.set_defaults(func=cmd_workflow_finalize)

    tm = sub.add_parser("tm", help="Build or inspect translation memory.")
    tm_sub = tm.add_subparsers(required=True)
    tm_build = tm_sub.add_parser("build")
    tm_build.add_argument("--source", required=True)
    tm_build.add_argument("--target", required=True)
    tm_build.add_argument("--output", default="cache/tm/exact.json")
    tm_build.set_defaults(func=cmd_tm_build)
    tm_eval = tm_sub.add_parser("evaluate")
    tm_eval.add_argument("--memory", default="cache/tm/exact.json")
    tm_eval.add_argument("--gold", required=True)
    tm_eval.add_argument("--report", default="build/tm-eval-report.json")
    tm_eval.add_argument("--top-k", type=int, default=3)
    tm_eval.add_argument("--min-similarity", type=float, default=0.35)
    tm_eval.add_argument("--thresholds", default="0.35,0.5,0.7")
    tm_eval.add_argument("--include-exact", action="store_true")
    tm_eval.set_defaults(func=cmd_tm_evaluate)

    lore = sub.add_parser("lore", help="Import worldbuilding notes for translation context.")
    lore_sub = lore.add_subparsers(required=True)
    lore_import = lore_sub.add_parser("import")
    lore_import.add_argument("--input", required=True, help="Markdown, JSON, JSONL, CSV, TXT, or a directory.")
    lore_import.add_argument("--output", default="cache/lore/world.json")
    lore_import.set_defaults(func=cmd_lore_import)
    lore_index = lore_sub.add_parser("index")
    lore_index.add_argument("--lore", default="cache/lore/world.json")
    lore_index.add_argument("--output", default="cache/lore/world-index.json")
    lore_index.add_argument("--dimensions", type=int, default=256)
    lore_index.set_defaults(func=cmd_lore_index)
    lore_search = lore_sub.add_parser("search")
    lore_search.add_argument("--index", default="cache/lore/world-index.json")
    lore_search.add_argument("--query", required=True)
    lore_search.add_argument("--limit", type=int, default=5)
    lore_search.add_argument("--output", default="")
    lore_search.set_defaults(func=cmd_lore_search)

    localize = sub.add_parser("localize", help="Prepare inputs from a LocalizeLimbusCompany checkout.")
    localize_sub = localize.add_subparsers(required=True)
    prepare_update = localize_sub.add_parser("prepare-update")
    prepare_update.add_argument("--repo", required=True, help="LocalizeLimbusCompany checkout path.")
    prepare_update.add_argument("--base", default="HEAD~1", help="Base commit for source baseline and diff.")
    prepare_update.add_argument("--head", default="HEAD", help="Head commit for changed-file diff.")
    prepare_update.add_argument("--work-dir", default="build", help="Directory for changed-files and source-baseline.")
    prepare_update.add_argument("--language-dir", default="KR", help="Source language directory to archive from base.")
    prepare_update.set_defaults(func=cmd_localize_prepare_update)
    make_patch = localize_sub.add_parser("make-patch")
    make_patch.add_argument("--repo", required=True, help="LocalizeLimbusCompany checkout path.")
    make_patch.add_argument("--units", default="build/missing-units.json")
    make_patch.add_argument("--state", required=True, help="Reviewed or locked unit state JSON.")
    make_patch.add_argument("--output", default="build/localize-translation.patch")
    make_patch.add_argument("--target-dir", default="LLC_zh-CN")
    make_patch.set_defaults(func=cmd_localize_make_patch)

    qa = sub.add_parser("qa", help="Check translated output against source units.")
    qa.add_argument("--units", default="build/missing-units.json")
    qa.add_argument("--output-root", default="build/LLC_zh-CN")
    qa.add_argument("--glossary", default="")
    qa.add_argument("--report", default="build/qa-report.json")
    qa.add_argument("--length-policy", default="")
    qa.add_argument("--fail-on-error", action="store_true")
    qa.set_defaults(func=cmd_qa)

    review = sub.add_parser("review", help="Export and apply human translation review packs.")
    review_sub = review.add_subparsers(required=True)
    review_pack = review_sub.add_parser("pack")
    review_pack.add_argument("--units", default="build/missing-units.json")
    review_pack.add_argument("--output-root", default="build/LLC_zh-CN")
    review_pack.add_argument("--qa-report", default="build/qa-report.json")
    review_pack.add_argument("--output-dir", default="build/translation-review")
    review_pack.set_defaults(func=cmd_review_pack)
    review_apply = review_sub.add_parser("apply")
    review_apply.add_argument("--review", default="build/translation-review/review.csv")
    review_apply.add_argument("--output", default="cache/state/reviewed.json")
    review_apply.add_argument("--merge", default="", help="Optional existing state JSON to merge before writing.")
    review_apply.add_argument("--status", choices=["reviewed", "locked"], default="reviewed")
    review_apply.set_defaults(func=cmd_review_apply)

    evaluation = sub.add_parser("eval", help="Run provider regression on a gold translation set.")
    eval_sub = evaluation.add_subparsers(required=True)
    eval_run = eval_sub.add_parser("run")
    eval_run.add_argument("--gold", required=True)
    eval_run.add_argument("--provider", default="dry-run")
    eval_run.add_argument("--report", default="build/eval-report.json")
    eval_run.add_argument("--candidate-cache", default="", help="Optional provider candidate cache JSON to read and update.")
    eval_run.add_argument("--request-log", default="", help="Optional JSONL path for provider request payloads.")
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
    eval_compare.add_argument("--candidate-cache", default="", help="Optional provider candidate cache JSON to read and update.")
    eval_compare.add_argument("--request-log", default="", help="Optional JSONL path for provider request payloads.")
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
    terms_refine.add_argument("--cache", default="", help="Optional persistent refined term cache JSON to reuse and update.")
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
    state_apply = state_sub.add_parser("apply")
    state_apply.add_argument("--source", required=True)
    state_apply.add_argument("--target", required=True)
    state_apply.add_argument("--units", default="build/missing-units.json")
    state_apply.add_argument("--state", required=True)
    state_apply.add_argument("--output", default="build/LLC_zh-CN-reviewed")
    state_apply.add_argument("--limit", type=int, default=None)
    state_apply.set_defaults(func=cmd_state_apply)
    state_status = state_sub.add_parser("status")
    state_status.add_argument("--units", default="build/missing-units.json")
    state_status.add_argument("--state", required=True)
    state_status.add_argument("--report", default="")
    state_status.add_argument("--fail-if-pending", action="store_true")
    state_status.set_defaults(func=cmd_state_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
