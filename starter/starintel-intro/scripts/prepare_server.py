"""Prepare a NEW local server checkout's file secrets. Never start services or replace secrets."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import shutil


def prepare(root: Path) -> None:
    if not (root / "docker-compose.yml").is_file():
        raise ValueError("Expected the pinned StarIntel server checkout")
    secret_dir = root / "secrets"
    if os.path.lexists(secret_dir) or os.path.lexists(root / ".env"):
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
    descriptor = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        with (root / ".env.example").open("rb") as source:
            shutil.copyfileobj(source, output)
    print("Prepared private file secrets. Review .env; no service was started.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", type=Path)
    prepare(parser.parse_args().server.resolve())
