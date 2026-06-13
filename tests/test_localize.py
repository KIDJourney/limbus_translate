import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from limbus_translate.localize import prepare_localize_update


def test_prepare_localize_update_writes_changed_files_and_source_baseline() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "LocalizeLimbusCompany"
        repo.mkdir()
        run_git(repo, "init")
        run_git(repo, "config", "user.email", "test@example.com")
        run_git(repo, "config", "user.name", "Test User")

        (repo / "KR").mkdir()
        (repo / "LLC_zh-CN").mkdir()
        (repo / "KR" / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "예전 문장입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (repo / "LLC_zh-CN" / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "旧译文。"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        run_git(repo, "add", ".")
        run_git(repo, "commit", "-m", "base")
        base = run_git(repo, "rev-parse", "HEAD").strip()

        (repo / "KR" / "Sample.json").write_text(
            json.dumps({"dataList": [{"id": 1, "desc": "새로운 문장입니다."}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (repo / "README.md").write_text("docs\n", encoding="utf-8")
        run_git(repo, "add", ".")
        run_git(repo, "commit", "-m", "head")
        head = run_git(repo, "rev-parse", "HEAD").strip()

        update = prepare_localize_update(repo=repo, base=base, head=head, work_dir=root / "work")
        changed_files = (root / "work" / "changed-files.txt").read_text(encoding="utf-8").splitlines()
        baseline = json.loads((root / "work" / "source-baseline" / "KR" / "Sample.json").read_text(encoding="utf-8"))

    assert update.changed_count == 2
    assert update.source_baseline.endswith("source-baseline/KR")
    assert changed_files == ["KR/Sample.json", "README.md"]
    assert baseline["dataList"][0]["desc"] == "예전 문장입니다."


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout
