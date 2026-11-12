"""Prepare a NEW local server checkout's file secrets. Never start services or replace secrets."""
from __future__ import annotations

import argparse
from pathlib import Path
import secrets
import shutil


def prepare(root: Path) -> None:
    if not (root / "docker-compose.yml").is_file():
        raise ValueError("Expected the pinned StarIntel server checkout")
    secret_dir = root / "secrets"
    if secret_dir.exists() or (root / ".env").exists():
        raise ValueError("Existing .env or secrets directory; inspect it manually, nothing was changed")
    secret_dir.mkdir(mode=0o700)
    for name in ("couchdb_password", "couchdb_secret", "rabbitmq_password", "valkey_password", "auth_pepper", "auth_bootstrap_secret"):
        path = secret_dir / name
        with path.open("x") as output:
            path.chmod(0o600)
            output.write(secrets.token_hex(32) + "\n")
    cookie = secret_dir / "erlang_cookie"
    with cookie.open("x") as output:
        cookie.chmod(0o600)
        output.write(secrets.token_hex(24).upper() + "\n")
    shutil.copyfile(root / ".env.example", root / ".env")
    (root / ".env").chmod(0o600)
    print("Prepared private file secrets. Review .env; no service was started.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", type=Path)
    prepare(parser.parse_args().server.resolve())
