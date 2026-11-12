"""Configure a prepared NEW local server stack; never start services or reset users."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import stat


# Reviewed startup/permission contract at server e08bd1f7ad01854a3a4866f04eae863423d6d8b8.
# Reject changed source rather than guessing whether init still precedes user creation.
SOURCE_HASHES = {
    "docker-compose.yml": "2f30d9e8b89c4f1bdd0fa7a7e429af563b0f1577df32966157732565b305a20b",
    ".env.example": "f1aa2ef03d8420b74bd6ce1f95d58c4b41ca1575303d03ed1156aa1e2cff62dd",
    "docker/star-server-init.lisp": "d3bbad45b55910f0f6118cfff71a8a15d995c810d89a1343d73a494d48ffe29b",
    "docker/star-server-entrypoint.sh": "bd763901930f2bcb5aa302aea525792cf2e87b59dbb368bf7f2fe06ed790fcb9",
    "source/runtime-lifecycle.lisp": "afe17d6427bd7e74129e6796e81629e3d523fd1faf93d58c46d84fbcb7cad19e",
    "source/init-loader.lisp": "9c506ed791b5f917587b20ec6eb85aaaded728d6a7132d7dd1d83da49ab2ff24",
    "source/auth/users.lisp": "c04c7519a8fac383922b7aab889df543d9b1b264bb1cf7675751d2975efed6fe",
    "source/gserver-settings.lisp": "b7c8597dad499ec8244183c2a275914c33b4e06349d1ce25db8144f164cbd20e",
    "nix/images.nix": "d1209b09fb289feb4267e626191cc6881384dddc4f2cbdec7dd8fa100a5f3a2b",
}
BASE_SECRETS = {
    "couchdb_password", "couchdb_secret", "rabbitmq_password", "valkey_password",
    "auth_pepper", "auth_bootstrap_secret", "erlang_cookie",
}
LOCAL_DIR = ".starintel-local"
PASSWORD_FILE = "local_admin_password"
OVERRIDE = """# Generated only for a new local learning stack. No credential values here.
services:
  star-server:
    user: "0:0"
    entrypoint: ["/bin/sh", "-ec"]
    command:
      - |
        test -s /run/secrets/local_admin_password
        STAR_LOCAL_INITIAL_PASSWORD="$$(cat /run/secrets/local_admin_password)"
        test "$${#STAR_LOCAL_INITIAL_PASSWORD}" -eq 64
        export STAR_LOCAL_INITIAL_PASSWORD
        exec /bin/star-server-entrypoint
    environment:
      STAR_SERVER_INIT_FILE: /etc/starintel/init.lisp
    secrets:
      - local_admin_password
    volumes:
      - type: bind
        source: ./.starintel-local/init.lisp
        target: /etc/starintel/init.lisp
        read_only: true
        bind:
          create_host_path: false
secrets:
  local_admin_password:
    file: ./secrets/local_admin_password
"""
INITIAL_USER_INIT = """
;; Override image-build-time defaults before ensure-initial-user runs.
(let ((password (uiop:getenv "STAR_LOCAL_INITIAL_PASSWORD")))
  (unless (and password (= (length password) 64)
               (every (lambda (c) (find c "0123456789abcdef")) password))
    (error "Local initial administrator password is missing or invalid"))
  (setf *auth-initial-username* "local-admin"
        *auth-initial-password* password))
"""


def no_symlinks(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("Symlink paths are not supported; nothing was overwritten")


def private_file(path: Path) -> bytes:
    no_symlinks(path)
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid() or info.st_nlink != 1):
        raise ValueError("Expected an owned, private regular file from prepare_server.py")
    return path.read_bytes()


def verify_source(root: Path) -> None:
    for name, expected in SOURCE_HASHES.items():
        path = root / name
        no_symlinks(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Server startup sources differ from the reviewed pin; refusing configuration")


def create_file(path: Path, content: str, mode: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "w") as output:
        os.fchmod(output.fileno(), mode)
        output.write(content)


def configure(root: Path) -> None:
    root = root.absolute()
    no_symlinks(root)
    verify_source(root)
    for name in (
        LOCAL_DIR, "docker-compose.override.yml", "docker-compose.override.yaml",
        "compose.yml", "compose.yaml", "compose.override.yml", "compose.override.yaml",
        "docker-compose.yaml",
    ):
        if os.path.lexists(root / name):
            raise ValueError("Existing local configuration; inspect manually, nothing was changed")
    secret_dir = root / "secrets"
    no_symlinks(secret_dir)
    info = secret_dir.stat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
            or info.st_uid != os.getuid()
            or {p.name for p in secret_dir.iterdir()} != BASE_SECRETS):
        raise ValueError("Expected only the seven private base secrets from prepare_server.py")
    for name in BASE_SECRETS:
        if not private_file(secret_dir / name).strip():
            raise ValueError("Empty base secret; refusing configuration")
    env = root / ".env"
    original_env = private_file(env)
    if original_env != (root / ".env.example").read_bytes():
        raise ValueError("Expected the untouched prepared .env; inspect manually, nothing was changed")

    # Exclusive directory creation also prevents two invocations from configuring together.
    # Incomplete attempts are deliberately left for manual inspection, never reset.
    (root / LOCAL_DIR).mkdir(mode=0o755)
    (root / LOCAL_DIR).chmod(0o755)
    create_file(secret_dir / PASSWORD_FILE, secrets.token_hex(32) + "\n", 0o600)
    upstream_init = (root / "docker/star-server-init.lisp").read_text()
    create_file(root / LOCAL_DIR / "init.lisp", upstream_init + INITIAL_USER_INIT, 0o644)
    project = "starintel-local-" + secrets.token_hex(16)
    # Append only to the exact prepared file, without replacing its inode or contents.
    fd = os.open(env, os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW)
    with os.fdopen(fd, "r+b") as output:
        if output.read() != original_env:
            raise ValueError("Prepared .env changed during configuration; inspect manually")
        output.write(("\nCOMPOSE_PROJECT_NAME=" + project + "\n").encode())
    # Activate last: plain docker compose discovers this override automatically.
    create_file(root / "docker-compose.override.yml", OVERRIDE, 0o600)
    print("Configured a unique local Compose project; no service was started.")
    print("Initial username: local-admin; password: secrets/local_admin_password (private file).")
    print("Use plain docker compose from this checkout; do not override its project or init settings.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", type=Path, help="prepared, never-started server checkout")
    args = parser.parse_args()
    try:
        configure(args.server)
    except (OSError, ValueError):
        parser.exit(1, "Refused local configuration; expected an untouched prepared pinned checkout. "
                    "Inspect existing paths manually; no service was started.\n")


if __name__ == "__main__":
    main()
