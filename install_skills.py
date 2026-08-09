#!/usr/bin/env python3
"""Install repository-local StarIntel editorial skills for supported agents."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"


@dataclass(frozen=True)
class Target:
    name: str
    destination: Path
    project_local: bool


def _agent_zero_destination() -> Path:
    root = os.environ.get("A0_USR", "/a0/usr")
    return Path(root).expanduser() / "skills"


def targets() -> dict[str, Target]:
    return {
        "codex": Target("codex", ROOT / ".agents" / "skills", True),
        "opencode": Target("opencode", ROOT / ".opencode" / "skills", True),
        "claude": Target("claude", ROOT / ".claude" / "skills", True),
        "agent-zero": Target("agent-zero", _agent_zero_destination(), False),
    }


def skill_dirs() -> list[Path]:
    return sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))


def destination_for(target: Target, override: Path | None) -> Path:
    return override.expanduser().resolve() if override else target.destination


def describe(target: Target, destination: Path) -> str:
    scope = "project" if target.project_local else "external"
    return f"{target.name}: {destination} ({scope})"


def copy_skill(source: Path, dest_root: Path, *, force: bool, dry_run: bool) -> str:
    dest = dest_root / source.name
    if dest.is_symlink() or dest.exists():
        if dest.is_symlink() and dest.resolve() == source.resolve():
            return f"unchanged symlink {dest}"
        if dest.is_dir() and not dest.is_symlink():
            source_files = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
            dest_files = {p.relative_to(dest): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            if source_files == dest_files:
                return f"unchanged copy {dest}"
        if not force:
            raise FileExistsError(f"refusing to overwrite {dest}; use --force")
        if not dry_run:
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
    if not dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
    return f"copy {source} -> {dest}"


def symlink_skill(source: Path, dest_root: Path, *, force: bool, dry_run: bool) -> str:
    dest = dest_root / source.name
    if dest.is_symlink() and dest.resolve() == source.resolve():
        return f"unchanged symlink {dest}"
    if dest.exists() or dest.is_symlink():
        if not force:
            raise FileExistsError(f"refusing to overwrite {dest}; use --force")
        if not dry_run:
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
    if not dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(source, target_is_directory=True)
    return f"symlink {source} -> {dest}"


def install(
    names: Iterable[str],
    *,
    mode: str,
    override: Path | None,
    force: bool,
    dry_run: bool,
) -> list[str]:
    known = targets()
    operations: list[str] = []
    for name in names:
        target = known[name]
        destination = destination_for(target, override)
        operations.append(describe(target, destination))
        for source in skill_dirs():
            op = (
                copy_skill(source, destination, force=force, dry_run=dry_run)
                if mode == "copy"
                else symlink_skill(source, destination, force=force, dry_run=dry_run)
            )
            operations.append(op)
    return operations


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--list", action="store_true", help="list skills and supported targets")
    p.add_argument(
        "--target",
        action="append",
        choices=sorted(targets()),
        help="installation target; repeat to install to several",
    )
    p.add_argument("--destination", type=Path, help="override destination (single target only)")
    p.add_argument("--mode", choices=("copy", "symlink"), default="copy")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="replace an existing differing skill directory")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    known = targets()

    if args.list:
        print("skills:")
        for skill in skill_dirs():
            print(f"  {skill.name}")
        print("targets:")
        for target in known.values():
            print(f"  {describe(target, target.destination)}")
        if not args.target:
            return 0

    selected = args.target or []
    if not selected:
        parser().error("choose at least one --target, or use --list")
    if args.destination and len(selected) != 1:
        parser().error("--destination requires exactly one --target")

    try:
        for line in install(
            selected,
            mode=args.mode,
            override=args.destination,
            force=args.force,
            dry_run=args.dry_run,
        ):
            print(line)
    except (FileExistsError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
