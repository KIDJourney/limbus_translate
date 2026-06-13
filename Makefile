.PHONY: validate-docs test smoke sync-glossary

validate-docs:
	./scripts/validate-docs.sh

test:
	python3 -c "from tests.test_scanner import test_scan_missing_detects_korean_target_and_blank_target; from tests.test_glossary import test_match_terms_uses_source_and_variants; test_scan_missing_detects_korean_target_and_blank_target(); test_match_terms_uses_source_and_variants(); print('direct unit tests passed')"

smoke:
	python3 -m limbus_translate.cli scan \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--output build/missing-units.json
	python3 -m limbus_translate.cli translate \
		--source tests/fixtures/localize/KR \
		--target tests/fixtures/localize/LLC_zh-CN \
		--units build/missing-units.json \
		--output build/LLC_zh-CN \
		--provider dry-run

sync-glossary:
	python3 -m limbus_translate.cli glossary sync-paratranz \
		--project-id 6860 \
		--output cache/glossary/paratranz-6860.json
