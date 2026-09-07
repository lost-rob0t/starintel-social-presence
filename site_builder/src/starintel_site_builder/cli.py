"""CLI entry point: python -m starintel_site_builder.cli build"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .builder import BuildReport, ExternalDocConfig, build_site


DEFAULT_EXTERNALS = (
    '[{"name":"starintel-server","repo_dir_env":"STARINTEL_SERVER_DIR",'
    '"entry":"README.org","title":"StarIntel Server"},'
    '{"name":"quasar","repo_dir_env":"STARINTEL_QUASAR_DIR",'
    '"entry":"README.md","title":"Quasar"}]'
)


def _externals_from_args(raw: str | None) -> list[ExternalDocConfig]:
    """Parse externals spec: JSON list of {name, repo_dir_env, entry, title}."""
    if raw is None:
        raw = DEFAULT_EXTERNALS
    if not raw:
        return []
    data = json.loads(raw)
    return [
        ExternalDocConfig(
            name=item["name"],
            repo_dir_env=item.get("repo_dir_env", ""),
            entry=item.get("entry", "README.md"),
            title=item.get("title", ""),
        )
        for item in data
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="starintel_site_builder", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="build the static site")
    build.add_argument("--root", default=".", type=Path, help="repository root")
    build.add_argument("--out", default="site", type=Path, help="output directory")
    build.add_argument("--build-dir", default=".build", type=Path)
    build.add_argument(
        "--externals",
        default=None,
        help="JSON list of external doc configs; pass '' for none",
    )

    args = parser.parse_args(argv)
    if args.command == "build":
        report = build_site(
            repo_root=args.root.resolve(),
            out_dir=args.out.resolve(),
            build_dir=args.build_dir.resolve(),
            externals=_externals_from_args(args.externals),
        )
        _print_report(report)
        return 0
    return 2


def _print_report(report: BuildReport) -> None:
    print(
        "site built: "
        f"{report.posts} posts, {report.drafts} drafts, "
        f"{report.docs} docs (+{report.external} external), "
        f"{report.portfolio} portfolio pages, {report.pages} pages total; "
        f"graph: {report.graph_nodes} nodes / {report.graph_edges} edges"
    )
    if report.isolated:
        print(f"isolated nodes: {', '.join(report.isolated)}")


if __name__ == "__main__":
    sys.exit(main())
