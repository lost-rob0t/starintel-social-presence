from __future__ import annotations

import subprocess
from pathlib import Path

from .models import NormalizedChange


_FIELD = "\x1f"
_RECORD = "\x1e"


class GitError(RuntimeError):
    pass


def _run(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


class GitChangeSource:
    def __init__(self, repository: Path | str) -> None:
        self.repository = Path(repository).expanduser().resolve()
        if not (self.repository / ".git").exists():
            raise GitError(f"not a Git repository: {self.repository}")

    @property
    def identity(self) -> str:
        try:
            remote = _run(self.repository, "remote", "get-url", "origin").strip()
        except GitError:
            return self.repository.name
        if not remote:
            return self.repository.name
        value = remote.removesuffix(".git")
        if value.startswith("git@") and ":" in value:
            value = value.split(":", 1)[1]
        elif "://" in value:
            value = value.split("://", 1)[1]
            value = value.split("/", 1)[1] if "/" in value else value
        return value.strip("/")

    def changes(self, revision_range: str = "HEAD~10..HEAD", limit: int = 100) -> list[NormalizedChange]:
        if limit < 1:
            raise ValueError("limit must be positive")
        pretty = f"{_RECORD}%H{_FIELD}%aI{_FIELD}%an{_FIELD}%s"
        raw = _run(
            self.repository,
            "log",
            f"--max-count={limit}",
            f"--pretty=format:{pretty}",
            "--name-only",
            revision_range,
        )
        result: list[NormalizedChange] = []
        for chunk in raw.split(_RECORD):
            chunk = chunk.strip()
            if not chunk:
                continue
            lines = chunk.splitlines()
            fields = lines[0].split(_FIELD)
            if len(fields) != 4:
                raise GitError(f"unexpected git log record: {lines[0]!r}")
            files = tuple(line.strip() for line in lines[1:] if line.strip())
            result.append(
                NormalizedChange(
                    repository=self.identity,
                    commit=fields[0],
                    timestamp=fields[1],
                    author=fields[2],
                    message=fields[3],
                    changed_files=files,
                    comparison_range=revision_range,
                )
            )
        return result
