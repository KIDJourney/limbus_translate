.PHONY: validate-docs test smoke sync-glossary

validate-docs:
	./scripts/validate-docs.sh

test:
	python3 -c "from tests.test_scanner import test_scan_missing_detects_korean_target_and_blank_target, test_scan_aligns_data_list_by_id_when_order_changes, test_scan_reports_missing_data_list_record; from tests.test_evaluation import test_gold_evaluation_passes_matching_provider, test_gold_evaluation_reports_quality_issues, test_eval_report_roundtrip, test_build_gold_cases_from_reference_tree, test_write_gold_cases_roundtrip; from tests.test_glossary import test_match_terms_uses_source_and_variants; from tests.test_lore import test_import_markdown_lore_cache_roundtrip_and_match, test_import_json_lore_uses_anchors, test_import_lore_directory_skips_readme, test_match_lore_uses_ngram_similarity_without_anchor_hit; from tests.test_qa import test_qa_detects_placeholder_mismatch, test_qa_detects_traditional_and_length, test_qa_uses_path_specific_length_policy, test_qa_uses_display_width_policy; from tests.test_terms import test_extract_term_candidates_excludes_known_glossary, test_rules_refiner_classifies_core_decisions, test_refined_terms_cache_roundtrip, test_get_term_refiner_resolves_supported_providers, test_promote_refined_terms_exports_only_confirmed_terms, test_write_term_review_pack_exports_review_and_paratranz_files, test_glossary_terms_from_review_csv_imports_only_approved_rows; from tests.test_translator import test_translate_appends_missing_data_list_record; from tests.test_state import test_translate_skips_locked_unit; from tests.test_context import test_translate_provider_receives_structured_context, test_context_includes_cross_file_similar_memory; test_scan_missing_detects_korean_target_and_blank_target(); test_scan_aligns_data_list_by_id_when_order_changes(); test_scan_reports_missing_data_list_record(); test_gold_evaluation_passes_matching_provider(); test_gold_evaluation_reports_quality_issues(); test_eval_report_roundtrip(); test_build_gold_cases_from_reference_tree(); test_write_gold_cases_roundtrip(); test_match_terms_uses_source_and_variants(); test_import_markdown_lore_cache_roundtrip_and_match(); test_import_json_lore_uses_anchors(); test_import_lore_directory_skips_readme(); test_match_lore_uses_ngram_similarity_without_anchor_hit(); test_qa_detects_placeholder_mismatch(); test_qa_detects_traditional_and_length(); test_qa_uses_path_specific_length_policy(); test_qa_uses_display_width_policy(); test_extract_term_candidates_excludes_known_glossary(); test_rules_refiner_classifies_core_decisions(); test_refined_terms_cache_roundtrip(); test_get_term_refiner_resolves_supported_providers(); test_promote_refined_terms_exports_only_confirmed_terms(); test_write_term_review_pack_exports_review_and_paratranz_files(); test_glossary_terms_from_review_csv_imports_only_approved_rows(); test_translate_appends_missing_data_list_record(); test_translate_skips_locked_unit(); test_translate_provider_receives_structured_context(); test_context_includes_cross_file_similar_memory(); print('direct unit tests passed')"

smoke:
	python3 -m limbus_translate.cli scan \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/missing-units.json
	python3 -m limbus_translate.cli tm build \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/tm.json
	python3 -m limbus_translate.cli state init \
		--units build/missing-units.json \
		--output build/state.json
	python3 -m limbus_translate.cli lore import \
		--input tests/fixtures/lore \
		--output build/lore.json
	python3 -m limbus_translate.cli translate \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--units build/missing-units.json \
		--memory build/tm.json \
		--lore build/lore.json \
		--state build/state.json \
		--output build/LLC_zh-CN \
		--provider dry-run
	python3 -m limbus_translate.cli qa \
		--units build/missing-units.json \
		--output-root build/LLC_zh-CN \
		--report build/qa-report.json \
		--length-policy config/length-policy.sample.json
	python3 -m limbus_translate.cli eval build-gold \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/gold-set.json
	python3 -m limbus_translate.cli eval run \
		--gold build/gold-set.json \
		--provider dry-run \
		--report build/eval-report.json
	python3 -m limbus_translate.cli terms extract \
		--units build/missing-units.json \
		--output build/term-candidates.json
	python3 -m limbus_translate.cli terms refine \
		--candidates build/term-candidates.json \
		--output build/refined-terms.json \
		--provider rules
	python3 -c "import json; rows=json.load(open('build/refined-terms.json', encoding='utf-8')); required={'source','decision','confidence','provider','contexts','count','sample_text','reason'}; assert isinstance(rows, list); assert all(required <= set(row) for row in rows); assert all(row['decision'] in {'term','not_term','needs_review'} for row in rows); assert all(row['provider'] == 'rules' for row in rows); print('refined terms schema ok')"
	python3 -m limbus_translate.cli terms review-pack \
		--refined build/refined-terms.json \
		--output-dir build/term-review
	python3 -c "import csv, json; review=list(csv.DictReader(open('build/term-review/review.csv', encoding='utf-8-sig'))); importable=list(csv.DictReader(open('build/term-review/paratranz-import.csv', encoding='utf-8-sig'))); jsonl=[json.loads(line) for line in open('build/term-review/review.jsonl', encoding='utf-8') if line.strip()]; assert len(review) == len(jsonl); assert all('source' in row and 'target' in row and 'approved' in row for row in review); assert all(row.get('term') and row.get('translation') for row in importable); print('term review pack schema ok')"
	python3 -c "import csv; rows=list(csv.DictReader(open('build/term-review/review.csv', encoding='utf-8-sig'))); assert rows; rows[0]['target']='审校译名'; rows[0]['approved']='yes'; fields=list(rows[0].keys()); handle=open('build/term-review/approved-review.csv', 'w', encoding='utf-8-sig', newline=''); writer=csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.close(); print('approved review fixture ok')"
	python3 -m limbus_translate.cli terms apply-review \
		--review build/term-review/approved-review.csv \
		--output build/local-reviewed-glossary.json
	python3 -c "import json; rows=json.load(open('build/local-reviewed-glossary.json', encoding='utf-8')); assert len(rows) == 1; assert rows[0]['provider'] == 'local-reviewed'; assert rows[0]['target'] == '审校译名'; print('reviewed glossary schema ok')"
	python3 -m limbus_translate.cli terms promote \
		--refined build/refined-terms.json \
		--output build/local-refined-glossary.json
	python3 -c "import json; rows=json.load(open('build/local-refined-glossary.json', encoding='utf-8')); assert isinstance(rows, list); assert all(row['provider'] == 'local-refined' for row in rows); print('promoted glossary schema ok')"

sync-glossary:
	python3 -m limbus_translate.cli glossary sync-paratranz \
		--project-id 6860 \
		--output cache/glossary/paratranz-6860.json
