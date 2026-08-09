from __future__ import annotations

import subprocess
from pathlib import Path

from starintel_change_fetcher import GitChangeSource


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def test_normalizes_git_history(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Tester")
    git(repo, "config", "user.email", "tester@example.invalid")
    git(repo, "remote", "add", "origin", "git@github.com:lost-rob0t/example.git")

    (repo / "README.md").write_text("one\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "first")
    first = git(repo, "rev-parse", "HEAD")

    (repo / "README.md").write_text("two\n")
    (repo / "new.txt").write_text("new\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "second")

    changes = GitChangeSource(repo).changes(f"{first}..HEAD")
    assert len(changes) == 1
    assert changes[0].repository == "lost-rob0t/example"
    assert changes[0].message == "second"
    assert changes[0].changed_files == ("README.md", "new.txt")
    assert changes[0].comparison_range == f"{first}..HEAD"
