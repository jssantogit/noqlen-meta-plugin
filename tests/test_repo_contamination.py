from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

CHECKER = Path(__file__).parents[1] / "scripts" / "check_repo_contamination.py"


def load_checker() -> dict[str, Any]:
    return runpy.run_path(str(CHECKER))


def test_personal_path_detectors_do_not_match_their_source() -> None:
    patterns = load_checker()["PERSONAL_PATH_PATTERNS"]

    assert not any(pattern.search(CHECKER.read_text(encoding="utf-8")) for pattern in patterns)


def test_checker_detects_synthetic_personal_path(tmp_path: Path, capsys) -> None:
    contaminated_file = tmp_path / "synthetic.txt"
    contaminated_file.write_text("/" + "home/example-user/music/", encoding="utf-8")
    checker = load_checker()
    main = checker["main"]
    main.__globals__["tracked_files"] = lambda: [contaminated_file]

    assert main() == 1
    assert f"personal path pattern found: {contaminated_file}" in capsys.readouterr().out
