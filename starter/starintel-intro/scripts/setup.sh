#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="${PYTHON:-python3}"
"$python" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ is required"'
"$python" "$root/scripts/fetch_sources.py" starintel-mcp starintel-client
if [[ ! -d "$root/.venv" ]]; then
  "$python" -m venv "$root/.venv"
fi
"$root/.venv/bin/python" -m pip install 'jsonschema>=4,<5' -e "$root/vendor/starintel-client"
"$root/.venv/bin/python" "$root/vendor/starintel-mcp/scripts/resolve_spec.py"
install -d -m 0700 "$root/workspace"
if [[ ! -e "$root/workspace/starintel-mcp.json" ]]; then
  install -m 0600 "$root/config/workspace-local.json" "$root/workspace/starintel-mcp.json"
fi
echo 'Ready. Run: bash scripts/local-demo.sh'
