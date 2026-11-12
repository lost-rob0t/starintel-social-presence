"""Print client configuration with absolute paths; never edit an existing config."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configuration(client: str) -> dict:
    command = [str(ROOT / ".venv/bin/python"), str(ROOT / "vendor/starintel-mcp/bin/starintel-mcp"), "serve"]
    environment = {"STARINTEL_WORKSPACE": str(ROOT / "workspace"), "STARINTEL_INGEST_HOSTS": ""}
    if client == "opencode":
        return {
            "$schema": "https://opencode.ai/config.json",
            "mcp": {"servers": {"starintel": {"type": "local", "command": command, "environment": environment}}},
        }
    return {"mcpServers": {"starintel": {"command": command[0], "args": command[1:], "env": environment}}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client", choices=["opencode", "claude"])
    print(json.dumps(configuration(parser.parse_args().client), indent=2))
