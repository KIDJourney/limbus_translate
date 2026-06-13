.PHONY: validate-docs test smoke sync-glossary

validate-docs:
	./scripts/validate-docs.sh

test:
	python3 -c "from tests.test_scanner import test_scan_missing_detects_korean_target_and_blank_target, test_scan_aligns_data_list_by_id_when_order_changes, test_scan_reports_missing_data_list_record, test_scan_policy_includes_non_default_text_path, test_scan_policy_excludes_noise_path, test_scan_can_limit_to_changed_files, test_scan_can_limit_to_changed_source_paths_and_marks_source_changed, test_read_changed_files_normalizes_repo_paths; from tests.test_evaluation import test_gold_evaluation_passes_matching_provider, test_gold_evaluation_reports_quality_issues, test_eval_report_roundtrip, test_eval_comparison_ranks_providers, test_gold_evaluation_reuses_candidate_cache_and_logs_requests, test_eval_comparison_cache_key_uses_provider_spec_not_label, test_sample_gold_cases_is_stratified_and_repeatable, test_build_gold_cases_from_reference_tree, test_write_gold_cases_roundtrip, test_write_gold_review_pack_exports_review_files, test_apply_gold_review_csv_preserves_original_case_structure; from tests.test_glossary import test_match_terms_uses_source_and_variants, test_audit_terms_reports_conflicts_and_invalid_rows; from tests.test_lore import test_import_markdown_lore_cache_roundtrip_and_match, test_import_json_lore_uses_anchors, test_import_lore_directory_skips_readme, test_match_lore_uses_ngram_similarity_without_anchor_hit, test_lore_index_roundtrip_and_search; from tests.test_qa import test_qa_detects_placeholder_mismatch, test_qa_detects_traditional_and_length, test_qa_uses_path_specific_length_policy, test_qa_uses_display_width_policy; from tests.test_review import test_translation_review_pack_exports_qa_and_apply_review_state; from tests.test_terms import test_extract_term_candidates_excludes_known_glossary, test_rules_refiner_classifies_core_decisions, test_refined_terms_cache_roundtrip, test_refine_candidates_with_cache_reuses_existing_terms, test_get_term_refiner_resolves_supported_providers, test_promote_refined_terms_exports_only_confirmed_terms, test_write_term_review_pack_exports_review_and_paratranz_files, test_glossary_terms_from_review_csv_imports_only_approved_rows; from tests.test_translator import test_translate_appends_missing_data_list_record, test_translate_reuses_candidate_cache_and_records_trace; from tests.test_state import test_translate_skips_locked_unit; from tests.test_context import test_translate_provider_receives_structured_context, test_context_includes_cross_file_similar_memory, test_source_changed_context_includes_previous_target_text; from tests.test_providers import test_openai_compatible_chat_provider_sends_structured_prompt, test_qwen_mt_provider_uses_translation_options_without_system_message, test_qwen_translation_options_tolerates_invalid_context, test_get_provider_accepts_compatible_provider_specs, test_get_provider_rejects_missing_compatible_model; test_scan_missing_detects_korean_target_and_blank_target(); test_scan_aligns_data_list_by_id_when_order_changes(); test_scan_reports_missing_data_list_record(); test_scan_policy_includes_non_default_text_path(); test_scan_policy_excludes_noise_path(); test_scan_can_limit_to_changed_files(); test_scan_can_limit_to_changed_source_paths_and_marks_source_changed(); test_read_changed_files_normalizes_repo_paths(); test_gold_evaluation_passes_matching_provider(); test_gold_evaluation_reports_quality_issues(); test_eval_report_roundtrip(); test_eval_comparison_ranks_providers(); test_gold_evaluation_reuses_candidate_cache_and_logs_requests(); test_eval_comparison_cache_key_uses_provider_spec_not_label(); test_sample_gold_cases_is_stratified_and_repeatable(); test_build_gold_cases_from_reference_tree(); test_write_gold_cases_roundtrip(); test_write_gold_review_pack_exports_review_files(); test_apply_gold_review_csv_preserves_original_case_structure(); test_match_terms_uses_source_and_variants(); test_audit_terms_reports_conflicts_and_invalid_rows(); test_import_markdown_lore_cache_roundtrip_and_match(); test_import_json_lore_uses_anchors(); test_import_lore_directory_skips_readme(); test_match_lore_uses_ngram_similarity_without_anchor_hit(); test_lore_index_roundtrip_and_search(); test_qa_detects_placeholder_mismatch(); test_qa_detects_traditional_and_length(); test_qa_uses_path_specific_length_policy(); test_qa_uses_display_width_policy(); test_translation_review_pack_exports_qa_and_apply_review_state(); test_extract_term_candidates_excludes_known_glossary(); test_rules_refiner_classifies_core_decisions(); test_refined_terms_cache_roundtrip(); test_refine_candidates_with_cache_reuses_existing_terms(); test_get_term_refiner_resolves_supported_providers(); test_promote_refined_terms_exports_only_confirmed_terms(); test_write_term_review_pack_exports_review_and_paratranz_files(); test_glossary_terms_from_review_csv_imports_only_approved_rows(); test_translate_appends_missing_data_list_record(); test_translate_reuses_candidate_cache_and_records_trace(); test_translate_skips_locked_unit(); test_translate_provider_receives_structured_context(); test_context_includes_cross_file_similar_memory(); test_source_changed_context_includes_previous_target_text(); test_openai_compatible_chat_provider_sends_structured_prompt(); test_qwen_mt_provider_uses_translation_options_without_system_message(); test_qwen_translation_options_tolerates_invalid_context(); test_get_provider_accepts_compatible_provider_specs(); test_get_provider_rejects_missing_compatible_model(); print('direct unit tests passed')"

