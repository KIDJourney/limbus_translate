import json
from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.evaluation import GoldCase
from limbus_translate.formatting import text_hash
from limbus_translate.memory import MemoryEntry, evaluate_memory_retrieval, write_memory_evaluation_report


def test_evaluate_memory_retrieval_scores_fuzzy_matches_and_thresholds() -> None:
    cases = [
        GoldCase(
            case_id="story-1",
            source_text="단테가 전투를 시작했다.",
            expected_text="但丁开始了战斗。",
        ),
        GoldCase(
            case_id="story-2",
            source_text="버스가 멈췄다.",
            expected_text="巴士停下了。",
        ),
    ]
    memory = {
        "exact": MemoryEntry(
            source_hash=text_hash("단테가 전투를 시작했다."),
            source_text="단테가 전투를 시작했다.",
            target_text="不应使用 exact。",
            relative_file="Story.json",
            json_path="dataList.0.content",
        ),
        "similar": MemoryEntry(
            source_hash=text_hash("단테가 전투를 개시했다."),
            source_text="단테가 전투를 개시했다.",
            target_text="但丁开始了战斗。",
            relative_file="Story.json",
            json_path="dataList.1.content",
        ),
        "unrelated": MemoryEntry(
            source_hash=text_hash("수감자가 웃었다."),
            source_text="수감자가 웃었다.",
            target_text="罪人笑了。",
            relative_file="Other.json",
            json_path="dataList.0.content",
        ),
    }

    report = evaluate_memory_retrieval(
        cases=cases,
        memory=memory,
        min_similarity=0.5,
        thresholds=[0.5, 0.8],
    )

    assert report["summary"]["total"] == 2
    assert report["summary"]["with_match"] == 1
    assert report["summary"]["coverage"] == 0.5
    assert report["summary"]["thresholds"][0]["matches"] == 1
    assert report["cases"][0]["matches"][0]["source_text"] == "단테가 전투를 개시했다."
    assert report["cases"][0]["matches"][0]["target_similarity"] == 1.0
    assert report["cases"][1]["matches"] == []
    assert all(match["target_text"] != "不应使用 exact。" for match in report["cases"][0]["matches"])

    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "tm-eval.json"
        write_memory_evaluation_report(path, report)
        loaded = json.loads(path.read_text(encoding="utf-8"))

    assert loaded["summary"]["with_match"] == 1
