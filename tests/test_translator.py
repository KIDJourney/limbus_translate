from pathlib import Path
import json
import tempfile

from limbus_translate.providers import DryRunProvider
from limbus_translate.scanner import scan_missing
from limbus_translate.translator import overlay_existing_target, translate_units


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def translate(self, request) -> str:
        self.calls += 1
        return "缓存译文。"


def test_translate_appends_missing_data_list_record() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        output = root / "out"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps(
                {
                    "dataList": [
                        {"id": 1, "desc": "이미 있음."},
                        {"id": 2, "desc": "새 기록입니다.", "name": "새 기록"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "已有。"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)
        overlay_existing_target(source, target, output)
        count = translate_units(
            source_root=source,
            target_root=target,
            output_root=output,
            units=units,
            glossary=[],
            provider=DryRunProvider(),
        )
        data = json.loads((output / "Sample.json").read_text(encoding="utf-8"))
    assert count == 2
    assert [row["id"] for row in data["dataList"]] == [1, 2]
    appended = data["dataList"][1]
    assert appended["desc"].startswith("[待译]")


def test_translate_reuses_candidate_cache_and_records_trace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "KR"
        target = root / "LLC_zh-CN"
        first_output = root / "out1"
        second_output = root / "out2"
        source.mkdir()
        target.mkdir()
        (source / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "새 문장입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (target / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": ""}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        units = scan_missing(source, target)

        provider = CountingProvider()
        cache_updates = []
        first_request_log = []
        first_trace = []
        overlay_existing_target(source, target, first_output)
        first_count = translate_units(
            source_root=source,
            target_root=target,
            output_root=first_output,
            units=units,
            glossary=[],
            provider=provider,
            candidate_cache={},
            candidate_cache_updates=cache_updates,
            request_log=first_request_log,
            trace=first_trace,
            provider_name="counting",
        )

        cache = {entry.cache_key: entry for entry in cache_updates}
        second_provider = CountingProvider()
        second_updates = []
        second_request_log = []
        second_trace = []
        overlay_existing_target(source, target, second_output)
        second_count = translate_units(
            source_root=source,
            target_root=target,
            output_root=second_output,
            units=units,
            glossary=[],
            provider=second_provider,
            candidate_cache=cache,
            candidate_cache_updates=second_updates,
            request_log=second_request_log,
            trace=second_trace,
            provider_name="counting",
        )

        data = json.loads((second_output / "Sample.json").read_text(encoding="utf-8"))

    assert first_count == second_count == 1
    assert provider.calls == 1
    assert second_provider.calls == 0
    assert len(cache_updates) == 1
    assert second_updates == []
    assert len(first_request_log) == 1
    assert first_request_log[0].cache_key == cache_updates[0].cache_key
    assert first_request_log[0].provider == "counting"
    assert first_request_log[0].source_text == "새 문장입니다."
    assert first_request_log[0].context
    assert first_request_log[0].glossary == []
    assert second_request_log == []
    assert first_trace[0].translation_source == "provider"
    assert second_trace[0].translation_source == "candidate_cache"
    assert data["dataList"][0]["desc"] == "缓存译文。"