smoke:
	rm -rf build
	mkdir -p build
	printf 'KR/Sample.json\nREADME.md\n' > build/changed-files.txt
	python3 -m limbus_translate.cli scan \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/missing-units.json \
		--scan-policy config/scan-policy.sample.json \
		--changed-files build/changed-files.txt
	python3 -c "import json, pathlib; base=pathlib.Path('build/source-baseline/KR'); target=pathlib.Path('build/source-changed-target'); base.mkdir(parents=True, exist_ok=True); target.mkdir(parents=True, exist_ok=True); json.dump({'dataList':[{'id':1,'desc':'예전 문장입니다.'}]}, open(base/'Changed.json','w',encoding='utf-8'), ensure_ascii=False); json.dump({'dataList':[{'id':1,'desc':'旧译文。'}]}, open(target/'Changed.json','w',encoding='utf-8'), ensure_ascii=False); pathlib.Path('build/source-current').mkdir(exist_ok=True); json.dump({'dataList':[{'id':1,'desc':'새로운 문장입니다.'}]}, open('build/source-current/Changed.json','w',encoding='utf-8'), ensure_ascii=False); print('source baseline fixture ok')"
	python3 -m limbus_translate.cli scan \
		--source build/source-current \
		--target build/source-changed-target \
		--source-baseline build/source-baseline/KR \
		--output build/source-changed-units.json
	python3 -c "import json; rows=json.load(open('build/source-changed-units.json', encoding='utf-8')); assert len(rows) == 1; assert rows[0]['reason'] == 'source_changed'; assert rows[0]['target_text'] == '旧译文。'; print('source baseline scan schema ok')"
	python3 -m limbus_translate.cli tm build \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/tm.json
	python3 -m limbus_translate.cli state init \
		--units build/missing-units.json \
		--output build/state.json
	python3 -c "import json; rows=[{'provider':'fixture','project_id':6860,'term_id':1,'source_lang':'ko','target_lang':'zh-cn','source':'수감자','target':'罪人','note':'fixture','part_of_speech':'noun','variants':['수감자들'],'case_sensitive':False,'created_at':None,'updated_at':'2026-06-13T00:00:00Z','raw':{},'fetched_at':'2026-06-13T00:00:00Z'},{'provider':'fixture','project_id':6860,'term_id':2,'source_lang':'ko','target_lang':'zh-cn','source':'단테','target':'但丁','note':'fixture','part_of_speech':'noun','variants':[],'case_sensitive':False,'created_at':None,'updated_at':'2026-06-13T00:00:00Z','raw':{},'fetched_at':'2026-06-13T00:00:00Z'}]; json.dump(rows, open('build/glossary.json','w',encoding='utf-8'), ensure_ascii=False, indent=2); print('glossary fixture ok')"
	python3 -m limbus_translate.cli glossary audit \
		--input build/glossary.json \
		--report build/glossary-audit.json \
		--fail-on error
	python3 -c "import json; report=json.load(open('build/glossary-audit.json', encoding='utf-8')); assert report['total_terms'] == 2; assert report['issues'] == []; print('glossary audit schema ok')"
	python3 -m limbus_translate.cli lore import \
		--input tests/fixtures/lore \
		--output build/lore.json
	python3 -m limbus_translate.cli lore index \
		--lore build/lore.json \
		--output build/lore-index.json \
		--dimensions 64
	python3 -m limbus_translate.cli lore search \
		--index build/lore-index.json \
		--query "전투를 시작한다" \
		--output build/lore-search.json
	python3 -c "import json; rows=json.load(open('build/lore-search.json', encoding='utf-8')); assert rows; assert rows[0]['title'] == '전투'; assert rows[0]['score'] > 0; print('lore index search schema ok')"
	python3 -m limbus_translate.cli translate \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--units build/missing-units.json \
		--memory build/tm.json \
		--lore build/lore.json \
		--lore-index build/lore-index.json \
		--state build/state.json \
		--candidate-cache build/translation-candidates.json \
		--trace build/translation-trace.jsonl \
		--request-log build/translation-requests.jsonl \
		--output build/LLC_zh-CN \
		--provider dry-run
	python3 -c "import json; cache=json.load(open('build/translation-candidates.json', encoding='utf-8')); trace=[json.loads(line) for line in open('build/translation-trace.jsonl', encoding='utf-8') if line.strip()]; requests=[json.loads(line) for line in open('build/translation-requests.jsonl', encoding='utf-8') if line.strip()]; assert len(cache) == 2; assert len(trace) == 2; assert len(requests) == 2; assert all(row['translation_source'] == 'provider' for row in trace); assert all(row['cache_key'] for row in trace); assert all(row['cache_key'] and row['source_text'] and row['target_text'] and row['context'] and 'glossary' in row and 'usage' in row for row in requests); print('translation cache, request log, and trace schema ok')"
	python3 -m limbus_translate.cli qa \
		--units build/missing-units.json \
		--output-root build/LLC_zh-CN \
		--report build/qa-report.json \
		--length-policy config/length-policy.sample.json
	python3 -m limbus_translate.cli review pack \
		--units build/missing-units.json \
		--output-root build/LLC_zh-CN \
		--qa-report build/qa-report.json \
		--output-dir build/translation-review
	python3 -c "import csv, json; review=list(csv.DictReader(open('build/translation-review/review.csv', encoding='utf-8-sig'))); jsonl=[json.loads(line) for line in open('build/translation-review/review.jsonl', encoding='utf-8') if line.strip()]; assert len(review) == len(jsonl) == 2; assert all('source_text' in row and 'proposed_text' in row and 'qa_codes' in row for row in review); print('translation review pack schema ok')"
	python3 -c "import csv; rows=list(csv.DictReader(open('build/translation-review/review.csv', encoding='utf-8-sig'))); assert rows; rows[0]['approved']='yes'; rows[0]['revised_target']='审校后的译文。'; fields=list(rows[0].keys()); handle=open('build/translation-review/approved-review.csv', 'w', encoding='utf-8-sig', newline=''); writer=csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.close(); print('approved translation review fixture ok')"
	python3 -m limbus_translate.cli review apply \
		--review build/translation-review/approved-review.csv \
		--output build/reviewed-state.json
	python3 -c "import json; rows=json.load(open('build/reviewed-state.json', encoding='utf-8')); assert len(rows) == 1; assert rows[0]['status'] == 'reviewed'; assert rows[0]['target_text'] == '审校后的译文。'; print('reviewed state schema ok')"
	python3 -m limbus_translate.cli eval build-gold \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/gold-set.json
	python3 -m limbus_translate.cli eval sample-gold \
		--gold build/gold-set.json \
		--output build/gold-sample.json \
		--per-group 1 \
		--group-by tag \
		--seed 7
	python3 -c "import json; rows=json.load(open('build/gold-sample.json', encoding='utf-8'))['cases']; assert rows; assert len(rows) <= 2; print('gold sample schema ok')"
	python3 -m limbus_translate.cli eval review-pack \
		--gold build/gold-sample.json \
		--output-dir build/gold-review
	python3 -c "import csv, json; review=list(csv.DictReader(open('build/gold-review/review.csv', encoding='utf-8-sig'))); jsonl=[json.loads(line) for line in open('build/gold-review/review.jsonl', encoding='utf-8') if line.strip()]; assert len(review) == len(jsonl); assert review and all('case_id' in row and 'approved' in row and 'revised_expected_text' in row for row in review); print('gold review pack schema ok')"
	python3 -c "import csv; rows=list(csv.DictReader(open('build/gold-review/review.csv', encoding='utf-8-sig'))); assert rows; rows[0]['approved']='yes'; rows[0]['revised_expected_text']=rows[0]['expected_text']; fields=list(rows[0].keys()); handle=open('build/gold-review/approved-review.csv', 'w', encoding='utf-8-sig', newline=''); writer=csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.close(); print('approved gold review fixture ok')"
	python3 -m limbus_translate.cli eval apply-review \
		--gold build/gold-sample.json \
		--review build/gold-review/approved-review.csv \
		--output build/gold-curated.json
	python3 -c "import json; rows=json.load(open('build/gold-curated.json', encoding='utf-8'))['cases']; assert len(rows) == 1; assert rows[0]['case_id']; assert rows[0]['expected_text']; print('curated gold schema ok')"
	python3 -m limbus_translate.cli eval run \
		--gold build/gold-set.json \
		--provider dry-run \
		--candidate-cache build/eval-candidates.json \
		--request-log build/eval-requests.jsonl \
		--report build/eval-report.json
	python3 -m limbus_translate.cli eval compare \
		--gold build/gold-sample.json \
		--provider baseline=dry-run \
		--provider candidate=dry-run \
		--candidate-cache build/eval-compare-candidates.json \
		--request-log build/eval-compare-requests.jsonl \
		--report build/eval-compare-report.json
	python3 -c "import json; cache=json.load(open('build/eval-candidates.json', encoding='utf-8')); requests=[json.loads(line) for line in open('build/eval-requests.jsonl', encoding='utf-8') if line.strip()]; eval_report=json.load(open('build/eval-report.json', encoding='utf-8')); compare_cache=json.load(open('build/eval-compare-candidates.json', encoding='utf-8')); compare_requests=[json.loads(line) for line in open('build/eval-compare-requests.jsonl', encoding='utf-8') if line.strip()]; report=json.load(open('build/eval-compare-report.json', encoding='utf-8')); assert cache and requests and all(row['provider'] == 'dry-run' for row in cache); assert all(row['target_text'] and 'usage' in row and row['response_model'] == 'dry-run' for row in requests); assert eval_report['summary']['usage']['requests'] == len(requests); assert eval_report['summary']['usage']['by_model']['dry-run']['requests'] == len(requests); assert compare_cache and compare_requests; assert {row['provider'] for row in compare_cache} == {'dry-run'}; assert all(row['target_text'] and 'usage' in row for row in compare_requests); assert report['summary']['providers'] == 2; assert report['summary']['usage']['requests'] == len(compare_requests); assert [row['provider'] for row in report['summary']['rankings']] == ['baseline','candidate']; assert len(report['providers']) == 2; print('eval cache, request log, usage, and compare schema ok')"
	python3 -m limbus_translate.cli terms extract \
		--units build/missing-units.json \
		--output build/term-candidates.json
	python3 -m limbus_translate.cli terms refine \
		--candidates build/term-candidates.json \
		--output build/refined-terms.json \
		--cache build/refined-terms-cache.json \
		--provider rules
	python3 -c "import json; rows=json.load(open('build/refined-terms.json', encoding='utf-8')); cache=json.load(open('build/refined-terms-cache.json', encoding='utf-8')); required={'source','decision','confidence','provider','contexts','count','sample_text','reason'}; assert isinstance(rows, list); assert len(cache) == len(rows); assert all(required <= set(row) for row in rows); assert all(row['decision'] in {'term','not_term','needs_review'} for row in rows); assert all(row['provider'] == 'rules' for row in rows); print('refined terms schema ok')"
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
	python3 -m limbus_translate.cli workflow run \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/workflow/LLC_zh-CN \
		--work-dir build/workflow \
		--scan-policy config/scan-policy.sample.json \
		--changed-files build/changed-files.txt \
		--glossary build/glossary.json \
		--lore-input tests/fixtures/lore \
		--terms-cache build/workflow/refined-terms-cache.json \
		--length-policy config/length-policy.sample.json \
		--provider dry-run
	python3 -c "import json; summary=json.load(open('build/workflow/summary.json', encoding='utf-8')); assert summary['units'] == 2; assert summary['translated'] == 2; assert summary['artifacts']['lore_index']; assert summary['artifacts']['glossary_audit']; assert summary['artifacts']['translation_candidates']; assert summary['artifacts']['translation_requests']; assert summary['artifacts']['translation_trace']; assert summary['artifacts']['term_candidates']; assert summary['artifacts']['refined_terms']; assert summary['artifacts']['refined_terms_cache']; assert summary['artifacts']['term_review_csv']; assert summary['artifacts']['translation_review_csv']; assert summary['artifacts']['translation_review_jsonl']; assert summary['glossary_audit']['total_terms'] == 2; assert summary['glossary_audit']['issues'] == 0; assert summary['translation_cache']['added'] == 2; assert summary['translation_cache']['total'] == 2; assert summary['translation_requests']['rows'] == 2; assert summary['translation_requests']['usage']['requests'] == 2; assert summary['translation_requests']['usage']['by_model']['dry-run']['requests'] == 2; assert summary['translation_trace']['rows'] == 2; assert summary['translation_review']['selected'] == 2; assert summary['terms']['candidates'] == 3; assert summary['terms']['refined'] == 3; assert summary['terms']['cache']['added'] == 3; assert summary['terms']['cache']['total'] == 3; assert summary['qa_issues'] == 2; print('workflow summary schema ok')"

sync-glossary:
	python3 -m limbus_translate.cli glossary sync-paratranz \
		--project-id 6860 \
		--output cache/glossary/paratranz-6860.json
